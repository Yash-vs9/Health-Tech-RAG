import React, { useState, useCallback, useEffect, useRef } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';
import { motion } from 'framer-motion';
import { X, ChevronLeft, ChevronRight, ZoomIn, ZoomOut, Loader } from 'lucide-react';

pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

const IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'];

function isImageFile(filename) {
  if (!filename) return false;
  const lower = filename.toLowerCase();
  return IMAGE_EXTENSIONS.some(ext => lower.endsWith(ext));
}

export default function PdfViewer({ pdfUrl, pageNumber: initialPage, filename, token, onClose }) {
  const [numPages, setNumPages] = useState(null);
  const [currentPage, setCurrentPage] = useState(initialPage || 1);
  const [scale, setScale] = useState(1.2);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [imageBlobUrl, setImageBlobUrl] = useState(null);
  const containerRef = useRef(null);

  const isImage = isImageFile(filename);

  useEffect(() => {
    if (initialPage) {
      setCurrentPage(initialPage);
    }
  }, [initialPage]);

  // Fetch image as blob with auth token
  useEffect(() => {
    if (!isImage || !pdfUrl || !token) return;

    let blobUrl = null;
    const controller = new AbortController();

    fetch(pdfUrl, {
      headers: { Authorization: `Bearer ${token}` },
      signal: controller.signal,
    })
      .then(res => {
        if (!res.ok) throw new Error('Failed to load image');
        return res.blob();
      })
      .then(blob => {
        blobUrl = URL.createObjectURL(blob);
        setImageBlobUrl(blobUrl);
        setLoading(false);
      })
      .catch(err => {
        if (err.name !== 'AbortError') {
          setError('Failed to load image. Please try again.');
          setLoading(false);
        }
      });

    return () => {
      controller.abort();
      if (blobUrl) URL.revokeObjectURL(blobUrl);
    };
  }, [isImage, pdfUrl, token]);

  const onDocumentLoadSuccess = useCallback(({ numPages: total }) => {
    setNumPages(total);
    setLoading(false);
    setError(null);
    if (initialPage && initialPage <= total) {
      setCurrentPage(initialPage);
    }
  }, [initialPage]);

  const onDocumentLoadError = useCallback((err) => {
    setError('Failed to load PDF. Please try again.');
    setLoading(false);
    console.error('PDF load error:', err);
  }, []);

  const goToPrevPage = () => setCurrentPage(p => Math.max(1, p - 1));
  const goToNextPage = () => setCurrentPage(p => Math.min(numPages || 1, p + 1));

  const handlePageInput = (e) => {
    if (e.key === 'Enter') {
      const val = parseInt(e.target.value, 10);
      if (val >= 1 && val <= numPages) {
        setCurrentPage(val);
      }
      e.target.value = '';
    }
  };

  const zoomIn = () => setScale(s => Math.min(3, s + 0.2));
  const zoomOut = () => setScale(s => Math.max(0.4, s - 0.2));

  return (
    <motion.div
      className="pdf-panel"
      initial={{ width: 0, opacity: 0 }}
      animate={{ width: '45%', opacity: 1 }}
      exit={{ width: 0, opacity: 0 }}
      transition={{ duration: 0.3, ease: 'easeInOut' }}
    >
      <div className="pdf-panel-header">
        <div className="pdf-panel-title">
          <span className="pdf-filename">{filename || 'Document'}</span>
          {!isImage && numPages && <span className="pdf-page-info">Page {currentPage} of {numPages}</span>}
          {isImage && <span className="pdf-page-info">Image</span>}
        </div>
        <div className="pdf-panel-actions">
          <button className="pdf-action-btn" onClick={zoomOut} title="Zoom out" disabled={loading || !!error}>
            <ZoomOut size={16} />
          </button>
          <span className="pdf-zoom-level">{Math.round(scale * 100)}%</span>
          <button className="pdf-action-btn" onClick={zoomIn} title="Zoom in" disabled={loading || !!error}>
            <ZoomIn size={16} />
          </button>
          <button className="pdf-close-btn" onClick={onClose} title="Close viewer">
            <X size={18} />
          </button>
        </div>
      </div>

      {!isImage && (
        <div className="pdf-controls">
          <button
            className="pdf-nav-btn"
            onClick={goToPrevPage}
            disabled={currentPage <= 1 || loading || !!error}
          >
            <ChevronLeft size={16} />
          </button>
          <input
            type="text"
            className="pdf-page-input"
            placeholder={numPages ? `1-${numPages}` : '...'}
            onKeyDown={handlePageInput}
            disabled={loading || !!error}
          />
          <button
            className="pdf-nav-btn"
            onClick={goToNextPage}
            disabled={currentPage >= (numPages || 1) || loading || !!error}
          >
            <ChevronRight size={16} />
          </button>
        </div>
      )}

      <div className="pdf-viewer-content" ref={containerRef}>
        {loading && (
          <div className="pdf-loading">
            <Loader size={32} className="spin" />
            <span>Loading {isImage ? 'image' : 'PDF'}...</span>
          </div>
        )}
        {error && (
          <div className="pdf-error">
            <span>{error}</span>
          </div>
        )}

        {isImage ? (
          imageBlobUrl && (
            <img
              src={imageBlobUrl}
              alt={filename}
              style={{ transform: `scale(${scale})`, transformOrigin: 'top left' }}
            />
          )
        ) : (
          <Document
            file={{ url: pdfUrl, httpHeaders: { Authorization: `Bearer ${token}` } }}
            onLoadSuccess={onDocumentLoadSuccess}
            onLoadError={onDocumentLoadError}
            loading=""
          >
            <Page
              pageNumber={currentPage}
              scale={scale}
              renderTextLayer={true}
              renderAnnotationLayer={true}
            />
          </Document>
        )}
      </div>
    </motion.div>
  );
}
