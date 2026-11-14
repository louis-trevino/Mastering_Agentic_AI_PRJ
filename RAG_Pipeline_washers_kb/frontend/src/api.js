const API_URL = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/+$/, "");

/**
 * Ask the MegaWasher RAG backend a question.
 * @returns {Promise<{question: string, answer: string, citations: Array}>}
 */
export async function askQuestion(question, { signal } = {}) {
  let res;
  try {
    res = await fetch(`${API_URL}/api/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
      signal,
    });
  } catch (err) {
    if (err.name === "AbortError") throw err;
    throw new Error(`Cannot reach the API at ${API_URL}. Is the backend running?`);
  }

  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") detail = body.detail;
      else if (Array.isArray(body.detail)) detail = body.detail.map((d) => d.msg).join("; ");
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail);
  }
  return res.json();
}
