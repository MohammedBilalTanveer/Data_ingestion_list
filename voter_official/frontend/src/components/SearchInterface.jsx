import { useState, useEffect } from 'react'
import './SearchInterface.css'
import { API_URL } from '../config'

export default function SearchInterface({ refreshTrigger }) {
  const [pdfs, setPdfs] = useState([])
  const [selectedParts, setSelectedParts] = useState([])
  const [searchQuery, setSearchQuery] = useState('')
  const [searching, setSearching] = useState(false)
  const [results, setResults] = useState(null)
  const [error, setError] = useState('')
  const [currentPage, setCurrentPage] = useState({})
  const [loading, setLoading] = useState(true)

  // Load PDFs on mount and when refreshTrigger changes
  useEffect(() => {
    loadPDFs()
  }, [refreshTrigger])

  const loadPDFs = async () => {
    try {
      setLoading(true)
      const response = await fetch(`${API_URL}/api/pdfs/list`)
      const data = await response.json()

      if (data.success) {
        const pdfList = data.pdfs || []
        setPdfs(pdfList)

        // Pre-select PDF 278 if available
        if (pdfList.some(p => p.part_number === 278)) {
          setSelectedParts([278])
        }
      }
    } catch (error) {
      setError('Failed to load PDF list')
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  const handlePartToggle = (partNumber) => {
    setSelectedParts(prev => {
      if (prev.includes(partNumber)) {
        return prev.filter(p => p !== partNumber)
      } else {
        return [...prev, partNumber]
      }
    })
    setCurrentPage({})
  }

  const handleSelectAll = () => {
    if (selectedParts.length === pdfs.length) {
      setSelectedParts([])
    } else {
      setSelectedParts(pdfs.map(p => p.part_number))
    }
    setCurrentPage({})
  }

  const handleSearch = async (e) => {
    e.preventDefault()
    setError('')
    setResults(null)
    setCurrentPage({})

    if (!searchQuery.trim() || searchQuery.length < 2) {
      setError('Search query must be at least 2 characters')
      return
    }

    if (selectedParts.length === 0) {
      setError('Please select at least one PDF')
      return
    }

    setSearching(true)

    try {
      const response = await fetch(`${API_URL}/api/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: searchQuery,
          part_numbers: selectedParts
        })
      })

      const data = await response.json()

      if (data.success) {
        setResults(data)
        setCurrentPage({})
      } else {
        setError(data.error || 'Search failed')
      }
    } catch (error) {
      setError('Error performing search: ' + error.message)
      console.error(error)
    } finally {
      setSearching(false)
    }
  }

  const handleClearResults = () => {
    setResults(null)
    setSearchQuery('')
    setCurrentPage({})
  }

  return (
    <div className="search-interface">
      <div className="search-container">
        {/* Search Form */}
        <form onSubmit={handleSearch} className="search-form">
          <div className="search-input-group">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Enter search query (name, number, keyword...)"
              className="search-input"
              disabled={searching}
              maxLength={100}
            />
            <button type="submit" disabled={searching} className="search-btn">
              {searching ? '⏳ Searching...' : '🔍 Search'}
            </button>
          </div>
        </form>

        {error && <div className="error-message">{error}</div>}

        {/* PDF Selection */}
        <div className="pdf-selection">
          <div className="selection-header">
            <h3>Select PDFs to Search</h3>
            <button 
              onClick={handleSelectAll}
              className="select-all-btn"
              disabled={loading || pdfs.length === 0}
            >
              {selectedParts.length === pdfs.length && pdfs.length > 0 ? 'Deselect All' : 'Select All'}
            </button>
          </div>

          {loading ? (
            <p className="loading">Loading PDFs...</p>
          ) : pdfs.length === 0 ? (
            <div className="no-pdfs-message">
              <p>📥 No PDFs downloaded yet</p>
              <small>Go to "Download PDFs" tab to download PDFs first</small>
            </div>
          ) : (
            <div className="pdf-checkboxes">
              {pdfs.map((pdf) => (
                <label key={pdf.part_number} className="pdf-checkbox-label">
                  <input
                    type="checkbox"
                    checked={selectedParts.includes(pdf.part_number)}
                    onChange={() => handlePartToggle(pdf.part_number)}
                    className="pdf-checkbox"
                  />
                  <span className="checkbox-custom"></span>
                  <span className="pdf-info">
                    <span className="pdf-part">Part {pdf.part_number}</span>
                    <span className="pdf-size">{pdf.size_mb} MB</span>
                  </span>
                </label>
              ))}
            </div>
          )}
        </div>

        {/* Selected Count */}
        {selectedParts.length > 0 && (
          <div className="selected-info">
            <span>📌 {selectedParts.length} PDF(s) selected</span>
          </div>
        )}
      </div>

      {/* Results Section */}
      {results && (
        <div className="results-section">
          <div className="results-header">
            <h2>🎯 Search Results</h2>
            <button onClick={handleClearResults} className="clear-btn">
              ✕ Clear Results
            </button>
          </div>

          <div className="results-summary">
            <p>
              Found <strong>{results.total_matches}</strong> match(es) for "<strong>{results.query}</strong>" 
              in <strong>{results.total_files_searched}</strong> PDF(s)
            </p>
          </div>

          {results.total_matches === 0 ? (
            <div className="no-results">
              <p>❌ No matches found</p>
              <small>Try a different search query or select more PDFs</small>
            </div>
          ) : (
            <div className="results-list">
              {Object.entries(results.results).map(([fileName, fileResults]) => (
                <ResultsCard 
                  key={fileName}
                  fileName={fileName}
                  fileResults={fileResults}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function ResultsCard({ fileName, fileResults }) {
  const [expanded, setExpanded] = useState(true)
  const [displayCount, setDisplayCount] = useState(10)
  const [viewingImage, setViewingImage] = useState(null)

  // Extract part number from results metadata or parse from filename
  const partNumber = fileResults.part_number || parseInt(fileName.replace(/[^0-9]/g, '').slice(-3)) || 0

  const handleViewPage = (page) => {
    if (viewingImage === page) {
      setViewingImage(null) // Toggle off
    } else {
      setViewingImage(page)
    }
  }

  return (
    <div className="results-card">
      <div className="card-header" onClick={() => setExpanded(!expanded)}>
        <div className="card-title">
          <span className="expand-icon">{expanded ? '▼' : '▶'}</span>
          <h4>📄 {fileName}</h4>
          <span className="match-count">{fileResults.count} matches</span>
        </div>
      </div>

      {expanded && (
        <div className="card-content">
          <div className="matches-list">
            {fileResults.matches.slice(0, displayCount).map((match, idx) => (
              <div key={idx} className="match-item">
                <div className="match-header">
                  <div className="match-header-left">
                    <span className="match-number">#{idx + 1}</span>
                    <span className="match-page">Page {match.page}</span>
                  </div>
                  <button 
                    className={`view-page-btn ${viewingImage === match.page ? 'active' : ''}`}
                    onClick={() => handleViewPage(match.page)}
                  >
                    {viewingImage === match.page ? '✖ Close Image' : '👁️ View Original Page'}
                  </button>
                </div>
                <div className="match-snippet">
                  {match.snippet}
                </div>
                
                {/* PDF Page Image Viewer */}
                {viewingImage === match.page && (
                  <div className="pdf-image-viewer">
                    <div className="image-loading-placeholder">Loading High Quality PDF Page...</div>
                    <img 
                      src={`${API_URL}/api/pdfs/render/${partNumber}/${match.page}`} 
                      alt={`PDF Part ${partNumber} Page ${match.page}`}
                      className="pdf-page-image"
                      loading="lazy"
                      onLoad={(e) => e.target.previousSibling.style.display = 'none'}
                      onError={(e) => {
                        e.target.previousSibling.innerText = 'Failed to load image. Ensure backend is running.';
                        e.target.style.display = 'none';
                      }}
                    />
                  </div>
                )}
              </div>
            ))}
          </div>

          {fileResults.count > displayCount && (
            <button
              onClick={() => setDisplayCount(displayCount + 10)}
              className="load-more-btn"
            >
              Load more ({fileResults.count - displayCount} remaining)
            </button>
          )}
        </div>
      )}
    </div>
  )
}
