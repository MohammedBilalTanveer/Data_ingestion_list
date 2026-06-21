# 🚀 Complete Setup & Run Guide

## Prerequisites

### Install Python & Node.js
```bash
# Check Python (3.9+)
python --version

# Check Node.js (16+)
node --version
npm --version
```

---

## Step 1: Backend Setup (Flask)

### 1.1 Create `.env` file in `backend/` folder

Copy `.env.example` to `.env`:

```bash
cd backend
cp .env.example .env
```

Edit `.env` for **local development**:

```bash
# For local dev (using local file storage)
USE_S3=false
PDF_STORAGE_PATH=./output/pdfs
FRONTEND_URL=http://localhost:3000
DISTRICT=BANGALORE URBAN
AC_NUMBER=88
PORT=5000
```

### 1.2 Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

**If you get an error installing boto3:**
```bash
pip install boto3==1.28.0
```

### 1.3 Run Backend

```bash
cd backend
python backend_api.py
```

**Expected output:**
```
================================================================================
Starting Voter List Search Backend API
================================================================================
District: BANGALORE URBAN
AC: 88 (Yelahanka)
PDF Directory: ./output/pdfs
✓ Storage initialized: LocalStorage

API will be available at: http://localhost:5000
================================================================================

 * Running on http://0.0.0.0:5000
```

✅ Backend is running at: **http://localhost:5000**

---

## Step 2: Frontend Setup (React)

### 2.1 Install Dependencies

```bash
cd voter_official/frontend
npm install
```

### 2.2 Create `.env.local` (if needed)

```bash
# Optional - if your API is on different port
VITE_API_URL=http://localhost:5000
```

### 2.3 Run Frontend Development Server

```bash
cd voter_official/frontend
npm run dev
```

**Expected output:**
```
  VITE v5.0.0  ready in 123 ms

  ➜  Local:   http://localhost:5173/
  ➜  press h to show help
```

✅ Frontend is running at: **http://localhost:5173**

---

## Step 3: Test Your Setup

### Test Backend Health
```bash
curl http://localhost:5000/api/health
```

**Expected response:**
```json
{"status": "ok", "message": "Backend API is running"}
```

### Open Frontend in Browser
```
http://localhost:5173
```

✅ You should see the Voter Search interface

---

## Complete Workflow (All Steps)

### Terminal 1: Backend
```bash
cd C:\Users\moham\Voter\backend
python backend_api.py
```

### Terminal 2: Frontend
```bash
cd C:\Users\moham\Voter\voter_official\frontend
npm run dev
```

### Terminal 3: Optional - Test API
```bash
# List PDFs
curl http://localhost:5000/api/pdfs/list

# Download PDFs (parts 1-5)
curl -X POST http://localhost:5000/api/pdfs/download \
  -H "Content-Type: application/json" \
  -d '{"start_part": 1, "end_part": 5}'

# Check download status
curl http://localhost:5000/api/downloads/status

# Search (after downloading)
curl -X POST http://localhost:5000/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "John Doe",
    "part_numbers": [1, 2, 3]
  }'
```

---

## Troubleshooting

### Backend Issues

**Error: "ModuleNotFoundError: No module named 'storage'"**
```bash
cd backend
python -c "from storage import get_storage_backend; print('OK')"
```
- If fails: Make sure `storage.py` exists in `backend/` folder

**Error: "Port 5000 already in use"**
```bash
# Change port in .env
PORT=5001

# Or kill process using port 5000 (Windows)
netstat -ano | findstr :5000
taskkill /PID <PID> /F
```

**Error: "No module named 'pdfplumber'"**
```bash
pip install -r requirements.txt
```

### Frontend Issues

**Error: "VITE is not recognized"**
```bash
# Inside frontend folder
npm install
```

**Error: "Cannot find module '@vitejs/plugin-vue'"**
```bash
cd voter_official/frontend
npm install
npm run dev
```

**CORS Error when searching**
- Make sure backend is running on `http://localhost:5000`
- Check `.env` has `FRONTEND_URL=http://localhost:3000` (or your frontend port)

---

## File Locations

```
Voter/
├── backend/
│   ├── .env                 ← Create this for local dev
│   ├── .env.example        
│   ├── backend_api.py      ← Flask app
│   ├── storage.py          ← Storage abstraction
│   └── requirements.txt    
│
├── voter_official/frontend/
│   ├── .env.local          ← Optional
│   ├── package.json
│   ├── vite.config.js
│   ├── src/
│   │   ├── App.jsx
│   │   └── main.jsx
│   └── index.html
```

---

## Using AWS S3 for Production

When you're ready to deploy to Render:

### 1. Update `backend/.env` (for production on Render):

```bash
USE_S3=true
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_S3_BUCKET=voter-pdfs-ac88
FRONTEND_URL=https://data-ingestion-list.vercel.app
DISTRICT=BANGALORE URBAN
AC_NUMBER=88
```

### 2. Deploy to Render

```bash
git add .
git commit -m "Update backend with S3 storage"
git push origin main

# Render will auto-deploy
# Check logs: https://dashboard.render.com
```

---

## Commands Summary

| Task | Command |
|------|---------|
| **Start Backend** | `cd backend && python backend_api.py` |
| **Start Frontend** | `cd voter_official/frontend && npm run dev` |
| **Install Backend Deps** | `cd backend && pip install -r requirements.txt` |
| **Install Frontend Deps** | `cd voter_official/frontend && npm install` |
| **Build Frontend** | `cd voter_official/frontend && npm run build` |
| **Test Backend Health** | `curl http://localhost:5000/api/health` |
| **View API Docs** | `http://localhost:5000/api/info` |

---

## What Each Component Does

### Backend (Flask on port 5000)
- ✅ Downloads PDFs from Karnataka government website
- ✅ Stores PDFs in S3 or local disk
- ✅ Searches PDFs for text
- ✅ Returns results to frontend

### Frontend (React/Vite on port 5173)
- ✅ User interface for searching
- ✅ Shows PDF list
- ✅ Manages PDF downloads
- ✅ Displays search results

### Storage Layer (`storage.py`)
- ✅ Handles both S3 and local file storage
- ✅ Auto-detects which backend to use via `USE_S3` env var
- ✅ Same code works for dev and production

---

## Next Steps

1. ✅ Create `.env` in `backend/`
2. ✅ Run `pip install -r requirements.txt`
3. ✅ Run `python backend_api.py`
4. ✅ Run `npm install` in frontend folder
5. ✅ Run `npm run dev` in frontend folder
6. ✅ Open http://localhost:5173 in browser
7. ✅ Download some PDFs (parts 1-5)
8. ✅ Search for voter names
9. ✅ Deploy to Render when ready

---

## Support

**Backend logs:** Check terminal running Flask  
**Frontend logs:** Check browser console (F12)  
**API documentation:** http://localhost:5000/api/info  
**Render logs:** https://dashboard.render.com → Your service → Logs

---

**Status: Ready to Run! 🚀**
