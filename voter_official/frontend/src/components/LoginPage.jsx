import { useState } from 'react'
import { createPortal } from 'react-dom'
import './LoginPage.css'

// Credentials are baked at build-time from env vars.
// Change VITE_DOWNLOAD_USER / VITE_DOWNLOAD_PASS in .env.local or Vercel settings.
const VALID_USER = import.meta.env.VITE_DOWNLOAD_USER || 'admin'
const VALID_PASS = import.meta.env.VITE_DOWNLOAD_PASS || 'voter@2024'

export default function LoginPage({ onLogin }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPass, setShowPass] = useState(false)
  const [error,    setError]    = useState('')
  const [loading,  setLoading]  = useState(false)

  const handleSubmit = (e) => {
    e.preventDefault()
    setError('')

    if (!username.trim() || !password) {
      setError('Please enter both username and password.')
      return
    }

    setLoading(true)

    // Small artificial delay for a natural feel
    setTimeout(() => {
      if (username.trim() === VALID_USER && password === VALID_PASS) {
        sessionStorage.setItem('voter_download_auth', '1')
        onLogin()
      } else {
        setError('Invalid username or password. Please try again.')
        setLoading(false)
      }
    }, 700)
  }

  // Use a portal so the overlay renders directly in document.body.
  // This escapes the .tab-content CSS animation stacking context that would
  // otherwise prevent position:fixed from covering the full viewport.
  return createPortal(
    <div className="lp-overlay">
      {/* Tricolor top bar */}
      <div className="lp-tricolor">
        <span className="lp-saffron" />
        <span className="lp-white" />
        <span className="lp-green" />
      </div>

      <div className="lp-card">
        {/* Emblem / logo area */}
        <div className="lp-logo-area">
          <div className="lp-shield">
            <span className="lp-shield-icon">🗳️</span>
          </div>
          <div className="lp-org-name">
            <span className="lp-org-top">Government of Karnataka</span>
            <span className="lp-org-main">Election Commission</span>
          </div>
        </div>

        <div className="lp-divider" />

        <h1 className="lp-title">Voter List Management</h1>
        <p className="lp-subtitle">
          <span className="lp-lock">🔒</span>
          Restricted Access — Authorized Personnel Only
        </p>

        <form onSubmit={handleSubmit} className="lp-form" autoComplete="off">
          {/* Username */}
          <div className="lp-field">
            <label htmlFor="lp-user" className="lp-label">Username</label>
            <div className="lp-input-wrap">
              <span className="lp-input-icon">👤</span>
              <input
                id="lp-user"
                type="text"
                className="lp-input"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Enter your username"
                disabled={loading}
                autoComplete="username"
              />
            </div>
          </div>

          {/* Password */}
          <div className="lp-field">
            <label htmlFor="lp-pass" className="lp-label">Password</label>
            <div className="lp-input-wrap">
              <span className="lp-input-icon">🔑</span>
              <input
                id="lp-pass"
                type={showPass ? 'text' : 'password'}
                className="lp-input lp-input-pass"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter your password"
                disabled={loading}
                autoComplete="current-password"
              />
              <button
                type="button"
                className="lp-toggle-pass"
                onClick={() => setShowPass(v => !v)}
                tabIndex={-1}
                aria-label={showPass ? 'Hide password' : 'Show password'}
              >
                {showPass ? '🙈' : '👁️'}
              </button>
            </div>
          </div>

          {error && (
            <div className="lp-error" role="alert">
              ⚠️ {error}
            </div>
          )}

          <button
            type="submit"
            className={`lp-submit ${loading ? 'lp-submit-loading' : ''}`}
            disabled={loading}
          >
            {loading ? (
              <span className="lp-spinner-row">
                <span className="lp-spinner" />
                Verifying…
              </span>
            ) : 'Sign In'}
          </button>
        </form>

        <p className="lp-footer">
          Karnataka Chief Electoral Officer &nbsp;|&nbsp; Yelahanka AC-88
        </p>
      </div>

      {/* Bottom tricolor bar */}
      <div className="lp-tricolor lp-tricolor-bottom">
        <span className="lp-saffron" />
        <span className="lp-white" />
        <span className="lp-green" />
      </div>
    </div>,
    document.body
  )
}
