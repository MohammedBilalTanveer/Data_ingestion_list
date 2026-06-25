import { useState, useEffect } from 'react'
import './PDFManager.css'
import { API_URL } from '../config'
import LoginPage from './LoginPage'

export default function PDFManager({ onDownloadComplete }) {
  const [authed, setAuthed] = useState(
    () => sessionStorage.getItem('voter_download_auth') === '1'
  )

  const handleLogin  = () => setAuthed(true)
  const handleLogout = () => {
    sessionStorage.removeItem('voter_download_auth')
    setAuthed(false)
  }

  if (!authed) return <LoginPage onLogin={handleLogin} />

  return <DownloadPanel onDownloadComplete={onDownloadComplete} onLogout={handleLogout} />
}

/* ── Download panel (shown after login) ─────────────────────────────────────── */
function DownloadPanel({ onDownloadComplete, onLogout }) {
  const [pdfs,             setPdfs]             = useState([])
  const [loading,          setLoading]          = useState(false)
  const [downloadMode,     setDownloadMode]     = useState('range')
  const [startPart,        setStartPart]        = useState(1)
  const [endPart,          setEndPart]          = useState(10)
  const [specificParts,    setSpecificParts]    = useState('278')
  const [downloading,      setDownloading]      = useState(false)
  const [downloadProgress, setDownloadProgress] = useState(null)
  const [error,            setError]            = useState('')
  const [success,          setSuccess]          = useState('')

  useEffect(() => { loadPDFs() }, [])

  // Poll status while downloading
  useEffect(() => {
    if (!downloading) return
    const iv = setInterval(async () => {
      try {
        const res  = await fetch(`${API_URL}/api/downloads/status`)
        const data = await res.json()
        setDownloadProgress(data)
        if (!data.in_progress) {
          setDownloading(false)
          setSuccess('✅ Download complete!')
          loadPDFs()
          onDownloadComplete()
        }
      } catch { /* network glitch — ignore */ }
    }, 2000) // poll every 2 s (was 1 s, halved to reduce requests)
    return () => clearInterval(iv)
  }, [downloading, onDownloadComplete])

  const loadPDFs = async () => {
    try {
      setLoading(true)
      setError('')
      const res  = await fetch(`${API_URL}/api/pdfs/list`)
      const data = await res.json()
      if (data.success) setPdfs(data.pdfs || [])
    } catch {
      setError('Failed to load PDF list')
    } finally {
      setLoading(false)
    }
  }

  const handleDownload = async () => {
    setError('')
    setSuccess('')

    let requestData
    if (downloadMode === 'range') {
      const s = parseInt(startPart), e = parseInt(endPart)
      if (!s || !e || s > e || s < 1 || e > 527) {
        setError('Part numbers must be between 1–527, start ≤ end')
        return
      }
      requestData = { start_part: s, end_part: e }
    } else {
      const parts = specificParts
        .split(',')
        .map(p => parseInt(p.trim()))
        .filter(p => !isNaN(p) && p >= 1 && p <= 527)
      if (parts.length === 0) {
        setError('Enter valid part numbers (1–527, comma-separated)')
        return
      }
      requestData = { start_part: Math.min(...parts), end_part: Math.max(...parts) }
    }

    try {
      const res  = await fetch(`${API_URL}/api/pdfs/download`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify(requestData)
      })
      const data = await res.json()
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
    } catch (err) {
      setError('Error starting download: ' + err.message)
    }
  }

  const progressPct = downloadProgress
    ? Math.round((downloadProgress.completed_parts / Math.max(downloadProgress.total_parts, 1)) * 100)
    : 0

  return (
    <div className="pdf-manager">
      <div className="manager-card">
        {/* Header with logout */}
        <div className="manager-header">
          <h2>📥 Download PDFs</h2>
          <button className="logout-btn" onClick={onLogout}>🚪 Logout</button>
        </div>

        <p className="description">
          Download voter list PDFs from the Karnataka CEO portal. Parts range from 1 to 527.
        </p>

        {error   && <div className="error-message">{error}</div>}
        {success && <div className="success-message">{success}</div>}

        {/* Mode selector */}
        <div className="mode-selector">
          {['range', 'specific'].map(mode => (
            <label key={mode} className="mode-option">
              <input
                type="radio"
                value={mode}
                checked={downloadMode === mode}
                onChange={() => setDownloadMode(mode)}
                disabled={downloading}
              />
              <span>{mode === 'range' ? 'Part Range' : 'Specific Parts'}</span>
            </label>
          ))}
        </div>

        {/* Range inputs */}
        {downloadMode === 'range' && (
          <div className="input-group">
            <div className="input-row">
              <div className="form-group">
                <label>Start Part</label>
                <input
                  type="number" min="1" max="527"
                  value={startPart}
                  onChange={e => setStartPart(e.target.value)}
                  disabled={downloading}
                  placeholder="1"
                />
              </div>
              <div className="form-group">
                <label>End Part</label>
                <input
                  type="number" min="1" max="527"
                  value={endPart}
                  onChange={e => setEndPart(e.target.value)}
                  disabled={downloading}
                  placeholder="10"
                />
              </div>
            </div>

            <div className="preset-buttons">
              {[[1,10],[1,50],[1,100],[278,278]].map(([s,e]) => (
                <button
                  key={`${s}-${e}`}
                  className="preset-btn"
                  disabled={downloading}
                  onClick={() => { setStartPart(s); setEndPart(e) }}
                >
                  {s === e ? `Part ${s}` : `${s}–${e}`}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Specific parts input */}
        {downloadMode === 'specific' && (
          <div className="input-group">
            <div className="form-group">
              <label>Part Numbers (comma-separated)</label>
              <input
                type="text"
                value={specificParts}
                onChange={e => setSpecificParts(e.target.value)}
                disabled={downloading}
                placeholder="e.g., 1, 5, 10, 278"
              />
              <small>Enter values between 1–527</small>
            </div>
          </div>
        )}

        <button
          className={`download-btn ${downloading ? 'downloading' : ''}`}
          onClick={handleDownload}
          disabled={downloading || loading}
        >
          {downloading ? '⏳ Downloading…' : '⬇️ Start Download'}
        </button>

        {/* Progress */}
        {downloadProgress?.in_progress && (
          <div className="progress-section">
            <div className="progress-info">
              <span>Part {downloadProgress.current_part} of {downloadProgress.total_parts}</span>
              <span className="progress-count">
                ✓ {downloadProgress.completed_parts} | ✗ {downloadProgress.failed_parts}
              </span>
            </div>
            <div className="progress-bar">
              <div className="progress-fill" style={{ width: `${progressPct}%` }} />
            </div>
            <div className="progress-status">
              <strong>{progressPct}%</strong> complete
            </div>
          </div>
        )}

        {/* PDF list */}
        <div className="pdfs-list">
          <h3>📁 Downloaded PDFs ({pdfs.length})</h3>
          {loading ? (
            <p className="loading">Loading…</p>
          ) : pdfs.length === 0 ? (
            <p className="no-pdfs">No PDFs downloaded yet</p>
          ) : (
            <div className="pdf-grid">
              {pdfs.map(pdf => (
                <div key={pdf.filename} className="pdf-item">
                  <div className="pdf-number">#{pdf.part_number}</div>
                  <div className="pdf-filename">{pdf.filename}</div>
                  <div className="pdf-size">{pdf.size_mb} MB</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
