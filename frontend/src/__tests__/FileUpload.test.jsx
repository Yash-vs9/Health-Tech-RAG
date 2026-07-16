import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import FileUpload from '../components/FileUpload'

describe('FileUpload', () => {
  const mockOnUpload = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders upload zone with text', () => {
    render(<FileUpload onUpload={mockOnUpload} />)
    expect(screen.getByText(/Click to upload/)).toBeInTheDocument()
    expect(screen.getByText(/drag and drop/)).toBeInTheDocument()
    expect(screen.getByText(/PDF, DOCX, JPG, JPEG, or PNG/)).toBeInTheDocument()
  })

  it('calls onUpload when file is selected', async () => {
    mockOnUpload.mockResolvedValueOnce()
    render(<FileUpload onUpload={mockOnUpload} />)

    const input = document.querySelector('input[type="file"]')
    const file = new File(['test'], 'test.pdf', { type: 'application/pdf' })
    
    Object.defineProperty(input, 'files', { value: [file] })
    fireEvent.change(input)

    await waitFor(() => {
      expect(mockOnUpload).toHaveBeenCalledWith(file)
    })
  })

  it('shows uploading state during upload', async () => {
    let resolveUpload
    mockOnUpload.mockImplementation(() => new Promise((resolve) => { resolveUpload = resolve }))
    
    render(<FileUpload onUpload={mockOnUpload} />)

    const input = document.querySelector('input[type="file"]')
    const file = new File(['test'], 'test.pdf', { type: 'application/pdf' })
    
    Object.defineProperty(input, 'files', { value: [file] })
    fireEvent.change(input)

    await waitFor(() => {
      expect(screen.getByText(/Processing/)).toBeInTheDocument()
    })

    resolveUpload()
    
    await waitFor(() => {
      expect(screen.queryByText(/Processing/)).not.toBeInTheDocument()
    })
  })

  it('validates file type on drag and drop', async () => {
    vi.spyOn(window, 'alert').mockImplementation(() => {})
    render(<FileUpload onUpload={mockOnUpload} />)

    const dropZone = document.querySelector('.upload-zone')
    const file = new File(['test'], 'test.exe', { type: 'application/octet-stream' })

    fireEvent.drop(dropZone, {
      dataTransfer: { files: [file] },
    })

    expect(window.alert).toHaveBeenCalledWith('Only PDF, DOCX, JPG, JPEG, and PNG files are supported.')
    expect(mockOnUpload).not.toHaveBeenCalled()
  })

  it('accepts PDF files on drag and drop', async () => {
    mockOnUpload.mockResolvedValueOnce()
    render(<FileUpload onUpload={mockOnUpload} />)

    const dropZone = document.querySelector('.upload-zone')
    const file = new File(['test'], 'test.pdf', { type: 'application/pdf' })

    fireEvent.drop(dropZone, {
      dataTransfer: { files: [file] },
    })

    await waitFor(() => {
      expect(mockOnUpload).toHaveBeenCalledWith(file)
    })
  })
})
