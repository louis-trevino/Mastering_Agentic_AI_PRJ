## Week 4 Project

# Categorization Eval App

By Luis C Trevino, 2026

## Project Links

[Documentation](https://docs.google.com/document/d/1hhCq1UY4R2XK21wq4UDZhqfaGZ73WHj4AtVp2LDVZus/edit?tab=t.0)

[Sample data](./kb_eyeglass_01.json)

[Demo](https://www.loom.com/share/6b637d09548c424aa0b1e9d0c3bb5cb0)

## Project Description

The Categorization Eval application will evaluate an intent classifier for SuperGlasses, an online eyeglass store customer support system. The classifier predicts which category a customer ticket belongs to.

 The possible categories are: order status, refund request, product issue, account help, and “other”.
The dataset would be generated from 25 seed tickets, which will later be expanded into 100 tickets by using LLM-driven paraphrasing.

Evaluations of the classification system will be executed by recording the actual values against the expected ones. We will manually annotate failures, define failure categories from the observations, improvements will be done (e.g. prompts, code or data), and the before-and-after results will be compared. 



## Setup
```
uv sync
```

## Run Categorization Eval App

The Ingestion app only needs to be run once, or every time the Knowledge Base data (json) changes.
```
py categ_eval.py
```

## App Flow
```mermaid
graph TD;
Cat(Define Customer Support Categories) --> SEED(Get Seed Data);
SEED --> XP(Expand sample data from seed data by Paraphrasing);
XP --> CA(Run Classification Agent) --> TR(Create Tracer) --> PR(Run Predictions using Tracer);
PR --> LS(Analyse result data in LangSmith portal);
PR --> RES(Export result data to CSV file and analyse results);
LS --> RF(Refactor Code, Prompts or Seed Data);
RES --> RF;
RF --> SEED;
```

## LangSmith Portal

[Result Data Overview](https://smith.langchain.com/o/d89f27c4-fd61-4737-8157-534feaf2c6cc/a/customer-support-evals)

[Tracing](https://smith.langchain.com/o/d89f27c4-fd61-4737-8157-534feaf2c6cc/a/customer-support-evals/projects/p/ae9e64f6-7abc-427d-80c0-90d83823d30e)

