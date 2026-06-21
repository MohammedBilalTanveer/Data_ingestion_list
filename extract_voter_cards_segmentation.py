"""
Voter Card Segmentation and Extraction
========================================
Uses OpenCV image segmentation to detect individual voter cards/boxes,
crop them, and extract structured voter information using OCR and regex.

This approach is more reliable than table detection because it:
1. Detects each voter card as a separate unit
2. Crops cards individually for cleaner OCR
3. Uses regex patterns to extract structured fields
4. Follows the predictable Karnataka electoral roll card format

Expected card format fields:
- Serial Number (क्र.सं.)
- Voter Name (मतदाता का नाम)
- Father's/Husband's Name (पिता/पति का नाम)
- House Number (मकान संख्या)
- Age (आयु)
- Gender (लिंग)
- EPIC Number (मतदाता पहचान संख्या)
"""

import os
import sys
import re
import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional
from pdf2image import convert_from_path
import pytesseract
import pandas as pd
from googletrans import Translator
import time
# Note: googletrans==4.0.2 is installed (4.0.0 doesn't exist as package version)

# Configuration
DISTRICT = "BANGALORE URBAN"
AC_NUMBER = "88"
PART_NUMBER = 278

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
TEMP_PDF_DIR = os.path.join(OUTPUT_DIR, "temp_pdfs")
CARDS_DIR = os.path.join(OUTPUT_DIR, "voter_cards")

START_PAGE = 1
NUM_PAGES_TO_PROCESS = 2

# Card detection settings
MIN_CARD_WIDTH = 250  # Minimum width for voter card
MIN_CARD_HEIGHT = 150  # Minimum height for voter card
MAX_CARD_WIDTH = 1200  # Maximum width for voter card
MAX_CARD_HEIGHT = 600  # Maximum height for voter card

# Image processing thresholds
CANNY_THRESHOLD1 = 50
CANNY_THRESHOLD2 = 150
MORPHOLOGY_KERNEL_SIZE = (3, 3)

# Tesseract paths for Windows
TESSERACT_PATHS = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    r"C:\Users\moham\AppData\Local\Tesseract-OCR\tesseract.exe",
]


class VoterCardSegmentation:
    """Detect and segment voter cards from electoral roll pages"""
    
    def __init__(self):
        """Initialize segmentation engine"""
        self.setup_tesseract()
        self.translator = Translator()
        print("✓ Voter Card Segmentation initialized")
    
    def setup_tesseract(self):
        """Setup Tesseract path for Windows"""
        for path in TESSERACT_PATHS:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                print(f"✓ Tesseract found at: {path}")
                return True
        print("⚠ Tesseract not found. Please install from: https://github.com/UB-Mannheim/tesseract/wiki")
        return False
    
    def preprocess_image(self, image_cv: np.ndarray) -> np.ndarray:
        """
        Preprocess image for card detection
        - Convert to grayscale
        - Apply CLAHE for contrast enhancement
        - Apply Gaussian blur for noise reduction
        """
        # Convert to grayscale if needed
        if len(image_cv.shape) == 3:
            gray = cv2.cvtColor(image_cv, cv2.COLOR_BGR2GRAY)
        else:
            gray = image_cv
        
        # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        
        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(enhanced, (3, 3), 0)
        
        return blurred
    
    def detect_card_boundaries(self, image_cv: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        Detect voter card boundaries using edge detection and contours
        Returns list of (x, y, width, height) for each detected card
        """
        # Preprocess image
        preprocessed = self.preprocess_image(image_cv)
        
        # Apply thresholding
        _, binary = cv2.threshold(preprocessed, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Apply morphological operations to connect card boundaries
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=2)
        
        # Detect edges
        edges = cv2.Canny(closed, CANNY_THRESHOLD1, CANNY_THRESHOLD2)
        
        # Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter contours by size to get card candidates
        cards = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            
            # Check if contour matches card dimensions
            if (MIN_CARD_WIDTH <= w <= MAX_CARD_WIDTH and 
                MIN_CARD_HEIGHT <= h <= MAX_CARD_HEIGHT):
                cards.append((x, y, w, h))
        
        # Sort cards from top to bottom, left to right
        cards = sorted(cards, key=lambda c: (c[1], c[0]))
        
        return cards
    
    def merge_overlapping_cards(self, cards: List[Tuple[int, int, int, int]], 
                               overlap_threshold: float = 0.3) -> List[Tuple[int, int, int, int]]:
        """
        Merge overlapping or near-overlapping card detections
        """
        if len(cards) <= 1:
            return cards
        
        merged = []
        used = set()
        
        for i, card1 in enumerate(cards):
            if i in used:
                continue
            
            x1, y1, w1, h1 = card1
            merged_card = list(card1)
            count = 1
            
            # Check for overlapping cards
            for j, card2 in enumerate(cards[i+1:], start=i+1):
                if j in used:
                    continue
                
                x2, y2, w2, h2 = card2
                
                # Calculate overlap
                overlap_area = max(0, min(x1 + w1, x2 + w2) - max(x1, x2)) * \
                              max(0, min(y1 + h1, y2 + h2) - max(y1, y2))
                
                card1_area = w1 * h1
                overlap_ratio = overlap_area / card1_area if card1_area > 0 else 0
                
                # If overlap, merge
                if overlap_ratio > overlap_threshold:
                    merged_card[0] = min(merged_card[0], x2)
                    merged_card[1] = min(merged_card[1], y2)
                    merged_card[2] = max(merged_card[0] + merged_card[2], x2 + w2) - merged_card[0]
                    merged_card[3] = max(merged_card[1] + merged_card[3], y2 + h2) - merged_card[1]
                    used.add(j)
                    count += 1
            
            merged.append(tuple(merged_card[:4]))
        
        return merged
    
    def extract_voter_data_from_card(self, card_image: np.ndarray) -> Dict[str, str]:
        """
        Extract structured voter data from a single card image
        Uses OCR and regex pattern matching
        """
        # Resize if too small for better OCR
        height, width = card_image.shape[:2]
        if width < 300 or height < 120:
            scale = max(300 / width, 120 / height)
            card_image = cv2.resize(card_image, (int(width * scale), int(height * scale)))
        
        # Perform OCR
        try:
            # Try Kannada first
            text_kannada = pytesseract.image_to_string(card_image, lang="kan")
            
            # Also try with English for mixed content
            text_mixed = pytesseract.image_to_string(card_image, lang="kan+eng")
        except Exception as e:
            print(f"    ⚠ OCR failed: {str(e)}")
            return {}
        
        # Clean OCR text
        text = text_kannada if len(text_kannada) > len(text_mixed) else text_mixed
        text = text.strip()
        
        if not text:
            return {}
        
        # Extract fields using patterns
        voter_data = self._parse_voter_card_text(text)
        
        return voter_data
    
    def _parse_voter_card_text(self, text: str) -> Dict[str, str]:
        """
        Parse extracted text to identify voter card fields
        Uses pattern matching for consistent extraction
        """
        # Split text into lines
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        voter_data = {
            'serial_number': '',
            'voter_name': '',
            'fathers_name': '',
            'house_number': '',
            'age': '',
            'gender': '',
            'epic_number': '',
            'raw_text': '\n'.join(lines[:15])  # Store first 15 lines as reference
        }
        
        # Pattern matching for common fields
        for i, line in enumerate(lines):
            # Serial number (usually starts with numbers)
            if not voter_data['serial_number']:
                match = re.match(r'^(\d+)', line)
                if match:
                    voter_data['serial_number'] = match.group(1)
            
            # Look for numeric age patterns
            if not voter_data['age']:
                age_match = re.search(r'(?:आयु|Age|वय)[\s:]*(\d+)', line)
                if age_match:
                    voter_data['age'] = age_match.group(1)
            
            # Look for gender patterns
            if not voter_data['gender']:
                if re.search(r'(?:M|Male|पुरुष|मर्द)', line, re.IGNORECASE):
                    voter_data['gender'] = 'Male'
                elif re.search(r'(?:F|Female|महिला|औरत|स्त्री)', line, re.IGNORECASE):
                    voter_data['gender'] = 'Female'
            
            # Look for EPIC number patterns
            if not voter_data['epic_number']:
                epic_match = re.search(r'[A-Z]{3}[0-9]{7}', line)
                if epic_match:
                    voter_data['epic_number'] = epic_match.group(0)
            
            # House number patterns
            if not voter_data['house_number']:
                house_match = re.search(r'(?:मकान|House|No\.?|नं)[\s:]*([A-Za-z0-9\-\/]+)', line)
                if house_match:
                    voter_data['house_number'] = house_match.group(1)
        
        # If no structured fields found, use heuristic
        if not voter_data['voter_name'] and len(lines) > 1:
            # Assume longest line is voter name (usually true for Kannada)
            voter_data['voter_name'] = max(lines, key=len)
        
        # Second line often father's name
        if not voter_data['fathers_name'] and len(lines) > 2:
            voter_data['fathers_name'] = lines[2] if len(lines) > 2 else ''
        
        return voter_data
    
    def extract_cards_from_page(self, pdf_path: str, page_num: int) -> List[Dict]:
        """
        Extract all voter cards from a single page
        """
        print(f"\n  Converting page {page_num} to image...")
        
        try:
            pages = convert_from_path(pdf_path, first_page=page_num, last_page=page_num, dpi=300)
            if not pages:
                print(f"  ✗ Failed to convert page {page_num}")
                return []
            
            page_image = pages[0]
            image_cv = cv2.cvtColor(np.array(page_image), cv2.COLOR_RGB2BGR)
        except Exception as e:
            print(f"  ✗ Error converting page: {str(e)}")
            return []
        
        print(f"  Detecting voter card boundaries...")
        card_boundaries = self.detect_card_boundaries(image_cv)
        
        if not card_boundaries:
            print(f"  ✗ No cards detected on page {page_num}")
            return []
        
        print(f"  Initial detections: {len(card_boundaries)} cards")
        
        # Merge overlapping cards
        card_boundaries = self.merge_overlapping_cards(card_boundaries)
        print(f"  After merge: {len(card_boundaries)} cards")
        
        # Extract data from each card
        print(f"  Extracting voter data from {len(card_boundaries)} cards...")
        all_voters = []
        
        for card_idx, (x, y, w, h) in enumerate(card_boundaries, 1):
            # Crop card from image
            card_image = image_cv[max(0, y):min(image_cv.shape[0], y+h),
                                  max(0, x):min(image_cv.shape[1], x+w)]
            
            if card_image.size == 0:
                continue
            
            # Extract voter data
            voter_data = self.extract_voter_data_from_card(card_image)
            
            if voter_data:
                voter_data['page'] = page_num
                voter_data['card_index'] = card_idx
                all_voters.append(voter_data)
            
            if card_idx % 5 == 0:
                print(f"    Processed {card_idx}/{len(card_boundaries)} cards...")
        
        print(f"  ✓ Extracted {len(all_voters)} complete voter records from page {page_num}")
        
        return all_voters
    
    def translate_voter_data(self, voters: List[Dict]) -> List[Dict]:
        """Translate voter data to English"""
        print(f"  Translating {len(voters)} voter records...")
        
        for idx, voter in enumerate(voters):
            if idx % 10 == 0:
                print(f"    Translated {idx}/{len(voters)}...")
            
            for field in ['voter_name', 'fathers_name', 'house_number']:
                if voter.get(field):
                    try:
                        result = self.translator.translate(voter[field], dest='en', src='kn')
                        if result and hasattr(result, 'text'):
                            voter[f'{field}_en'] = result.text.strip()
                        else:
                            voter[f'{field}_en'] = voter[field]
                    except Exception as e:
                        voter[f'{field}_en'] = voter[field]
                    
                    time.sleep(0.05)  # Rate limiting
        
        return voters


def save_voter_data_to_excel(all_voters: List[Dict], output_file: str):
    """Save extracted voter data to Excel"""
    
    if not all_voters:
        print("✗ No voter data to save")
        return
    
    # Prepare data for DataFrame
    records = []
    
    for voter in all_voters:
        record = {
            'Page': voter.get('page', ''),
            'Card #': voter.get('card_index', ''),
            'Serial Number': voter.get('serial_number', ''),
            'Voter Name (KN)': voter.get('voter_name', ''),
            'Voter Name (EN)': voter.get('voter_name_en', ''),
            "Father's/Husband's Name (KN)": voter.get('fathers_name', ''),
            "Father's/Husband's Name (EN)": voter.get('fathers_name_en', ''),
            'House Number (KN)': voter.get('house_number', ''),
            'House Number (EN)': voter.get('house_number_en', ''),
            'Age': voter.get('age', ''),
            'Gender': voter.get('gender', ''),
            'EPIC Number': voter.get('epic_number', '')
        }
        records.append(record)
    
    # Create DataFrame
    df = pd.DataFrame(records)
    
    # Save to Excel
    try:
        os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)
        
        with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Voter Cards")
            
            ws = writer.sheets["Voter Cards"]
            
            # Adjust column widths
            column_widths = {
                'A': 8, 'B': 8, 'C': 12, 'D': 25, 'E': 25,
                'F': 25, 'G': 25, 'H': 20, 'I': 20, 'J': 8,
                'K': 12, 'L': 15
            }
            
            for col, width in column_widths.items():
                ws.column_dimensions[col].width = width
        
        print(f"✓ Voter data saved to: {output_file}")
        print(f"  Total records: {len(records)}")
        
    except Exception as e:
        print(f"✗ Error saving Excel: {str(e)}")


def main():
    """Main function using voter card segmentation"""
    print("=" * 100)
    print("KANNADA VOTER CARDS - SEGMENTATION & EXTRACTION")
    print("=" * 100)
    print(f"District: {DISTRICT}")
    print(f"AC: {AC_NUMBER}")
    print(f"Part Number: {PART_NUMBER}")
    print(f"Processing: Pages {START_PAGE + 1} to {START_PAGE + NUM_PAGES_TO_PROCESS}")
    print(f"Output Directory: {OUTPUT_DIR}")
    print("=" * 100)
    
    # Create output directories
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(TEMP_PDF_DIR, exist_ok=True)
    os.makedirs(CARDS_DIR, exist_ok=True)
    
    # Initialize segmentation engine
    print("\nInitializing voter card segmentation engine...")
    segmenter = VoterCardSegmentation()
    
    # Find PDF
    pdf_path = os.path.join(TEMP_PDF_DIR, f"A088{PART_NUMBER:03d}.pdf")
    
    if not os.path.exists(pdf_path):
        print(f"\n⚠ PDF not found: {pdf_path}")
        print("  Please download the PDF first using fetch_data.py")
        return
    
    print(f"PDF found: {pdf_path}")
    
    # Extract cards from all pages
    print("\n" + "=" * 100)
    print("SEGMENTING AND EXTRACTING VOTER CARDS")
    print("=" * 100)
    
    all_voters = []
    
    for page_offset in range(NUM_PAGES_TO_PROCESS):
        page_num = START_PAGE + 1 + page_offset
        print(f"\nPage {page_num}:")
        
        voters = segmenter.extract_cards_from_page(pdf_path, page_num)
        all_voters.extend(voters)
    
    if not all_voters:
        print("\n✗ No voter records extracted. Exiting.")
        return
    
    print(f"\n✓ Total voter records extracted: {len(all_voters)}")
    
    # Display sample records
    print("\n" + "=" * 100)
    print("SAMPLE EXTRACTED RECORDS (First 3)")
    print("=" * 100)
    
    for idx, voter in enumerate(all_voters[:3], 1):
        print(f"\nRecord {idx}:")
        print(f"  Serial: {voter.get('serial_number', 'N/A')}")
        print(f"  Name (KN): {voter.get('voter_name', 'N/A')}")
        print(f"  Father/Husband (KN): {voter.get('fathers_name', 'N/A')}")
        print(f"  House #: {voter.get('house_number', 'N/A')}")
        print(f"  Age: {voter.get('age', 'N/A')}")
        print(f"  Gender: {voter.get('gender', 'N/A')}")
        print(f"  EPIC: {voter.get('epic_number', 'N/A')}")
    
    # Translate to English
    print("\n" + "=" * 100)
    print("TRANSLATING VOTER DATA TO ENGLISH")
    print("=" * 100)
    
    all_voters = segmenter.translate_voter_data(all_voters)
    
    # Display translated samples
    print("\n" + "=" * 100)
    print("TRANSLATED RECORDS (First 3)")
    print("=" * 100)
    
    for idx, voter in enumerate(all_voters[:3], 1):
        print(f"\nRecord {idx}:")
        print(f"  Serial: {voter.get('serial_number', 'N/A')}")
        print(f"  Name (EN): {voter.get('voter_name_en', 'N/A')}")
        print(f"  Father/Husband (EN): {voter.get('fathers_name_en', 'N/A')}")
        print(f"  House # (EN): {voter.get('house_number_en', 'N/A')}")
        print(f"  Age: {voter.get('age', 'N/A')}")
        print(f"  Gender: {voter.get('gender', 'N/A')}")
        print(f"  EPIC: {voter.get('epic_number', 'N/A')}")
    
    # Save to Excel
    print("\n" + "=" * 100)
    print("SAVING TO EXCEL")
    print("=" * 100)
    
    xlsx_filename = f"voter_cards_part_{PART_NUMBER:03d}_segmentation.xlsx"
    xlsx_path = os.path.join(OUTPUT_DIR, xlsx_filename)
    save_voter_data_to_excel(all_voters, xlsx_path)
    
    print("\n" + "=" * 100)
    print("✓ PROCESS COMPLETED SUCCESSFULLY!")
    print(f"Output file: {xlsx_path}")
    print("=" * 100)


if __name__ == "__main__":
    main()
