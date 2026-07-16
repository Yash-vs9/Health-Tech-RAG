import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import ChatView from '../components/ChatView'

describe('ChatView', () => {
  const defaultProps = {
    chat: { id: '1', title: 'Test Chat' },
    messages: [
      { id: 'm1', role: 'user', content: 'What is the rate?' },
      { id: 'm2', role: 'assistant', content: 'The rate is 8.5%.', sources: [], feedback: null },
    ],
    docs: [{ id: 'd1', filename: 'test.pdf', status: 'ready', num_chunks: 5 }],
    onSend: vi.fn(),
    onUpload: vi.fn(),
    onDeleteDoc: vi.fn(),
    onRename: vi.fn(),
    loading: false,
    onSourceClick: vi.fn(),
    onFeedback: vi.fn(),
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders empty state when no chat selected', () => {
    render(<ChatView {...defaultProps} chat={null} />)
    expect(screen.getByText('Mortgage RAG Assistant')).toBeInTheDocument()
    expect(screen.getByText('Select a chat or create a new one to get started.')).toBeInTheDocument()
  })

  it('renders chat title', () => {
    render(<ChatView {...defaultProps} />)
    expect(screen.getByText('Test Chat')).toBeInTheDocument()
  })

  it('renders messages', () => {
    render(<ChatView {...defaultProps} />)
    expect(screen.getByText('What is the rate?')).toBeInTheDocument()
    expect(screen.getByText('The rate is 8.5%.')).toBeInTheDocument()
  })

  it('renders user and assistant labels', () => {
    render(<ChatView {...defaultProps} />)
    expect(screen.getByText('You')).toBeInTheDocument()
    expect(screen.getAllByText('Assistant')[0]).toBeInTheDocument()
  })

  it('calls onSend when form submitted', () => {
    render(<ChatView {...defaultProps} />)
    const input = screen.getByPlaceholderText('Ask about your mortgage documents...')
    fireEvent.change(input, { target: { value: 'What are the fees?' } })
    fireEvent.submit(input.closest('form'))
    expect(defaultProps.onSend).toHaveBeenCalledWith('What are the fees?')
  })

  it('does not call onSend when input is empty', () => {
    render(<ChatView {...defaultProps} />)
    const input = screen.getByPlaceholderText('Ask about your mortgage documents...')
    fireEvent.submit(input.closest('form'))
    expect(defaultProps.onSend).not.toHaveBeenCalled()
  })

  it('shows document list', () => {
    render(<ChatView {...defaultProps} />)
    expect(screen.getByText('test.pdf')).toBeInTheDocument()
    expect(screen.getByText('ready')).toBeInTheDocument()
    expect(screen.getByText('5 chunks')).toBeInTheDocument()
  })

  it('calls onDeleteDoc when remove button clicked', () => {
    render(<ChatView {...defaultProps} />)
    fireEvent.click(screen.getByTitle('Remove'))
    expect(defaultProps.onDeleteDoc).toHaveBeenCalledWith('d1')
  })

  it('shows loading indicator when loading', () => {
    render(<ChatView {...defaultProps} loading={true} />)
    expect(screen.getAllByText('Assistant').length).toBeGreaterThanOrEqual(2)
    expect(document.querySelector('.typing-indicator')).toBeInTheDocument()
  })

  it('disables input when loading', () => {
    render(<ChatView {...defaultProps} loading={true} />)
    const input = screen.getByPlaceholderText('Ask about your mortgage documents...')
    expect(input).toBeDisabled()
  })

  it('calls onFeedback when thumbs up clicked', () => {
    render(<ChatView {...defaultProps} />)
    const thumbsUpButtons = screen.getAllByTitle('Good response')
    fireEvent.click(thumbsUpButtons[0])
    expect(defaultProps.onFeedback).toHaveBeenCalledWith(defaultProps.messages[1], 'up')
  })

  it('calls onFeedback when thumbs down clicked', () => {
    render(<ChatView {...defaultProps} />)
    const thumbsDownButtons = screen.getAllByTitle('Bad response')
    fireEvent.click(thumbsDownButtons[0])
    expect(defaultProps.onFeedback).toHaveBeenCalledWith(defaultProps.messages[1], 'down')
  })

  it('shows document count in header', () => {
    render(<ChatView {...defaultProps} />)
    expect(screen.getByText('1 docs ready')).toBeInTheDocument()
  })

  it('shows empty messages state', () => {
    render(<ChatView {...defaultProps} messages={[]} />)
    expect(screen.getByText('Ask a question about your documents.')).toBeInTheDocument()
  })
})
