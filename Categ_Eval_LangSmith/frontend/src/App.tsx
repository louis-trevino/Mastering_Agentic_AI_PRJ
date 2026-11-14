import { useState } from 'react'
import { CircleAlert, Glasses, Sparkles } from 'lucide-react'
import { searchKnowledgeBase, type SearchResponse } from './api'
import { AnswerPanel } from './components/AnswerPanel'
import { QuestionForm } from './components/QuestionForm'

function App() {
  const [result, setResult] = useState<SearchResponse | null>(null)
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  async function handleSearch(question: string) {
    setIsLoading(true)
    setError('')
    setResult(null)
    try {
      setResult(await searchKnowledgeBase(question))
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : 'The assistant is temporarily unavailable. Please try again.',
      )
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="app-shell">
      <header className="site-header">
        <a className="brand" href="#top" aria-label="SuperGlasses home">
          <span className="brand-mark"><Glasses aria-hidden="true" /></span>
          <span>Super<span>Glasses</span></span>
        </a>
        <div className="header-badge"><span /> Support assistant</div>
      </header>

      <main id="top">
        <section className="hero">
          <div className="eyebrow">
            <Sparkles aria-hidden="true" /> AI-powered customer support
          </div>
          <h1>How can we help<br />you <em>see</em> better?</h1>
          <p>
            Ask about orders, returns, prescriptions, or your account. Our
            assistant searches our support knowledge base for the best answer.
          </p>
          <QuestionForm onSearch={handleSearch} isLoading={isLoading} />
        </section>

        <section className="result-panel" aria-live="polite" aria-busy={isLoading}>
          {error && (
            <p className="request-error" role="alert">
              <CircleAlert aria-hidden="true" /> {error}
            </p>
          )}
          <AnswerPanel result={result} isLoading={isLoading} />
        </section>
      </main>

      <footer>
        <span>SuperGlasses Support Assistant</span>
        <span>AI-generated guidance · Please verify order-specific details</span>
      </footer>
    </div>
  )
}

export default App
