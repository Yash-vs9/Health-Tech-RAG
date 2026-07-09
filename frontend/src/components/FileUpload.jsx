import { useRef, useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Upload, FileText } from 'lucide-react';

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
    <motion.div
      className={`upload-zone ${dragOver ? 'drag-over' : ''} ${uploading ? 'uploading' : ''}`}
      onClick={() => !uploading && inputRef.current?.click()}
      onDragEnter={onDragEnter}
      onDragLeave={onDragLeave}
      onDragOver={onDragOver}
      onDrop={onDrop}
      whileHover={!uploading ? { scale: 1.005 } : {}}
      transition={{ duration: 0.2 }}
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
          <p className="upload-label">
            <FileText size={14} style={{ marginRight: 6, verticalAlign: 'middle' }} />
            Processing {selectedFile?.name || 'file'}...
          </p>
          <p className="upload-hint">This may take a moment while we extract and index the content.</p>
        </div>
      ) : (
        <div className="upload-zone-content">
          <div className="upload-icon">
            <Upload size={28} />
          </div>
          <p className="upload-label">
            <strong>Click to upload</strong> or drag and drop
          </p>
          <p className="upload-hint">PDF or DOCX (max 25MB)</p>
        </div>
      )}
    </motion.div>
  );
}
