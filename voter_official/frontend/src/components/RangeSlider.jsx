import { useCallback } from 'react'
import './RangeSlider.css'

const MIN = 1
const MAX = 527

export default function RangeSlider({ start, end, onChange, disabled }) {
  const leftPct  = ((start - MIN) / (MAX - MIN)) * 100
  const rightPct = ((end   - MIN) / (MAX - MIN)) * 100

  const handleStart = useCallback((e) => {
    const v = Math.min(Number(e.target.value), end)
    onChange(v, end)
  }, [end, onChange])

  const handleEnd = useCallback((e) => {
    const v = Math.max(Number(e.target.value), start)
    onChange(start, v)
  }, [start, onChange])

  const count = end - start + 1

  return (
    <div className={`ni-wrapper ${disabled ? 'ni-disabled' : ''}`}>
      {/* Floating value bubbles above each thumb */}
      <div className="ni-bubbles" aria-hidden="true">
        <span className="ni-bubble ni-bubble-start" style={{ left: `${leftPct}%` }}>
          {start}
        </span>
        {start !== end && (
          <span className="ni-bubble ni-bubble-end" style={{ left: `${rightPct}%` }}>
            {end}
          </span>
        )}
      </div>

      {/* Track + fill + thumbs */}
      <div className="ni-track-area">
        <div className="ni-track" />
        <div
          className="ni-fill"
          style={{ left: `${leftPct}%`, right: `${100 - rightPct}%` }}
        />

        {/* Start thumb — raised z-index when at max so it stays draggable */}
        <input
          type="range"
          className="ni-input"
          min={MIN}
          max={MAX}
          value={start}
          onChange={handleStart}
          disabled={disabled}
          aria-label="Start part number"
          style={{ zIndex: start >= end ? 5 : 3 }}
        />

        {/* End thumb */}
        <input
          type="range"
          className="ni-input"
          min={MIN}
          max={MAX}
          value={end}
          onChange={handleEnd}
          disabled={disabled}
          aria-label="End part number"
          style={{ zIndex: 4 }}
        />
      </div>

      {/* Scale labels */}
      <div className="ni-scale">
        <span>Part 1</span>
        <span>Part 132</span>
        <span>Part 264</span>
        <span>Part 395</span>
        <span>Part 527</span>
      </div>

      {/* Summary badge */}
      <div className="ni-summary">
        <span className="ni-summary-range">
          Parts&nbsp;<strong>{start}</strong>&nbsp;—&nbsp;<strong>{end}</strong>
        </span>
        <span className="ni-summary-count">{count} part{count !== 1 ? 's' : ''} selected</span>
        {count > 100 && (
          <span className="ni-summary-warn">Large range — search may take longer</span>
        )}
      </div>
    </div>
  )
}
