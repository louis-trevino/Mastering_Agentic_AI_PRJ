import os
import json
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
import warnings
warnings.filterwarnings("ignore")

from typing import Optional
from pydantic import BaseModel, Field


print("RAG Pipeline Demo -- Metadata search \nAuthor: Louis Trevino 2026")

load_dotenv()
print(os.environ["PINECONE_INDEX_NAME"])

# Define embeddings with 512 dimensions 
embeddings = OpenAIEmbeddings(model="text-embedding-3-small", dimensions=512)  # 512-dim vectors

#connect to the existing Pinecone index 
pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
index = pc.Index(os.environ["PINECONE_INDEX_NAME"])

vector_store = PineconeVectorStore(
    index=index,
    embedding=embeddings,
    namespace="myshop-basic-rag",
)

# data check
stats = index.describe_index_stats()
print(stats["namespaces"].get("myshop-basic-rag"))



llm = ChatOpenAI(model="gpt-4.1-mini")

# Build prompt template
template = """You are a customer-support assistant for Myshop, an e-commerce shop.
Use the following pieces of retrieved internal information context to help resolve the customer's query.
If the context doesn't contain the answer, say you don't have that information rather than guessing.
Be concise and practical: state the likely cause and the next step the agent should take.

Context:
{context}

Customer issue: {question}

Support guidance:"""

rag_prompt_template = PromptTemplate.from_template(template)

"""
# With Metadata filter
my_filter = {
    "doc_type": {"$eq": "runbook"},
    "product_area": {"$eq": "shipping"},
}

retriever = vector_store.as_retriever(
    search_kwargs={"k": 5, "filter": my_filter}, search_type="similarity"
)

"""

class TicketFilter(BaseModel):
    """Structured metadata filter inferred from a customer support ticket."""
    product_area: str = Field(
        description="One of: payments, returns, shipping, orders, account"
    )
    doc_type: Optional[str] = Field(
        default=None,
        description="Optionally one of: runbook, past_ticket, product_doc, bug_report, faq. "
                    "Set only if the ticket clearly targets a doc type (e.g. asking about a known bug -> bug_report).",
    )
    customer_tier: Optional[str] = Field(
        default=None,
        description="Optionally one of: plus, regular. Set only if the customer's tier is explicitly mentioned.",
    )

classifier_llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0)
structured_llm = classifier_llm.with_structured_output(TicketFilter)

classify_template = """You classify Myshop customer support tickets so we can filter the knowledge base.
Read the ticket and return the metadata that best scopes the search.

Ticket: {question}
"""
classify_prompt_template = PromptTemplate.from_template(classify_template)

def build_pinecone_filter(ticket_filter: TicketFilter) -> dict:
    """Turn the classified fields into a Pinecone metadata filter, skipping empty ones.

    customer_tier is special: a value of "all" in the data means "applies to every
    tier". So for a 'plus' (or 'regular') member we match BOTH that tier AND "all"
    via $in -- otherwise an $eq filter would silently drop the general docs that
    also apply to this customer (and can leave us with zero results).
    """
    pinecone_filter = {}
    for field, value in ticket_filter.model_dump().items():
        if not value:
            continue
        if field == "customer_tier":
            pinecone_filter[field] = {"$in": [value, "all"]}
        else:
            pinecone_filter[field] = {"$eq": value}
    return pinecone_filter

user_question = "My product was shipped with a smile. What happened?"
prompt = classify_prompt_template.invoke({"question": user_question})
ticket_filter = structured_llm.invoke(prompt)
print("Classified:", ticket_filter)

pinecone_filter = build_pinecone_filter(ticket_filter)
print("Pinecone filter:", pinecone_filter)

retriever = vector_store.as_retriever(
    search_kwargs={"k": 5, "filter": pinecone_filter}, search_type="similarity"
)
retrieved_docs = retriever.invoke(user_question)

# Show results
for doc in retrieved_docs:
    m = doc.metadata
    print(f"[{m['doc_type']} / {m['product_area']}] {m['title']}")
    print(doc.page_content)
    print("-" * 100)
