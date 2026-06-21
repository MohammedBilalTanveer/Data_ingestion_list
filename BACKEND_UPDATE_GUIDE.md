# BACKEND_API.PY MODIFICATIONS FOR S3 SUPPORT

# Add this import near the top (after existing imports):
# from storage import get_storage_backend

# ============================================================================
# STEP 1: Replace the initialization section (lines ~30-40)
# ============================================================================

# OLD CODE:
# DISTRICT = os.getenv('DISTRICT', 'BANGALORE URBAN')
# AC_NUMBER = int(os.getenv('AC_NUMBER', '88'))
# BASE_DIR = os.path.dirname(__file__)
# PDF_DIR = os.getenv('PDF_STORAGE_PATH', os.path.join(BASE_DIR, 'output', 'pdfs'))

# NEW CODE:
from storage import get_storage_backend

DISTRICT = os.getenv('DISTRICT', 'BANGALORE URBAN')
AC_NUMBER = int(os.getenv('AC_NUMBER', '88'))
BASE_DIR = os.path.dirname(__file__)

# Initialize storage backend (S3 or local)
try:
    storage = get_storage_backend()
    print(f"Storage initialized: {storage.__class__.__name__}")
except Exception as e:
    print(f"ERROR: Failed to initialize storage: {str(e)}")
    raise


# ============================================================================
# STEP 2: Update download_pdf_file() function
# ============================================================================

# OLD CODE (lines ~74-99):
# def download_pdf_file(url: str, output_path: str, max_retries: int = 3) -> bool:
#     for attempt in range(max_retries):
#         try:
#             response = requests.get(url, timeout=60, verify=True)
#             response.raise_for_status()
#             
#             os.makedirs(os.path.dirname(output_path), exist_ok=True)
#             with open(output_path, 'wb') as f:
#                 f.write(response.content)
#             
#             if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
#                 return True
#             ...

# NEW CODE:
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


# ============================================================================
# STEP 3: Update download_pdfs_in_range() function
# ============================================================================

# OLD CODE (lines ~174-217):
# def download_pdfs_in_range(start_part: int, end_part: int) -> None:
#     ...
#     os.makedirs(PDF_DIR, exist_ok=True)
#     
#     for part in range(start_part, end_part + 1):
#         ...
#         filename = get_pdf_filename(AC_NUMBER, part)
#         pdf_path = os.path.join(PDF_DIR, filename)
#         
#         if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
#             download_state["completed_parts"].append(part)
#             continue
#         
#         url = create_pdf_url(DISTRICT, AC_NUMBER, part)
#         if download_pdf_file(url, pdf_path):
#             download_state["completed_parts"].append(part)

# NEW CODE:
def download_pdfs_in_range(start_part: int, end_part: int) -> None:
    """Download PDFs in the specified range in background"""
    global download_state
    
    download_state["in_progress"] = True
    download_state["status"] = "downloading"
    download_state["completed_parts"] = []
    download_state["failed_parts"] = []
    download_state["total_parts"] = end_part - start_part + 1
    
    for part in range(start_part, end_part + 1):
        download_state["current_part"] = part
        
        try:
            filename = get_pdf_filename(AC_NUMBER, part)
            file_path = f"pdfs/{filename}"  # S3 key format (also works for local)
            
            # Skip if already exists
            if storage.file_exists(file_path) and storage.get_file_size(file_path) > 0:
                download_state["completed_parts"].append(part)
                continue
            
            # Download
            url = create_pdf_url(DISTRICT, AC_NUMBER, part)
            
            if download_pdf_file(url, file_path):
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
# STEP 4: Update list_pdfs() endpoint
# ============================================================================

# OLD CODE (lines ~226-250):
# @app.route('/api/pdfs/list', methods=['GET'])
# def list_pdfs():
#     try:
#         os.makedirs(PDF_DIR, exist_ok=True)
#         pdfs = []
#         
#         if os.path.exists(PDF_DIR):
#             for filename in sorted(os.listdir(PDF_DIR)):
#                 if filename.endswith('.pdf'):
#                     filepath = os.path.join(PDF_DIR, filename)
#                     size_mb = os.path.getsize(filepath) / (1024 * 1024)
#                     part_num = int(filename[5:8]) if len(filename) >= 8 else 0
#                     pdfs.append({...})

# NEW CODE:
@app.route('/api/pdfs/list', methods=['GET'])
def list_pdfs():
    """List all downloaded PDFs"""
    try:
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
        
        return jsonify({"success": True, "pdfs": pdfs, "total": len(pdfs)})
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================================
# STEP 5: Update search() endpoint - for reading PDFs
# ============================================================================

# OLD CODE (lines ~300-330):
# def search():
#     ...
#     pdf_path = os.path.join(PDF_DIR, filename)
#     if not os.path.exists(pdf_path):
#         continue
#     matches = search_in_pdf(pdf_path, query)

# NEW CODE:
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
                file_path = f"pdfs/{filename}"
                
                # Load PDF from storage
                pdf_content = storage.load_file(file_path)
                if not pdf_content:
                    continue
                
                # Write to temp file for pdfplumber (it needs a file path)
                import tempfile
                with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                    tmp.write(pdf_content)
                    tmp_path = tmp.name
                
                try:
                    matches = search_in_pdf(tmp_path, query)
                    
                    if matches:
                        results[f"Part {part_num}"] = {
                            "filename": filename,
                            "part_number": part_num,
                            "matches": matches,
                            "count": len(matches)
                        }
                        total_matches += len(matches)
                finally:
                    # Clean up temp file
                    import os
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
            
            except Exception as e:
                print(f"Error searching part {part_num}: {str(e)}")
                continue
        
        return jsonify({
            "success": True,
            "results": results,
            "total_matches": total_matches
        })
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================================
# SUMMARY OF CHANGES
# ============================================================================
# 1. Import storage backend
# 2. Replace os.path.join() → storage methods
# 3. Replace open() → storage.load_file() / storage.save_file()
# 4. Replace os.path.exists() → storage.file_exists()
# 5. Replace os.path.getsize() → storage.get_file_size()
# 6. Replace os.listdir() → storage.list_files()

# File paths should use format: "pdfs/filename.pdf" for S3
# This works for both S3 (as keys) and local (as relative paths)
