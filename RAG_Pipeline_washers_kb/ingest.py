import os
import json
import sys
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate

"""
Hybrid RAG Retrieval by Louis C Trevino 2026

This Ingest program will perform RAG ingestion of a json data source.
Once the data has been read, this program will perform chunking, 
embedding, indexing and will store the vector data in PineCone vector database.    
"""
print("RAG Pipeline Demo -- Ingest data \nAuthor: Louis Trevino 2026")

load_dotenv()
PINECONE_IDX = os.environ["PINECONE_INDEX_NAME"]
PINECONE_NS = os.environ["PINECONE_NAMESPACE"]

# Ingest data
with open("kb_washers_01.json") as f:
    kb = json.load(f)

docs = [
    Document(page_content=entry["content"], metadata=entry["metadata"])
    for entry in kb
]

print("Docs count:", len(docs))
# print("Metadata sample:", docs[1].metadata)

def wrap_text(text, width=80):
    return '\n'.join([text[i:i+width] for i in range(0, len(text), width)])


print(wrap_text(docs[1].page_content))
print("-" * 50)

# Do splitting (chunking)
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=150,  
    chunk_overlap=50,  
    add_start_index=True,  
)
print("Splitting data into chunks...")
splits = text_splitter.split_documents(docs)

print(f"Documents in:  {len(docs)}")
print(f"Chunks out:    {len(splits)}")
print("-" * 100)

embeddings = OpenAIEmbeddings(model="text-embedding-3-small", dimensions=512)  # 512-dim vectors

pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
print("PC Idx:", PINECONE_IDX)
print("PC NS:", PINECONE_NS)
index = pc.Index(PINECONE_IDX)

#ref: https://python.langchain.com/docs/concepts/vectorstores/
vector_store = PineconeVectorStore(
    index=index,
    embedding=embeddings,
    namespace=PINECONE_NS,
)

# Store chunks in Vector DB
print("Storing vector data...")
document_ids = vector_store.add_documents(documents=splits)
print("Vector data saved.\n")

index.fetch(ids=[document_ids[1]], namespace=PINECONE_NS)
