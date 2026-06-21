# 🗳️ Voter List PDF Search - Complete Application

A professional React + Python Flask web application for downloading and searching Karnataka voter lists PDF documents.

## 📋 Features

- **📥 PDF Download Manager**
  - Download PDFs by range (e.g., 1-10, 1-100)
  - Download specific PDF numbers (e.g., 278)
  - Preset buttons for quick selection
  - Real-time download progress tracking
  - Automatic retry on failure

- **🔍 Advanced Search**
  - Search across multiple PDFs simultaneously
  - Case-insensitive search (default)
  - Minimum 2 characters query
  - Context-aware results (shows surrounding lines)
  - Paginated results with "load more" functionality
  - Support for Kannada text

- **🎨 Professional UI**
  - Modern gradient design
  - Responsive layout (desktop, tablet, mobile)
  - Real-time progress indicators
  - Smooth animations and transitions
  - Accessible components

## 🏗️ Project Structure

```
voter_official/
├── frontend/                 # React application
│   ├── src/
│   │   ├── components/      # React components
│   │   │   ├── Header.jsx
│   │   │   ├── PDFManager.jsx
│   │   │   └── SearchInterface.jsx
│   │   ├── App.jsx
│   │   └── App.css
│   ├── package.json
│   └── vite.config.js
├── backend_api.py           # Flask backend API
├── voter_download\ and\ search.py.py  # Original Python CLI tool
├── requirements.txt         # Python dependencies
└── output/
    └── pdfs/               # Downloaded PDFs stored here
```

## 🚀 Quick Start

### Prerequisites

- Python 3.7+
- Node.js 14+
- npm or yarn

### Step 1: Setup Backend

```bash
# Install Python dependencies
pip install -r requirements.txt

# Start the Flask API server
python backend_api.py
```

The API will run at `http://localhost:5000`

### Step 2: Setup Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The React app will run at `http://localhost:5173`

### Step 3: Use the Application

1. Open `http://localhost:5173` in your browser
2. Go to "Download PDFs" tab
3. Choose download mode:
   - **Range**: Select start and end part numbers (or use presets)
   - **Specific**: Enter specific PDF numbers comma-separated
4. Click "Start Download"
5. Once downloaded, go to "Search" tab
6. Select PDFs to search
7. Enter search query and click "Search"
8. View results with context

## 📖 Configuration

### District & AC Information

The application is configured for:
- **District**: Bangalore Urban
- **AC (Assembly Constituency)**: 88 (Yelahanka)
- **Max PDFs**: 527 parts

To modify, edit the configuration in `backend_api.py`:

```python
DISTRICT = "BANGALORE URBAN"
AC_NUMBER = 88
```

### PDF Directory

By default, PDFs are stored in: `./output/pdfs/`

This is configured in `backend_api.py`:

```python
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
PDF_DIR = os.path.join(OUTPUT_DIR, "pdfs")
```

## 🔌 API Endpoints

### Health Check
- `GET /api/health` - API health status

### PDF Management
- `GET /api/pdfs/list` - List all downloaded PDFs
- `POST /api/pdfs/download` - Start downloading PDFs in range
- `GET /api/downloads/status` - Get download progress

### Search
- `POST /api/search` - Search across multiple PDFs
- `POST /api/search/single` - Search single PDF with pagination

### Info
- `GET /api/info` - Get application information

## 📊 Search Query Format

The search functionality supports:
- **Names**: Search for voter names (works with Kannada text)
- **Numbers**: Search for any numbers (serial, ID, etc.)
- **Keywords**: Search for any text content
- **Minimum**: 2 characters required

Examples:
- Search: "राहुल" (Kannada name)
- Search: "278"
- Search: "Yelahanka"

## 🎯 Download Range Examples

- **1-10**: Download first 10 PDFs
- **1-50**: Download first 50 PDFs
- **1-100**: Download first 100 PDFs
- **278**: Download only PDF 278
- **100, 200, 278**: Download specific PDFs (Specific mode)

## ⚙️ Troubleshooting

### API Connection Error

**Error**: "Backend API Not Connected"

**Solution**: 
1. Make sure Flask is running: `python backend_api.py`
2. Check API is at `http://localhost:5000`
3. Click "Retry Connection" button

### No PDFs After Download

**Solution**:
1. Check download progress bar completed
2. Verify internet connection
3. Check `./output/pdfs/` folder
4. Go to "Search" tab and refresh browser

### Search Returns No Results

**Solution**:
1. Ensure PDFs are downloaded first
2. Try different search terms
3. Check Kannada text encoding
4. Select more PDFs to search

### Slow Search

**Optimization**:
- The search scans all text in PDFs
- First search may take 2-5 seconds
- Subsequent searches are cached
- Search is limited to 10 matches per file initially

## 🔐 Security Notes

- API runs on localhost only by default
- No data is sent to external servers except PDF downloads
- All searches are local to your machine
- PDFs are stored locally

## 📝 Development

### Running in Development Mode

```bash
# Terminal 1: Backend
python backend_api.py

# Terminal 2: Frontend
cd frontend
npm run dev
```

### Building for Production

```bash
cd frontend
npm run build

# Build output in frontend/dist/
```

## 🐛 Known Limitations

1. **Large PDFs**: Searching very large PDFs (500+ pages) may take longer
2. **Kannada Rendering**: Requires proper font support for Kannada text
3. **Concurrent Downloads**: Only one download session at a time
4. **Memory**: Large batch searches may use significant RAM

## 📄 License

This project is for educational purposes.

## 👤 Support

For issues or questions, please check:
1. API is running on port 5000
2. Frontend can connect to backend (check browser console)
3. PDFs are being downloaded to `output/pdfs/`

---

**Built with ❤️ using React, Flask, and Python**
