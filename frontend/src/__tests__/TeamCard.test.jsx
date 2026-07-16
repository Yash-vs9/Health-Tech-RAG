import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import TeamCard from '../components/TeamCard'

describe('TeamCard', () => {
  it('renders name and role', () => {
    render(<TeamCard name="John Doe" role="Developer" index={0} />)
    expect(screen.getByText('John Doe')).toBeInTheDocument()
    expect(screen.getByText('Developer')).toBeInTheDocument()
  })

  it('renders initials in avatar', () => {
    render(<TeamCard name="Jane Smith" role="Designer" index={1} />)
    expect(screen.getByText('JS')).toBeInTheDocument()
  })

  it('handles single word name', () => {
    render(<TeamCard name="Madonna" role="Singer" index={0} />)
    expect(screen.getByText('M')).toBeInTheDocument()
  })

  it('renders without role when not provided', () => {
    render(<TeamCard name="John Doe" index={0} />)
    expect(screen.getByText('John Doe')).toBeInTheDocument()
    expect(screen.queryByText('Developer')).not.toBeInTheDocument()
  })
})
