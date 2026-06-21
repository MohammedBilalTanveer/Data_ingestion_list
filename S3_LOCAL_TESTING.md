# 🚀 AWS S3 Local Testing Guide

## ✅ What I Fixed

1. **`.env` file** - Updated to use AWS S3
   - `USE_S3=true` (was `false`)
   - AWS credentials added
   - Local CORS fixed

2. **`storage.py`** - Fixed S3 connection
   - Added proper boto3 exception handling
   - Added S3 bucket validation on init
   - Better error messages

3. **`backend_api.py`** - Fixed initialization order
   - Moved `load_dotenv()` to TOP (before storage init)
   - Now environment variables load BEFORE storage tries to connect to S3

---

## 🧪 Step 1: Test S3 Connection

Before running the full app, verify your S3 setup:

```powershell
cd C:\Users\moham\Voter\backend
python test_s3_connection.py
```

**You should see:**
```
============================================================
AWS S3 Connection Test
============================================================

1. Checking environment variables...
------------------------------------------------------------
   USE_S3: True
   AWS_REGION: us-east-1
   AWS_S3_BUCKET: voter-pdfs-ac88
   AWS_ACCESS_KEY_ID: AKIA...
   AWS_SECRET_ACCESS_KEY: ****...

✓ All environment variables set

2. Testing boto3 import...
------------------------------------------------------------
   ✓ boto3 imported successfully

3. Testing S3 bucket connection...
------------------------------------------------------------
   ✓ Successfully connected to S3 bucket: voter-pdfs-ac88

4. Testing file upload and download...
------------------------------------------------------------
   ✓ Test file uploaded: pdfs/test.txt
   ✓ Test file downloaded and verified
   ✓ Test file deleted

5. Testing storage.py...
------------------------------------------------------------
   ✓ Storage backend initialized: S3Storage

============================================================
✓ ALL TESTS PASSED!
============================================================

Your S3 setup is working correctly.
You can now run: python backend_api.py
```

---

## ❌ If Test Fails

### Error: "AWS credentials not found"
```
Make sure your .env has:
  AWS_ACCESS_KEY_ID=AKIA...
  AWS_SECRET_ACCESS_KEY=...
```

### Error: "Bucket does not exist"
```
Create bucket in AWS console:
  1. Go to https://console.aws.amazon.com/s3
  2. Click "Create bucket"
  3. Name: voter-pdfs-ac88
  4. Region: us-east-1
```

### Error: "Access denied (403)"
```
Your IAM user doesn't have S3 permissions:
  1. Go to IAM: https://console.aws.amazon.com/iam
  2. Select your user (voter-pdf-app)
  3. Add policy: AmazonS3FullAccess
```

### Error: "ModuleNotFoundError: No module named 'boto3'"
```
Install boto3:
  pip install boto3==1.28.0
```

---

## ✅ Step 2: Start Backend with S3

Once test passes:

```powershell
cd C:\Users\moham\Voter\backend
python backend_api.py
```

**You should see:**
```
✓ S3 storage initialized: bucket=voter-pdfs-ac88, region=us-east-1
✓ Storage initialized: S3Storage

================================================================================
Starting Voter List Search Backend API
================================================================================
District: BANGALORE URBAN
AC: 88 (Yelahanka)
✓ Storage initialized: S3Storage

API will be available at: http://localhost:5000
================================================================================

 * Running on http://0.0.0.0:5000
```

✅ **Backend is running with S3!**

---

## ✅ Step 3: Start Frontend

In a NEW terminal:

```powershell
cd C:\Users\moham\Voter\voter_official\frontend
npm run dev
```

---

## ✅ Step 4: Test the App

1. **Go to:** http://localhost:5173

2. **Download some PDFs:**
   - Start: 1
   - End: 3 (just 3 for testing)
   - Click "Download"

3. **Watch the logs:**
   - Backend terminal should show:
     ```
     ⬇ Downloading Part 1...
     ✓ Uploaded to S3: pdfs/A0880001.pdf
     ✓ Part 1 downloaded
     ⬇ Downloading Part 2...
     ✓ Uploaded to S3: pdfs/A0880002.pdf
     ✓ Part 2 downloaded
     ...
     ```

4. **Check AWS S3:**
   - Go to https://console.aws.amazon.com/s3
   - Click `voter-pdfs-ac88` bucket
   - You should see `pdfs/` folder with PDFs:
     - A0880001.pdf
     - A0880002.pdf
     - A0880003.pdf

5. **Search for data:**
   - Go back to http://localhost:5173
   - Click "View PDFs"
   - You should see your downloaded PDFs
   - Search for a name

---

## 📋 Current Configuration

### `.env` (for local S3 testing)
```
USE_S3=true
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=YOUR_AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY=YOUR_AWS_SECRET_ACCESS_KEY
AWS_S3_BUCKET=voter-pdfs-ac88
FRONTEND_URL=http://localhost:3000,http://localhost:5173
DISTRICT=BANGALORE URBAN
AC_NUMBER=88
PORT=5000
```

**⚠️ NOTE:** Replace `YOUR_AWS_ACCESS_KEY_ID` and `YOUR_AWS_SECRET_ACCESS_KEY` with your actual credentials from AWS IAM.

### Files Updated
- ✅ `.env` - S3 config
- ✅ `backend_api.py` - load_dotenv() moved to top
- ✅ `storage.py` - Better S3 exception handling
- ✅ `test_s3_connection.py` - New test script

---

## 🧠 How It Works

1. **Backend starts** → loads `.env` with `load_dotenv()`
2. **Storage initializes** → sees `USE_S3=true`, connects to S3 bucket
3. **Validates S3** → tests connection, shows error if bucket doesn't exist
4. **User downloads PDFs** → saves directly to S3 (not local disk)
5. **User searches** → loads PDFs from S3, searches in memory, returns results
6. **Service restarts** → PDFs still in S3 (persistent!) ✓

---

## 🚀 Commands Summary

| Task | Command |
|------|---------|
| **Test S3 setup** | `python test_s3_connection.py` |
| **Start Backend** | `python backend_api.py` |
| **Start Frontend** | `npm run dev` |
| **Access App** | http://localhost:5173 |
| **Check S3 Bucket** | https://console.aws.amazon.com/s3 |
| **Check Logs** | Watch backend terminal |

---

## 🎯 What to Test

- ✅ Test S3 connection (run test script)
- ✅ Download 3 PDFs (check S3 console)
- ✅ View PDFs in app (list should show S3 files)
- ✅ Search for data
- ✅ Restart backend (PDFs should still be there)
- ✅ Delete backend folder, restart (PDFs still work from S3)

---

## ⚠️ Production Notes

When deploying to Render:
1. Don't include `.env` in git (it has credentials!)
2. Set env variables in Render dashboard instead
3. PDFs will stay in S3 even after service restarts
4. Cost: ~$0.30/month per 1000 PDFs

---

## 🆘 Need Help?

1. Run `python test_s3_connection.py` to see exact error
2. Check AWS S3 console for bucket existence
3. Verify IAM user has S3 permissions
4. Check backend logs for connection errors

---

**You're ready to test S3! 🎉**

Run: `python test_s3_connection.py`
