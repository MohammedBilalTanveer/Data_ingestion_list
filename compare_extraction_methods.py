"""
Compare Google Vision OCR vs Card Segmentation
===============================================
Side-by-side comparison of both extraction methods
with quality metrics and recommendations.
"""

import os
import sys
import json
import time
from typing import Dict, List, Tuple
import pandas as pd
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

# Configuration
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
COMPARISON_DIR = os.path.join(OUTPUT_DIR, "comparisons")
TEMP_PDF_DIR = os.path.join(OUTPUT_DIR, "temp_pdfs")


class ExtractionComparator:
    """Compare extraction quality between methods"""
    
    def __init__(self):
        """Initialize comparator"""
        os.makedirs(COMPARISON_DIR, exist_ok=True)
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'google_vision': {},
            'card_segmentation': {},
            'comparison': {}
        }
    
    def load_excel_file(self, excel_path: str) -> Tuple[pd.DataFrame, bool]:
        """Load and parse Excel file"""
        try:
            df = pd.read_excel(excel_path)
            return df, True
        except Exception as e:
            print(f"  ✗ Error loading Excel: {str(e)}")
            return None, False
    
    def calculate_metrics(self, df: pd.DataFrame, method_name: str) -> Dict:
        """Calculate quality metrics for extracted data"""
        
        if df is None or df.empty:
            return {
                'rows': 0,
                'columns': 0,
                'errors': 'Empty DataFrame'
            }
        
        metrics = {
            'rows': len(df),
            'columns': len(df.columns),
            'total_cells': len(df) * len(df.columns),
            'empty_cells': int(df.isna().sum().sum() + (df == '').sum().sum()),
            'column_names': list(df.columns),
            'data_types': df.dtypes.astype(str).to_dict(),
        }
        
        # Calculate fill rate
        metrics['fill_rate_percent'] = round(
            ((metrics['total_cells'] - metrics['empty_cells']) / metrics['total_cells'] * 100)
            if metrics['total_cells'] > 0 else 0,
            2
        )
        
        # Sample data
        metrics['sample_rows'] = df.head(3).to_dict('records')
        
        return metrics
    
    def compare_row_counts(self, df1: pd.DataFrame, df2: pd.DataFrame) -> Dict:
        """Compare row counts between methods"""
        count1 = len(df1) if df1 is not None else 0
        count2 = len(df2) if df2 is not None else 0
        
        if count1 == 0 or count2 == 0:
            difference_percent = 100
        else:
            difference_percent = abs(count1 - count2) / max(count1, count2) * 100
        
        return {
            'google_vision_rows': count1,
            'segmentation_rows': count2,
            'difference': abs(count1 - count2),
            'difference_percent': round(difference_percent, 2),
            'winner': 'Google Vision' if count1 > count2 else 'Card Segmentation' if count2 > count1 else 'Tie'
        }
    
    def compare_data_quality(self, df1: pd.DataFrame, df2: pd.DataFrame) -> Dict:
        """Compare data quality metrics"""
        
        if df1 is None or df2 is None or df1.empty or df2.empty:
            return {'error': 'One or both DataFrames are empty'}
        
        metrics1 = self.calculate_metrics(df1, 'Google Vision')
        metrics2 = self.calculate_metrics(df2, 'Card Segmentation')
        
        return {
            'google_vision': {
                'fill_rate': metrics1['fill_rate_percent'],
                'empty_cells': metrics1['empty_cells']
            },
            'card_segmentation': {
                'fill_rate': metrics2['fill_rate_percent'],
                'empty_cells': metrics2['empty_cells']
            },
            'winner': 'Google Vision' if metrics1['fill_rate_percent'] > metrics2['fill_rate_percent'] else 'Card Segmentation'
        }
    
    def compare_column_coverage(self, df1: pd.DataFrame, df2: pd.DataFrame) -> Dict:
        """Compare how well each method covered columns"""
        
        coverage1 = {col: len(df1[df1[col].notna()]) / len(df1) * 100 if col in df1.columns else 0 
                    for col in df1.columns} if df1 is not None else {}
        coverage2 = {col: len(df2[df2[col].notna()]) / len(df2) * 100 if col in df2.columns else 0 
                    for col in df2.columns} if df2 is not None else {}
        
        return {
            'google_vision_coverage': {k: round(v, 2) for k, v in coverage1.items()},
            'segmentation_coverage': {k: round(v, 2) for k, v in coverage2.items()}
        }
    
    def detect_language(self, text_sample: str) -> Dict:
        """Detect which language is more prevalent in sample"""
        if not text_sample or not isinstance(text_sample, str):
            return {'kannada': 0, 'english': 0, 'other': 100}
        
        kannada_count = sum(1 for c in text_sample if '\u0c80' <= c <= '\u0cff')  # Kannada range
        english_count = sum(1 for c in text_sample if c.isascii() and c.isalpha())
        total = len(text_sample)
        
        return {
            'kannada_percent': round(kannada_count / total * 100, 2) if total > 0 else 0,
            'english_percent': round(english_count / total * 100, 2) if total > 0 else 0,
            'other_percent': round((total - kannada_count - english_count) / total * 100, 2) if total > 0 else 0
        }
    
    def generate_recommendation(self, metrics: Dict) -> Dict:
        """Generate recommendation based on comparison metrics"""
        
        row_comparison = metrics.get('row_counts', {})
        quality_comparison = metrics.get('data_quality', {})
        
        recommendations = []
        winner = None
        confidence = 0.0
        
        # Score each method
        gv_score = 0
        cs_score = 0
        
        # Row count factor
        if row_comparison.get('winner') == 'Google Vision':
            gv_score += 10
        elif row_comparison.get('winner') == 'Card Segmentation':
            cs_score += 10
        
        # Data quality factor
        if quality_comparison.get('winner') == 'Google Vision':
            gv_score += 10
            recommendations.append("Google Vision has better data completeness")
        elif quality_comparison.get('winner') == 'Card Segmentation':
            cs_score += 10
            recommendations.append("Card Segmentation has better data completeness")
        
        # Determine winner
        if gv_score > cs_score:
            winner = 'Google Vision'
            confidence = (gv_score / (gv_score + cs_score)) * 100 if (gv_score + cs_score) > 0 else 0
        elif cs_score > gv_score:
            winner = 'Card Segmentation'
            confidence = (cs_score / (gv_score + cs_score)) * 100 if (gv_score + cs_score) > 0 else 0
        else:
            winner = 'Tie - Use based on other factors'
            confidence = 50.0
        
        return {
            'recommended_method': winner,
            'confidence_percent': round(confidence, 2),
            'recommendations': recommendations,
            'next_steps': [
                'Use recommended method for full production run',
                'Review sample output for manual verification',
                'Adjust thresholds if needed for your specific documents'
            ]
        }
    
    def run_comparison(self, pdf_part_number: int = 278) -> bool:
        """Run full comparison between both methods"""
        
        print("\n" + "=" * 100)
        print("COMPARING EXTRACTION METHODS")
        print("=" * 100)
        
        # Find Excel files
        gv_file = os.path.join(OUTPUT_DIR, f"voter_list_part_{pdf_part_number:03d}_google_vision.xlsx")
        cs_file = os.path.join(OUTPUT_DIR, f"voter_cards_part_{pdf_part_number:03d}_segmentation.xlsx")
        
        gv_exists = os.path.exists(gv_file)
        cs_exists = os.path.exists(cs_file)
        
        if not gv_exists and not cs_exists:
            print("\n✗ No output files found!")
            print(f"  Expected: {gv_file}")
            print(f"  Expected: {cs_file}")
            print("\n  Please run both extraction scripts first:")
            print("    python extract_google_vision.py")
            print("    python extract_voter_cards_segmentation.py")
            return False
        
        if not gv_exists:
            print(f"\n⚠ Google Vision file not found: {gv_file}")
        else:
            print(f"✓ Found Google Vision output: {gv_file}")
        
        if not cs_exists:
            print(f"⚠ Card Segmentation file not found: {cs_file}")
        else:
            print(f"✓ Found Card Segmentation output: {cs_file}")
        
        # Load files
        print("\nLoading data files...")
        gv_df, gv_ok = self.load_excel_file(gv_file) if gv_exists else (None, False)
        cs_df, cs_ok = self.load_excel_file(cs_file) if cs_exists else (None, False)
        
        if not gv_ok and not cs_ok:
            print("✗ Failed to load any files")
            return False
        
        # Calculate metrics
        print("\nCalculating metrics...")
        
        if gv_ok:
            print("\n📊 GOOGLE VISION OCR")
            print("-" * 100)
            gv_metrics = self.calculate_metrics(gv_df, 'Google Vision')
            print(f"  Rows: {gv_metrics['rows']}")
            print(f"  Columns: {gv_metrics['columns']}")
            print(f"  Total Cells: {gv_metrics['total_cells']}")
            print(f"  Empty Cells: {gv_metrics['empty_cells']}")
            print(f"  Data Fill Rate: {gv_metrics['fill_rate_percent']}%")
            print(f"  Columns: {', '.join(gv_metrics['column_names'][:5])}...")
            self.results['google_vision'] = gv_metrics
        
        if cs_ok:
            print("\n📊 CARD SEGMENTATION")
            print("-" * 100)
            cs_metrics = self.calculate_metrics(cs_df, 'Card Segmentation')
            print(f"  Rows: {cs_metrics['rows']}")
            print(f"  Columns: {cs_metrics['columns']}")
            print(f"  Total Cells: {cs_metrics['total_cells']}")
            print(f"  Empty Cells: {cs_metrics['empty_cells']}")
            print(f"  Data Fill Rate: {cs_metrics['fill_rate_percent']}%")
            print(f"  Columns: {', '.join(cs_metrics['column_names'][:5])}...")
            self.results['card_segmentation'] = cs_metrics
        
        # Compare
        if gv_ok and cs_ok:
            print("\n" + "=" * 100)
            print("COMPARISON RESULTS")
            print("=" * 100)
            
            # Row counts
            row_comparison = self.compare_row_counts(gv_df, cs_df)
            print("\n📈 ROW COUNT")
            print(f"  Google Vision: {row_comparison['google_vision_rows']} rows")
            print(f"  Card Segmentation: {row_comparison['segmentation_rows']} rows")
            print(f"  Difference: {row_comparison['difference']} ({row_comparison['difference_percent']}%)")
            print(f"  Winner: {row_comparison['winner']}")
            self.results['comparison']['row_counts'] = row_comparison
            
            # Data quality
            quality_comparison = self.compare_data_quality(gv_df, cs_df)
            print("\n🎯 DATA QUALITY")
            print(f"  Google Vision Fill Rate: {quality_comparison['google_vision']['fill_rate']}%")
            print(f"  Card Segmentation Fill Rate: {quality_comparison['card_segmentation']['fill_rate']}%")
            print(f"  Winner: {quality_comparison['winner']}")
            self.results['comparison']['data_quality'] = quality_comparison
            
            # Recommendations
            print("\n" + "=" * 100)
            print("RECOMMENDATION")
            print("=" * 100)
            recommendation = self.generate_recommendation(self.results['comparison'])
            print(f"\n✅ Recommended Method: {recommendation['recommended_method']}")
            print(f"   Confidence: {recommendation['confidence_percent']}%")
            print("\n📋 Reasons:")
            for rec in recommendation['recommendations']:
                print(f"   • {rec}")
            print("\n📌 Next Steps:")
            for step in recommendation['next_steps']:
                print(f"   • {step}")
            
            self.results['comparison']['recommendation'] = recommendation
        
        # Save comparison report
        print("\n" + "=" * 100)
        print("SAVING COMPARISON REPORT")
        print("=" * 100)
        
        report_file = os.path.join(COMPARISON_DIR, 
                                   f"comparison_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, indent=2, ensure_ascii=False)
            print(f"✓ Comparison report saved: {report_file}")
        except Exception as e:
            print(f"✗ Error saving report: {str(e)}")
        
        print("\n" + "=" * 100)
        print("✓ COMPARISON COMPLETE")
        print("=" * 100)
        
        return True


def main():
    """Main comparison function"""
    print("=" * 100)
    print("VOTER DATA EXTRACTION - METHOD COMPARISON")
    print("=" * 100)
    print("\nThis script compares the output from:")
    print("  • extract_google_vision.py")
    print("  • extract_voter_cards_segmentation.py")
    print("\nMake sure both scripts have been run before proceeding!")
    print("=" * 100)
    
    comparator = ExtractionComparator()
    
    # Check if files exist
    print("\nChecking for extracted data...")
    success = comparator.run_comparison()
    
    if not success:
        print("\n⚠️  Comparison could not be completed.")
        print("\nTo create comparable data:")
        print("  1. Run: python extract_google_vision.py")
        print("  2. Run: python extract_voter_cards_segmentation.py")
        print("  3. Run this script again")
        sys.exit(1)
    
    print("\n✓ Done! Check the output folder for detailed reports.")


if __name__ == "__main__":
    main()
