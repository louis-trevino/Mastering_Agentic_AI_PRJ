#from app_prompts.app_prompts import CLASSIFIER_PROMPT, CLASSIFIER_PROMPT_V2

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from typing import List

from utils.app_utils import get_tuples_from_csv

from collections import Counter

from typing import TypedDict, Literal
from langgraph.graph import StateGraph, START, END
from langchain_core.prompts import ChatPromptTemplate


class Classification(BaseModel):
    category: Literal["order_status", "refund_request", "product_issue", "account_help", "other"]
    reasoning: str = Field(description="One short sentence explaining the choice.")

class AgentState(TypedDict):
    ticket_text: str
    category: str
    reasoning: str

def build_agent(prompt_template: str):
    """Compile a LangGraph agent. Re-call this any time you change the prompt."""
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0).with_structured_output(Classification)
    prompt = ChatPromptTemplate.from_template(prompt_template)

    def classify_node(state: AgentState) -> AgentState:
        result = (prompt | llm).invoke({"ticket_text": state["ticket_text"]})
        return {"ticket_text": state["ticket_text"], "category": result.category, "reasoning": result.reasoning}

    graph = StateGraph(AgentState)
    graph.add_node("classify", classify_node)
    graph.add_edge(START, "classify")
    graph.add_edge("classify", END)
    return graph.compile()
