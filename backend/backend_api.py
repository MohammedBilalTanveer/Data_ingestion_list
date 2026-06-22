"""
Flask backend API for Voter List PDF Management and Search
"""
import os
import sys
import json
import time
import threading
from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
from urllib.parse import quote
import pdfplumber
import fitz  # PyMuPDF
import io
from flask import send_file
from pathlib import Path
from dotenv import load_dotenv

# LOAD ENVIRONMENT VARIABLES FIRST (before any other initialization)
load_dotenv()

from storage import get_storage_backend

# Initialize storage backend (S3 or local)
try:
    storage = get_storage_backend()
    print(f"[OK] Storage initialized: {storage.__class__.__name__}")
except Exception as e:
    print(f"[ERROR] Storage error: {str(e)}")
    raise

# Configuration
app = Flask(__name__)

# Simpler CORS configuration for local development
# For local dev (localhost), allow all origins
# For production, set FRONTEND_URL environment variable
if os.getenv('FRONTEND_URL'):
    # Production mode - use specific URLs
    allowed_origins = os.getenv('FRONTEND_URL', '').split(',')
    CORS(app, resources={r"/api/*": {
        "origins": allowed_origins,
        "methods": ["GET", "POST", "OPTIONS", "DELETE", "PUT"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True,
        "max_age": 3600
    }})
else:
    # Local development - allow all
    CORS(app, resources={r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS", "DELETE", "PUT"],
        "allow_headers": ["Content-Type", "Authorization"],
        "max_age": 3600
    }})

# Additional manual CORS headers for reliability
@app.after_request
def add_cors_headers(response):
    origin = request.headers.get('Origin', '*')
    
    # For local development, allow any origin
    if 'localhost' in origin or '127.0.0.1' in origin:
        response.headers['Access-Control-Allow-Origin'] = origin
    elif os.getenv('FRONTEND_URL') and origin in [u.strip() for u in os.getenv('FRONTEND_URL', '').split(',')]:
        response.headers['Access-Control-Allow-Origin'] = origin
    else:
        response.headers['Access-Control-Allow-Origin'] = '*'
    
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS, DELETE, PUT'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    response.headers['Access-Control-Max-Age'] = '3600'
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    return response

DISTRICT = os.getenv('DISTRICT', 'BANGALORE URBAN')
AC_NUMBER = int(os.getenv('AC_NUMBER', '88'))
BASE_DIR = os.path.dirname(__file__)
# On Render, PDF_STORAGE_PATH points to the mounted persistent disk.
# Locally it falls back to output/pdfs/ inside the backend folder.
PDF_DIR = os.getenv('PDF_STORAGE_PATH', os.path.join(BASE_DIR, 'output', 'pdfs'))

# Global state for downloads
download_state = {
    "in_progress": False,
    "current_part": 0,
    "total_parts": 0,
    "completed_parts": [],
    "failed_parts": [],
    "status": "idle",
    "cancel_requested": False
}

# Credentials from environment variables - NO HARDCODED SECRETS
# Set via environment variables: DOWNLOAD_USERNAME, DOWNLOAD_PASSWORD
# Defaults to empty (will reject all logins if not set)
DOWNLOAD_USERNAME = os.getenv('DOWNLOAD_USERNAME', '')
DOWNLOAD_PASSWORD = os.getenv('DOWNLOAD_PASSWORD', '')

# Flag to enable/disable authentication
AUTH_ENABLED = bool(DOWNLOAD_USERNAME and DOWNLOAD_PASSWORD)

if not AUTH_ENABLED:
    print("⚠️  WARNING: Authentication disabled - no DOWNLOAD_USERNAME/PASSWORD set")
    print("    Set environment variables to enable login")


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_pdf_filename(ac: int, part_number: int) -> str:
    """Get standard PDF filename"""
    ac_str = str(ac).zfill(3)
    part_str = str(part_number).zfill(3)
    return f"A{ac_str}0{part_str}.pdf"


def create_pdf_url(district: str, ac: int, part_number: int) -> str:
    """Construct the PDF URL"""
    ac_str = str(ac).zfill(3)
    part_str = str(part_number).zfill(3)
    pdf_number = f"A{ac_str}0{part_str}"
    
    district_encoded = quote(district)
    ac_encoded = quote(f"AC {ac}")
    
    url = f"https://ceo.karnataka.gov.in/uploads/{district_encoded}/{ac_encoded}/{pdf_number}.pdf"
    return url


def download_pdf_file(url: str, file_path: str, max_retries: int = 3) -> bool:
    """Download single PDF with retry logic and save to storage"""
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=60, verify=True)
            response.raise_for_status()
            
            # Save to storage (S3 or local)
            if storage.save_file(file_path, response.content):
                return True
            
            if storage.file_exists(file_path) and storage.get_file_size(file_path) > 0:
                return True
                
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            continue
        except requests.exceptions.ConnectionError:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            continue
        except Exception as e:
            print(f"Error downloading {url}: {str(e)}")
            return False
    
    return False


def extract_text_from_pdf(pdf_path: str) -> dict:
    """Extract all text from a PDF organized by page"""
    pages_text = {}
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                try:
                    text = page.extract_text()
                    if text:
                        pages_text[page_num] = text
                    else:
                        pages_text[page_num] = ""
                except Exception:
                    pages_text[page_num] = ""
        return pages_text
    except Exception as e:
        print(f"Error reading PDF: {str(e)}")
        return {}


def search_in_pdf(pdf_path: str, query: str, case_sensitive: bool = False) -> list:
    """Search for query in a single PDF"""
    if not query or len(query.strip()) < 2:
        return []
    
    query = query.strip()
    pages_text = extract_text_from_pdf(pdf_path)
    
    if not pages_text:
        return []
    
    matches = []
    query_lower = query.lower() if not case_sensitive else query
    
    for page_num in sorted(pages_text.keys()):
        text = pages_text[page_num]
        if not text:
            continue
        
        lines = text.split('\n')
        
        for line_idx, line in enumerate(lines):
            line_check = line.lower() if not case_sensitive else line
            
            if query_lower in line_check:
                context_lines = []
                
                if line_idx > 0:
                    prev_line = lines[line_idx - 1].strip()
                    if prev_line:
                        context_lines.append(prev_line)
                
                context_lines.append(line.strip())
                
                if line_idx < len(lines) - 1:
                    next_line = lines[line_idx + 1].strip()
                    if next_line:
                        context_lines.append(next_line)
                
                matches.append({
                    'page': page_num,
                    'snippet': ' | '.join(context_lines),
                    'original_line': line.strip()
                })
    
    return matches


def download_pdfs_in_range(start_part: int, end_part: int) -> None:
    """Download PDFs in the specified range in background"""
    global download_state
    
    download_state["in_progress"] = True
    download_state["status"] = "downloading"
    download_state["cancel_requested"] = False
    download_state["completed_parts"] = []
    download_state["failed_parts"] = []
    download_state["total_parts"] = end_part - start_part + 1
    
    for part in range(start_part, end_part + 1):
        # Check if cancel was requested
        if download_state["cancel_requested"]:
            download_state["status"] = "cancelled"
            print(f"[CANCELLED] Download cancelled at part {part}")
            break
        
        download_state["current_part"] = part
        
        try:
            filename = get_pdf_filename(AC_NUMBER, part)
            file_path = f"pdfs/{filename}"  # S3 key format (works for local too)
            
            # Skip if already exists
            if storage.file_exists(file_path) and storage.get_file_size(file_path) > 0:
                download_state["completed_parts"].append(part)
                print(f"[OK] Part {part} already exists")
                continue
            
            # Download
            url = create_pdf_url(DISTRICT, AC_NUMBER, part)
            print(f"⬇ Downloading Part {part}...")
            
            if download_pdf_file(url, file_path):
                download_state["completed_parts"].append(part)
                print(f"[OK] Part {part} downloaded")
            else:
                download_state["failed_parts"].append(part)
                print(f"[ERROR] Part {part} failed")
        
        except Exception as e:
            print(f"Error processing part {part}: {str(e)}")
            download_state["failed_parts"].append(part)
        
        time.sleep(0.5)  # Small delay between downloads
    
    download_state["in_progress"] = False
    if download_state["status"] != "cancelled":
        download_state["status"] = "idle"
    print(f"\n{'='*60}")
    print(f"Completed: {len(download_state['completed_parts'])}, Failed: {len(download_state['failed_parts'])}")
    print(f"{'='*60}")


# ============================================================================
# API ROUTES
# ============================================================================

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok", "message": "Backend API is running"})


@app.route('/api/auth', methods=['POST'])
def authenticate():
    """Authenticate user for download access"""
    try:
        data = request.json
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        if not username or not password:
            return jsonify({
                "success": False,
                "error": "Username and password required"
            }), 400
        
        # Check if auth is enabled
        if not AUTH_ENABLED:
            return jsonify({
                "success": False,
                "error": "Authentication not configured"
            }), 503
        
        # Check credentials
        if (username == DOWNLOAD_USERNAME and 
            password == DOWNLOAD_PASSWORD):
            return jsonify({
                "success": True,
                "token": "authenticated",
                "message": "Login successful"
            })
        else:
            return jsonify({
                "success": False,
                "error": "Invalid credentials"
            }), 401
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/pdfs/list', methods=['GET'])
def list_pdfs():
    """List all downloaded PDFs with pagination"""
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
        
        if page < 1:
            page = 1
        if per_page < 1 or per_page > 100:
            per_page = 50
        
        pdfs = []
        pdf_files = storage.list_files(prefix="pdfs/")
        
        for filename in pdf_files:
            try:
                file_path = f"pdfs/{filename}"
                size_bytes = storage.get_file_size(file_path)
                size_mb = size_bytes / (1024 * 1024)
                
                # Extract part number from filename (e.g., A0880278.pdf -> 278)
                part_num = int(filename[5:8]) if len(filename) >= 8 else 0
                
                pdfs.append({
                    "filename": filename,
                    "part_number": part_num,
                    "size_mb": round(size_mb, 2)
                })
            except Exception as e:
                print(f"Error processing file {filename}: {str(e)}")
                continue
        
        # Sort by part number
        pdfs.sort(key=lambda x: x['part_number'])
        
        # Paginate
        total_items = len(pdfs)
        total_pages = (total_items + per_page - 1) // per_page
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_pdfs = pdfs[start_idx:end_idx]
        
        return jsonify({
            "success": True,
            "pdfs": paginated_pdfs,
            "total": total_items,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages
        })
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/pdfs/range', methods=['GET'])
def get_pdfs_by_range():
    """Get PDFs by part number range for efficient selection"""
    try:
        start = int(request.args.get('start', 1))
        end = int(request.args.get('end', 50))
        
        # Validate range
        if start < 1:
            start = 1
        if end < start:
            end = start + 49
        if end - start > 200:  # Max 200 PDFs at once
            end = start + 199
        
        pdfs = []
        pdf_files = storage.list_files(prefix="pdfs/")
        
        for filename in pdf_files:
            try:
                file_path = f"pdfs/{filename}"
                size_bytes = storage.get_file_size(file_path)
                size_mb = size_bytes / (1024 * 1024)
                
                # Extract part number from filename (e.g., A0880278.pdf -> 278)
                part_num = int(filename[5:8]) if len(filename) >= 8 else 0
                
                # Filter by range
                if start <= part_num <= end:
                    pdfs.append({
                        "filename": filename,
                        "part_number": part_num,
                        "size_mb": round(size_mb, 2),
                        "selected": False
                    })
            except Exception as e:
                print(f"Error processing file {filename}: {str(e)}")
                continue
        
        # Sort by part number
        pdfs.sort(key=lambda x: x['part_number'])
        
        return jsonify({
            "success": True,
            "pdfs": pdfs,
            "total": len(pdfs),
            "range": {"start": start, "end": end},
            "message": f"PDFs from {start} to {end}"
        })
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/pdfs/download', methods=['POST'])
def download_pdfs():
    """Start downloading PDFs in range (requires authentication)"""
    try:
        data = request.json
        
        # Check authentication
        token = data.get('token')
        if token != "authenticated":
            return jsonify({
                "success": False,
                "error": "Authentication required. Please login first."
            }), 401
        
        start_part = int(data.get('start_part', 1))
        end_part = int(data.get('end_part', 10))
        
        # Validate input
        if start_part < 1 or end_part > 527 or start_part > end_part:
            return jsonify({
                "success": False,
                "error": "Invalid range. Start: 1-527, End: 1-527, Start <= End"
            }), 400
        
        # Check if download already in progress
        if download_state["in_progress"]:
            return jsonify({
                "success": False,
                "error": "Download already in progress"
            }), 429
        
        # Start download in background thread
        download_thread = threading.Thread(
            target=download_pdfs_in_range,
            args=(start_part, end_part)
        )
        download_thread.daemon = True
        download_thread.start()
        
        return jsonify({
            "success": True,
            "message": f"Starting download for parts {start_part}-{end_part}",
            "total_pdfs": end_part - start_part + 1
        })
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/downloads/cancel', methods=['POST'])
def cancel_download():
    """Cancel ongoing download"""
    try:
        if not download_state["in_progress"]:
            return jsonify({
                "success": False,
                "error": "No download in progress"
            }), 400
        
        download_state["cancel_requested"] = True
        return jsonify({
            "success": True,
            "message": "Download cancellation requested",
            "completed_parts": len(download_state["completed_parts"]),
            "failed_parts": len(download_state["failed_parts"])
        })
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/downloads/status', methods=['GET'])
def download_status():
    """Get current download status"""
    return jsonify({
        "in_progress": download_state["in_progress"],
        "current_part": download_state["current_part"],
        "total_parts": download_state["total_parts"],
        "completed_parts": len(download_state["completed_parts"]),
        "failed_parts": len(download_state["failed_parts"]),
        "status": download_state["status"],
        "cancel_requested": download_state["cancel_requested"]
    })


@app.route('/api/search', methods=['POST'])
def search():
    """Search across specified PDFs"""
    import tempfile
    try:
        data = request.json
        query = data.get('query', '').strip()
        part_numbers = data.get('part_numbers', [])
        
        if not query or len(query) < 2:
            return jsonify({
                "success": False,
                "error": "Query must be at least 2 characters"
            }), 400
        
        if not part_numbers:
            return jsonify({
                "success": False,
                "error": "No PDFs specified"
            }), 400
        
        results = {}
        total_matches = 0
        
        for part_num in part_numbers:
            temp_path = None
            try:
                filename = get_pdf_filename(AC_NUMBER, part_num)
                file_path = f"pdfs/{filename}"
                
                # Load PDF from storage
                pdf_content = storage.load_file(file_path)
                if not pdf_content:
                    continue
                
                # Write to temp file for pdfplumber (it needs a file path)
                with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                    tmp.write(pdf_content)
                    temp_path = tmp.name
                
                matches = search_in_pdf(temp_path, query)
                
                if matches:
                    results[f"Part {part_num}"] = {
                        "filename": filename,
                        "part_number": part_num,
                        "matches": matches,
                        "count": len(matches)
                    }
                    total_matches += len(matches)
            
            except Exception as e:
                print(f"Error searching part {part_num}: {str(e)}")
                continue
            finally:
                # Clean up temp file
                if temp_path and os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except:
                        pass
        
        return jsonify({
            "success": True,
            "query": query,
            "total_matches": total_matches,
            "results": results,
            "total_files_searched": len(part_numbers)
        })
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/search/single', methods=['POST'])
def search_single():
    """Search in a single PDF and return paginated results"""
    import tempfile
    try:
        data = request.json
        query = data.get('query', '').strip()
        part_number = int(data.get('part_number', 0))
        page = int(data.get('page', 1))
        per_page = int(data.get('per_page', 20))
        
        if not query or len(query) < 2:
            return jsonify({
                "success": False,
                "error": "Query must be at least 2 characters"
            }), 400
        
        filename = get_pdf_filename(AC_NUMBER, part_number)
        file_path = f"pdfs/{filename}"
        
        # Load PDF from storage
        pdf_content = storage.load_file(file_path)
        if not pdf_content:
            return jsonify({
                "success": False,
                "error": f"PDF Part {part_number} not found"
            }), 404
        
        # Write to temp file for pdfplumber
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                tmp.write(pdf_content)
                temp_path = tmp.name
            
            matches = search_in_pdf(temp_path, query)
            
            # Paginate results
            total_matches = len(matches)
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            paginated_matches = matches[start_idx:end_idx]
            
            return jsonify({
                "success": True,
                "query": query,
                "part_number": part_number,
                "total_matches": total_matches,
                "page": page,
                "per_page": per_page,
                "total_pages": (total_matches + per_page - 1) // per_page,
                "matches": paginated_matches
            })
        finally:
            # Clean up temp file
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/info', methods=['GET'])
def info():
    """Get application info"""
    return jsonify({
        "app": "Voter List Search",
        "district": DISTRICT,
        "ac_number": AC_NUMBER,
        "ac_name": "Yelahanka",
        "max_parts": 527,
        "pdf_directory": PDF_DIR
    })


@app.route('/api/pdfs/render/<int:part_number>/<int:page>', methods=['GET'])
def render_pdf_page(part_number, page):
    """Render a specific page of a PDF as a PNG image"""
    try:
        filename = get_pdf_filename(AC_NUMBER, part_number)
        pdf_path = os.path.join(PDF_DIR, filename)
        
        if not os.path.exists(pdf_path):
            return jsonify({"success": False, "error": f"PDF Part {part_number} not found"}), 404
            
        # Open PDF with PyMuPDF
        doc = fitz.open(pdf_path)
        
        # Validate page number (1-indexed from frontend, 0-indexed in fitz)
        if page < 1 or page > len(doc):
            doc.close()
            return jsonify({"success": False, "error": f"Invalid page number. Max: {len(doc)}"}), 400
            
        # Get the page
        pdf_page = doc[page - 1]
        
        # Render page to a pixmap (image)
        # zoom=2 for better quality (144 dpi instead of 72 dpi)
        zoom = 2.0
        mat = fitz.Matrix(zoom, zoom)
        pix = pdf_page.get_pixmap(matrix=mat, alpha=False)
        
        # Convert to bytes
        img_bytes = pix.tobytes("png")
        doc.close()
        
        return send_file(
            io.BytesIO(img_bytes),
            mimetype='image/png',
            as_attachment=False,
            download_name=f"part_{part_number}_page_{page}.png"
        )
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    print("\n" + "="*80)
    print("Starting Voter List Search Backend API")
    print("="*80)
    print(f"District: {DISTRICT}")
    print(f"AC: {AC_NUMBER} (Yelahanka)")
    print(f"PDF Directory: {PDF_DIR}")
    print(f"\nAPI will be available at: http://localhost:{port}")
    print("="*80 + "\n")

    app.run(debug=False, host='0.0.0.0', port=port)
