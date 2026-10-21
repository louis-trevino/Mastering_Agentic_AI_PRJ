# MegaWasher RAG App


## Project Links

[Documentation](https://docs.google.com/document/d/1UxR1Wpt8PjF3Yl5VHa8RpFMtSpVUAz8KTxyUZBsHRBE/edit?tab=t.0)

[Sample data](./kb_washers_01.json)

[Demo](https://www.loom.com/share/317e2ab3b43341cb8514752e1a22163f)

## Project Description

MegaWash RAG App helps customers answer customer support questions from the internal Knowledge Base (support tickets + FAQ documents + product manuals).

An ingestion program written in Python will take the data and perform extraction, fragmentation into chunks, embedding , indexing and saving the resulting vector data into a PineCone vector database. 

The retrieval will be done by a Hybrid Retriever application written in Python that will perform hybrid (semantic / BM25 keywords). The semantic search will be done by making calls to the PineCone vector database. Top-k value will be 3.

## Setup
```
uv sync
```

## Run Ingestion App

The Ingestion app only needs to be run once, or every time the Knowledge Base data (json) changes.
```
py ingest.py
```

## Run Retrieval App
```
py retriever_hybrid.py
```

## Sample user query

You can use the User Query below to test the Retriever app:

My front load washer door won't open. What can I do?
