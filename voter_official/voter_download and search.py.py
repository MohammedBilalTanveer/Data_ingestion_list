import os
import sys
import time
import requests
from urllib.parse import quote
import pdfplumber
from typing import List, Dict, Tuple
from pathlib import Path

# ============================================================================
# CONFIGURATION
# ============================================================================

DISTRICT = "BANGALORE URBAN"
AC_NUMBER = 88  # Yelahanka
PART_NUMBERS = [278]  # Start with 278, extend for more parts

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
PDF_DIR = os.path.join(OUTPUT_DIR, "pdfs")  # Dedicated folder for PDFs

# Search settings
SEARCH_CASE_SENSITIVE = False
MIN_QUERY_LENGTH = 2
MAX_RETRIES = 3
TIMEOUT = 60


# ============================================================================
# PDF URL & DOWNLOAD
# ============================================================================

def download_pdf(url: str, output_path: str, max_retries: int = MAX_RETRIES) -> bool:
    """Download PDF with retry logic and better error handling"""
    filename = os.path.basename(output_path)
    print(f"  📥 Downloading: {filename}")
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=TIMEOUT, verify=True)
            response.raise_for_status()
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Write file
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            # Verify file was written
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                size_mb = os.path.getsize(output_path) / (1024 * 1024)
                print(f"  ✓ Successfully downloaded ({size_mb:.2f} MB)")
                return True
            else:
                print(f"  ✗ File verification failed")
                if os.path.exists(output_path):
                    os.remove(output_path)
                continue
                
        except requests.exceptions.Timeout:
            print(f"  ⚠ Timeout (attempt {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
            continue
        except requests.exceptions.ConnectionError:
            print(f"  ⚠ Connection error (attempt {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            continue
        except requests.exceptions.HTTPError as e:
            print(f"  ✗ HTTP Error: {e.response.status_code}")
            return False
        except Exception as e:
            print(f"  ✗ Unexpected error: {str(e)}")
            return False
    
    print(f"  ✗ Failed to download after {max_retries} attempts")
    return False



# ============================================================================
# PDF SEARCH
# ============================================================================

def extract_text_from_pdf(pdf_path: str) -> Dict[int, str]:
    """
    Extract all text from a PDF organized by page
    Returns: {page_num: text}
    """
    pages_text = {}
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            for page_num, page in enumerate(pdf.pages, 1):
                try:
                    text = page.extract_text()
                    if text:
                        pages_text[page_num] = text
                    else:
                        # Try alternative extraction if primary fails
                        pages_text[page_num] = ""
                except Exception as e:
                    print(f"    ⚠ Error extracting page {page_num}: {str(e)}")
                    pages_text[page_num] = ""
        
        if pages_text:
            extracted_count = sum(1 for text in pages_text.values() if text)
            return pages_text
        else:
            print(f"    ⚠ No text extracted from PDF")
            return {}
            
    except Exception as e:
        print(f"    ✗ Error reading PDF: {str(e)}")
        return {}


def search_in_pdf(pdf_path: str, query: str) -> List[Dict]:
    """
    Search for query in a single PDF and return matching results with context
    """
    if not query or len(query.strip()) < MIN_QUERY_LENGTH:
        return []
    
    query = query.strip()
    pages_text = extract_text_from_pdf(pdf_path)
    
    if not pages_text:
        return []
    
    matches = []
    query_lower = query.lower() if not SEARCH_CASE_SENSITIVE else query
    
    for page_num in sorted(pages_text.keys()):
        text = pages_text[page_num]
        if not text:
            continue
        
        lines = text.split('\n')
        
        for line_idx, line in enumerate(lines):
            # Check if query matches
            line_check = line.lower() if not SEARCH_CASE_SENSITIVE else line
            
            if query_lower in line_check:
                # Build context (previous and next lines)
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
                
                # Create match entry
                match = {
                    'page': page_num,
                    'snippet': ' | '.join(context_lines),
                    'line_idx': line_idx,
                    'original_line': line.strip()
                }
                matches.append(match)
    
    return matches


def search_all_pdfs(pdf_paths: List[str], query: str) -> Dict[str, List[Dict]]:
    """Search across all provided PDFs"""
    results = {}
    total_matches = 0
    
    print(f"\n  🔍 Searching for: '{query}'")
    print(f"  📄 Scanning {len(pdf_paths)} PDF(s)...\n")
    
    for pdf_path in pdf_paths:
        filename = os.path.basename(pdf_path)
        try:
            matches = search_in_pdf(pdf_path, query)
            if matches:
                results[filename] = matches
                total_matches += len(matches)
                print(f"     ✓ {filename}: {len(matches)} match(es)")
            else:
                print(f"     ○ {filename}: No matches")
        except Exception as e:
            print(f"     ✗ {filename}: Error - {str(e)}")
    
    if total_matches > 0:
        print(f"\n  ✅ Total: {total_matches} match(es) found")
    else:
        print(f"\n  ❌ No matches found")
    
    return results


# ============================================================================
# INTERACTIVE SEARCH
# ============================================================================

def display_search_help():
    """Display help information"""
    print("\n" + "="*80)
    print("SEARCH HELP")
    print("="*80)
    print("• Type any name, part number, serial, or keyword to search")
    print("• Search works on all loaded PDFs")
    print("• Minimum 2 characters required")
    print("• Results show context (previous and next lines)")
    print("\nCommands:")
    print("  'exit' or 'quit' - Exit search")
    print("  'help'           - Show this help")
    print("  'list'           - List loaded PDFs")
    print("="*80 + "\n")


def interactive_search(pdf_paths: List[str]):
    """Interactive terminal search with improved UX"""
    if not pdf_paths:
        print("❌ No PDFs available for searching")
        return
    
    print("\n" + "="*80)
    print("📚 VOTER LIST PDF SEARCH")
    print("="*80)
    print(f"Loaded PDFs: {len(pdf_paths)}")
    for i, pdf_path in enumerate(pdf_paths, 1):
        filename = os.path.basename(pdf_path)
        size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
        print(f"  {i}. {filename} ({size_mb:.2f} MB)")
    print("="*80)
    print("\n📝 Enter search query (type 'help' for options, 'exit' to quit)")
    
    search_count = 0
    while True:
        try:
            query = input("\n🔎 Search: ").strip()
            
            # Handle commands
            if query.lower() in ['exit', 'quit', 'q']:
                print("\n👋 Goodbye!")
                break
            elif query.lower() == 'help':
                display_search_help()
                continue
            elif query.lower() == 'list':
                print("\n📄 Loaded PDFs:")
                for i, pdf_path in enumerate(pdf_paths, 1):
                    filename = os.path.basename(pdf_path)
                    size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
                    print(f"  {i}. {filename} ({size_mb:.2f} MB)")
                continue
            elif query.lower() == 'clear':
                os.system('cls' if os.name == 'nt' else 'clear')
                continue
            elif len(query) == 0:
                continue
            elif len(query) < MIN_QUERY_LENGTH:
                print(f"❌ Query too short (minimum {MIN_QUERY_LENGTH} characters)")
                continue
            
            # Perform search
            search_count += 1
            start_time = time.time()
            results = search_all_pdfs(pdf_paths, query)
            elapsed = time.time() - start_time
            
            if not results:
                print(f"❌ No matches found for '{query}'")
                continue
            
            # Display results
            total_matches = sum(len(m) for m in results.values())
            print(f"\n" + "="*80)
            print(f"✅ SEARCH RESULTS - {total_matches} match(es) found ({elapsed:.2f}s)")
            print("="*80)
            
            for filename, matches in results.items():
                print(f"\n📄 {filename} ({len(matches)} matches):")
                print("-" * 80)
                
                # Display up to 10 matches per file
                for idx, match in enumerate(matches[:10], 1):
                    page = match['page']
                    snippet = match['snippet']
                    
                    # Truncate long snippets
                    if len(snippet) > 100:
                        snippet = snippet[:97] + "..."
                    
                    print(f"  {idx}. [Page {page}] {snippet}")
                
                if len(matches) > 10:
                    remaining = len(matches) - 10
                    print(f"\n  ... and {remaining} more match(es)")
            
            print("\n" + "="*80)
                    
        except KeyboardInterrupt:
            print("\n\n👋 Search interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"⚠️  Error during search: {str(e)}")
            print("   Please try again or type 'exit' to quit")



# ============================================================================
# MAIN
# ============================================================================

def ensure_pdfs_downloaded() -> List[str]:
    """
    Download missing PDFs and return list of all available PDF paths
    Flow: Check → Download → Verify
    """
    os.makedirs(PDF_DIR, exist_ok=True)
    pdf_paths = []
    
    print("\n" + "="*80)
    print("📥 DOWNLOAD PHASE - Checking/Downloading PDFs")
    print("="*80)
    
    for part in PART_NUMBERS:
        try:
            # Get filename and path
            ac_str = str(AC_NUMBER).zfill(3)
            part_str = str(part).zfill(3)
            # Important: The PDF number format includes an extra 0: A088 + 0 + 278 = A0880278
            pdf_number = f"A{ac_str}0{part_str}"
            filename = f"{pdf_number}.pdf"
            pdf_path = os.path.join(PDF_DIR, filename)
            
            # Check if file already exists
            if os.path.exists(pdf_path):
                size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
                print(f"\n✓ Found: {filename} ({size_mb:.2f} MB)")
                pdf_paths.append(pdf_path)
                continue
            
            # File doesn't exist, need to download
            print(f"\n⏳ Part {part}: Preparing download...")
            
            # Build URL with correct PDF number format
            district_encoded = quote(DISTRICT)
            ac_encoded = quote(f"AC {AC_NUMBER}")
            url = f"https://ceo.karnataka.gov.in/uploads/{district_encoded}/{ac_encoded}/{filename}"
            
            print(f"  URL: {url[:70]}...")
            
            # Download
            if download_pdf(url, pdf_path):
                pdf_paths.append(pdf_path)
            else:
                print(f"  ⚠️  Skipping part {part} due to download failure")
                
        except Exception as e:
            print(f"  ✗ Error processing part {part}: {str(e)}")
            continue
    
    print("\n" + "="*80)
    if pdf_paths:
        print(f"✅ Download complete: {len(pdf_paths)} PDF(s) ready")
    else:
        print("❌ No PDFs available for searching")
    print("="*80)
    
    return pdf_paths


def main():
    """Main entry point with proper flow: Download → Search"""
    print("\n")
    print("█" * 80)
    print("█" + " " * 78 + "█")
    print("█" + "  🗳️  KARNATAKA VOTER LIST - PDF DOWNLOAD & SEARCH TOOL".center(78) + "█")
    print("█" + " " * 78 + "█")
    print("█" * 80)
    
    print(f"\n📍 Configuration:")
    print(f"   • District    : {DISTRICT}")
    print(f"   • AC           : {AC_NUMBER} (Yelahanka)")
    print(f"   • Parts        : {', '.join(map(str, PART_NUMBERS))}")
    print(f"   • PDF Location : {PDF_DIR}")
    
    # Phase 1: Download PDFs
    print("\n")
    pdf_paths = ensure_pdfs_downloaded()
    
    if not pdf_paths:
        print("\n❌ Cannot proceed without PDFs. Exiting.")
        return
    
    # Phase 2: Interactive Search
    print("\n" + "="*80)
    print("🔍 SEARCH PHASE - Ready to search")
    print("="*80)
    
    interactive_search(pdf_paths)
    
    print("\n" + "█" * 80)
    print("Thank you for using Voter List Search Tool! 👋\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Program interrupted by user. Exiting...")
        sys.exit(0)
    except Exception as e:
        print(f"\n💥 Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)