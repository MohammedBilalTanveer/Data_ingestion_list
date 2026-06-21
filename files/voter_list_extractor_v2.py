#pdf_search_extractor.py
"""
Simplified Voter List Extractor for Kannada PDFs
=================================================
Fetches PDF from election website and extracts text using pdfplumber.
No OCR, no complex transformations - just straightforward extraction.

Based on improved version of fetch_data.py with corrections.
Works for Part 278 (Yelahanka AC 88, Bangalore Urban)
"""

import os
import sys
import time
import requests
import pdfplumber
import pandas as pd
from typing import List, Dict, Tuple
from urllib.parse import quote


# ============================================================================
# CONFIGURATION
# ============================================================================

DISTRICT = "BANGALORE URBAN"
AC_NUMBER = 88  # Yelahanka
PART_NUMBER = 278

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
TEMP_PDF_DIR = os.path.join(OUTPUT_DIR, "temp_pdfs")

# Page extraction settings
START_PAGE = 1  # Start from page 2 (0-indexed)
NUM_PAGES_TO_PROCESS = 5  # Process 5 pages (adjust as needed)


# ============================================================================
# PDF URL CREATION & DOWNLOAD
# ============================================================================

def create_pdf_url(district: str, ac: int, part_number: int) -> str:
    """
    Construct the PDF URL from district, AC, and part number.
    
    Format: https://ceo.karnataka.gov.in/uploads/{DISTRICT}/{AC}/{A088278.pdf}
    """
    # Format: A + AC (3 digits) + Part (3 digits)
    # Example: A88278 or A088278
    ac_str = str(ac).zfill(3)  # Pad AC to 3 digits: 88 -> 088
    part_str = str(part_number).zfill(3)  # Pad part to 3 digits: 278 -> 278
    pdf_number = f"A{ac_str}{part_str}"  # A088278
    
    # URL encode the parameters
    district_encoded = quote(district)  # BANGALORE%20URBAN
    ac_encoded = quote(f"AC {ac}")      # AC%2088
    
    # Construct URL
    url = f"https://ceo.karnataka.gov.in/uploads/{district_encoded}/{ac_encoded}/{pdf_number}.pdf"
    
    return url


def get_pdf_filename(ac: int, part_number: int) -> str:
    """Get the standard PDF filename"""
    ac_str = str(ac).zfill(3)
    part_str = str(part_number).zfill(3)
    return f"A{ac_str}{part_str}.pdf"


def download_pdf(url: str, output_path: str) -> bool:
    """Download PDF from the given URL"""
    print(f"\n📥 Downloading PDF: {os.path.basename(output_path)}")
    print(f"   URL: {url}")
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # Create directory if needed
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Save PDF
        with open(output_path, 'wb') as f:
            f.write(response.content)
        
        file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
        print(f"✓ PDF downloaded successfully ({file_size_mb:.2f} MB)")
        return True
        
    except requests.exceptions.Timeout:
        print(f"✗ Download timeout - server took too long to respond")
        return False
    except requests.exceptions.ConnectionError:
        print(f"✗ Connection error - cannot reach server")
        return False
    except requests.exceptions.RequestException as e:
        print(f"✗ Request failed: {str(e)}")
        return False
    except Exception as e:
        print(f"✗ Error saving PDF: {str(e)}")
        return False


# ============================================================================
# PDF TEXT EXTRACTION
# ============================================================================

def extract_text_from_pdf(pdf_path: str) -> List[Dict]:
    """
    Extract text from PDF using pdfplumber
    Returns list of rows with extracted data
    """
    print(f"\n📄 Extracting text from PDF: {os.path.basename(pdf_path)}")
    
    rows = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            print(f"   Total pages: {total_pages}")
            print(f"   Processing pages {START_PAGE + 1} to {min(START_PAGE + NUM_PAGES_TO_PROCESS, total_pages)}...")
            
            # Process specified pages
            for page_idx in range(START_PAGE, min(START_PAGE + NUM_PAGES_TO_PROCESS, total_pages)):
                print(f"   Processing page {page_idx + 1}/{total_pages}...", end="\r")
                
                page = pdf.pages[page_idx]
                text = page.extract_text()
                
                if not text:
                    continue
                
                # Extract lines
                lines = text.split('\n')
                
                for line in lines:
                    line = line.strip()
                    if not line or len(line) < 5:
                        continue
                    
                    # Split by multiple spaces (typical table separator)
                    cells = [cell.strip() for cell in line.split('  ') if cell.strip()]
                    
                    if len(cells) >= 3:  # At least 3 meaningful columns
                        row = {
                            'raw_line': line,
                            'cells': cells,
                            'num_fields': len(cells),
                            'page': page_idx + 1
                        }
                        rows.append(row)
        
        print(f"   ✓ Extracted {len(rows)} rows from PDF" + " " * 30)
        return rows
        
    except Exception as e:
        print(f"✗ Error extracting text from PDF: {str(e)}")
        return []


def extract_table_from_pdf(pdf_path: str) -> List[List[str]]:
    """
    Extract table data from PDF using pdfplumber's built-in table detection.
    This is cleaner than raw text extraction for structured tables.
    """
    print(f"\n📊 Extracting tables from PDF: {os.path.basename(pdf_path)}")
    
    all_rows = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            print(f"   Total pages: {total_pages}")
            print(f"   Processing pages {START_PAGE + 1} to {min(START_PAGE + NUM_PAGES_TO_PROCESS, total_pages)}...")
            
            # Process specified pages
            for page_idx in range(START_PAGE, min(START_PAGE + NUM_PAGES_TO_PROCESS, total_pages)):
                print(f"   Processing page {page_idx + 1}/{total_pages}...", end="\r")
                
                page = pdf.pages[page_idx]
                
                # Extract tables from page
                tables = page.extract_tables()
                
                if not tables:
                    continue
                
                # Process each table on the page
                for table in tables:
                    for row in table:
                        # Clean row data - handle None values
                        cleaned_row = [str(cell).strip() if cell else "" for cell in row]
                        
                        # Skip completely empty rows
                        if all(c == "" for c in cleaned_row):
                            continue
                        
                        all_rows.append(cleaned_row)
        
        print(f"   ✓ Extracted {len(all_rows)} rows from {total_pages} pages" + " " * 20)
        return all_rows
        
    except Exception as e:
        print(f"✗ Error extracting tables: {str(e)}")
        print("   Falling back to text extraction...")
        return []


# ============================================================================
# DATA PROCESSING
# ============================================================================

def clean_table_data(rows: List[List[str]]) -> List[List[str]]:
    """
    Clean extracted table data
    """
    cleaned_rows = []
    
    for row in rows:
        if not row or all(c == "" for c in row):
            continue
        
        # Remove any separator artifacts
        cleaned_row = []
        for cell in row:
            cleaned_cell = str(cell).replace("|||CELLSEP|||", "").replace("|SEP|", "").replace("|||", "").strip()
            cleaned_row.append(cleaned_cell)
        
        cleaned_rows.append(cleaned_row)
    
    return cleaned_rows


# ============================================================================
# EXCEL EXPORT
# ============================================================================

def save_to_excel(rows: List[List[str]], output_path: str) -> bool:
    """Save extracted rows to Excel file"""
    print(f"\n💾 Saving to Excel: {os.path.basename(output_path)}")
    
    if not rows:
        print("✗ No data to save")
        return False
    
    try:
        # Determine max columns
        max_cols = max(len(row) for row in rows) if rows else 8
        
        # Pad rows to have equal columns
        padded_rows = []
        for row in rows:
            padded_row = row + [""] * (max_cols - len(row))
            padded_rows.append(padded_row)
        
        # Create column names
        column_names = [
            "Serial No.",
            "Voter Name",
            "Relation Name",
            "Relation Type",
            "Gender",
            "Age",
            "Voter ID",
        ]
        
        # Add extra column names if needed
        for i in range(len(column_names), max_cols):
            column_names.append(f"Column {i+1}")
        
        # Create DataFrame
        df = pd.DataFrame(padded_rows, columns=column_names[:max_cols])
        
        # Create output directory
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Save to Excel
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Voter List')
            
            # Adjust column widths
            ws = writer.sheets['Voter List']
            for col_idx, col_name in enumerate(column_names[:max_cols], 1):
                ws.column_dimensions[chr(64 + col_idx)].width = 22
        
        print(f"✓ Saved to Excel")
        print(f"  📁 File: {output_path}")
        print(f"  📊 Rows: {len(padded_rows)}")
        print(f"  📋 Columns: {max_cols}")
        return True
        
    except Exception as e:
        print(f"✗ Error saving to Excel: {str(e)}")
        return False


# ============================================================================
# MAIN WORKFLOW
# ============================================================================

def main():
    """Main workflow"""
    print("\n" + "=" * 80)
    print("SIMPLIFIED VOTER LIST EXTRACTOR")
    print("=" * 80)
    print(f"District:      {DISTRICT}")
    print(f"AC Number:     {AC_NUMBER} (Yelahanka)")
    print(f"Part Number:   {PART_NUMBER}")
    print(f"Pages to Read: {START_PAGE + 1} to {START_PAGE + NUM_PAGES_TO_PROCESS}")
    print(f"Output Dir:    {OUTPUT_DIR}")
    print("=" * 80)
    
    # Create directories
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(TEMP_PDF_DIR, exist_ok=True)
    
    # ========================================================================
    # STEP 1: GET PDF
    # ========================================================================
    print("\n" + "=" * 80)
    print("STEP 1: GET PDF")
    print("=" * 80)
    
    pdf_filename = get_pdf_filename(AC_NUMBER, PART_NUMBER)
    pdf_path = os.path.join(TEMP_PDF_DIR, pdf_filename)
    
    # Check if PDF already exists
    if os.path.exists(pdf_path):
        file_size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
        print(f"✓ PDF already exists: {pdf_filename} ({file_size_mb:.2f} MB)")
    else:
        pdf_url = create_pdf_url(DISTRICT, AC_NUMBER, PART_NUMBER)
        
        if not download_pdf(pdf_url, pdf_path):
            print("\n" + "=" * 80)
            print("⚠️  AUTOMATIC DOWNLOAD FAILED - MANUAL DOWNLOAD REQUIRED")
            print("=" * 80)
            print("\n📌 FOLLOW THESE STEPS:")
            print("\n1. Visit: https://ceo.karnataka.gov.in/voter_list/en")
            print("\n2. Select:")
            print(f"   • District: {DISTRICT}")
            print(f"   • AC: {AC_NUMBER} (Yelahanka)")
            print(f"   • Part Number: {PART_NUMBER}")
            print("\n3. Download the PDF")
            print(f"\n4. Save to: {pdf_path}")
            print("\n5. Run this script again")
            print("\n" + "=" * 80)
            return
    
    # ========================================================================
    # STEP 2: EXTRACT DATA
    # ========================================================================
    print("\n" + "=" * 80)
    print("STEP 2: EXTRACT DATA FROM PDF")
    print("=" * 80)
    
    # Try table extraction first (better for structured tables)
    table_data = extract_table_from_pdf(pdf_path)
    
    # Fall back to text extraction if table extraction fails
    if not table_data:
        print("\n   ⚠ Table extraction didn't work, trying text extraction...")
        raw_rows = extract_text_from_pdf(pdf_path)
        
        if raw_rows:
            # Convert to table format
            table_data = [row['cells'] for row in raw_rows]
        else:
            print("✗ Could not extract any data from PDF")
            return
    
    # Clean the data
    table_data = clean_table_data(table_data)
    
    if not table_data:
        print("✗ No valid data extracted")
        return
    
    # ========================================================================
    # STEP 3: DISPLAY SAMPLE
    # ========================================================================
    print("\n" + "=" * 80)
    print("SAMPLE DATA (First 5 rows)")
    print("=" * 80)
    
    for idx, row in enumerate(table_data[:5], 1):
        print(f"\nRow {idx}:")
        for col_idx, cell in enumerate(row[:7], 1):  # Show first 7 columns
            preview = cell[:45] + "..." if len(cell) > 45 else cell
            print(f"  Col {col_idx}: {preview}")
        
        if len(row) > 7:
            print(f"  ... and {len(row) - 7} more columns")
    
    # ========================================================================
    # STEP 4: SAVE TO EXCEL
    # ========================================================================
    print("\n" + "=" * 80)
    print("STEP 3: SAVE TO EXCEL")
    print("=" * 80)
    
    xlsx_filename = f"voter_list_part_{PART_NUMBER:03d}.xlsx"
    xlsx_path = os.path.join(OUTPUT_DIR, xlsx_filename)
    
    if save_to_excel(table_data, xlsx_path):
        # ====================================================================
        # SUMMARY
        # ====================================================================
        print("\n" + "=" * 80)
        print("✓ PROCESS COMPLETED SUCCESSFULLY")
        print("=" * 80)
        print(f"\n📁 Output file created: {xlsx_path}")
        print(f"\n📊 Summary:")
        print(f"   • Total rows extracted: {len(table_data)}")
        print(f"   • Total columns: {max(len(row) for row in table_data)}")
        
        print(f"\n📋 Next Steps:")
        print(f"   1. Open {xlsx_filename} and verify the data")
        print(f"   2. To process other parts, change PART_NUMBER in the script")
        print(f"   3. Or create a loop to batch process multiple parts")
        
        print("\n" + "=" * 80)
    else:
        print("\n✗ Failed to save Excel file")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠ Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Unexpected error: {str(e)}")
        sys.exit(1)
