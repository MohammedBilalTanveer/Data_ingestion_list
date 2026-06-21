# PDF Storage Architecture for Render Deployment

## Current Architecture (Problem)

```
Vercel (Frontend)                    Render (Backend)                  Karnataka Govt
https://...vercel.app          https://...onrender.com          https://ceo.karnataka.gov.in
     │                                  │
     │ Search PDF                       │
     ├─────────────────────────────────>│
     │                                  │ Download PDF
     │                                  ├─────────────────────────────────>
     │                                  │ Save to local disk (EPHEMERAL) ❌
     │ Results                          │
     │<─────────────────────────────────┤
     │                                  │
     │                         [SERVICE RESTART]
     │                         ❌ ALL FILES DELETED ❌
     │                                  │
     │ Search again (same file)         │
     ├─────────────────────────────────>│
     │                                  │ File not found!
     │ Error: File not found ❌         │
     │<─────────────────────────────────┤
```

---

## New Architecture (Solution)

```
Vercel (Frontend)             Render (Backend)              AWS S3                 Karnataka Govt
https://...vercel.app    https://...onrender.com    voter-pdfs-ac88 bucket    https://ceo.karnataka.gov.in
     │                          │                           │
     │                          │ Download PDF              │
     │                          ├──────────────────────────────────────>
     │                          │ Save PDF                  │
     │                          │ (streaming upload)        │
     │                          ├──────────────────>
     │ Search PDF               │                   │ Store in S3 (PERSISTENT) ✓
     ├─────────────────────────>│
     │                          │ Load PDF from S3
     │                          ├──────────────────>
     │ Search results           │ (retrieved from cache)
     │<─────────────────────────┤
     │                          │
     │                  [SERVICE RESTART]
     │                  ✓ Data persists in S3 ✓
     │                          │
     │ Search again (same file) │
     ├─────────────────────────>│
     │                          │ Load PDF from S3
     │                          ├──────────────────>
     │ Search results ✓         │ (retrieved from cache)
     │<─────────────────────────┤
```

---

## Data Flow Diagram

### Scenario 1: PDF Download & Storage

```
User Action: "Download PDFs 1-10"
     ↓
Frontend (Vercel)
     ↓ POST /api/pdfs/download
Backend (Render)
     ├─ For each PDF part:
     │  ├─ Create download URL
     │  ├─ GET from Karnataka govt
     │  ├─ Receive PDF bytes
     │  └─ Send to storage
     │
     └─→ Storage Backend
         ├─ Is USE_S3=true? YES
         └─→ AWS S3 Storage
             ├─ Create S3 client (boto3)
             ├─ Upload to: s3://voter-pdfs-ac88/pdfs/A0880001.pdf
             ├─ Upload to: s3://voter-pdfs-ac88/pdfs/A0880002.pdf
             ├─ Upload to: s3://voter-pdfs-ac88/pdfs/A0880003.pdf
             └─ ... (up to A0880010.pdf)
             
Frontend receives: {"success": true, "message": "Download started"}
```

### Scenario 2: PDF Search

```
User Action: "Search for 'John Doe'"
     ↓
Frontend (Vercel)
     ↓ POST /api/search
Backend (Render)
     ├─ For each selected PDF:
     │  └─ storage.load_file("pdfs/A0880001.pdf")
     │
     └─→ Storage Backend
         ├─ Is USE_S3=true? YES
         └─→ AWS S3 Storage
             ├─ Create S3 client (boto3)
             ├─ GET s3://voter-pdfs-ac88/pdfs/A0880001.pdf
             └─ Return file bytes (from cache if recent)
                    ↓
Backend (Render)
     ├─ Write to temp file: /tmp/A0880001.pdf
     ├─ Extract text using pdfplumber
     ├─ Search for "John Doe"
     ├─ Find matches on pages 5, 23, 187
     └─ Delete temp file

Frontend receives: 
{
  "success": true,
  "results": {
    "Part 1": {
      "matches": [
        {"page": 5, "snippet": "...John Doe..."},
        {"page": 23, "snippet": "...John Doe..."},
        {"page": 187, "snippet": "...John Doe..."}
      ]
    }
  }
}
```

### Scenario 3: Service Restart (Persistence Test)

```
Before Restart: 5 PDFs in S3
     ↓
Render Service: [Restart Signal]
     ↓
OLD (before fix):
└─→ Local disk DELETED ❌
    Result: PDFs gone forever

NEW (with S3):
└─→ Local disk cleared (OK, temporary)
    S3 bucket: Unchanged ✓
     ↓
Backend re-starts
     ↓
User searches → GET from S3 → Works! ✓
```

---

## System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (Vercel)                        │
│  ├─ React App (src/App.jsx)                                    │
│  ├─ PDF Download Component (PDFManager.jsx)                    │
│  └─ Search Component (SearchInterface.jsx)                     │
└──────────────────────┬──────────────────────────────────────────┘
                       │ HTTPS REST API
┌──────────────────────┴──────────────────────────────────────────┐
│                     Backend (Render)                            │
│  ├─ Flask Application (backend_api.py)                         │
│  ├─ Routes:                                                     │
│  │  ├─ GET  /api/health              → Health check           │
│  │  ├─ GET  /api/pdfs/list           → List downloaded PDFs   │
│  │  ├─ POST /api/pdfs/download       → Download PDFs          │
│  │  ├─ GET  /api/downloads/status    → Download progress      │
│  │  └─ POST /api/search              → Search in PDFs         │
│  └─ Storage Abstraction Layer (storage.py)                    │
│     ├─ Detects: USE_S3 environment variable                   │
│     └─ Routes to: S3Storage OR LocalStorage                   │
└──────┬────────────────────────────────────────────┬────────────┘
       │ (S3 Persistence)                           │ (Local Development)
       │                                             │
┌──────┴──────────────────┐                   ┌─────┴──────────┐
│   AWS S3 Bucket         │                   │  Local Disk    │
│                         │                   │                │
│ voter-pdfs-ac88         │                   │ ./output/pdfs/ │
│  ├─ pdfs/              │                   │  ├─ A0880001.pdf
│  │  ├─ A0880001.pdf   │                   │  ├─ A0880002.pdf
│  │  ├─ A0880002.pdf   │                   │  └─ ...
│  │  ├─ A0880003.pdf   │                   │
│  │  └─ ...             │                   │ (Recreated on restart)
│  │ (Persists forever)   │                   │ (Use only for dev)
│  └─ (PRODUCTION) ✓     │                   └─ (DEVELOPMENT) ✓
└──────────────────────────┘                   └────────────────┘
```

---

## Environment Configuration

### Production (Render)

```yaml
USE_S3: true
AWS_REGION: us-east-1
AWS_ACCESS_KEY_ID: AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_S3_BUCKET: voter-pdfs-ac88
FRONTEND_URL: https://data-ingestion-list.vercel.app
DISTRICT: BANGALORE URBAN
AC_NUMBER: 88
```

### Development (Local)

```bash
USE_S3=false
PDF_STORAGE_PATH=./output/pdfs
FRONTEND_URL=http://localhost:3000
DISTRICT=BANGALORE URBAN
AC_NUMBER=88
```

---

## File Structure

```
voter-pdfs-ac88 (S3 Bucket)
├── pdfs/
│   ├── A0880001.pdf  (2.5 MB)
│   ├── A0880002.pdf  (2.4 MB)
│   ├── A0880003.pdf  (2.6 MB)
│   ├── A0880004.pdf  (2.3 MB)
│   └── ... (up to 527 PDFs)
│
Total Size: ~1.3 GB
Monthly Cost: ~$0.30
Retrieval: <100ms (with CloudFront)
Availability: 99.99%
```

---

## Request/Response Flow

### 1. List PDFs

```
GET /api/pdfs/list

Response:
{
  "success": true,
  "pdfs": [
    {
      "filename": "A0880001.pdf",
      "part_number": 1,
      "size_mb": 2.5
    },
    {
      "filename": "A0880002.pdf",
      "part_number": 2,
      "size_mb": 2.4
    }
  ],
  "total": 2
}
```

### 2. Download PDFs

```
POST /api/pdfs/download
{
  "start_part": 1,
  "end_part": 10
}

Response:
{
  "success": true,
  "message": "Starting download for parts 1-10",
  "total_pdfs": 10
}

Then polls: GET /api/downloads/status
{
  "in_progress": true,
  "current_part": 5,
  "total_parts": 10,
  "completed_parts": 4,
  "failed_parts": 0,
  "status": "downloading"
}
```

### 3. Search

```
POST /api/search
{
  "query": "John Doe",
  "part_numbers": [1, 2, 3]
}

Response:
{
  "success": true,
  "results": {
    "Part 1": {
      "filename": "A0880001.pdf",
      "part_number": 1,
      "matches": [
        {
          "page": 5,
          "snippet": "...John Doe...",
          "original_line": "John Doe, Bangalore"
        }
      ],
      "count": 1
    }
  },
  "total_matches": 3
}
```

---

## Performance Characteristics

| Operation | Local Disk | AWS S3 |
|-----------|-----------|---------|
| Save PDF | 0.5s | 1.5s (+ network) |
| List files | 0.1s | 0.3s (+ network) |
| Load PDF | 0.2s | 0.8s (+ network) |
| Search 1 PDF | 2s | 3s (load delay) |
| Persistence | ❌ Lost on restart | ✅ Forever |
| Cost | $0 (included) | ~$0.30/month |
| Scalability | Limited (10GB) | Unlimited |

---

## Disaster Recovery

### Backup Strategy

```bash
# Daily backup (AWS to local)
aws s3 sync s3://voter-pdfs-ac88 /backups/voter-pdfs/

# Restore from backup
aws s3 sync /backups/voter-pdfs/ s3://voter-pdfs-ac88
```

### Failure Scenarios

| Scenario | Before (Local) | After (S3) |
|----------|---|---|
| Render restarts | ❌ All PDFs lost | ✅ All PDFs in S3 |
| Disk failure | ❌ No recovery | ✅ Auto-replicated by AWS |
| Accidental delete | ❌ Permanent loss | ✅ AWS S3 versioning (optional) |
| Regional outage | N/A | ✅ Use cross-region replication |

---

## Next Steps

1. **Create AWS S3 bucket** → `voter-pdfs-ac88`
2. **Create IAM credentials** → Access keys
3. **Update backend code** → Integrate storage.py
4. **Set Render environment** → Add AWS credentials
5. **Deploy & test** → Verify persistence
6. **Monitor costs** → Check AWS billing

**Expected monthly cost:** $0.30 - $1.00 for 1000+ PDFs
