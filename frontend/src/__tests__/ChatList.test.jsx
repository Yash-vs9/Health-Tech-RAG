import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import ChatList from '../components/ChatList'

describe('ChatList', () => {
  const defaultProps = {
    chats: [
      { id: '1', title: 'First Chat', document_count: 3 },
      { id: '2', title: 'Second Chat', document_count: 1 },
    ],
    activeChat: null,
    onSelect: vi.fn(),
    onNew: vi.fn(),
    onDelete: vi.fn(),
    onRename: vi.fn(),
    user: { email: 'test@example.com' },
    onLogout: vi.fn(),
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders chat list with titles', () => {
    render(<ChatList {...defaultProps} />)
    expect(screen.getByText('First Chat')).toBeInTheDocument()
    expect(screen.getByText('Second Chat')).toBeInTheDocument()
  })

  it('renders document counts', () => {
    render(<ChatList {...defaultProps} />)
    expect(screen.getByText('3 docs')).toBeInTheDocument()
    expect(screen.getByText('1 docs')).toBeInTheDocument()
  })

  it('renders user email', () => {
    render(<ChatList {...defaultProps} />)
    expect(screen.getByText('test@example.com')).toBeInTheDocument()
  })

  it('shows empty state when no chats', () => {
    render(<ChatList {...defaultProps} chats={[]} />)
    expect(screen.getByText('No chats yet.')).toBeInTheDocument()
  })

  it('calls onNew when New button clicked', () => {
    render(<ChatList {...defaultProps} />)
    fireEvent.click(screen.getByText('New'))
    expect(defaultProps.onNew).toHaveBeenCalled()
  })

  it('calls onSelect when chat item clicked', () => {
    render(<ChatList {...defaultProps} />)
    fireEvent.click(screen.getByText('First Chat'))
    expect(defaultProps.onSelect).toHaveBeenCalledWith(defaultProps.chats[0])
  })

  it('calls onDelete when delete button clicked', () => {
    render(<ChatList {...defaultProps} />)
    const deleteButtons = screen.getAllByTitle('Delete')
    fireEvent.click(deleteButtons[0])
    expect(defaultProps.onDelete).toHaveBeenCalledWith('1')
  })

  it('calls onLogout when logout button clicked', () => {
    render(<ChatList {...defaultProps} />)
    fireEvent.click(screen.getByText('Logout'))
    expect(defaultProps.onLogout).toHaveBeenCalled()
  })

  it('highlights active chat', () => {
    render(<ChatList {...defaultProps} activeChat={defaultProps.chats[0]} />)
    const chatItems = screen.getAllByText('First Chat')
    const activeItem = chatItems[0].closest('.chat-item')
    expect(activeItem).toHaveClass('active')
  })
})
