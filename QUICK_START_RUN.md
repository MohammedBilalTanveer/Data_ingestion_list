# 🚀 Quick Start Guide - Run Everything

## ONE-TIME SETUP

### Step 1: Install Dependencies

Open PowerShell in the `Voter` folder and run:

```powershell
# Install backend dependencies
cd backend
pip install -r requirements.txt

# Install frontend dependencies
cd ../voter_official/frontend
npm install

# Go back to root
cd ../..
```

✅ Done! This only needs to be done once.

---

## RUN THE APP (Every Time)

You need **2 terminal windows** open:

### Terminal 1: Start Backend (Flask)

```powershell
cd C:\Users\moham\Voter\backend
python backend_api.py
```

OR simply double-click: **`start_backend.bat`**

**You should see:**
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

✅ **Backend is running!** Keep this terminal open.

---

### Terminal 2: Start Frontend (React)

```powershell
cd C:\Users\moham\Voter\voter_official\frontend
npm run dev
```

OR simply double-click: **`start_frontend.bat`**

**You should see:**
```
  VITE v5.0.0  ready in 123 ms

  ➜  Local:   http://localhost:5173/
  ➜  press h to show help
```

✅ **Frontend is running!** Keep this terminal open.

---

## OPEN IN BROWSER

Go to: **http://localhost:5173**

You should see the Voter Search application!

---

## USING THE APP

### Step 1: Download PDFs

1. Click **"Download PDFs"**
2. Enter part range: **1** to **5** (to test with just 5 files)
3. Click **"Download"**
4. Wait for download to complete (you'll see progress in terminal)

### Step 2: View Downloaded PDFs

1. Click **"View PDFs"**
2. You should see list of downloaded PDFs with their sizes

### Step 3: Search

1. Enter a search query (e.g., a voter name)
2. Select which PDF parts to search
3. Click **"Search"**
4. View results!

---

## QUICK REFERENCE

| Action | Command |
|--------|---------|
| **Setup (one-time)** | `pip install -r requirements.txt` + `npm install` |
| **Start Backend** | `start_backend.bat` or `python backend_api.py` |
| **Start Frontend** | `start_frontend.bat` or `npm run dev` |
| **Access App** | http://localhost:5173 |
| **Test API** | http://localhost:5000/api/health |
| **View PDFs** | http://localhost:5000/api/pdfs/list |

---

## TROUBLESHOOTING

### "Backend won't start - Port 5000 in use"
```powershell
# Kill process on port 5000
netstat -ano | findstr :5000
taskkill /PID <PID> /F
```

### "Frontend won't start - npm not found"
```powershell
# Install Node.js from: https://nodejs.org
# Then:
node --version
npm --version
```

### "No module named 'storage'"
```powershell
# Make sure storage.py is in backend folder:
ls backend/storage.py

# Should show: storage.py exists
```

### "Cannot download PDFs"
1. Check internet connection
2. Verify DISTRICT and AC_NUMBER in `.env`
3. Check backend logs for errors

### "Search not working"
1. Download PDFs first
2. Check that PDFs appear in list
3. Try searching with exact text from a PDF

---

## FILE STRUCTURE

```
Voter/
├── start_backend.bat      ← Double-click to start backend
├── start_frontend.bat     ← Double-click to start frontend
├── RUN_GUIDE.md          ← Full setup guide
│
├── backend/
│   ├── .env              ← Local config (already created!)
│   ├── backend_api.py    ← Flask app (UPDATED ✓)
│   ├── storage.py        ← Storage handler (CREATED ✓)
│   ├── requirements.txt   ← Dependencies (UPDATED ✓)
│   └── output/pdfs/      ← Downloaded PDFs stored here
│
└── voter_official/frontend/
    ├── package.json
    ├── src/App.jsx
    ├── vite.config.js
    └── index.html
```

---

## WHAT'S READY?

✅ Backend code updated to use storage abstraction  
✅ `.env` file created for local development  
✅ `storage.py` ready (S3 + local)  
✅ `requirements.txt` has boto3  
✅ Frontend can run  

---

## NEXT STEPS AFTER TESTING

When you're ready to go **PRODUCTION**:

1. Create AWS S3 bucket
2. Create AWS IAM user with access keys
3. Update Render environment variables
4. Push to git: `git push origin main`
5. Render will auto-deploy

See **QUICK_START.md** for AWS setup.

---

## KEEP TERMINALS OPEN

✅ Both terminals must stay open while using the app  
✅ If you close them, the app stops  
✅ To stop: Press `Ctrl+C` in each terminal

---

**You're ready to go! 🚀**

Start with: Double-click `start_backend.bat` then `start_frontend.bat`
