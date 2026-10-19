import os
import json
from dotenv import load_dotenv
from langchain_community.retrievers import BM25Retriever
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_classic.retrievers import EnsembleRetriever
import warnings

from typing import Optional
from pydantic import BaseModel, Field

warnings.filterwarnings("ignore")
"""
Hybrid RAG Retrieval by Louis C Trevino 2026

This program will perform RAG by running hybrid (semantic / BM25 keyword) retrievals.  
"""
load_dotenv()
PINECONE_IDX = os.environ["PINECONE_INDEX_NAME"]
PINECONE_NS = os.environ["PINECONE_NAMESPACE"]

embeddings = OpenAIEmbeddings(model="text-embedding-3-small", dimensions=512) 

# Vector DB
pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
index = pc.Index(PINECONE_IDX)

vector_store = PineconeVectorStore(
    index=index,
    embedding=embeddings,
    namespace=PINECONE_NS,
)

vector_retriever = vector_store.as_retriever(search_kwargs={"k": 3})

# BM25 search
with open("kb_washers_01.json") as f:
    kb = json.load(f)

raw_docs = [
    Document(page_content=entry["content"], metadata=entry["metadata"])
    for entry in kb
]

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=150,      # chunk size (characters)
    chunk_overlap=50,   # chunk overlap (characters)
    add_start_index=True,
)
docs = text_splitter.split_documents(raw_docs)
# print(f"{len(raw_docs)} documents -> {len(docs)} chunks for BM25")

# Instantiate BM25Retriever with Top-k = 3
bm25_retriever = BM25Retriever.from_documents(docs)
bm25_retriever.k = 3 


# Instantiate LLM
llm = ChatOpenAI(model="gpt-4.1-mini")

template = """You are a customer support specialist for MegaWasher, a washing machine company.
Use the context below to help resolve the customer's qustion.

If the context doesn't contain the answer, state that you don't have that information rather than guessing.
Be concise and practical: state the likely cause and the next step the agent should take.

Context:
{context}

Customer issue: {question}

Support guidance:"""

rag_prompt_template = PromptTemplate.from_template(template)


# Doc Fusion
ensemble_retriever = EnsembleRetriever(
    retrievers=[vector_retriever, bm25_retriever],
    weights=[0.5, 0.5],  # equal weight to semantic and keyword search
)

print("\n*** Welcome to MegaWasher FAQ Tool ***")

# Helper: show docs for BM25 Keywords, Semantic and Fused retrievals.
def show_hybrid(query):
    vector_docs = vector_retriever.invoke(query)
    bm25_docs = bm25_retriever.invoke(query)
    fused_docs = ensemble_retriever.invoke(query)

    print(f"QUERY: {query}\n")
    # print("Citations - semantic:")
    for doc in vector_docs:
        m = doc.metadata
        # print(f"   [{m['doc_type']}/{m['product_area']}] {m['title']}")
    # print("\nCitations - BM25 (keyword):")
    for doc in bm25_docs:
        m = doc.metadata
        # print(f"   [{m['doc_type']}/{m['product_area']}] {m['title']}")
    print("\nCitations:")
    for doc in fused_docs:
        m = doc.metadata
        print(f"   [{m['doc_type']}/{m['product_area']}] {m['title']}")
    return fused_docs

user_query = input("\nQuery: ")
fused_docs = show_hybrid(user_query)


# Generate the support answer from the fused context.
docs_content = "\n\n".join(doc.page_content for doc in fused_docs)
prompt = rag_prompt_template.invoke({"question": user_query, "context": docs_content})
response = llm.invoke(prompt)
print("\n" + "-" * 80 + "\n")
print(response.content)
print("\n" + "-" * 80 + "\n")

print("Thank you for using the MegaWasher RAG app! Have an awesome day :) ")
