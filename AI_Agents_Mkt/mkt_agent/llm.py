"""Groq LLM factory."""

import groq
from langchain_core.exceptions import OutputParserException
from langchain_groq import ChatGroq
from pydantic import BaseModel

from . import cache, config


class CachedStructuredLLM:
    """Returns cached `schema` outputs for prompts seen within the cache TTL.

    Since Keenable results are cached too, re-running the same research reproduces
    the same prompts and costs no Groq tokens."""

    def __init__(self, runnable, schema: type[BaseModel], temperature: float):
        self._runnable = runnable
        self._schema = schema
        self._key_parts = (config.GROQ_MODEL, temperature, schema.model_json_schema())

    async def ainvoke(self, prompt: str) -> BaseModel:
        key = cache.make_key(*self._key_parts, prompt)
        cached = cache.get("llm", key)
        if cached is not None:
            return self._schema.model_validate(cached)
        result = await self._runnable.ainvoke(prompt)
        cache.put("llm", key, result.model_dump())
        return result


def structured_llm(schema: type[BaseModel], temperature: float = 0.0) -> CachedStructuredLLM:
    """A Groq chat model that returns instances of `schema`."""
    # Generous retries: Groq's free tier (8k tokens/min) returns 429s when competitor
    # analyses run in parallel; the SDK backs off and retries them
    llm = ChatGroq(model=config.GROQ_MODEL, temperature=temperature, max_retries=8)
    # strict=True makes Groq enforce the schema during generation; without it the model
    # sometimes returns nested objects as JSON strings. Malformed output still slips
    # through occasionally (400 json_validate_failed, or a parse error), so retry those
    runnable = llm.with_structured_output(schema, method="json_schema", strict=True).with_retry(
        retry_if_exception_type=(groq.BadRequestError, OutputParserException), stop_after_attempt=3
    )
    return CachedStructuredLLM(runnable, schema, temperature)
