# DEPLOYMENT CHECKLIST: PDF Storage on Render

## ✅ Pre-Deployment (Local Testing)

- [ ] Install boto3: `pip install boto3`
- [ ] Update `requirements.txt` with `boto3==1.28.0`
- [ ] Create `storage.py` file ✓ (already done)
- [ ] Update `backend_api.py` with storage integration (see BACKEND_UPDATE_GUIDE.md)
- [ ] Test locally:
  ```bash
  export USE_S3=false
  cd backend && python -m flask run
  ```
- [ ] Verify PDFs save to `./backend/output/pdfs/`

---

## ✅ AWS Setup

- [ ] Create AWS account (if needed): https://aws.amazon.com
- [ ] Create S3 bucket: `voter-pdfs-ac88`
  - Region: `us-east-1`
  - Block all public access: ON
- [ ] Create IAM user: `voter-pdf-app`
- [ ] Attach policy: `AmazonS3FullAccess`
- [ ] Create access key and save:
  - `AWS_ACCESS_KEY_ID` = _______________
  - `AWS_SECRET_ACCESS_KEY` = _______________

---

## ✅ Render Configuration

1. Go to Render dashboard: https://dashboard.render.com

2. Select your backend service

3. Go to **Settings** → **Environment**

4. Add these variables:
   ```
   USE_S3=true
   AWS_REGION=us-east-1
   AWS_ACCESS_KEY_ID=your_key_here
   AWS_SECRET_ACCESS_KEY=your_secret_here
   AWS_S3_BUCKET=voter-pdfs-ac88
   FRONTEND_URL=https://data-ingestion-list.vercel.app
   DISTRICT=BANGALORE URBAN
   AC_NUMBER=88
   ```

5. Click **Save** (Render will auto-redeploy)

---

## ✅ Code Deployment

```bash
# In your local repo
cd backend

# Verify storage.py is in place
ls storage.py  # Should exist

# Update requirements.txt
grep boto3 requirements.txt  # Should show: boto3==1.28.0

# Update backend_api.py
# - Add: from storage import get_storage_backend
# - Replace file operations with storage methods
# - See BACKEND_UPDATE_GUIDE.md for details

# Commit and push
git add .
git commit -m "Add S3 storage support for PDF persistence"
git push origin main
```

---

## ✅ Post-Deployment Verification

1. **Check Render logs:**
   - Go to Render dashboard → Your backend service → Logs
   - Look for: `Storage initialized: S3Storage` ✓
   - No Python import errors ✓

2. **Test health endpoint:**
   ```
   https://data-ingestion-list.onrender.com/api/health
   
   Expected response:
   {"status": "ok", "message": "Backend API is running"}
   ```

3. **Test PDF list endpoint:**
   ```
   https://data-ingestion-list.onrender.com/api/pdfs/list
   
   Expected response:
   {"success": true, "pdfs": [], "total": 0}
   ```

4. **Download a PDF part:**
   - Use Vercel frontend to download PDF part 1
   - Check AWS S3 bucket: should see `pdfs/A0880001.pdf` ✓

5. **Verify persistence:**
   - Restart Render service (Manual deploy)
   - List PDFs again: should still see `A0880001.pdf` ✓

6. **Search test:**
   - Download a few PDFs
   - Use search feature on frontend
   - Should find results ✓

---

## ✅ Troubleshooting

### PDFs not saving to S3
```
1. Check Render logs for boto3 errors
2. Verify AWS credentials in Render environment
3. Verify S3 bucket name is correct
4. Check S3 bucket exists in us-east-1 region
5. Verify IAM user has S3 permissions
```

### "ModuleNotFoundError: No module named 'boto3'"
```
1. Add boto3==1.28.0 to backend/requirements.txt
2. Push to git
3. Render will reinstall dependencies on next deploy
4. Check Render build logs
```

### Files disappearing after service restart
```
1. Verify USE_S3=true in Render environment
2. Check Render logs show "S3Storage" (not "LocalStorage")
3. Verify AWS credentials are set
```

### S3 upload succeeds but files don't appear in bucket
```
1. Log into AWS console
2. Go to S3 → voter-pdfs-ac88 bucket
3. Check if files are there with "pdfs/" prefix
4. Verify IAM user permissions (should have s3:PutObject, s3:GetObject)
```

---

## ✅ Production Monitoring

### Daily Checks
- [ ] Render service status: GREEN ✓
- [ ] API responding: https://data-ingestion-list.onrender.com/api/health
- [ ] S3 bucket has PDFs: AWS S3 dashboard
- [ ] Frontend loading: https://data-ingestion-list.vercel.app

### Weekly Tasks
- [ ] Review Render logs for errors
- [ ] Check AWS S3 storage costs (should be <$1)
- [ ] Test PDF search functionality
- [ ] Monitor error rate

### Monthly Tasks
- [ ] Review AWS billing (should be <$1)
- [ ] Backup important data
- [ ] Update dependencies if needed

---

## ✅ Optional: Cost Optimization

If storing 1000+ PDFs, consider:

1. **S3 Lifecycle Policies** - Archive old PDFs after 90 days
2. **CloudFront CDN** - Cache PDFs for faster downloads
3. **S3 Intelligent-Tiering** - Auto-move to cheaper storage classes
4. **Render Persistent Disk** - If <100GB (cheaper than S3)

---

## ✅ Backup & Recovery

### Backup PDFs from S3
```bash
aws s3 sync s3://voter-pdfs-ac88 ./backup/
```

### Restore from backup
```bash
aws s3 sync ./backup/ s3://voter-pdfs-ac88
```

### Delete all PDFs from S3 (danger!)
```bash
aws s3 rm s3://voter-pdfs-ac88 --recursive
```

---

## ✅ Questions?

- Render support: support@render.com
- AWS support: https://console.aws.amazon.com/support
- Check logs: https://dashboard.render.com (Logs tab)

**Status:** Ready for production ✓
