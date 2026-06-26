import React, { useRef } from 'react';

const ACCEPT = '.pdf,.docx';

export default function FileUpload({ onUpload }) {
  const inputRef = useRef(null);

  const handleChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      onUpload(file);
      e.target.value = '';
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) onUpload(file);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
  };

  return (
    <div
      className="file-upload"
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onClick={() => inputRef.current.click()}
    >
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPT}
        onChange={handleChange}
        hidden
      />
      <div className="upload-icon">📄</div>
      <p>Drop a PDF or DOCX here</p>
      <p className="upload-hint">or click to browse</p>
    </div>
  );
}
