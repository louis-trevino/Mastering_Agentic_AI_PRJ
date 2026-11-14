export interface Source {
  title: string
  content: string
  doc_type: string
  category: string
  ticket_id?: string
}

export interface SearchResponse {
  question: string
  answer: string
  sources: Source[]
}

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000').replace(
  /\/$/,
  '',
)

export async function searchKnowledgeBase(question: string): Promise<SearchResponse> {
  const response = await fetch(`${API_BASE_URL}/api/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  })

  if (!response.ok) {
    let detail = 'The assistant is temporarily unavailable. Please try again.'
    try {
      const payload = (await response.json()) as { detail?: string }
      if (payload.detail) detail = payload.detail
    } catch {
      // Keep the friendly fallback when the server did not return JSON.
    }
    throw new Error(detail)
  }

  return (await response.json()) as SearchResponse
}
