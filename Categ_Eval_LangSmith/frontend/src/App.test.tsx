import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import { searchKnowledgeBase } from './api'

vi.mock('./api', () => ({ searchKnowledgeBase: vi.fn() }))

const mockedSearch = vi.mocked(searchKnowledgeBase)

describe('App', () => {
  beforeEach(() => {
    mockedSearch.mockReset()
  })

  it('requires a meaningful question', async () => {
    const user = userEvent.setup()
    render(<App />)

    await user.type(screen.getByLabelText('What would you like to know?'), '  ')
    await user.click(screen.getByRole('button', { name: /ask/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent('at least 3 characters')
    expect(mockedSearch).not.toHaveBeenCalled()
  })

  it('submits a question and displays the answer with sources', async () => {
    mockedSearch.mockResolvedValue({
      question: 'How do I track my order?',
      answer: 'Open your order page to view its latest status.',
      sources: [
        {
          title: 'Order tracking',
          content: 'Tracking can pause for up to five business days.',
          doc_type: 'support_ticket',
          category: 'order_status',
          ticket_id: 'TKT-00003',
        },
      ],
    })
    const user = userEvent.setup()
    render(<App />)

    await user.type(screen.getByLabelText('What would you like to know?'), 'How do I track my order?')
    await user.click(screen.getByRole('button', { name: /ask/i }))

    expect(await screen.findByText('Open your order page to view its latest status.')).toBeInTheDocument()
    expect(screen.getByText('Order tracking')).toBeInTheDocument()
    expect(screen.getByText(/Reference: TKT-00003/)).toBeInTheDocument()
    expect(mockedSearch).toHaveBeenCalledWith('How do I track my order?')
  })

  it('shows a friendly error when the request fails', async () => {
    mockedSearch.mockRejectedValue(new Error('The assistant is temporarily unavailable.'))
    const user = userEvent.setup()
    render(<App />)

    await user.type(screen.getByLabelText('What would you like to know?'), 'Track my order')
    await user.click(screen.getByRole('button', { name: /ask/i }))

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('temporarily unavailable')
    })
  })
})
