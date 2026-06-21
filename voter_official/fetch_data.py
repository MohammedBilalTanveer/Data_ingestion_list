#fetch_data.py
import os
import re
import sys
import time
import requests
import pandas as pd
import pytesseract
import cv2
import numpy as np

from pdf2image import convert_from_path
from googletrans import Translator
from urllib.parse import quote
from PIL import Image

# Configuration
DISTRICT = "BANGALORE URBAN"
AC_NUMBER = "88"  # Yelahanka
PART_NUMBER = 278  # Currently downloading only part 278

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
TEMP_PDF_DIR = os.path.join(OUTPUT_DIR, "temp_pdfs")

# Page extraction settings
START_PAGE = 1  # Start from page 2 (0-indexed, so page 1 means 2nd page)
NUM_PAGES_TO_PROCESS = 2  # Process only 2 pages for testing

# Windows users - Tesseract path configuration
# Try common installation paths
TESSERACT_PATHS = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    r"C:\Users\moham\AppData\Local\Tesseract-OCR\tesseract.exe",
]

# Poppler paths for Conda and manual installations
POPPLER_PATHS = [
    os.path.expanduser(r"~\anaconda3\Library\bin"),  # Anaconda
    os.path.expanduser(r"~\miniconda3\Library\bin"),  # Miniconda
    os.path.expanduser(r"~\miniforge3\Library\bin"),  # Miniforge
    r"C:\poppler\Library\bin",  # Manual download
]

def setup_tesseract():
    """Setup Tesseract path for Windows"""
    for path in TESSERACT_PATHS:
        if os.path.exists(path):
            pytesseract.pytesseract.tesseract_cmd = path
            print(f"✓ Tesseract found at: {path}")
            return True
    print("⚠ Tesseract not found. Please install from: https://github.com/UB-Mannheim/tesseract/wiki")
    return False

def setup_poppler():
    """Setup Poppler path from Conda or manual installation"""
    for poppler_path in POPPLER_PATHS:
        if os.path.exists(poppler_path):
            # Add to PATH so pdf2image can find it
            if poppler_path not in os.environ.get('PATH', ''):
                os.environ['PATH'] = poppler_path + os.pathsep + os.environ.get('PATH', '')
            print(f"✓ Poppler found at: {poppler_path}")
            return True
    
    print("⚠ Poppler not found in expected locations")
    print("  Expected paths:")
    for path in POPPLER_PATHS:
        print(f"    - {path}")
    return False


def detect_table_cells(image_path):
    """
    Detect table structure in an image using edge detection
    Returns bounding boxes of detected cells
    """
    img = cv2.imread(image_path)
    if img is None:
        return []
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Apply thresholding
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
    
    # Detect edges
    edges = cv2.Canny(thresh, 50, 150)
    
    # Dilate to connect nearby edges
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    dilated = cv2.dilate(edges, kernel, iterations=2)
    
    # Find contours
    contours, _ = cv2.findContours(dilated, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    
    cells = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        # Filter cells by size (avoid noise)
        if w > 20 and h > 15:
            cells.append((x, y, w, h))
    
    # Sort cells: top to bottom, then left to right
    cells = sorted(cells, key=lambda c: (c[1], c[0]))
    
    return cells


def extract_text_from_region(image, x, y, w, h):
    """Extract text from a specific region of an image - optimized"""
    roi = image[max(0, y):min(image.shape[0], y+h), 
                max(0, x):min(image.shape[1], x+w)]
    
    if roi.size == 0 or roi.shape[0] < 5 or roi.shape[1] < 5:
        return ""
    
    try:
        text = pytesseract.image_to_string(roi, lang="kan", config='--psm 6')
        return text.strip()
    except:
        return ""


def extract_table_from_page_optimized(image_cv2, image_pil):
    """
    Optimized table extraction using full-page OCR with layout analysis
    IMPROVED: Intelligent column detection, dynamic row height, separator handling
    Instead of calling OCR for each cell, we do one pass and group results by grid
    """
    height, width = image_cv2.shape[:2]
    
    print(f"  [OCR] Performing full-page OCR with improved grid detection...")
    
    try:
        # Use pytesseract.image_to_data for word-level coordinates
        data = pytesseract.image_to_data(image_pil, lang="kan", output_type=pytesseract.Output.DICT)
    except Exception as e:
        print(f"  ✗ Full-page OCR failed: {e}. Using grid fallback...")
        return extract_table_manual(image_cv2)
    
    # Group words by approximate row and column positions with improved logic
    print(f"  [Post-processing] Organizing OCR results into intelligent grid...")
    
    if not data or not data['text']:
        return extract_table_manual(image_cv2)
    
    # Find actual table boundaries from detected text
    text_positions = []
    for i in range(len(data['text'])):
        if data['text'][i].strip() and data['conf'][i] > 30:
            text_positions.append({
                'x': data['left'][i],
                'y': data['top'][i],
                'w': data['width'][i],
                'h': data['height'][i],
                'text': data['text'][i],
                'conf': data['conf'][i]
            })
    
    if not text_positions:
        return extract_table_manual(image_cv2)
    
    # Calculate intelligent column boundaries from X-coordinates
    x_coords = sorted(set([t['x'] for t in text_positions]))
    
    if len(x_coords) < 2:
        num_cols = 8
        col_positions = None
    else:
        # Group x-coordinates by proximity to find actual column positions
        col_positions = []
        current_group = [x_coords[0]]
        
        for x in x_coords[1:]:
            if x - current_group[-1] < 25:  # Words within 25px are same column
                current_group.append(x)
            else:
                col_positions.append(sum(current_group) // len(current_group))
                current_group = [x]
        col_positions.append(sum(current_group) // len(current_group))
        
        # Limit to reasonable number of columns (6-12)
        if len(col_positions) > 12:
            col_positions = col_positions[:12]
        elif len(col_positions) < 6:
            # If too few columns detected, use fixed grid
            col_positions = None
        
        num_cols = len(col_positions) if col_positions else 8
    
    # Calculate intelligent row height from detected text
    y_coords = sorted(set([t['y'] for t in text_positions]))
    
    if len(y_coords) < 2:
        row_height = 40
    else:
        # Find average gap between y-coordinates (skip very small gaps)
        y_gaps = [y_coords[i+1] - y_coords[i] for i in range(len(y_coords)-1) if y_coords[i+1] - y_coords[i] > 8]
        if y_gaps:
            row_height = max(20, min(int(sum(y_gaps) / len(y_gaps)), 50))
        else:
            row_height = 40
    
    print(f"  [Grid] Detected: {num_cols} columns, row_height={row_height}px")
    
    # Group words by grid cell
    grid = {}
    
    for pos in text_positions:
        text = pos['text'].strip()
        if not text:
            continue
        
        x = pos['x']
        y = pos['y']
        
        # Determine grid cell
        if col_positions:
            # Use intelligent column detection
            col = 0
            for i, col_pos in enumerate(col_positions):
                if x < col_pos:
                    break
                col = i
            col = min(col, num_cols - 1)
        else:
            # Use fixed grid
            col_width = width // num_cols
            col = min(x // col_width, num_cols - 1)
        
        row = y // row_height
        
        key = (row, col)
        if key not in grid:
            grid[key] = []
        grid[key].append(text)
    
    # Convert grid to table format
    if not grid:
        return extract_table_manual(image_cv2)
    
    max_row = max(key[0] for key in grid) + 1
    
    table_data = []
    for row_idx in range(max_row):
        row_data = []
        for col_idx in range(num_cols):
            key = (row_idx, col_idx)
            if key in grid:
                # Join words in cell with spaces (no separators)
                cell_text = " ".join(grid[key])
                # Safety: remove any lingering separators
                cell_text = cell_text.replace("|||CELLSEP|||", "").replace("|SEP|", "").replace("|||", "")
            else:
                cell_text = ""
            row_data.append(cell_text)
        
        # Only add non-empty rows
        if any(row_data):
            table_data.append(row_data)
    
    return table_data


def extract_table_from_page(image_cv2, image_pil):
    """
    Extract table data from a page image
    Returns list of rows, where each row is a list of cell values
    """
    # Convert to grayscale
    gray = cv2.cvtColor(image_cv2, cv2.COLOR_BGR2GRAY)
    
    # Apply thresholding
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
    
    # Find horizontal and vertical lines
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
    
    horizontal = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, horizontal_kernel)
    vertical = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, vertical_kernel)
    
    # Find contours of table structure
    contours_h, _ = cv2.findContours(horizontal, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours_v, _ = cv2.findContours(vertical, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Extract row and column boundaries
    rows = []
    cols = []
    
    for contour in contours_h:
        x, y, w, h = cv2.boundingRect(contour)
        if w > 100:  # Filter small noise
            rows.append(y)
    
    for contour in contours_v:
        x, y, w, h = cv2.boundingRect(contour)
        if h > 100:  # Filter small noise
            cols.append(x)
    
    rows = sorted(set(rows))
    cols = sorted(set(cols))
    
    # If lines not detected well, use manual cell detection
    if len(rows) < 2 or len(cols) < 2:
        return extract_table_manual(image_cv2)
    
    # Extract cells
    table_data = []
    for i in range(len(rows) - 1):
        row_data = []
        for j in range(len(cols) - 1):
            x1, y1 = cols[j], rows[i]
            x2, y2 = cols[j + 1], rows[i + 1]
            
            cell_text = extract_text_from_region(image_cv2, x1, y1, x2 - x1, y2 - y1)
            row_data.append(cell_text)
        
        table_data.append(row_data)
    
    return table_data


def extract_table_manual(image_cv2):
    """
    Manual table extraction using OCR with spatial awareness
    Divides the page into a grid and extracts text from each cell
    """
    height, width = image_cv2.shape[:2]
    
    # Define grid: typical voter list has 8-10 columns
    num_cols = 8
    col_width = width // num_cols
    
    # Estimate row height
    row_height = 40
    num_rows = height // row_height
    
    table_data = []
    
    for row in range(num_rows):
        row_data = []
        y_start = row * row_height
        y_end = min((row + 1) * row_height, height)
        
        for col in range(num_cols):
            x_start = col * col_width
            x_end = min((col + 1) * col_width, width)
            
            cell_text = extract_text_from_region(image_cv2, x_start, y_start, 
                                                 x_end - x_start, y_end - y_start)
            row_data.append(cell_text)
        
        # Only add row if it has some text
        if any(row_data):
            table_data.append(row_data)
    
    return table_data


def create_pdf_url(district, ac, part_number):
    """Construct the PDF URL from district, AC, and part number"""
    ac_str = str(ac).zfill(3)  # Ensure AC is 3 digits (88 -> 088)
    part_padded = str(part_number).zfill(3)  # Ensure part is 3 digits
    pdf_number = f"A{ac_str}0{part_padded}"
    
    # URL encode the district
    district_encoded = quote(district)
    # AC format: "AC 88" (with space)
    ac_encoded = quote(f"AC {ac}")
    
    url = f"https://ceo.karnataka.gov.in/uploads/{district_encoded}/{ac_encoded}/{pdf_number}.pdf"
    print(f"Generated URL: {url}")
    return url


def download_pdf(url, output_path):
    """Download PDF file from URL"""
    print(f"Downloading: {url}")
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'wb') as f:
            f.write(response.content)
        
        print(f"✓ PDF downloaded successfully: {output_path}")
        return True
    except Exception as e:
        print(f"✗ Error downloading PDF: {str(e)}")
        return False


def translate_text_batch(text_list, max_retries=2):
    """
    Translate texts cell-by-cell (more reliable than batch with separators)
    googletrans API doesn't reliably preserve separators, so translate individually
    """
    if not text_list or not any(text_list):
        return text_list
    
    translator = Translator()
    translated_list = []
    
    for cell_text in text_list:
        if not cell_text or not cell_text.strip():
            translated_list.append("")
            continue
        
        for attempt in range(max_retries):
            try:
                result = translator.translate(cell_text, dest='en', src='kn')
                if result and hasattr(result, 'text'):
                    trans_text = result.text.strip()
                    # Clean up any artifacts
                    trans_text = trans_text.replace("|||CELLSEP|||", "").replace("|SEP|", "").replace("|||", "")
                    translated_list.append(trans_text)
                    break
                else:
                    translated_list.append(cell_text)
                    break
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(0.3)
                else:
                    # Return original if translation fails
                    translated_list.append(cell_text)
    
    return translated_list


def translate_table_data(table_data):
    """
    Translate table data from Kannada to English
    IMPROVED: Batch translation per-row while preserving column structure
    """
    if not table_data:
        return []
    
    print(f"\nTranslating {len(table_data)} rows to English (batch translation per row)...")
    
    translated_table = []
    
    for row_idx, row in enumerate(table_data):
        if row_idx > 0 and row_idx % 10 == 0:
            print(f"  Translated {row_idx}/{len(table_data)} rows...")
            time.sleep(0.2)  # Small delay to avoid rate limiting
        
        try:
            # Translate entire row as a batch while keeping structure
            translated_row = translate_text_batch(row, max_retries=2)
            
            # Final safety check: remove any separators that might have leaked in
            cleaned_row = []
            for cell in translated_row:
                cleaned_cell = str(cell).replace("|||CELLSEP|||", "").replace("|SEP|", "").replace("|||", "").strip()
                cleaned_row.append(cleaned_cell)
            
            translated_table.append(cleaned_row)
        except Exception as e:
            print(f"    ⚠ Error translating row {row_idx}: {str(e)}, keeping original")
            translated_table.append(row)
    
    print(f"✓ Translation complete!")
    return translated_table


def extract_kannada_text_with_ocr(pdf_path):
    """Extract Kannada text from PDF using OCR"""
    print("Converting PDF pages to images...")
    
    try:
        pages = convert_from_path(pdf_path, dpi=300)
    except Exception as e:
        print(f"✗ Error converting PDF to images: {str(e)}")
        print("  Poppler not found. Install with:")
        print("  - Windows: Download from https://github.com/oschwartz10612/poppler-windows/releases/")
        print("  - Linux: sudo apt install poppler-utils")
        print("  - macOS: brew install poppler")
        return []
    
    all_rows = []
    
    for page_no, page in enumerate(pages, start=1):
        print(f"Processing Page {page_no} with OCR...")
        
        try:
            text = pytesseract.image_to_string(page, lang="kan")
        except pytesseract.TesseractNotFoundError:
            print("✗ Tesseract not found. Please install it first.")
            print("  Download from: https://github.com/UB-Mannheim/tesseract/wiki")
            return []
        except Exception as e:
            print(f"✗ Error during OCR: {str(e)}")
            continue
        
        lines = text.split("\n")
        
        for line in lines:
            line = line.strip()
            
            if len(line) < 3:
                continue
            
            all_rows.append({
                "page": page_no,
                "kannada_text": line
            })
    
    return all_rows


def extract_structured_table_data(pdf_path):
    """
    Extract structured table data from PDF starting at page 2
    Returns rows and columns properly formatted
    """
    print(f"\nConverting PDF pages to images (starting from page {START_PAGE + 1}, processing {NUM_PAGES_TO_PROCESS} pages)...")
    
    try:
        all_pages = convert_from_path(pdf_path, dpi=300)
    except Exception as e:
        print(f"✗ Error converting PDF to images: {str(e)}")
        return []
    
    # Extract only specified pages
    pages = all_pages[START_PAGE:START_PAGE + NUM_PAGES_TO_PROCESS]
    
    all_table_data = []
    
    for idx, page in enumerate(pages):
        actual_page_no = START_PAGE + idx + 1
        print(f"\nExtracting table from Page {actual_page_no}...")
        
        # Convert PIL Image to OpenCV format
        page_cv = cv2.cvtColor(np.array(page), cv2.COLOR_RGB2BGR)
        
        # Extract table using optimized method
        table_data = extract_table_from_page_optimized(page_cv, page)
        
        if table_data:
            print(f"✓ Extracted {len(table_data)} rows with columns from page {actual_page_no}")
            all_table_data.extend(table_data)
        else:
            print(f"✗ No table data extracted from page {actual_page_no}")
    
    return all_table_data


def extract_voter_data_structured(pdf_path):
    """Extract structured voter data with specific columns"""
    print("Converting PDF pages to images for structured extraction...")
    
    try:
        pages = convert_from_path(pdf_path, dpi=300)
    except Exception as e:
        print(f"✗ Error converting PDF to images: {str(e)}")
        return []
    
    voters = []
    
    for page_no, page in enumerate(pages, start=1):
        print(f"Extracting voter data from Page {page_no}...")
        
        try:
            text = pytesseract.image_to_string(page, lang="kan")
        except Exception as e:
            print(f"✗ Error during OCR on page {page_no}: {str(e)}")
            continue
        
        lines = text.split("\n")
        
        for line in lines:
            line = line.strip()
            if len(line) < 3:
                continue
            
            # Split by whitespace or common separators
            parts = re.split(r'\s{2,}|\t|,', line)
            
            voter = {
                "page": page_no,
                "raw_kannada": line,
                "english_translation": ""
            }
            
            voters.append(voter)
    
    return voters


def translate_rows(rows):
    """Translate all rows from Kannada to English"""
    total = len(rows)
    
    for idx, row in enumerate(rows):
        if idx % 20 == 0:
            print(f"Translated {idx}/{total} rows")
        
        row["english_text"] = translate_text(row["kannada_text"])
    
    return rows


def save_excel(rows, output_file):
    """
    Save extracted and translated data to Excel
    IMPROVED: Extra sanitization to ensure no separators in output
    """
    
    if not rows:
        print("✗ No data to save")
        return
    
    # Sanitize all rows: remove separators and clean text
    sanitized_rows = []
    for row in rows:
        cleaned_row = []
        for cell in row:
            if not cell:
                cleaned_row.append("")
            else:
                # Remove all possible separators and clean up
                cleaned = str(cell).replace("|||CELLSEP|||", "").replace("|SEP|", "").replace("|||", "").strip()
                cleaned_row.append(cleaned)
        sanitized_rows.append(cleaned_row)
    
    # Create DataFrame from table data
    column_names = [
        "क्र.सं. (Serial)",
        "मं/बॅ.नं. (Name/ID)",
        "मतरर ष (Voter Name)",
        "सं.बं (Relationship)",
        "सं.बंय ष (Related Name)",
        "ग/ं (Gender)",
        "वय (Age)",
        "मत्र.ैर.सं (Electoral ID)"
    ]
    
    # Pad rows to match column count
    max_cols = max(len(row) for row in sanitized_rows) if sanitized_rows else 8
    padded_rows = []
    
    for row in sanitized_rows:
        while len(row) < max_cols:
            row.append("")
        padded_rows.append(row)
    
    # Adjust column names if needed
    if max_cols != len(column_names):
        column_names = [f"Column {i+1}" for i in range(max_cols)]
    
    df = pd.DataFrame(padded_rows, columns=column_names[:max_cols])
    
    # Save to Excel
    try:
        with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Voter List")
            
            ws = writer.sheets["Voter List"]
            
            # Adjust column widths
            for col_idx, col_name in enumerate(column_names[:max_cols], 1):
                ws.column_dimensions[chr(64 + col_idx)].width = 20
        
        print(f"✓ Data saved to XLSX: {output_file}")
        print(f"  Rows: {len(padded_rows)}")
        print(f"  Columns: {max_cols}")
        
    except Exception as e:
        print(f"✗ Error saving Excel: {str(e)}")


def main():
    """Main function to orchestrate download, OCR, translation, and Excel export"""
    print("=" * 70)
    print("KANNADA VOTER LIST → ENGLISH TABLE EXTRACTION & TRANSLATION")
    print("=" * 70)
    print(f"District: {DISTRICT}")
    print(f"AC: {AC_NUMBER} (Yelahanka)")
    print(f"Part Number: {PART_NUMBER}")
    print(f"Processing: Pages {START_PAGE + 1} to {START_PAGE + NUM_PAGES_TO_PROCESS}")
    print(f"Output Directory: {OUTPUT_DIR}")
    print("=" * 70)
    
    # Setup Tesseract
    if not setup_tesseract():
        print("\n⚠ WARNING: Tesseract OCR not found!")
        print("The script will likely fail. Please install Tesseract first.")
        response = input("Continue anyway? (y/n): ").lower()
        if response != 'y':
            return
    
    # Setup Poppler
    setup_poppler()
    
    # Create output directories
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(TEMP_PDF_DIR, exist_ok=True)
    
    # Step 1: Download PDF
    print("\n" + "=" * 70)
    print("STEP 1: Downloading PDF")
    print("=" * 70)
    pdf_url = create_pdf_url(DISTRICT, AC_NUMBER, PART_NUMBER)
    pdf_filename = f"A088{PART_NUMBER:03d}.pdf"
    pdf_path = os.path.join(TEMP_PDF_DIR, pdf_filename)
    
    if not download_pdf(pdf_url, pdf_path):
        print("Failed to download PDF. Exiting.")
        return
    
    # Step 2: Extract structured table data
    print("\n" + "=" * 70)
    print("STEP 2: Extracting Structured Table Data")
    print("=" * 70)
    table_data = extract_structured_table_data(pdf_path)
    
    if not table_data:
        print("Failed to extract table data from PDF. Exiting.")
        return
    
    print(f"\n✓ Successfully extracted {len(table_data)} rows")
    
    # Step 3: Display sample data
    print("\n" + "=" * 70)
    print("SAMPLE DATA - KANNADA (First 5 rows):")
    print("=" * 70)
    for idx, row in enumerate(table_data[:5], 1):
        print(f"\nRow {idx}:")
        for col_idx, cell in enumerate(row, 1):
            print(f"  Col {col_idx}: {cell[:50]}..." if len(cell) > 50 else f"  Col {col_idx}: {cell}")
    
    # Step 4: Translate to English
    print("\n" + "=" * 70)
    print("STEP 3: Translating Kannada to English")
    print("=" * 70)
    translated_table = translate_table_data(table_data)
    
    if not translated_table:
        print("⚠ Translation failed. Saving untranslated Kannada data instead...")
        translated_table = table_data
    
    # Step 5: Display translated sample data
    print("\n" + "=" * 70)
    print("SAMPLE DATA - ENGLISH (First 5 rows):")
    print("=" * 70)
    for idx, row in enumerate(translated_table[:5], 1):
        print(f"\nRow {idx}:")
        for col_idx, cell in enumerate(row, 1):
            print(f"  Col {col_idx}: {cell[:50]}..." if len(cell) > 50 else f"  Col {col_idx}: {cell}")
    
    # Step 6: Save to Excel
    print("\n" + "=" * 70)
    print("STEP 4: Saving to Excel")
    print("=" * 70)
    xlsx_filename = f"voter_list_part_{PART_NUMBER:03d}_english_translated.xlsx"
    xlsx_path = os.path.join(OUTPUT_DIR, xlsx_filename)
    save_excel(translated_table, xlsx_path)
    
    print("\n" + "=" * 70)
    print("✓ Process completed successfully!")
    print(f"Output file: {xlsx_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
