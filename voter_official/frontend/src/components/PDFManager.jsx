import { useState, useEffect } from 'react'
import './PDFManager.css'
import { API_URL } from '../config'
import Auth from './Auth'

export default function PDFManager({ onDownloadComplete }) {
  const [pdfs, setPdfs] = useState([])
  const [loading, setLoading] = useState(false)
  const [downloadMode, setDownloadMode] = useState('range') // 'range' or 'specific'
  const [startPart, setStartPart] = useState(1)
  const [endPart, setEndPart] = useState(10)
  const [specificParts, setSpecificParts] = useState('278')
  const [downloading, setDownloading] = useState(false)
  const [downloadProgress, setDownloadProgress] = useState(null)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [authToken, setAuthToken] = useState(null)
  const [currentPage, setCurrentPage] = useState(1)
  const [itemsPerPage] = useState(20)
  const [totalPdfs, setTotalPdfs] = useState(0)
  const [totalPages, setTotalPages] = useState(0)

  // Load PDFs on mount
  useEffect(() => {
    loadPDFs()
  }, [currentPage])

  const handleLoginSuccess = (token) => {
    setAuthToken(token)
    setIsAuthenticated(true)
    setError('')
  }

  const handleLogout = () => {
    setAuthToken(null)
    setIsAuthenticated(false)
    setDownloading(false)
    setDownloadProgress(null)
  }

  // Poll download status while downloading
  useEffect(() => {
    if (!downloading) return

    const interval = setInterval(async () => {
      try {
        const response = await fetch(`${API_URL}/api/downloads/status`)
        const data = await response.json()
        setDownloadProgress(data)

        if (!data.in_progress) {
          setDownloading(false)
          if (data.status === 'cancelled') {
            setSuccess(`✅ Download cancelled. Completed: ${data.completed_parts}, Failed: ${data.failed_parts}`)
          } else {
            setSuccess(`✅ Download completed! Completed: ${data.completed_parts}, Failed: ${data.failed_parts}`)
          }
          loadPDFs()
          onDownloadComplete()
        }
      } catch (error) {
        console.error('Error polling download status:', error)
      }
    }, 1000)

    return () => clearInterval(interval)
  }, [downloading, onDownloadComplete])

  const loadPDFs = async () => {
    try {
      setLoading(true)
      setError('')
      const response = await fetch(`${API_URL}/api/pdfs/list?page=${currentPage}&per_page=${itemsPerPage}`)
      const data = await response.json()

      if (data.success) {
        setPdfs(data.pdfs || [])
        setTotalPdfs(data.total || 0)
        setTotalPages(data.total_pages || 0)
      }
    } catch (error) {
      setError('Failed to load PDF list')
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  const handleCancelDownload = async () => {
    try {
      const response = await fetch(`${API_URL}/api/downloads/cancel`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      })

      const data = await response.json()

      if (data.success) {
        setSuccess(`✓ Cancellation requested. Completed: ${data.completed_parts}`)
      } else {
        setError(data.error || 'Failed to cancel download')
      }
    } catch (error) {
      setError('Error cancelling download: ' + error.message)
    }
  }

  const handleDownload = async () => {
    setError('')
    setSuccess('')

    if (!isAuthenticated) {
      setError('Please login first to download PDFs')
      return
    }

    try {
      let partNumbers = []

      if (downloadMode === 'range') {
        if (!startPart || !endPart) {
          setError('Please enter valid start and end part numbers')
          return
        }

        if (parseInt(startPart) > parseInt(endPart)) {
          setError('Start part must be less than or equal to end part')
          return
        }

        if (parseInt(startPart) < 1 || parseInt(endPart) > 527) {
          setError('Part numbers must be between 1 and 527')
          return
        }
      } else {
        // Specific parts mode
        partNumbers = specificParts
          .split(',')
          .map(p => parseInt(p.trim()))
          .filter(p => !isNaN(p) && p > 0 && p <= 527)

        if (partNumbers.length === 0) {
          setError('Please enter valid part numbers (1-527)')
          return
        }
      }

      const requestData = downloadMode === 'range'
        ? {
            start_part: parseInt(startPart),
            end_part: parseInt(endPart),
            token: authToken
          }
        : {
            start_part: Math.min(...partNumbers),
            end_part: Math.max(...partNumbers),
            token: authToken
          }

      const response = await fetch(`${API_URL}/api/pdfs/download`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestData)
      })

      const data = await response.json()

      if (data.success) {
        setDownloading(true)
        setDownloadProgress({
          in_progress: true,
          current_part: 0,
          total_parts: data.total_pdfs,
          completed_parts: 0,
          failed_parts: 0,
          status: 'downloading'
        })
      } else {
        setError(data.error || 'Download failed')
      }
    } catch (error) {
      setError('Error starting download: ' + error.message)
      console.error(error)
    }
  }

  return (
    <>
      {!isAuthenticated && <Auth onLoginSuccess={handleLoginSuccess} />}
      
      <div className="pdf-manager" style={{ opacity: !isAuthenticated ? 0.5 : 1 }}>
        <div className="manager-card">
          <div className="manager-header">
            <h2>📥 Download PDFs</h2>
            {isAuthenticated && (
              <button onClick={handleLogout} className="logout-btn" title="Logout">
                🚪 Logout
              </button>
            )}
          </div>
          <p className="description">
            Select PDFs to download and store persistently in AWS S3.
          </p>

          {error && <div className="error-message">{error}</div>}
          {success && <div className="success-message">{success}</div>}

          {/* Download Mode Selector */}
          <div className="mode-selector">
            <label className="mode-option">
              <input
                type="radio"
                value="range"
                checked={downloadMode === 'range'}
                onChange={(e) => setDownloadMode(e.target.value)}
                disabled={downloading}
              />
              <span>Download Range</span>
            </label>
            <label className="mode-option">
              <input
                type="radio"
                value="specific"
                checked={downloadMode === 'specific'}
                onChange={(e) => setDownloadMode(e.target.value)}
                disabled={downloading}
              />
              <span>Specific PDFs</span>
            </label>
          </div>

          {/* Range Input */}
          {downloadMode === 'range' && (
            <div className="input-group">
              <div className="input-row">
                <div className="form-group">
                  <label>Start Part Number</label>
                  <input
                    type="number"
                    min="1"
                    max="527"
                    value={startPart}
                    onChange={(e) => setStartPart(e.target.value)}
                    disabled={downloading}
                    placeholder="1"
                  />
                </div>
                <div className="form-group">
                  <label>End Part Number</label>
                  <input
                    type="number"
                    min="1"
                    max="527"
                    value={endPart}
                    onChange={(e) => setEndPart(e.target.value)}
                    disabled={downloading}
                    placeholder="10"
                  />
                </div>
              </div>
              <div className="preset-buttons">
                <button
                  onClick={() => { setStartPart(1); setEndPart(10) }}
                  disabled={downloading}
                  className="preset-btn"
                >
                  1-10
                </button>
                <button
                  onClick={() => { setStartPart(1); setEndPart(50) }}
                  disabled={downloading}
                  className="preset-btn"
                >
                  1-50
                </button>
                <button
                  onClick={() => { setStartPart(1); setEndPart(100) }}
                  disabled={downloading}
                  className="preset-btn"
                >
                  1-100
                </button>
                <button
                  onClick={() => { setStartPart(278); setEndPart(278) }}
                  disabled={downloading}
                  className="preset-btn"
                >
                  Only 278
                </button>
              </div>
            </div>
          )}

          {/* Specific Parts Input */}
          {downloadMode === 'specific' && (
            <div className="input-group">
              <div className="form-group">
                <label>Enter Part Numbers (comma-separated)</label>
                <input
                  type="text"
                  value={specificParts}
                  onChange={(e) => setSpecificParts(e.target.value)}
                  disabled={downloading}
                  placeholder="e.g., 1, 5, 10, 278"
                />
                <small>Enter 1-527, separated by commas</small>
              </div>
            </div>
          )}

          {/* Download Buttons */}
          <div className="button-group">
            <button
              onClick={handleDownload}
              disabled={downloading || loading || !isAuthenticated}
              className={`download-btn ${downloading ? 'downloading' : ''}`}
            >
              {downloading ? '⏳ Downloading...' : '⬇️ Start Download'}
            </button>
            {downloading && (
              <button
                onClick={handleCancelDownload}
                className="cancel-btn"
              >
                ❌ Cancel Download
              </button>
            )}
          </div>

          {/* Progress Bar */}
          {downloadProgress && downloadProgress.in_progress && (
            <div className="progress-section">
              <div className="progress-info">
                <span>
                  Part {downloadProgress.current_part} of {downloadProgress.total_parts}
                </span>
                <span className="progress-count">
                  ✓ {downloadProgress.completed_parts} | ✗ {downloadProgress.failed_parts}
                </span>
              </div>
              <div className="progress-bar">
                <div
                  className="progress-fill"
                  style={{
                    width: `${(downloadProgress.completed_parts / downloadProgress.total_parts) * 100}%`
                  }}
                />
              </div>
              <p className="progress-status">
                Status: <strong>{downloadProgress.status.toUpperCase()}</strong>
              </p>
            </div>
          )}

          {/* Downloaded PDFs List */}
          <div className="pdfs-list">
            <div className="pdfs-list-header">
              <h3>📁 Downloaded PDFs (Total: {totalPdfs})</h3>
            </div>
            {loading ? (
              <div className="loading-skeleton">
                <p>🔄 Loading PDFs...</p>
              </div>
            ) : pdfs.length === 0 ? (
              <p className="no-pdfs">No PDFs downloaded yet. Start downloading to see them here.</p>
            ) : (
              <>
                <div className="pdf-grid">
                  {pdfs.map((pdf) => (
                    <div key={pdf.filename} className="pdf-item">
                      <div className="pdf-number">#{pdf.part_number}</div>
                      <div className="pdf-filename">{pdf.filename}</div>
                      <div className="pdf-size">{pdf.size_mb} MB</div>
                    </div>
                  ))}
                </div>
                {totalPages > 1 && (
                  <div className="pagination">
                    <button
                      onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                      disabled={currentPage === 1}
                      className="pagination-btn"
                    >
                      ← Previous
                    </button>
                    <span className="pagination-info">
                      Page {currentPage} of {totalPages}
                    </span>
                    <button
                      onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                      disabled={currentPage >= totalPages}
                      className="pagination-btn"
                    >
                      Next →
                    </button>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </>
  )
}
