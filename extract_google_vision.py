"""
Google Vision OCR Extraction for Kannada Voter Lists
======================================================
Uses Google Cloud Vision API for superior Kannada text recognition,
layout detection, and coordinate-based row reconstruction.

Features:
- Best-in-class Kannada recognition
- Accurate layout detection with text blocks
- Coordinate-based row and column detection
- Returns structured table data
"""

import os
import sys
import json
import time
from typing import List, Dict, Tuple
from pdf2image import convert_from_path
from google.cloud import vision
import pandas as pd
from googletrans import Translator
# Note: googletrans==4.0.2 is installed (4.0.0 doesn't exist as package version)

# Configuration
DISTRICT = "BANGALORE URBAN"
AC_NUMBER = "88"  # Yelahanka
PART_NUMBER = 278

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
TEMP_PDF_DIR = os.path.join(OUTPUT_DIR, "temp_pdfs")

# Page extraction settings
START_PAGE = 1  # Start from page 2 (0-indexed)
NUM_PAGES_TO_PROCESS = 2

# Google Vision settings
VISION_CONFIDENCE_THRESHOLD = 0.6  # Minimum confidence for text blocks

# Row/Column detection settings
ROW_PROXIMITY_THRESHOLD = 15  # Y-coordinates within this are same row
COL_PROXIMITY_THRESHOLD = 20  # X-coordinates within this are same column
MIN_BLOCK_HEIGHT = 20
MIN_BLOCK_WIDTH = 30


class GoogleVisionOCR:
    """Google Cloud Vision OCR handler for Kannada text extraction"""
    
    def __init__(self, project_id=None):
        """Initialize Google Vision client"""
        try:
            self.client = vision.ImageAnnotatorClient()
            print("✓ Google Vision client initialized successfully")
        except Exception as e:
            print(f"✗ Error initializing Google Vision: {str(e)}")
            print("  Make sure to set GOOGLE_APPLICATION_CREDENTIALS environment variable")
            print("  Export: $env:GOOGLE_APPLICATION_CREDENTIALS='path/to/credentials.json' (PowerShell)")
            sys.exit(1)
    
    def extract_text_from_image(self, image_path: str) -> Dict:
        """
        Extract text and layout information from image using Google Vision
        Returns dictionary with text blocks and their coordinates
        """
        try:
            with open(image_path, 'rb') as image_file:
                content = image_file.read()
        except Exception as e:
            print(f"✗ Error reading image {image_path}: {str(e)}")
            return {}
        
        image = vision.Image(content=content)
        
        try:
            # Use document text detection for better layout preservation
            response = self.client.document_text_detection(image=image)
            return self._parse_vision_response(response)
        except Exception as e:
            print(f"✗ Error during Vision API call: {str(e)}")
            return {}
    
    def _parse_vision_response(self, response) -> Dict:
        """
        Parse Google Vision response and extract structured text with coordinates
        """
        if not response.text_annotations:
            return {'text_blocks': [], 'full_text': ''}
        
        text_blocks = []
        
        # Skip first annotation which is full page text
        for annotation in response.text_annotations[1:]:
            text = annotation.description.strip()
            
            if not text:
                continue
            
            # Extract bounding box coordinates
            vertices = annotation.bounding_poly.vertices
            if vertices:
                x_coords = [v.x for v in vertices]
                y_coords = [v.y for v in vertices]
                
                block_info = {
                    'text': text,
                    'x_min': min(x_coords),
                    'y_min': min(y_coords),
                    'x_max': max(x_coords),
                    'y_max': max(y_coords),
                    'width': max(x_coords) - min(x_coords),
                    'height': max(y_coords) - min(y_coords)
                }
                
                # Filter out very small blocks (noise)
                if block_info['width'] >= MIN_BLOCK_WIDTH and block_info['height'] >= MIN_BLOCK_HEIGHT:
                    text_blocks.append(block_info)
        
        full_text = response.text_annotations[0].description if response.text_annotations else ""
        
        return {
            'text_blocks': text_blocks,
            'full_text': full_text
        }
    
    def reconstruct_table_from_blocks(self, text_blocks: List[Dict]) -> List[List[str]]:
        """
        Reconstruct table structure from text blocks using coordinate-based clustering
        Groups text blocks into rows and columns based on spatial proximity
        """
        if not text_blocks:
            return []
        
        # Sort blocks by Y-coordinate (top to bottom)
        sorted_blocks = sorted(text_blocks, key=lambda b: b['y_min'])
        
        # Group blocks into rows based on Y-proximity
        rows = []
        current_row = [sorted_blocks[0]]
        
        for block in sorted_blocks[1:]:
            # Check if block is in same row (Y within threshold)
            if abs(block['y_min'] - current_row[0]['y_min']) <= ROW_PROXIMITY_THRESHOLD:
                current_row.append(block)
            else:
                # New row detected
                rows.append(current_row)
                current_row = [block]
        
        if current_row:
            rows.append(current_row)
        
        # For each row, sort blocks by X-coordinate and group into columns
        table_data = []
        
        for row_blocks in rows:
            # Sort by X-coordinate (left to right)
            sorted_row = sorted(row_blocks, key=lambda b: b['x_min'])
            
            # Group into columns based on X-proximity
            row_data = []
            current_col = [sorted_row[0]]
            
            for block in sorted_row[1:]:
                if abs(block['x_min'] - current_col[0]['x_min']) <= COL_PROXIMITY_THRESHOLD:
                    # Same column, merge text
                    current_col.append(block)
                else:
                    # New column detected
                    col_text = " ".join([b['text'] for b in current_col])
                    row_data.append(col_text)
                    current_col = [block]
            
            # Add last column
            if current_col:
                col_text = " ".join([b['text'] for b in current_col])
                row_data.append(col_text)
            
            # Only add non-empty rows
            if any(row_data):
                table_data.append(row_data)
        
        return table_data
    
    def extract_table_from_pdf_page(self, pdf_path: str, page_num: int) -> List[List[str]]:
        """
        Extract table from specific PDF page using Google Vision
        """
        try:
            print(f"Converting PDF page {page_num} to image...")
            pages = convert_from_path(pdf_path, first_page=page_num, last_page=page_num, dpi=300)
            
            if not pages:
                print(f"✗ Failed to convert page {page_num}")
                return []
            
            page_image = pages[0]
            
            # Save temporary image
            temp_img_path = os.path.join(TEMP_PDF_DIR, f"temp_page_{page_num}.png")
            os.makedirs(TEMP_PDF_DIR, exist_ok=True)
            page_image.save(temp_img_path)
            
            print(f"  Sending to Google Vision API for OCR...")
            vision_result = self.extract_text_from_image(temp_img_path)
            
            if not vision_result.get('text_blocks'):
                print(f"✗ No text blocks detected on page {page_num}")
                return []
            
            print(f"  Detected {len(vision_result['text_blocks'])} text blocks")
            print(f"  Reconstructing table structure from coordinates...")
            
            table_data = self.reconstruct_table_from_blocks(vision_result['text_blocks'])
            
            # Cleanup temp image
            try:
                os.remove(temp_img_path)
            except:
                pass
            
            return table_data
        
        except Exception as e:
            print(f"✗ Error extracting table from page {page_num}: {str(e)}")
            return []


def translate_table_data_batch(table_data: List[List[str]]) -> List[List[str]]:
    """
    Translate entire table from Kannada to English using batch translation
    """
    if not table_data:
        return []
    
    translator = Translator()
    translated_table = []
    
    total_rows = len(table_data)
    
    for row_idx, row in enumerate(table_data):
        if row_idx % 10 == 0:
            print(f"  Translated {row_idx}/{total_rows} rows...")
        
        translated_row = []
        
        for cell_text in row:
            if not cell_text or not cell_text.strip():
                translated_row.append("")
                continue
            
            try:
                result = translator.translate(cell_text, dest='en', src='kn')
                if result and hasattr(result, 'text'):
                    trans_text = result.text.strip()
                    translated_row.append(trans_text)
                else:
                    translated_row.append(cell_text)
            except Exception as e:
                print(f"    ⚠ Translation error for '{cell_text[:30]}...': {str(e)}")
                translated_row.append(cell_text)
            
            time.sleep(0.05)  # Small delay to avoid rate limiting
        
        translated_table.append(translated_row)
    
    return translated_table


def save_to_excel(table_data: List[List[str]], output_file: str):
    """Save table data to Excel file"""
    
    if not table_data:
        print("✗ No data to save")
        return
    
    # Determine column count
    max_cols = max(len(row) for row in table_data) if table_data else 8
    
    # Pad rows to match max columns
    padded_rows = []
    for row in table_data:
        padded_row = row + [""] * (max_cols - len(row))
        padded_rows.append(padded_row)
    
    # Create column names
    column_names = [f"Column {i+1}" for i in range(max_cols)]
    
    # Create DataFrame
    df = pd.DataFrame(padded_rows, columns=column_names)
    
    # Save to Excel
    try:
        os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)
        
        with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Voter List")
            
            ws = writer.sheets["Voter List"]
            
            # Adjust column widths
            for col_idx in range(1, max_cols + 1):
                ws.column_dimensions[chr(64 + col_idx)].width = 25
        
        print(f"✓ Data saved to XLSX: {output_file}")
        print(f"  Rows: {len(padded_rows)}")
        print(f"  Columns: {max_cols}")
        
    except Exception as e:
        print(f"✗ Error saving Excel: {str(e)}")


def main():
    """Main function using Google Vision OCR"""
    print("=" * 80)
    print("KANNADA VOTER LIST EXTRACTION - GOOGLE VISION OCR")
    print("=" * 80)
    print(f"District: {DISTRICT}")
    print(f"AC: {AC_NUMBER}")
    print(f"Part Number: {PART_NUMBER}")
    print(f"Processing: Pages {START_PAGE + 1} to {START_PAGE + NUM_PAGES_TO_PROCESS}")
    print(f"Output Directory: {OUTPUT_DIR}")
    print("=" * 80)
    
    # Create output directories
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(TEMP_PDF_DIR, exist_ok=True)
    
    # Initialize Google Vision OCR
    print("\nInitializing Google Vision OCR...")
    ocr = GoogleVisionOCR()
    
    # For demo: use existing PDF if available
    pdf_path = os.path.join(TEMP_PDF_DIR, f"A088{PART_NUMBER:03d}.pdf")
    
    if not os.path.exists(pdf_path):
        print(f"\n⚠ PDF not found: {pdf_path}")
        print("  Please download the PDF first using fetch_data.py")
        return
    
    print(f"\nPDF found: {pdf_path}")
    
    # Extract table from pages
    print("\n" + "=" * 80)
    print("EXTRACTING TABLE DATA FROM PDF USING GOOGLE VISION")
    print("=" * 80)
    
    all_table_data = []
    
    for page_offset in range(NUM_PAGES_TO_PROCESS):
        page_num = START_PAGE + 1 + page_offset
        print(f"\nProcessing Page {page_num}...")
        
        table_data = ocr.extract_table_from_pdf_page(pdf_path, page_num)
        
        if table_data:
            print(f"✓ Extracted {len(table_data)} rows from page {page_num}")
            all_table_data.extend(table_data)
        else:
            print(f"✗ Failed to extract table from page {page_num}")
    
    if not all_table_data:
        print("\n✗ No table data extracted. Exiting.")
        return
    
    print(f"\n✓ Total rows extracted: {len(all_table_data)}")
    
    # Display sample
    print("\n" + "=" * 80)
    print("SAMPLE DATA - KANNADA (First 3 rows)")
    print("=" * 80)
    for idx, row in enumerate(all_table_data[:3], 1):
        print(f"\nRow {idx}:")
        for col_idx, cell in enumerate(row, 1):
            preview = cell[:60] + "..." if len(cell) > 60 else cell
            print(f"  Col {col_idx}: {preview}")
    
    # Translate to English
    print("\n" + "=" * 80)
    print("TRANSLATING TO ENGLISH")
    print("=" * 80)
    translated_table = translate_table_data_batch(all_table_data)
    
    # Display translated sample
    print("\n" + "=" * 80)
    print("SAMPLE DATA - ENGLISH (First 3 rows)")
    print("=" * 80)
    for idx, row in enumerate(translated_table[:3], 1):
        print(f"\nRow {idx}:")
        for col_idx, cell in enumerate(row, 1):
            preview = cell[:60] + "..." if len(cell) > 60 else cell
            print(f"  Col {col_idx}: {preview}")
    
    # Save to Excel
    print("\n" + "=" * 80)
    print("SAVING TO EXCEL")
    print("=" * 80)
    xlsx_filename = f"voter_list_part_{PART_NUMBER:03d}_google_vision.xlsx"
    xlsx_path = os.path.join(OUTPUT_DIR, xlsx_filename)
    save_to_excel(translated_table, xlsx_path)
    
    print("\n" + "=" * 80)
    print("✓ PROCESS COMPLETED SUCCESSFULLY!")
    print(f"Output file: {xlsx_path}")
    print("=" * 80)


if __name__ == "__main__":
    main()
