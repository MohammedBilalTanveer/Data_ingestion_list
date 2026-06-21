# 🚀 Installation & Setup Guide

Complete step-by-step guide to set up and run the Voter List Search application.

## System Requirements

- **OS**: Windows, macOS, or Linux
- **Python**: 3.7 or higher
- **Node.js**: 14 or higher
- **RAM**: Minimum 2GB (recommended 4GB)
- **Disk Space**: 500MB minimum (varies based on downloaded PDFs)

## Step 1: Verify Prerequisites

### Check Python
```bash
python --version
# Should output: Python 3.7.x or higher
```

### Check Node.js & npm
```bash
node --version
npm --version
# Should output: v14.x or higher
```

If any are missing, install them from:
- **Python**: https://www.python.org/downloads/
- **Node.js**: https://nodejs.org/ (choose LTS version)

## Step 2: Install Python Dependencies

Open Command Prompt/Terminal in the project folder and run:

```bash
pip install -r requirements.txt
```

This will install:
- Flask (web framework)
- Flask-CORS (cross-origin requests)
- requests (HTTP library)
- pdfplumber (PDF text extraction)

## Step 3: Install Frontend Dependencies

```bash
cd frontend
npm install
```

This will install:
- React
- React DOM
- Vite (build tool)

Then return to project root:
```bash
cd ..
```

## Step 4: Start the Application

### Option A: Using the Startup Script (Windows)

Double-click `START.bat` in the project folder.

This will:
1. Check dependencies ✓
2. Start Flask API on port 5000
3. Start React frontend on port 5173
4. Open browser automatically

### Option B: Manual Startup

#### Terminal 1 - Backend API:
```bash
python backend_api.py
```

Expected output:
```
========================================
🚀 Starting Voter List Search Backend API
========================================
District: BANGALORE URBAN
AC: 88 (Yelahanka)
PDF Directory: ./output/pdfs

API will be available at: http://localhost:5000
========================================
```

#### Terminal 2 - Frontend:
```bash
cd frontend
npm run dev
```

Expected output:
```
  VITE v8.0.12  ready in 234 ms

  ➜  Local:   http://localhost:5173/
  ➜  press h to show help
```

## Step 5: Access the Application

Open your browser and go to:
```
http://localhost:5173
```

You should see the application with:
- ✓ Header with district/AC info
- ✓ Two tabs: Search and Download PDFs
- ✓ API connection status

## 🎯 First Time Setup Checklist

- [ ] Python installed and version checked
- [ ] Node.js installed and version checked
- [ ] `pip install -r requirements.txt` completed
- [ ] `cd frontend && npm install` completed
- [ ] Backend running on port 5000
- [ ] Frontend running on port 5173
- [ ] Browser showing http://localhost:5173
- [ ] "Download PDFs" tab is accessible

## 🧪 Verify Installation

### Check Backend API
```bash
curl http://localhost:5000/api/health
```

Expected response:
```json
{"status": "ok", "message": "Backend API is running"}
```

### Check Frontend
Visit http://localhost:5173 - should load without errors

### Check Kannada Font Support
Go to Search tab - should display Kannada text properly if searches exist

## 📁 Folder Structure After Setup

```
voter_official/
├── output/
│   └── pdfs/              # PDFs downloaded here
├── frontend/
│   ├── node_modules/      # ✓ Created by npm install
│   ├── src/
│   ├── package.json
│   └── vite.config.js
├── backend_api.py
├── requirements.txt
├── README.md
└── START.bat
```

## 🔧 Configuration

### Change Download Directory

Edit `backend_api.py`:
```python
OUTPUT_DIR = "D:/MyPDFs"  # Change this path
PDF_DIR = os.path.join(OUTPUT_DIR, "pdfs")
```

### Change API Port

Edit `backend_api.py`:
```python
app.run(debug=False, host='0.0.0.0', port=8000)  # Change port to 8000
```

Then update `frontend/src/App.jsx`:
```javascript
const response = await fetch('http://localhost:8000/api/health')
```

### Change Frontend Port

Edit `frontend/vite.config.js`:
```javascript
export default {
  server: {
    port: 3000  // Change to 3000
  }
}
```

## ⚠️ Troubleshooting

### Error: "Python not found"
- **Solution**: Install Python from https://www.python.org/downloads/
- Make sure to check "Add Python to PATH" during installation

### Error: "npm not found"
- **Solution**: Install Node.js from https://nodejs.org/
- Node.js includes npm automatically

### Error: "Port 5000 already in use"
```bash
# Find process using port 5000
netstat -ano | findstr :5000

# Kill the process (replace PID with the number from above)
taskkill /PID <PID> /F
```

Then start backend again.

### Error: "Cannot find module 'flask'"
```bash
# Make sure you're in the project root directory
pip install -r requirements.txt
```

### Frontend loads but says "API not connected"
1. Check if backend is running on port 5000
2. Try clicking "Retry Connection" button
3. Check browser console for errors (F12)
4. Verify Flask started without errors

### Search shows no results
1. Make sure PDFs are downloaded first
2. Check `./output/pdfs/` folder for PDF files
3. Try with a different search term
4. Refresh the page

## 🌐 Accessing from Another Computer

### Local Network Access

**Backend**:
```python
app.run(debug=False, host='0.0.0.0', port=5000)  # Already set
```

**Frontend**: Update `frontend/src/App.jsx`
```javascript
const fetch_url = 'http://YOUR_COMPUTER_IP:5000'
// Replace YOUR_COMPUTER_IP with actual IP (e.g., 192.168.1.100)

fetch(fetch_url + '/api/health')
```

Find your computer's IP:
```bash
# Windows
ipconfig

# macOS/Linux
ifconfig
```

Look for IPv4 Address (usually starts with 192.168.x.x or 10.x.x.x)

## 📚 Helpful Commands

```bash
# Check pip packages
pip list

# Check npm packages
npm list

# Clear npm cache
npm cache clean --force

# Reinstall frontend dependencies
cd frontend
rm -rf node_modules package-lock.json
npm install
cd ..

# Run backend with debug mode
python backend_api.py

# Build frontend for production
cd frontend
npm run build
# Output in frontend/dist/
```

## ✅ Ready to Use!

Once everything is set up:

1. **Download PDFs**:
   - Go to "Download PDFs" tab
   - Select range or specific PDFs
   - Click "Start Download"
   - Wait for completion

2. **Search PDFs**:
   - Go to "Search" tab
   - Select PDFs to search
   - Enter search query
   - Click "Search"
   - View results

3. **Manage PDFs**:
   - See list of downloaded PDFs
   - Current size in MB
   - Part numbers for reference

---

**Congratulations! 🎉 Your Voter List Search application is ready to use!**

For more information, see README.md
