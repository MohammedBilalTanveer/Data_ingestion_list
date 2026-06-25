import os

# Bind to the port Render provides via $PORT
bind = f"0.0.0.0:{os.getenv('PORT', '5000')}"

# 1 worker is required because download_state is stored in-memory.
# Multiple workers each get their own copy, breaking download status polling.
workers = 1

# gthread = threaded sync worker.
# Required for SSE streaming (/api/search/stream): one thread holds the
# long-lived SSE connection open while executor threads process PDFs in parallel.
worker_class = "gthread"

# 4 HTTP threads — handles concurrent requests (SSE + status polling + render).
threads = 4

# Generous timeout for SSE streaming over large ranges and slow PDF renders.
timeout = 300

# Keep connections alive between requests.
keepalive = 5

# Log to stdout so Render captures it in the dashboard.
accesslog = "-"
errorlog = "-"
loglevel = "info"
