import { useState } from 'react'
import './Auth.css'
import { API_URL } from '../config'

export default function Auth({ onLoginSuccess }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [showPassword, setShowPassword] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')

    if (!username.trim() || !password.trim()) {
      setError('Please enter both username and password')
      return
    }

    setLoading(true)

    try {
      const response = await fetch(`${API_URL}/api/auth`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: username.trim(),
          password: password.trim()
        })
      })

      const data = await response.json()

      if (data.success) {
        // Pass token to parent component
        onLoginSuccess(data.token)
        setUsername('')
        setPassword('')
      } else {
        setError(data.error || 'Authentication failed')
      }
    } catch (error) {
      setError('Connection error: ' + error.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-container">
      <div className="auth-card">
        <h2>🔐 Authentication Required</h2>
        <p className="auth-description">
          Sign in with your credentials to download PDFs
        </p>

        {error && <div className="auth-error">{error}</div>}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="username">Email</label>
            <input
              id="username"
              type="email"
              placeholder="your-email@example.com"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              disabled={loading}
              className="form-input"
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Password</label>
            <div className="password-input-wrapper">
              <input
                id="password"
                type={showPassword ? 'text' : 'password'}
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={loading}
                className="form-input"
              />
              <button
                type="button"
                className="password-toggle"
                onClick={() => setShowPassword(!showPassword)}
                title={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? '👁️' : '👁️‍🗨️'}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="auth-button"
          >
            {loading ? 'Authenticating...' : 'Login'}
          </button>
        </form>

        <div className="auth-hint">
          <p>Demo credentials:</p>
          <p><strong>Email:</strong> admin123@gmail.com</p>
          <p><strong>Password:</strong> admin123@!</p>
        </div>
      </div>
    </div>
  )
}
