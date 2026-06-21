import os
import sys
import time
import requests
from urllib.parse import quote
import pdfplumber
from typing import List, Dict

# ============================================================================
# CONFIGURATION
# ============================================================================

DISTRICT = "BANGALORE URBAN"
AC_NUMBER = 88  # Yelahanka
PART_NUMBERS = [278]  # Start with 278, you can extend this list later

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
PDF_DIR = os.path.join(OUTPUT_DIR, "pdfs")  # Dedicated folder for PDFs

# Search settings
SEARCH_CASE_SENSITIVE = False
MIN_QUERY_LENGTH = 2


# ============================================================================
# PDF URL & DOWNLOAD
# ============================================================================

def create_pdf_url(district: str, ac: int, part_number: int) -> str:
    """Construct the PDF URL"""
    ac_str = str(ac).zfill(3)
    part_str = str(part_number).zfill(3)
    pdf_number = f"A{ac_str}{part_str}"
    
    district_encoded = quote(district)
    ac_encoded = quote(f"AC {ac}")
    
    url = f"https://ceo.karnataka.gov.in/uploads/{district_encoded}/{ac_encoded}/{pdf_number}.pdf"
    return url


def get_pdf_filename(ac: int, part_number: int) -> str:
    """Get standard PDF filename"""
    ac_str = str(ac).zfill(3)
    part_str = str(part_number).zfill(3)
    return f"A{ac_str}{part_str}.pdf"


def download_pdf(url: str, output_path: str) -> bool:
    """Download PDF"""
    print(f"📥 Downloading: {os.path.basename(output_path)}")
    try:
        response = requests.get(url, timeout=45)
        response.raise_for_status()
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'wb') as f:
            f.write(response.content)
        
        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        print(f"✓ Downloaded successfully ({size_mb:.2f} MB)")
        return True
    except Exception as e:
        print(f"✗ Download failed: {str(e)}")
        return False


def ensure_pdfs_downloaded() -> List[str]:
    """Download missing PDFs and return list of all PDF paths"""
    os.makedirs(PDF_DIR, exist_ok=True)
    pdf_paths = []
    
    print("\n=== Checking/Downloading PDFs ===")
    for part in PART_NUMBERS:
        filename = get_pdf_filename(AC_NUMBER, part)
        pdf_path = os.path.join(PDF_DIR, filename)
        
        if os.path.exists(pdf_path):
            size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
            print(f"✓ Found: {filename} ({size_mb:.2f} MB)")
        else:
            print(f"Downloading missing part {part}...")
            url = create_pdf_url(DISTRICT, AC_NUMBER, part)
            if not download_pdf(url, pdf_path):
                print(f"⚠ Skipping part {part} due to download failure")
                continue
        
        if os.path.exists(pdf_path):
            pdf_paths.append(pdf_path)
    
    return pdf_paths


# ============================================================================
# PDF SEARCH
# ============================================================================

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract all text from a PDF"""
    full_text = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text()
                if text:
                    full_text.append(f"--- Page {page_num} ---\n{text}\n")
        return "\n".join(full_text)
    except Exception as e:
        print(f"✗ Error reading {os.path.basename(pdf_path)}: {str(e)}")
        return ""


def search_in_pdf(pdf_path: str, query: str) -> List[Dict]:
    """Search for query in a single PDF and return matching snippets"""
    if not query or len(query.strip()) < MIN_QUERY_LENGTH:
        return []
    
    query = query.strip()
    text = extract_text_from_pdf(pdf_path)
    if not text:
        return []
    
    matches = []
    lines = text.split('\n')
    
    for i, line in enumerate(lines):
        if not SEARCH_CASE_SENSITIVE:
            if query.lower() in line.lower():
                # Get context (previous and next line)
                context = []
                if i > 0:
                    context.append(lines[i-1].strip())
                context.append(line.strip())
                if i < len(lines) - 1:
                    context.append(lines[i+1].strip())
                
                matches.append({
                    'page': "Unknown" if "--- Page" not in line else line.split('--- Page')[1].split('---')[0].strip(),
                    'snippet': " | ".join([c for c in context if c]),
                    'line_num': i + 1
                })
        else:
            if query in line:
                matches.append({
                    'snippet': line.strip(),
                    'line_num': i + 1
                })
    
    return matches


def search_all_pdfs(pdf_paths: List[str], query: str) -> Dict[str, List[Dict]]:
    """Search across all PDFs"""
    results = {}
    print(f"\n🔍 Searching for: '{query}' across {len(pdf_paths)} PDFs...")
    
    for pdf_path in pdf_paths:
        filename = os.path.basename(pdf_path)
        matches = search_in_pdf(pdf_path, query)
        if matches:
            results[filename] = matches
            print(f"   ✓ Found {len(matches)} matches in {filename}")
    
    return results


# ============================================================================
# INTERACTIVE SEARCH
# ============================================================================

def interactive_search(pdf_paths: List[str]):
    """Interactive terminal search prompt"""
    print("\n" + "="*80)
    print("VOTER LIST SEARCH TOOL")
    print("="*80)
    print("Type your search query (Kannada or English names/words work)")
    print("Commands:")
    print("   exit     - Quit")
    print("   help     - Show this message")
    print("   count    - Show total PDFs loaded")
    print("="*80)
    
    while True:
        try:
            query = input("\n🔎 Enter search query: ").strip()
            
            if query.lower() in ['exit', 'quit', 'q']:
                print("👋 Goodbye!")
                break
            elif query.lower() == 'help':
                print("Type any name, part number, serial, or keyword to search.")
                continue
            elif query.lower() == 'count':
                print(f"Loaded {len(pdf_paths)} PDFs")
                continue
            elif len(query) < MIN_QUERY_LENGTH:
                print(f"Query too short. Minimum {MIN_QUERY_LENGTH} characters.")
                continue
            
            start_time = time.time()
            results = search_all_pdfs(pdf_paths, query)
            elapsed = time.time() - start_time
            
            if not results:
                print(f"❌ No matches found for '{query}'")
                continue
            
            total_matches = sum(len(m) for m in results.values())
            print(f"\n✅ Found {total_matches} matches in {len(results)} files ({elapsed:.2f}s)")
            
            # Display results
            for filename, matches in results.items():
                print(f"\n📄 {filename} ({len(matches)} matches):")
                for i, match in enumerate(matches[:8], 1):  # Show top 8 per file
                    print(f"   {i}. {match['snippet'][:120]}{'...' if len(match['snippet']) > 120 else ''}")
                if len(matches) > 8:
                    print(f"   ... and {len(matches)-8} more matches")
                    
        except KeyboardInterrupt:
            print("\n\n👋 Search interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"⚠ Error during search: {str(e)}")


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("="*80)
    print("KARNATAKA VOTER LIST PDF DOWNLOADER + SEARCH TOOL")
    print("="*80)
    print(f"District : {DISTRICT}")
    print(f"AC       : {AC_NUMBER}")
    print(f"Parts    : {PART_NUMBERS}")
    print(f"PDF Dir  : {PDF_DIR}")
    print("="*80)
    
    # Download / verify PDFs
    pdf_paths = ensure_pdfs_downloaded()
    
    if not pdf_paths:
        print("❌ No PDFs available. Exiting.")
        return
    
    print(f"\n✅ Ready with {len(pdf_paths)} PDFs.")
    print("Starting interactive search...\n")
    
    interactive_search(pdf_paths)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Exited by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n💥 Unexpected error: {str(e)}")
        sys.exit(1)