"""
Quick test to verify PDF URL and connectivity
Run this first if the main script fails
"""

import requests
import sys

# Configuration
AC_NUMBER = "88"
PART_NUMBER = 278

# Try different URL patterns that might work
URLS_TO_TRY = [
    f"http://ceokarnataka.nic.in/eroll/14-BBNUPL/A{AC_NUMBER:02d}{PART_NUMBER:03d}.pdf",
    f"http://ceokarnataka.nic.in/eroll/pdf/A{AC_NUMBER:02d}{PART_NUMBER:03d}.pdf",
    f"https://ceokarnataka.nic.in/eroll/14-BBNUPL/A{AC_NUMBER:02d}{PART_NUMBER:03d}.pdf",
    f"https://ceokarnataka.nic.in/eroll/pdf/A{AC_NUMBER:02d}{PART_NUMBER:03d}.pdf",
]


def test_url(url: str) -> bool:
    """Test if URL is accessible"""
    try:
        print(f"Testing: {url}")
        response = requests.head(url, timeout=10, allow_redirects=True)
        
        if response.status_code == 200:
            print(f"  ✓ SUCCESS - Status: {response.status_code}")
            print(f"    Content-Type: {response.headers.get('content-type', 'N/A')}")
            print(f"    Content-Length: {response.headers.get('content-length', 'N/A')} bytes")
            return True
        else:
            print(f"  ✗ FAILED - Status: {response.status_code}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"  ✗ TIMEOUT - Server took too long to respond")
        return False
    except requests.exceptions.ConnectionError:
        print(f"  ✗ CONNECTION ERROR - Can't reach server")
        return False
    except Exception as e:
        print(f"  ✗ ERROR - {str(e)}")
        return False


def main():
    print("=" * 80)
    print("PDF URL CONNECTIVITY TEST")
    print("=" * 80)
    print(f"AC Number: {AC_NUMBER}")
    print(f"Part Number: {PART_NUMBER}")
    print(f"Expected filename: A{AC_NUMBER:02d}{PART_NUMBER:03d}.pdf")
    print("=" * 80)
    
    print("\nTrying different URL patterns...\n")
    
    working_url = None
    for url in URLS_TO_TRY:
        if test_url(url):
            working_url = url
            break
        print()
    
    if working_url:
        print("\n" + "=" * 80)
        print("✓ FOUND WORKING URL!")
        print("=" * 80)
        print(f"\nWorking URL:\n{working_url}")
        print("\nUpdate your script with this URL in the create_pdf_url() function")
    else:
        print("\n" + "=" * 80)
        print("✗ NO WORKING URLs FOUND")
        print("=" * 80)
        print("\nPossible issues:")
        print("  1. The part number doesn't exist")
        print("  2. The AC number is wrong")
        print("  3. The website URL format has changed")
        print("  4. The PDF is not available for this constituency")
        print("\nNext steps:")
        print("  1. Visit Karnataka Election Commission website manually")
        print("  2. Find the correct URL for part 278")
        print("  3. Update the URLS_TO_TRY list with the correct pattern")
        print("  4. Re-run this test")
        sys.exit(1)


if __name__ == "__main__":
    main()
