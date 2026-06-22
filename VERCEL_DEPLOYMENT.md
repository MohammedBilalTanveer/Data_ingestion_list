# ⚙️ Vercel Deployment Guide - Environment Variables

When deploying the frontend to Vercel, you need to set environment variables so the app can connect to your Render backend.

## 🔗 Fix for Render Connection Issue

The issue you faced ("cannot connect to backend from frontend when hosted on Render") is solved by setting the correct API URL in Vercel.

### Step 1: Get Your Render Backend URL

1. Go to https://dashboard.render.com
2. Select your backend service
3. Copy the URL from the top (should look like: `https://voter-backend-xyz.onrender.com`)
4. **Make sure it's HTTPS, not HTTP**

### Step 2: Set Vercel Environment Variable

1. Go to https://vercel.com/dashboard
2. Click on your "voter" project (or "Data_ingestion_list")
3. Click **Settings** → **Environment Variables**
4. Click **Add New**
5. Fill in:
   ```
   Name: VITE_API_URL
   Value: https://your-render-service.onrender.com
   ```
   **Replace `your-render-service.onrender.com` with your actual Render URL**

6. Select all environments (Production, Preview, Development)
7. Click **Add**

### Step 3: Redeploy Frontend

1. Commit and push your changes:
   ```bash
   git add .
   git commit -m "Add authentication and pagination"
   git push
   ```

2. Go to Vercel dashboard
3. Your project should auto-deploy
4. Wait for deployment to complete (check for green checkmark)

### Step 4: Test the Connection

1. Open your Vercel app (https://your-project.vercel.app)
2. The frontend should now connect to your Render backend
3. Try the download feature to verify

---

## 📋 Complete Environment Setup

### For Local Development (`.env.local` in frontend folder)
```
VITE_API_URL=http://localhost:5000
```

### For Vercel Production
```
VITE_API_URL=https://your-render-service.onrender.com
```

### For Render Backend (`.env` in backend folder)
```
USE_S3=true
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_S3_BUCKET=voter-pdfs-ac88
FRONTEND_URL=https://your-vercel-app.vercel.app
DISTRICT=BANGALORE URBAN
AC_NUMBER=88
PORT=5000
```

---

## 🔐 CORS Configuration for Production

The backend automatically handles CORS based on `FRONTEND_URL` env variable.

**Make sure to set `FRONTEND_URL` to your Vercel domain in Render dashboard:**
- Go to Render dashboard
- Select your backend service
- Environment: Add/Update `FRONTEND_URL=https://your-vercel-app.vercel.app`

---

## ✅ Verification Checklist

- [ ] Render backend URL copied correctly (must be HTTPS)
- [ ] Vercel env var `VITE_API_URL` set to Render URL
- [ ] Frontend redeployed after env var change
- [ ] Backend `FRONTEND_URL` set to Vercel app URL
- [ ] Can login to download PDFs
- [ ] PDFs download successfully
- [ ] Search works on downloaded PDFs
- [ ] Can cancel downloads

---

## 🚨 Common Issues

| Issue | Solution |
|-------|----------|
| **403 Forbidden when connecting to backend** | Check CORS: Backend's `FRONTEND_URL` must match your Vercel domain exactly |
| **404 when calling API** | Check API URL: Should end with `.onrender.com` and be HTTPS |
| **"API_URL is undefined"** | Vercel env var name must be exactly `VITE_API_URL` |
| **Connection timeout** | Render app might be sleeping - wait 30 seconds and try again |
| **Mixed content error** | Frontend is HTTPS but API is HTTP - must both be HTTPS |

---

## 📚 URLs Reference

- **Frontend**: https://your-project.vercel.app
- **Backend**: https://your-render-service.onrender.com
- **API Health Check**: https://your-render-service.onrender.com/api/health
- **Vercel Dashboard**: https://vercel.com/dashboard
- **Render Dashboard**: https://dashboard.render.com

---

**After setting these env variables and redeploying, your app will work perfectly!**
