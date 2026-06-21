# PDF Storage Solution for Render Deployment

## Problem
Your backend on Render uses **ephemeral storage** — files are deleted when the dyno restarts (every 15 minutes of inactivity). PDFs stored locally won't persist.

---

## Solution: AWS S3 (Recommended)

### Why S3?
- ✅ Persistent storage (files never deleted)
- ✅ Highly available and scalable
- ✅ Cost-effective: ~$0.023/GB per month
- ✅ Works perfectly with Render
- ✅ CDN integration available for faster downloads

---

## Implementation Steps

### 1. Create AWS S3 Bucket

**Via AWS Console:**
1. Go to https://console.aws.amazon.com/s3
2. Click **"Create bucket"**
3. Name: `voter-pdfs-ac88` (or your choice)
4. Region: `us-east-1` (or your preference)
5. Block public access: **ON** ✅
6. Click **"Create bucket"**

### 2. Create IAM Access Keys

1. Go to https://console.aws.amazon.com/iam
2. Left menu → **"Users"** → **"Create user"** (name: `voter-pdf-app`)
3. Attach policy: **"AmazonS3FullAccess"** (or create custom policy)
4. **Create access key** and save:
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`

⚠️ **Keep these secret!** Never commit to git.

### 3. Update Backend Code

The `storage.py` file has been created and handles both local and S3 storage.

**Update `backend_api.py`** (add near top after imports):

```python
from storage import get_storage_backend

# Initialize storage backend
storage = get_storage_backend()
```

**Replace local file operations:** (examples below)

**Old:**
```python
pdf_path = os.path.join(PDF_DIR, filename)
with open(pdf_path, 'wb') as f:
    f.write(response.content)
```

**New:**
```python
file_path = f"pdfs/{filename}"  # S3 key format
storage.save_file(file_path, response.content)
```

### 4. Configure Environment Variables

**On Render Dashboard:**
1. Go to your backend service
2. **Settings** → **Environment**
3. Add these variables:

```
USE_S3=true
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
AWS_S3_BUCKET=voter-pdfs-ac88
FRONTEND_URL=https://data-ingestion-list.vercel.app
DISTRICT=BANGALORE URBAN
AC_NUMBER=88
```

4. **Save** and redeploy

**Locally (update `.env`):**
```
USE_S3=false
PDF_STORAGE_PATH=./output/pdfs
FRONTEND_URL=http://localhost:3000
DISTRICT=BANGALORE URBAN
AC_NUMBER=88
```

### 5. Deploy Updated Backend

```bash
git add .
git commit -m "Add S3 storage support"
git push origin main
```

Render will auto-redeploy. Check logs in Render dashboard.

---

## Storage Architecture

```
Your App (Render)
    ↓
    ├─ PDF Downloaded from Karnataka govt
    └─ Uploaded to AWS S3 ✓ (Persistent)
         ↓
    ├─ PDFs retrieved from S3 (on-demand)
    └─ Sent to Frontend (Vercel)
```

---

## Cost Estimation

| Storage | Estimated Cost (100 voter PDFs) |
|---------|----------------------------------|
| AWS S3  | ~$0.30-0.50/month |
| Render Disk (100GB) | ~$20/month |
| Vercel (Frontend) | FREE |

---

## Alternative: Render Persistent Disk

**If you prefer not to use AWS:**

1. In Render dashboard: **Disks** → **Create disk**
2. Mount path: `/opt/render/project/pdfs`
3. Size: 10GB (~$2/month) or 100GB (~$20/month)
4. Set env: `PDF_STORAGE_PATH=/opt/render/project/pdfs`
5. Set env: `USE_S3=false`

✅ Files persist even after restarts

---

## Testing

### Local Testing
```bash
cd backend
export USE_S3=false
python -m flask run
# Try uploading PDFs — should save to ./output/pdfs
```

### Production Testing
```bash
# Check Render logs for S3 connection
# Visit: https://data-ingestion-list.onrender.com/api/health
# Should return: {"status": "ok", "message": "Backend API is running"}
```

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'boto3'"
```bash
pip install boto3==1.28.0
git push origin main
```

### S3 files not appearing
1. Check AWS credentials in Render environment
2. Verify bucket name is correct
3. Check S3 bucket exists in correct region
4. Review Render logs for errors

### Files still disappearing?
Make sure `USE_S3=true` in Render environment variables

---

## Security Best Practices

✅ **DO:**
- Use IAM users (not root AWS account)
- Rotate access keys periodically
- Use environment variables (never hardcode credentials)
- Enable S3 bucket versioning (optional)

❌ **DON'T:**
- Commit credentials to git
- Use root AWS account credentials
- Make S3 bucket public
- Use `US_S3=false` in production

---

## Next Steps

1. ✅ Create S3 bucket
2. ✅ Create IAM user with access keys
3. ✅ Add environment variables to Render
4. ✅ Push updated code (with boto3 in requirements.txt)
5. ✅ Test PDF uploads
6. ✅ Monitor Render logs

---

## Questions?

- **Render Docs**: https://render.com/docs
- **AWS S3 Docs**: https://docs.aws.amazon.com/s3/
- **Flask + S3**: https://boto3.amazonaws.com/v1/documentation/api/latest/guide/s3-uploading-files.html
