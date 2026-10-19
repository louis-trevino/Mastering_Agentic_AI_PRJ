# MegaWasher RAG App

MegaWash RAG App helps customers answer customer support questions from the internal Knowledge Base (support tickets + FAQ documents + product manuals).

An ingestion program written in Python will take the data and perform extraction, fragmentation into chunks, embedding , indexing and saving the resulting vector data into a PineCone vector database. 

The retrieval will be done by a Hybrid Retriever application written in Python that will perform hybrid (semantic / BM25 keywords). The semantic search will be done by making calls to the PineCone vector database. Top-k value will be 3.

## Setup
```
uv sync
```

## Run Ingestion App
```
py ingest.py
```

## Run Retrieval App
```
py retriever_hybrid.py
```

