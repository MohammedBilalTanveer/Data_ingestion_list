# Simple Voter List Extractor

A minimal, working script to fetch Kannada voter lists and extract data to Excel.

## What's Different (vs Your Previous Code)

| Aspect | Previous | New |
|--------|----------|-----|
| OCR | Tesseract + Kannada pack ❌ | Not needed ✓ |
| Transformations | Google Vision, card segmentation | Direct PDF text ✓ |
| Dependencies | 15+ packages | 4 packages |
| Setup Time | 1+ hours | 5 minutes |
| Works Out of Box | Often fails | Yes ✓ |

## Quick Start

### 1. Install Dependencies

```bash
pip install pdfplumber requests pandas openpyxl
```

That's it! No Tesseract, no complex setup.

### 2. Run the Script

```bash
python simple_voter_extractor.py
```

### 3. Output

The script will:
- 📥 Download the PDF (once, cached locally)
- 📄 Extract all tables from the PDF
- 💾 Save to `output/voter_list_part_278_simple.xlsx`

## How It Works

```
PDF Download
    ↓
Fetch via requests
    ↓
Open with pdfplumber
    ↓
Extract tables (built-in table detection)
    ↓
Save to Excel
```

No OCR. No translation. No magic. Just straightforward extraction.

## Configuration

Edit these variables at the top of the script:

```python
DISTRICT = "BANGALORE URBAN"
AC_NUMBER = "88"  # Yelahanka
PART_NUMBER = 278  # Change this for other parts
```

## Processing Other Parts

To process a different part (e.g., 279, 280):

```python
PART_NUMBER = 279  # Change this line
```

Then run:

```bash
python simple_voter_extractor.py
```

## Troubleshooting

### Script can't find the PDF

**Problem**: "Could not download PDF"

**Solution**: Check the URL:
- Current: `http://ceokarnataka.nic.in/eroll/14-BBNUPL/A{AC}{PART}.pdf`
- Verify the URL works in your browser
- The electoral roll site structure may have changed

### Excel file is empty or has wrong structure

**Problem**: Extracted data looks wrong

**Solution**: The script uses built-in PDF table detection, which works if:
- ✓ The PDF has obvious table structure (lines/grids)
- ✗ The PDF is scanned/image-based
- ✗ The PDF has no visible table borders

### Download is slow or times out

**Problem**: PDF takes too long to download

**Solution**: 
- The PDF is already cached in `output/temp_pdfs/` after first run
- Subsequent runs will skip download
- Delete the file to re-download

## Output File Structure

```
voter_list_part_278_simple.xlsx
├─ Serial No.
├─ Voter Name
├─ Relation Name
├─ Relation Type (Father/Spouse)
├─ Gender
├─ Age
└─ Voter ID
```

The script preserves original Kannada text (no translation). If you need English translation, that's a separate step.

## Limitations

This script:
- ✓ Works with searchable PDFs (text-based)
- ✗ Won't work with scanned PDFs (images)
- ✓ Handles Kannada text as-is
- ✓ Fast and reliable

If the PDF is scanned/image-based, you'll need OCR (which requires Tesseract). The original complex setup was for that case.

## Next Steps

1. ✓ Get the basic extraction working (this script)
2. Add simple Kannada-to-English transliteration (if needed)
3. Process other part numbers (change one variable)
4. Batch process multiple parts

## Help

If it still doesn't work:
1. Check the PDF URL in a browser
2. Verify the AC and Part numbers
3. Try a different part number (maybe 278 doesn't exist)
4. Check the Karnataka Election Commission website for the correct URLs

---

**Note**: This is intentionally simple. No complex logic, no magic—just fetch and extract.
