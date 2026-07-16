import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import Navbar from '../components/Navbar'
import { AuthProvider } from '../context/AuthContext'

vi.mock('../api', () => ({
  api: {
    me: vi.fn().mockResolvedValue({ id: '1', email: 'test@example.com' }),
    logout: vi.fn().mockResolvedValue({}),
  },
  setOnUnauthorized: vi.fn(),
}))

const renderWithAuth = (isAuthenticated = false) => {
  const mockUser = isAuthenticated ? { id: '1', email: 'test@example.com' } : null
  
  return render(
    <MemoryRouter>
      <AuthProvider>
        <Navbar />
      </AuthProvider>
    </MemoryRouter>
  )
}

describe('Navbar', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('renders logo and brand name', () => {
    renderWithAuth()
    expect(screen.getByText('FinAssist AI')).toBeInTheDocument()
  })

  it('renders Features and Team links', () => {
    renderWithAuth()
    expect(screen.getByText('Features')).toBeInTheDocument()
    expect(screen.getByText('Team')).toBeInTheDocument()
  })

  it('renders Login and Get Started when not authenticated', () => {
    renderWithAuth(false)
    expect(screen.getByText('Login')).toBeInTheDocument()
    expect(screen.getByText('Get Started')).toBeInTheDocument()
  })

  it('renders Dashboard and Logout when authenticated', () => {
    localStorage.setItem('token', 'fake-token')
    localStorage.setItem('user', JSON.stringify({ id: '1', email: 'test@example.com' }))
    renderWithAuth(true)
    expect(screen.getByText('Dashboard')).toBeInTheDocument()
    expect(screen.getByText('Logout')).toBeInTheDocument()
  })
})
