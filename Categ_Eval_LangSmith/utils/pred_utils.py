import pandas as pd
from tqdm import tqdm

def run_predictions(agent, tracer, tickets, run_name="baseline", prompt_version="v1") -> pd.DataFrame:
    rows = []
    for t in tqdm(tickets, desc=f"Classifying {run_name}"):
        # One parent span per ticket makes the spreadsheet row traceable in LangSmith.
        with tracer.start_as_current_span("customer_support.classify_ticket") as span:
            span.set_attribute("langsmith.span.kind", "chain")
            span.set_attribute("eval.run_name", run_name)
            span.set_attribute("eval.prompt_version", prompt_version)
            span.set_attribute("eval.example_id", t["id"])
            span.set_attribute("eval.true_category", t["true_category"])
            span.set_attribute("input.ticket_text", t["text"])

            out = agent.invoke({"ticket_text": t["text"], "category": "", "reasoning": ""})
            correct = t["true_category"] == out["category"]

            span.set_attribute("eval.predicted_category", out["category"])
            span.set_attribute("eval.correct", correct)
            span.set_attribute("eval.reasoning", out["reasoning"])
            span.set_attribute("output.category", out["category"])

            rows.append({
                "id": t["id"],
                "ticket_text": t["text"],
                "true_category": t["true_category"],
                "predicted_category": out["category"],
                "reasoning": out["reasoning"],
                "correct": correct,
                "otel_run_name": run_name,
                "otel_prompt_version": prompt_version,
            })
    return pd.DataFrame(rows)
