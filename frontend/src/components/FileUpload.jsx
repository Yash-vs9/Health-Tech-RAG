import { useRef, useState, useCallback } from 'react';

export default function FileUpload({ onUpload }) {
  const inputRef = useRef(null);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);

  const handleFile = useCallback(async (file) => {
    if (!file) return;
    setSelectedFile(file);
    setUploading(true);
    try {
      await onUpload(file);
      setSelectedFile(null);
    } catch (err) {
      console.error('Upload failed:', err);
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = '';
    }
  }, [onUpload]);

  const onInputChange = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    handleFile(file);
  };

  const onDragEnter = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (!uploading) setDragOver(true);
  };

  const onDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(false);
  };

  const onDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (!uploading) setDragOver(true);
  };

  const onDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(false);
    const file = e.dataTransfer?.files?.[0];
    if (!file) return;
    if (!file.name.endsWith('.pdf') && !file.name.endsWith('.docx')) {
      alert('Only PDF and DOCX files are supported.');
      return;
    }
    handleFile(file);
  };

  return (
    <div
      className={`upload-zone ${dragOver ? 'drag-over' : ''} ${uploading ? 'uploading' : ''}`}
      onClick={() => !uploading && inputRef.current?.click()}
      onDragEnter={onDragEnter}
      onDragLeave={onDragLeave}
      onDragOver={onDragOver}
      onDrop={onDrop}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.docx"
        onChange={onInputChange}
        style={{ display: 'none' }}
      />

      {uploading ? (
        <div className="upload-zone-content">
          <div className="upload-spinner" />
          <p className="upload-label">Processing {selectedFile?.name || 'file'}...</p>
          <p className="upload-hint">This may take a moment while we extract and index the content.</p>
        </div>
      ) : (
        <div className="upload-zone-content">
          <div className="upload-icon">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
          </div>
          <p className="upload-label">
            <strong>Click to upload</strong> or drag and drop
          </p>
          <p className="upload-hint">PDF or DOCX (max 25MB)</p>
        </div>
      )}
    </div>
  );
}
