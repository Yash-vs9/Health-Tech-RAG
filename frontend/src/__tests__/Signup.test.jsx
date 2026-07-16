import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import Signup from '../pages/Signup'
import { AuthProvider } from '../context/AuthContext'

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

vi.mock('../api', () => ({
  api: {
    signup: vi.fn(),
    me: vi.fn().mockResolvedValue({ id: '1', email: 'test@example.com' }),
    logout: vi.fn().mockResolvedValue({}),
  },
  setOnUnauthorized: vi.fn(),
}))

import { api } from '../api'

const renderSignup = () => {
  return render(
    <MemoryRouter>
      <AuthProvider>
        <Signup />
      </AuthProvider>
    </MemoryRouter>
  )
}

describe('Signup', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('renders signup form', () => {
    renderSignup()
    expect(screen.getByText('Create your account')).toBeInTheDocument()
    expect(screen.getByText('Start analyzing your financial documents with AI')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('John Doe')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('you@example.com')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('Create a strong password')).toBeInTheDocument()
  })

  it('renders create account button', () => {
    renderSignup()
    expect(screen.getByText('Create Account')).toBeInTheDocument()
  })

  it('renders link to login', () => {
    renderSignup()
    expect(screen.getByText('Sign in')).toBeInTheDocument()
  })

  it('calls signup and navigates on success', async () => {
    api.signup.mockResolvedValueOnce({
      access_token: 'fake-token',
      user_id: '1',
      email: 'test@example.com',
    })

    renderSignup()
    
    fireEvent.change(screen.getByPlaceholderText('John Doe'), {
      target: { value: 'John Doe' },
    })
    fireEvent.change(screen.getByPlaceholderText('you@example.com'), {
      target: { value: 'test@example.com' },
    })
    fireEvent.change(screen.getByPlaceholderText('Create a strong password'), {
      target: { value: 'password123' },
    })
    fireEvent.click(screen.getByText('Create Account'))

    await waitFor(() => {
      expect(api.signup).toHaveBeenCalledWith('test@example.com', 'password123', 'John Doe')
      expect(mockNavigate).toHaveBeenCalledWith('/dashboard')
    })
  })

  it('shows error message on signup failure', async () => {
    api.signup.mockRejectedValueOnce(new Error('Email already exists'))

    renderSignup()
    
    fireEvent.change(screen.getByPlaceholderText('John Doe'), {
      target: { value: 'John Doe' },
    })
    fireEvent.change(screen.getByPlaceholderText('you@example.com'), {
      target: { value: 'existing@example.com' },
    })
    fireEvent.change(screen.getByPlaceholderText('Create a strong password'), {
      target: { value: 'password123' },
    })
    fireEvent.click(screen.getByText('Create Account'))

    await waitFor(() => {
      expect(screen.getByText('Email already exists')).toBeInTheDocument()
    })
  })

  it('disables button during loading', async () => {
    api.signup.mockImplementation(() => new Promise(() => {}))

    renderSignup()
    
    fireEvent.change(screen.getByPlaceholderText('John Doe'), {
      target: { value: 'John Doe' },
    })
    fireEvent.change(screen.getByPlaceholderText('you@example.com'), {
      target: { value: 'test@example.com' },
    })
    fireEvent.change(screen.getByPlaceholderText('Create a strong password'), {
      target: { value: 'password123' },
    })
    fireEvent.click(screen.getByText('Create Account'))

    await waitFor(() => {
      expect(screen.getByText('Creating account...')).toBeInTheDocument()
      expect(screen.getByText('Creating account...')).toBeDisabled()
    })
  })
})
