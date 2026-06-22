import { useState, useEffect } from 'react'
import './App.css'
import PDFManager from './components/PDFManager'
import SearchInterface from './components/SearchInterface'
import Header from './components/Header'
import { API_URL } from './config'

function App() {
  const [apiReady, setApiReady] = useState(false)
  const [activeTab, setActiveTab] = useState('search')
  const [refreshTrigger, setRefreshTrigger] = useState(0)
  const [checking, setChecking] = useState(true)
  const [retryCount, setRetryCount] = useState(0)

  useEffect(() => {
    checkAPI()
  }, [])

  useEffect(() => {
    // Auto-retry if not ready (up to 30 seconds with exponential backoff)
    if (!apiReady && checking && retryCount < 6) {
      const delay = Math.min(1000 * Math.pow(2, retryCount), 30000)
      const timeout = setTimeout(() => {
        checkAPI()
      }, delay)
      return () => clearTimeout(timeout)
    }
  }, [apiReady, checking, retryCount])

  const checkAPI = async () => {
    setChecking(true)
    try {
      const response = await fetch(`${API_URL}/api/health`)
      if (response.ok) {
        setApiReady(true)
        setChecking(false)
        setRetryCount(0)
        console.log('✓ Backend API connected successfully')
      } else {
        throw new Error(`Health check returned ${response.status}`)
      }
    } catch (error) {
      console.error('API not available:', error.message)
      setApiReady(false)
      setChecking(false)
      setRetryCount(prev => prev + 1)
    }
  }

  const handleDownloadComplete = () => {
    setRefreshTrigger(prev => prev + 1)
  }

  return (
    <div className="app">
      <Header />
      
      {!apiReady && (
        <div className="api-warning">
          <div className="warning-content">
            <h3>⚠️ Backend API Not Connected</h3>
            <p>Make sure to run: <code>python backend_api.py</code></p>
            <p>API should be running at <code>{API_URL}</code></p>
            {checking && (
              <p className="retry-info">
                {retryCount === 0 
                  ? 'Checking connection...' 
                  : `Retrying... (Attempt ${retryCount})`}
              </p>
            )}
            {!checking && (
              <button onClick={checkAPI} className="retry-btn">
                🔄 Retry Connection
              </button>
            )}
          </div>
        </div>
      )}

      {apiReady && (
        <div className="container">
          <div className="tabs">
            <button 
              className={`tab-btn ${activeTab === 'search' ? 'active' : ''}`}
              onClick={() => setActiveTab('search')}
            >
              🔍 Search
            </button>
            <button 
              className={`tab-btn ${activeTab === 'manage' ? 'active' : ''}`}
              onClick={() => setActiveTab('manage')}
            >
              📥 Download PDFs
            </button>
          </div>

          <div className="tab-content">
            {activeTab === 'search' && (
              <SearchInterface refreshTrigger={refreshTrigger} />
            )}
            {activeTab === 'manage' && (
              <PDFManager onDownloadComplete={handleDownloadComplete} />
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default App
