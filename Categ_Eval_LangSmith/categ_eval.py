"""
Categorization Eval app

By Louis Trevino, 2026
"""

from dotenv import load_dotenv
import os
import getpass

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from typing import List

from utils.app_utils import get_tuples_from_csv

from collections import Counter

from typing import TypedDict, Literal
from langgraph.graph import StateGraph, START, END
from langchain_core.prompts import ChatPromptTemplate

# uv add opentelemetry-distro opentelemetry-exporter-otlp
from opentelemetry import trace

# Clear stale tracing vars 
for k in [
    "LANGCHAIN_API_KEY",
    "LANGCHAIN_ENDPOINT",
    "LANGCHAIN_TRACING_V2",
    "OTEL_EXPORTER_OTLP_ENDPOINT",
    "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT",
    "OTEL_EXPORTER_OTLP_HEADERS",
    "OTEL_EXPORTER_OTLP_TRACES_HEADERS",
    "OTEL_EXPORTER_OTLP_PROTOCOL",
]:
    os.environ.pop(k, None)

load_dotenv()

def _set(key: str, prompt: str):
    if not os.environ.get(key):
        os.environ[key] = getpass.getpass(prompt)

_set("OPENAI_API_KEY",    "OpenAI API key: ")
_set("LANGSMITH_API_KEY", "LangSmith API key: ")

# LangSmith is still the evaluation/debugging UI.
os.environ["LANGSMITH_TRACING"]  = "true"
os.environ["LANGSMITH_PROJECT"]  = "customer-support-evals"
os.environ["LANGSMITH_ENDPOINT"] = "https://api.smith.langchain.com"  # use https://eu.api.smith.langchain.com for EU accounts

# OpenTelemetry is the standard tracing layer. LangSmith receives the emitted spans.
os.environ["LANGSMITH_OTEL_ENABLED"] = "true"
os.environ["OTEL_SERVICE_NAME"] = "customer-support-evals-notebook"
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "https://api.smith.langchain.com/otel"
os.environ["OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"] = "https://api.smith.langchain.com/otel/v1/traces"
os.environ["OTEL_EXPORTER_OTLP_PROTOCOL"] = "http/protobuf"

otel_headers = f"x-api-key={os.environ['LANGSMITH_API_KEY']},Langsmith-Project={os.environ['LANGSMITH_PROJECT']}"
os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = otel_headers
os.environ["OTEL_EXPORTER_OTLP_TRACES_HEADERS"] = otel_headers

print("Traces will appear in LangSmith project:", os.environ["LANGSMITH_PROJECT"])
print("OpenTelemetry service name:", os.environ["OTEL_SERVICE_NAME"])
print("OpenTelemetry traces endpoint:", os.environ["OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"])

#filtered_vars = {k: v for k, v in os.environ.items() if k.startswith("LANGSMITH")}
#for k, v in filtered_vars.items():
#    print(f"{k}={v} ")

# *** Define Ticket Categories ***

# Domain categories for tickets
CATEGORIES = [
    "order_status",
    "refund_request",
    "product_issue",
    "account_help",
    "other",
]

# *** Generate Ticket dataset *** 

SEED_TICKETS: list[tuple[str, str]] = get_tuples_from_csv(filename="seed_tickets_01.csv")

EXPANSIONS_PER_SEED = 3  # n seeds * (1 + 3) = total

generator_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.9)

class Paraphrases(BaseModel):
    variations: List[str] = Field(description="Realistic paraphrases of the original ticket")

def expand_text(seed_text: str, n: int) -> List[str]:
    if n <= 0:
        return []
    structured = generator_llm.with_structured_output(Paraphrases)
    out = structured.invoke(
        f"You write realistic e-commerce customer-support tickets.\n"
        f"Produce {n} short paraphrases of the ticket below. KEEP THE SAME UNDERLYING INTENT, "
        f"but vary tone (frustrated, polite, terse, rambling, sarcastic), names, order numbers, "
        f"products, and the specific phrasing. If the original is ambiguous or mentions keywords "
        f"from multiple categories, preserve that ambiguity — don't sanitize it.\n\n"
        f"Original ticket:\n{seed_text}"
    )
    return out.variations

tickets = []
#print(SEED_TICKETS.count())

for text, label in SEED_TICKETS:
    tickets.append({"id": f"t{len(tickets):03d}", "text": text, "true_category": label, "source": "seed"})
    for variation in expand_text(text, EXPANSIONS_PER_SEED):
        tickets.append({"id": f"t{len(tickets):03d}", "text": variation, "true_category": label, "source": "synthetic"})

print(f"Generated {len(tickets)} tickets across {len(CATEGORIES)} categories.")

for cat, n in Counter(t["true_category"] for t in tickets).items():
    print(f"  {cat:>15}: {n}")

#print()
#for t in tickets[:5]:
#    print(f"  [{t['true_category']:>15}] {t['text'][:90]}")

# *** LangGraph Classification Agent *** 

from app_agents.classif_agent import build_agent
from app_prompts.app_prompts import CATEG_PROMPT, CATEG_PROMPT_WEAK, CATEG_PROMPT_STRONG

agent = build_agent(CATEG_PROMPT_STRONG)

# Show one ticket.
#sample = agent.invoke({"ticket_text": tickets[0]["text"], "category": "", "reasoning": ""})
#print("Ticket:    ", tickets[0]["text"])
#print("Predicted: ", sample["category"])
#print("Reasoning: ", sample["reasoning"])


# uv add opentelemetry-distro opentelemetry-exporter-otlp
from opentelemetry import trace

# This tracer creates ticket-level spans. LangSmith receives them because
# LANGSMITH_OTEL_ENABLED=true is set above.
tracer = trace.get_tracer("customer-support-evals")

# *** Run the Agent on every ticket ***
from utils.pred_utils import run_predictions

results_v1 = run_predictions(agent, tracer, tickets, run_name="baseline", prompt_version="v1")
results_v1.head(10)

# Export results
results_v1_export = results_v1.copy()
results_v1_export["validator_comment"] = ""
results_v1_export["failure_category"] = ""
results_v1_export.to_csv("results_v1.csv", index=False)
print("Exported ticket data to CSV file.")
print("Columns:", list(results_v1_export.columns))


