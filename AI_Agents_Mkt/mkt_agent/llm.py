"""Groq LLM factory."""

import groq
from langchain_core.exceptions import OutputParserException
from langchain_groq import ChatGroq
from pydantic import BaseModel

from . import config


def structured_llm(schema: type[BaseModel], temperature: float = 0.0):
    """A Groq chat model that returns instances of `schema`."""
    # Generous retries: Groq's free tier (8k tokens/min) returns 429s when competitor
    # analyses run in parallel; the SDK backs off and retries them
    llm = ChatGroq(model=config.GROQ_MODEL, temperature=temperature, max_retries=8)
    # strict=True makes Groq enforce the schema during generation; without it the model
    # sometimes returns nested objects as JSON strings. Malformed output still slips
    # through occasionally (400 json_validate_failed, or a parse error), so retry those
    return llm.with_structured_output(schema, method="json_schema", strict=True).with_retry(
        retry_if_exception_type=(groq.BadRequestError, OutputParserException), stop_after_attempt=3
    )
