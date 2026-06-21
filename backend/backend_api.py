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

load_dotenv()

# Configuration
app = Flask(__name__)

# Restrict CORS to the deployed frontend URL in production; allow all in dev
_frontend_url = os.getenv('FRONTEND_URL')
if _frontend_url:
    CORS(app, origins=_frontend_url.split(','))
else:
    CORS(app)

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
    "status": "idle"
}


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


def download_pdf_file(url: str, output_path: str, max_retries: int = 3) -> bool:
    """Download single PDF with retry logic"""
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=60, verify=True)
            response.raise_for_status()
            
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                return True
            
            if os.path.exists(output_path):
                os.remove(output_path)
                
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
    download_state["completed_parts"] = []
    download_state["failed_parts"] = []
    download_state["total_parts"] = end_part - start_part + 1
    
    os.makedirs(PDF_DIR, exist_ok=True)
    
    for part in range(start_part, end_part + 1):
        download_state["current_part"] = part
        
        try:
            filename = get_pdf_filename(AC_NUMBER, part)
            pdf_path = os.path.join(PDF_DIR, filename)
            
            # Skip if already exists
            if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
                download_state["completed_parts"].append(part)
                continue
            
            # Download
            url = create_pdf_url(DISTRICT, AC_NUMBER, part)
            
            if download_pdf_file(url, pdf_path):
                download_state["completed_parts"].append(part)
            else:
                download_state["failed_parts"].append(part)
        
        except Exception as e:
            print(f"Error processing part {part}: {str(e)}")
            download_state["failed_parts"].append(part)
        
        time.sleep(0.5)  # Small delay between downloads
    
    download_state["in_progress"] = False
    download_state["status"] = "idle"


# ============================================================================
# API ROUTES
# ============================================================================

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok", "message": "Backend API is running"})


@app.route('/api/pdfs/list', methods=['GET'])
def list_pdfs():
    """List all downloaded PDFs"""
    try:
        os.makedirs(PDF_DIR, exist_ok=True)
        pdfs = []
        
        if os.path.exists(PDF_DIR):
            for filename in sorted(os.listdir(PDF_DIR)):
                if filename.endswith('.pdf'):
                    filepath = os.path.join(PDF_DIR, filename)
                    size_mb = os.path.getsize(filepath) / (1024 * 1024)
                    # Extract part number from filename (e.g., A0880278.pdf -> 278)
                    part_num = int(filename[5:8]) if len(filename) >= 8 else 0
                    pdfs.append({
                        "filename": filename,
                        "part_number": part_num,
                        "size_mb": round(size_mb, 2)
                    })
        
        return jsonify({"success": True, "pdfs": pdfs, "total": len(pdfs)})
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/pdfs/download', methods=['POST'])
def download_pdfs():
    """Start downloading PDFs in range"""
    try:
        data = request.json
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


@app.route('/api/downloads/status', methods=['GET'])
def download_status():
    """Get current download status"""
    return jsonify({
        "in_progress": download_state["in_progress"],
        "current_part": download_state["current_part"],
        "total_parts": download_state["total_parts"],
        "completed_parts": len(download_state["completed_parts"]),
        "failed_parts": len(download_state["failed_parts"]),
        "status": download_state["status"]
    })


@app.route('/api/search', methods=['POST'])
def search():
    """Search across specified PDFs"""
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
            try:
                filename = get_pdf_filename(AC_NUMBER, part_num)
                pdf_path = os.path.join(PDF_DIR, filename)
                
                if not os.path.exists(pdf_path):
                    continue
                
                matches = search_in_pdf(pdf_path, query)
                
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
        pdf_path = os.path.join(PDF_DIR, filename)
        
        if not os.path.exists(pdf_path):
            return jsonify({
                "success": False,
                "error": f"PDF Part {part_number} not found"
            }), 404
        
        matches = search_in_pdf(pdf_path, query)
        
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
