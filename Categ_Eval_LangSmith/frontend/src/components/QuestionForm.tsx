import { useState, type FormEvent } from 'react'
import { ArrowRight, CircleAlert, LoaderCircle, Search } from 'lucide-react'

const examples = [
  'How do I track my order?',
  'What is your return policy?',
  'How do I update my prescription?',
]

interface QuestionFormProps {
  onSearch: (question: string) => Promise<void>
  isLoading: boolean
}

export function QuestionForm({ onSearch, isLoading }: QuestionFormProps) {
  const [question, setQuestion] = useState('')
  const [validationError, setValidationError] = useState('')

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const trimmed = question.trim()
    if (trimmed.length < 3) {
      setValidationError('Please enter a question with at least 3 characters.')
      return
    }
    setValidationError('')
    await onSearch(trimmed)
  }

  return (
    <>
      <form className="search-box" onSubmit={handleSubmit} noValidate>
        <label htmlFor="question">What would you like to know?</label>
        <div className="input-row">
          <div className="input-wrap">
            <Search aria-hidden="true" />
            <input
              id="question"
              name="question"
              value={question}
              onChange={(event) => {
                setQuestion(event.target.value)
                if (validationError) setValidationError('')
              }}
              placeholder="e.g. How do I track my order?"
              maxLength={1000}
              disabled={isLoading}
              aria-describedby={validationError ? 'search-error' : undefined}
              aria-invalid={Boolean(validationError)}
            />
          </div>
          <button type="submit" disabled={isLoading}>
            {isLoading ? (
              <LoaderCircle className="spin" aria-hidden="true" />
            ) : (
              <ArrowRight aria-hidden="true" />
            )}
            <span>{isLoading ? 'Searching' : 'Ask'}</span>
          </button>
        </div>
        {validationError && (
          <p id="search-error" className="form-error" role="alert">
            <CircleAlert aria-hidden="true" /> {validationError}
          </p>
        )}
      </form>

      <div className="examples" aria-label="Example questions">
        <span>Try asking:</span>
        {examples.map((example) => (
          <button key={example} type="button" onClick={() => setQuestion(example)}>
            {example}
          </button>
        ))}
      </div>
    </>
  )
}
