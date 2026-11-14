import { useRef, useState } from "react";
import { askQuestion } from "./api.js";

const SAMPLE_QUESTIONS = [
  "My front load washer door won't open. What can I do?",
  "Water is leaking from the front load door.",
  "How do I connect my smart washer to Wi-Fi?",
  "What does the extended warranty cover?",
];

const DOC_TYPE_LABELS = {
  support_ticket: "Support ticket",
  user_manual: "User manual",
};

function labelize(value) {
  return value ? value.replace(/_/g, " ") : "";
}

function Citation({ citation, index }) {
  return (
    <li className="citation">
      <div className="citation-head">
        <span className="citation-num">{index + 1}</span>
        <span className="citation-title">{citation.title}</span>
      </div>
      <div className="citation-tags">
        <span className={`tag tag-${citation.doc_type}`}>
          {DOC_TYPE_LABELS[citation.doc_type] || labelize(citation.doc_type)}
        </span>
        {citation.product_type && <span className="tag">{labelize(citation.product_type)}</span>}
        {citation.ticket_id && <span className="tag tag-id">{citation.ticket_id}</span>}
      </div>
      <p className="citation-snippet">{citation.snippet}</p>
    </li>
  );
}

export default function App() {
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const abortRef = useRef(null);

  async function runSearch(q) {
    const text = q.trim();
    if (text.length < 3 || loading) return;

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setLoading(true);
    setError("");
    setResult(null);
    try {
      setResult(await askQuestion(text, { signal: controller.signal }));
    } catch (err) {
      if (err.name !== "AbortError") setError(err.message);
    } finally {
      if (abortRef.current === controller) setLoading(false);
    }
  }

  function handleSubmit(e) {
    e.preventDefault();
    runSearch(question);
  }

  function handleSample(q) {
    setQuestion(q);
    runSearch(q);
  }

  function handleKeyDown(e) {
    // Enter submits; Shift+Enter inserts a newline.
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      runSearch(question);
    }
  }

  return (
    <div className="page">
      <header className="header">
        <h1>MegaWasher Support Assistant</h1>
        <p className="subtitle">
          Ask a question about MegaWasher washers. Answers come from our support tickets and user manuals.
        </p>
      </header>

      <main>
        <form className="ask-form" onSubmit={handleSubmit}>
          <label htmlFor="question" className="visually-hidden">Your question</label>
          <textarea
            id="question"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Describe the issue, e.g. My washer won't drain…"
            rows={3}
            maxLength={1000}
            disabled={loading}
          />
          <div className="form-row">
            <span className="hint">Enter to search · Shift+Enter for a new line</span>
            <button type="submit" disabled={loading || question.trim().length < 3}>
              {loading ? "Searching…" : "Ask"}
            </button>
          </div>
        </form>

        <div className="samples" aria-label="Sample questions">
          <span className="samples-label">Try:</span>
          {SAMPLE_QUESTIONS.map((q) => (
            <button key={q} type="button" className="chip" onClick={() => handleSample(q)} disabled={loading}>
              {q}
            </button>
          ))}
        </div>

        {loading && (
          <div className="status" role="status">
            <span className="spinner" aria-hidden="true" /> Searching the knowledge base and writing an answer…
          </div>
        )}

        {error && (
          <div className="error" role="alert">
            <strong>Something went wrong.</strong> {error}
          </div>
        )}

        {result && (
          <section className="result" aria-live="polite">
            <p className="result-question">“{result.question}”</p>
            <div className="answer">
              <h2>Answer</h2>
              <p>{result.answer}</p>
            </div>
            {result.citations.length > 0 && (
              <div className="citations">
                <h2>Sources ({result.citations.length})</h2>
                <ol>
                  {result.citations.map((c, i) => (
                    <Citation key={`${c.ticket_id}-${i}`} citation={c} index={i} />
                  ))}
                </ol>
              </div>
            )}
          </section>
        )}
      </main>

      <footer className="footer">Hybrid RAG search: semantic (Pinecone) + keyword (BM25)</footer>
    </div>
  );
}
