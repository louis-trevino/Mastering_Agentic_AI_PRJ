import { BookOpen, CheckCircle2, LoaderCircle, Sparkles } from 'lucide-react'
import type { SearchResponse, Source } from '../api'

interface AnswerPanelProps {
  result: SearchResponse | null
  isLoading: boolean
}

function SourceCard({ source, index }: { source: Source; index: number }) {
  return (
    <article className="source-card">
      <div className="source-index">{String(index + 1).padStart(2, '0')}</div>
      <div>
        <div className="source-tags">
          <span>{source.category.replaceAll('_', ' ')}</span>
          <span>{source.doc_type.replaceAll('_', ' ')}</span>
        </div>
        <h3>{source.title}</h3>
        <p>{source.content}</p>
        {source.ticket_id && <small>Reference: {source.ticket_id}</small>}
      </div>
    </article>
  )
}

export function AnswerPanel({ result, isLoading }: AnswerPanelProps) {
  if (isLoading) {
    return (
      <div className="loading-card">
        <LoaderCircle className="spin large" aria-hidden="true" />
        <div>
          <h2>Finding the best answer…</h2>
          <p>Searching orders, returns, prescriptions, and account guidance.</p>
        </div>
      </div>
    )
  }

  if (!result) {
    return (
      <div className="empty-state">
        <span><Sparkles aria-hidden="true" /></span>
        <h2>Answers grounded in our support knowledge</h2>
        <p>
          Enter your question above and we’ll retrieve relevant guidance and cite
          the sources.
        </p>
      </div>
    )
  }

  return (
    <>
      <div className="answer-card">
        <div className="answer-heading">
          <span><CheckCircle2 aria-hidden="true" /> Support answer</span>
          <small>
            Based on {result.sources.length} retrieved{' '}
            {result.sources.length === 1 ? 'source' : 'sources'}
          </small>
        </div>
        <h2>{result.question}</h2>
        <p className="answer-text">{result.answer}</p>
      </div>

      {result.sources.length > 0 && (
        <div className="sources">
          <div className="sources-heading">
            <BookOpen aria-hidden="true" />
            <h2>Sources</h2>
            <span>Knowledge-base references</span>
          </div>
          <div className="source-grid">
            {result.sources.map((source, index) => (
              <SourceCard
                key={`${source.ticket_id ?? source.title}-${index}`}
                source={source}
                index={index}
              />
            ))}
          </div>
        </div>
      )}
    </>
  )
}
