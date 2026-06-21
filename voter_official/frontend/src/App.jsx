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

  useEffect(() => {
    checkAPI()
  }, [])

  const checkAPI = async () => {
    try {
      const response = await fetch(`${API_URL}/api/health`)
      if (response.ok) {
        setApiReady(true)
      }
    } catch (error) {
      console.error('API not available:', error)
      setApiReady(false)
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
            <button onClick={checkAPI} className="retry-btn">
              Retry Connection
            </button>
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
