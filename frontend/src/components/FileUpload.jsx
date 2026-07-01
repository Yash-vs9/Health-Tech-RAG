import React, { useRef } from 'react';

export default function FileUpload({ onUpload }) {
  const inputRef = useRef(null);

  const handleChange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    try {
      await onUpload(file);
    } catch (err) {
      alert(`Upload failed: ${err.message}`);
    }
    e.target.value = '';
  };

  return (
    <div className="file-upload">
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.docx"
        onChange={handleChange}
        style={{ display: 'none' }}
      />
      <button className="btn-upload" onClick={() => inputRef.current.click()}>
        + Upload PDF or DOCX
      </button>
    </div>
  );
}
