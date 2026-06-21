import './Header.css'

export default function Header() {
  return (
    <header className="header">
      <div className="header-content">
        <div className="header-left">
          <h1 className="app-title">🗳️ Voter List Search</h1>
          <p className="app-subtitle">Karnataka Voter List PDF Search Tool</p>
        </div>
        <div className="header-info">
          <div className="info-item">
            <span className="label">District:</span>
            <span className="value">Bangalore Urban</span>
          </div>
          <div className="info-item">
            <span className="label">AC:</span>
            <span className="value">88 (Yelahanka)</span>
          </div>
          <div className="info-item">
            <span className="label">Max PDFs:</span>
            <span className="value">527</span>
          </div>
        </div>
      </div>
    </header>
  )
}
