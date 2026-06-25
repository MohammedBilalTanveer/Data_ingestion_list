import { useState, useCallback, useEffect, useRef } from 'react'
import './SearchInterface.css'
import { API_URL } from '../config'
import RangeSlider from './RangeSlider'

export default function SearchInterface() {
  const [startPart,  setStartPart]  = useState(1)
  const [endPart,    setEndPart]    = useState(10)
  const [query,      setQuery]      = useState('')
  const [searching,  setSearching]  = useState(false)
  const [error,      setError]      = useState('')

  // Translation
  const [translateOn,      setTranslateOn]      = useState(false)
  const [kannadaPreview,   setKannadaPreview]   = useState('')   // live preview
  const [previewLoading,   setPreviewLoading]   = useState(false)
  const [translatedQuery,  setTranslatedQuery]  = useState('')   // used in results

  // Streaming result state
  const [results,       setResults]       = useState({})   // { "Part N": resultObj }
  const [progress,      setProgress]      = useState(null) // { searched, total, done }
  const [totalMatches,  setTotalMatches]  = useState(0)
  const [searchedQuery, setSearchedQuery] = useState('')

  const hasResults = Object.keys(results).length > 0

  const handleRangeChange = useCallback((s, e) => {
    setStartPart(s)
    setEndPart(e)
  }, [])

  // Debounced live Kannada preview — fires 600 ms after the user stops typing
  const previewTimer = useRef(null)
  useEffect(() => {
    if (!translateOn || query.trim().length < 2) {
      setKannadaPreview('')
      return
    }
    clearTimeout(previewTimer.current)
    previewTimer.current = setTimeout(async () => {
      setPreviewLoading(true)
      try {
        const res  = await fetch(`${API_URL}/api/translate`, {
          method:  'POST',
          headers: { 'Content-Type': 'application/json' },
          body:    JSON.stringify({ text: query.trim() })
        })
        const data = await res.json()
        if (data.success) setKannadaPreview(data.translated)
      } catch { /* silent — preview is best-effort */ }
      finally { setPreviewLoading(false) }
    }, 600)
    return () => clearTimeout(previewTimer.current)
  }, [query, translateOn])

  const handleSearch = async (ev) => {
    ev.preventDefault()
    setError('')
    setResults({})
    setProgress(null)
    setTotalMatches(0)
    setSearchedQuery('')

    if (!query.trim() || query.length < 2) {
      setError('Search query must be at least 2 characters')
      return
    }

    const partNumbers = Array.from(
      { length: endPart - startPart + 1 },
      (_, i) => startPart + i
    )

    setSearching(true)
    setTranslatedQuery('')

    try {
      const response = await fetch(`${API_URL}/api/search/stream`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ query: query.trim(), part_numbers: partNumbers, translate: translateOn })
      })

      if (!response.ok) {
        const err = await response.json().catch(() => ({}))
        throw new Error(err.error || `HTTP ${response.status}`)
      }

      const reader  = response.body.getReader()
      const decoder = new TextDecoder()
      let   buffer  = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })

        // SSE events are delimited by double newlines
        const events = buffer.split('\n\n')
        buffer = events.pop() // last element may be incomplete

        for (const event of events) {
          const dataLine = event.split('\n').find(l => l.startsWith('data: '))
          if (!dataLine) continue

          let payload
          try { payload = JSON.parse(dataLine.slice(6)) } catch { continue }

          if (payload.type === 'start') {
            setProgress({ searched: 0, total: payload.total, done: false })
            if (payload.translated_query) setTranslatedQuery(payload.translated_query)

          } else if (payload.type === 'result') {
            setProgress({ searched: payload.searched, total: payload.total, done: false })
            setTotalMatches(payload.total_matches)
            const key = `Part ${payload.data.part_number}`
            setResults(prev => ({ ...prev, [key]: payload.data }))

          } else if (payload.type === 'progress') {
            setProgress({ searched: payload.searched, total: payload.total, done: false })
            setTotalMatches(payload.total_matches)

          } else if (payload.type === 'done') {
            setProgress({ searched: payload.searched, total: payload.total, done: true })
            setTotalMatches(payload.total_matches)
            setSearchedQuery(payload.query)
            if (payload.translated_query) setTranslatedQuery(payload.translated_query)
            setSearching(false)
          }
        }
      }
    } catch (err) {
      setError('Search error: ' + err.message)
      setSearching(false)
    }
  }

  const handleClear = () => {
    setResults({})
    setProgress(null)
    setTotalMatches(0)
    setSearchedQuery('')
    setError('')
    setQuery('')
  }

  // Sort result entries by part number for consistent ordering
  const sortedEntries = Object.entries(results).sort(
    ([, a], [, b]) => a.part_number - b.part_number
  )

  return (
    <div className="search-interface">
      <div className="search-container">

        {/* Search form */}
        <form onSubmit={handleSearch} className="search-form">
          <div className="search-input-group">
            <input
              type="text"
              value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder={translateOn ? 'Type name in English — will search in Kannada…' : 'Enter name, voter ID, number…'}
              className="search-input"
              disabled={searching}
              maxLength={100}
            />
            <button
              type="button"
              className={`translate-toggle ${translateOn ? 'translate-on' : ''}`}
              onClick={() => { setTranslateOn(v => !v); setKannadaPreview('') }}
              disabled={searching}
              title={translateOn ? 'Disable Kannada translation' : 'Enable Kannada translation'}
            >
              {translateOn ? '🌐 ಕನ್ನಡ ON' : '🌐 ಕನ್ನಡ'}
            </button>
            <button type="submit" disabled={searching} className="search-btn">
              {searching ? '⏳ Searching…' : '🔍 Search'}
            </button>
          </div>

          {/* Live Kannada preview */}
          {translateOn && (
            <div className="kannada-preview">
              {previewLoading
                ? <span className="kp-loading">Translating…</span>
                : kannadaPreview
                  ? <><span className="kp-label">Will search in Kannada:</span> <span className="kp-text">{kannadaPreview}</span></>
                  : <span className="kp-hint">Type a name above to see its Kannada translation</span>
              }
            </div>
          )}
        </form>

        {error && <div className="error-message">{error}</div>}

        {/* Numerical Interval selector */}
        <div className="pdf-selection">
          <div className="selection-header">
            <h3>Numerical Interval — Select Part Range</h3>
          </div>
          <RangeSlider
            start={startPart}
            end={endPart}
            onChange={handleRangeChange}
            disabled={searching}
          />
          <div className="preset-row">
            <span className="preset-label">Quick:</span>
            {[[1,10],[1,50],[1,100],[278,278],[1,527]].map(([s,e]) => (
              <button
                key={`${s}-${e}`}
                className="preset-chip"
                onClick={() => { setStartPart(s); setEndPart(e) }}
                disabled={searching}
              >
                {s === e ? `Part ${s}` : `${s}–${e}`}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ── Live streaming progress bar ── */}
      {progress && (
        <div className={`stream-progress-bar ${progress.done ? 'stream-done' : 'stream-active'}`}>
          <div className="stream-track">
            <div
              className="stream-fill"
              style={{ width: `${Math.round((progress.searched / Math.max(progress.total, 1)) * 100)}%` }}
            />
          </div>
          <div className="stream-labels">
            <span className="stream-status">
              {progress.done
                ? `✓ Done — ${progress.total} part${progress.total !== 1 ? 's' : ''} searched`
                : `Searching ${progress.searched} / ${progress.total} parts…`}
            </span>
            {totalMatches > 0 && (
              <span className="stream-match-pill">{totalMatches} match{totalMatches !== 1 ? 'es' : ''} found</span>
            )}
          </div>
        </div>
      )}

      {/* ── Results (appear progressively) ── */}
      {(hasResults || (progress?.done && totalMatches === 0)) && (
        <div className="results-section">
          <div className="results-header">
            <h2>🎯 Results</h2>
            <button onClick={handleClear} className="clear-btn">✕ Clear</button>
          </div>

          {progress?.done && (
            <div className="results-summary">
              <p>
                Found <strong>{totalMatches}</strong> match{totalMatches !== 1 ? 'es' : ''} for&nbsp;
                "<strong>{searchedQuery}</strong>"
                {translatedQuery && (
                  <span className="translated-label"> → searched as "<strong className="kannada-result">{translatedQuery}</strong>" in Kannada</span>
                )}
                &nbsp;in <strong>{sortedEntries.length}</strong> PDF{sortedEntries.length !== 1 ? 's' : ''}&nbsp;
                <span className="summary-range">(Parts {startPart}–{endPart})</span>
              </p>
              {totalMatches === 0 && progress.searched > 0 && (
                <p className="no-pdf-hint">
                  No matches — try a different query or download more PDFs in this range.
                </p>
              )}
              {progress.searched > 0 && sortedEntries.length === 0 && totalMatches === 0 && (
                <p className="no-pdf-hint">
                  No PDFs were found in this range. Go to the Download tab to fetch them first.
                </p>
              )}
            </div>
          )}

          {/* Streaming skeleton cards for parts still being searched */}
          {searching && (
            <div className="stream-hint">
              Results appear as each PDF finishes — keep scrolling
            </div>
          )}

          {sortedEntries.length === 0 && progress?.done ? (
            <div className="no-results">
              <p>No matches found</p>
              <small>Try a different query or expand the range</small>
            </div>
          ) : (
            <div className="results-list">
              {sortedEntries.map(([key, fileResults]) => (
                <ResultsCard key={key} fileName={key} fileResults={fileResults} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

/* ── Individual result card ─────────────────────────────────────────────────── */
function ResultsCard({ fileName, fileResults }) {
  const [expanded,     setExpanded]     = useState(true)
  const [displayCount, setDisplayCount] = useState(10)
  const [viewingImage, setViewingImage] = useState(null)

  const partNumber = fileResults.part_number ||
    parseInt(fileName.replace(/[^0-9]/g, '').slice(-3)) || 0

  const toggleImage = (page) =>
    setViewingImage(v => (v === page ? null : page))

  return (
    <div className="results-card results-card-enter">
      <div className="card-header" onClick={() => setExpanded(x => !x)}>
        <div className="card-title">
          <span className="expand-icon">{expanded ? '▼' : '▶'}</span>
          <h4>📄 {fileName}</h4>
          <span className="match-count">{fileResults.count} match{fileResults.count !== 1 ? 'es' : ''}</span>
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
                    onClick={() => toggleImage(match.page)}
                  >
                    {viewingImage === match.page ? '✖ Close' : '👁️ View Page'}
                  </button>
                </div>

                <div className="match-snippet">{match.snippet}</div>

                {viewingImage === match.page && (
                  <div className="pdf-image-viewer">
                    <div className="image-loading-placeholder">Loading page…</div>
                    <img
                      src={`${API_URL}/api/pdfs/render/${partNumber}/${match.page}`}
                      alt={`Part ${partNumber} Page ${match.page}`}
                      className="pdf-page-image"
                      loading="lazy"
                      onLoad={e => (e.target.previousSibling.style.display = 'none')}
                      onError={e => {
                        e.target.previousSibling.innerText = 'Failed to load image.'
                        e.target.style.display = 'none'
                      }}
                    />
                  </div>
                )}
              </div>
            ))}
          </div>

          {fileResults.count > displayCount && (
            <button
              onClick={() => setDisplayCount(c => c + 10)}
              className="load-more-btn"
            >
              Load {Math.min(10, fileResults.count - displayCount)} more
              ({fileResults.count - displayCount} remaining)
            </button>
          )}
        </div>
      )}
    </div>
  )
}
