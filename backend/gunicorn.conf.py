import os

# Bind to the port Render provides via $PORT
bind = f"0.0.0.0:{os.getenv('PORT', '5000')}"

# 1 worker is required because download_state is stored in-memory.
# Multiple workers each get their own copy, breaking download status polling.
workers = 1

# Threads let the single worker handle concurrent requests:
# e.g. a PDF download running in a background thread while the frontend
# polls /api/downloads/status every second.
threads = 4

# PDF rendering with PyMuPDF and large PDF searches can be slow.
timeout = 120

# Keep connections alive between requests (helps with frequent status polls).
keepalive = 5

# Log to stdout so Render captures it in the dashboard.
accesslog = "-"
errorlog = "-"
loglevel = "info"
