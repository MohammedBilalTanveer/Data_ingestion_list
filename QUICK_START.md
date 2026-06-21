# QUICK START: PDF Storage Solution for Render

## Your Problem

❌ **Current Issue:** PDFs stored locally on Render are **deleted every 15 minutes** when the service restarts.

✅ **Solution:** Store PDFs in **AWS S3** — they persist forever and cost ~$0.30-1/month.

---

## What I've Created For You

✅ **`storage.py`** - Handles both S3 and local storage (100% drop-in replacement)  
✅ **`.env.example`** - Updated with S3 configuration options  
✅ **`requirements.txt`** - Added boto3 for AWS S3 support  
✅ **`PDF_STORAGE_GUIDE.md`** - Complete setup guide  
✅ **`BACKEND_UPDATE_GUIDE.md`** - Exact code changes needed  
✅ **`DEPLOYMENT_CHECKLIST.md`** - Step-by-step deployment  
✅ **`ARCHITECTURE.md`** - Visual diagrams & system design  

---

## 5-Minute Setup

### Step 1: Create AWS S3 Bucket (2 mins)

1. Go to https://console.aws.amazon.com/s3
2. Click **"Create bucket"**
3. Name: `voter-pdfs-ac88`
4. Click **Create** ✓

### Step 2: Create AWS Access Keys (2 mins)

1. Go to https://console.aws.amazon.com/iam
2. Left menu: **Users** → **Create user** (name: `voter-pdf-app`)
3. Attach policy: **AmazonS3FullAccess**
4. **Create access key**
5. **Save these values:**
   ```
   AWS_ACCESS_KEY_ID = _______________
   AWS_SECRET_ACCESS_KEY = _______________
   ```

### Step 3: Configure Render (1 min)

1. Go to https://dashboard.render.com
2. Select your **backend service**
3. **Settings** → **Environment**
4. Add:
   ```
   USE_S3=true
   AWS_REGION=us-east-1
   AWS_S3_BUCKET=voter-pdfs-ac88
   AWS_ACCESS_KEY_ID=your_key_from_step_2
   AWS_SECRET_ACCESS_KEY=your_secret_from_step_2
   ```
5. **Save** ✓

---

## Code Updates Needed

### In `backend/backend_api.py` - ADD AT TOP (after imports):

```python
from storage import get_storage_backend

# Initialize storage backend
storage = get_storage_backend()
```

### Replace 5 Functions (See BACKEND_UPDATE_GUIDE.md for details):

1. `download_pdf_file()` - Use `storage.save_file()`
2. `download_pdfs_in_range()` - Use `storage.file_exists()` & `storage.save_file()`
3. `list_pdfs()` - Use `storage.list_files()` & `storage.get_file_size()`
4. `search_in_pdf()` - Use `storage.load_file()` with temp file
5. Any other file operations

**Key change:**
- OLD: `pdf_path = os.path.join(PDF_DIR, filename)` + `open(pdf_path)`
- NEW: `file_path = f"pdfs/{filename}"` + `storage.save_file(file_path, content)`

---

## Deploy

```bash
cd /path/to/Voter

# Push code
git add .
git commit -m "Add S3 storage support"
git push origin main

# Render auto-redeploys
# Check logs: https://dashboard.render.com
```

---

## Verify It Works

### Test 1: Health Check
```bash
curl https://data-ingestion-list.onrender.com/api/health
```
✅ Should return: `{"status": "ok"}`

### Test 2: List PDFs
```bash
curl https://data-ingestion-list.onrender.com/api/pdfs/list
```
✅ Should return: `{"success": true, "pdfs": [], "total": 0}`

### Test 3: Download a PDF
1. Go to https://data-ingestion-list.vercel.app
2. Download PDF part 1-1
3. Go to AWS S3 console → voter-pdfs-ac88 bucket
4. ✅ Should see: `pdfs/A0880001.pdf`

### Test 4: Restart & Verify
1. Restart Render service (manual deploy)
2. List PDFs again
3. ✅ PDF should still be there!

---

## Troubleshooting

### "ModuleNotFoundError: boto3"
- Add `boto3==1.28.0` to `backend/requirements.txt`
- Push to git
- Render will reinstall

### "Access Denied" or "Auth Failed"
- Check AWS credentials in Render environment
- Verify IAM user has S3 permissions
- Verify bucket name is spelled correctly

### PDFs still disappearing
- Verify `USE_S3=true` in Render environment
- Check Render logs: should say "S3Storage" not "LocalStorage"
- Verify AWS credentials are set

### Files upload to S3 but can't read them
- Check file path format: should be `pdfs/filename.pdf`
- Verify S3 bucket permissions
- Check IAM user has `s3:GetObject` permission

---

## Costs

**AWS S3 Pricing:**
- Storage: $0.023 per GB/month
- For 1000 PDFs (1.3 GB): ~$0.30/month
- FREE: First 5GB included in AWS free tier (12 months)

**Render:**
- Free tier: $0
- Paid tier (if needed): $7/month

**Total: ~$0.30-7/month** (vs. $20/month for Render persistent disk)

---

## Optional Enhancements

### 1. Enable S3 Versioning (Data Protection)
```bash
aws s3api put-bucket-versioning \
  --bucket voter-pdfs-ac88 \
  --versioning-configuration Status=Enabled
```

### 2. Set Lifecycle Policy (Cost Savings)
Archive PDFs after 90 days:
- AWS S3 console → voter-pdfs-ac88 → Lifecycle
- Create rule: move to Glacier after 90 days

### 3. Add CloudFront CDN (Speed)
- Faster downloads worldwide
- Automatic caching
- Extra cost: ~$0.085 per GB

---

## Files Reference

| File | Purpose |
|------|---------|
| `storage.py` ✓ | Storage abstraction layer |
| `BACKEND_UPDATE_GUIDE.md` | Code modification guide |
| `PDF_STORAGE_GUIDE.md` | Setup & configuration |
| `DEPLOYMENT_CHECKLIST.md` | Step-by-step deployment |
| `ARCHITECTURE.md` | System design & diagrams |
| `.env.example` ✓ | Updated config template |
| `requirements.txt` ✓ | Added boto3 |

---

## Next Actions

1. ✅ Create S3 bucket (2 mins)
2. ✅ Create IAM access keys (2 mins)
3. ✅ Update Render environment (1 min)
4. ✅ Modify backend code (10-15 mins, see BACKEND_UPDATE_GUIDE.md)
5. ✅ Deploy & test (5 mins)

**Total time: ~30 minutes for full setup**

---

## Support

- **AWS S3 Help:** https://aws.amazon.com/s3/
- **Render Help:** https://render.com/docs
- **Error logs:** https://dashboard.render.com (Logs tab)

---

## Summary

| Aspect | Before | After |
|--------|--------|-------|
| **PDF Storage** | Local (ephemeral) | AWS S3 (persistent) |
| **Data Loss Risk** | 🔴 High | 🟢 None |
| **Cost** | $0 (but broken) | ~$0.30/month |
| **Download Time** | <1s | 1-2s |
| **Scalability** | Limited to 10GB | Unlimited |
| **Availability** | 99% (Render only) | 99.99% (AWS SLA) |

**Status:** Ready to implement ✓
