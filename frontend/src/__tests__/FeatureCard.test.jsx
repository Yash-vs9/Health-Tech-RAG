import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import FeatureCard from '../components/FeatureCard'

describe('FeatureCard', () => {
  const defaultProps = {
    icon: 'upload',
    title: 'Upload Documents',
    description: 'Upload your mortgage PDFs for analysis',
    index: 0,
  }

  it('renders title and description', () => {
    render(<FeatureCard {...defaultProps} />)
    expect(screen.getByText('Upload Documents')).toBeInTheDocument()
    expect(screen.getByText('Upload your mortgage PDFs for analysis')).toBeInTheDocument()
  })

  it('renders different icons based on prop', () => {
    const { rerender } = render(<FeatureCard {...defaultProps} icon="chat" />)
    expect(screen.getByText('Upload Documents')).toBeInTheDocument()

    rerender(<FeatureCard {...defaultProps} icon="search" title="Search" description="Search docs" />)
    expect(screen.getByText('Search')).toBeInTheDocument()
  })

  it('renders with index for animation delay', () => {
    render(<FeatureCard {...defaultProps} index={2} />)
    expect(screen.getByText('Upload Documents')).toBeInTheDocument()
  })
})
