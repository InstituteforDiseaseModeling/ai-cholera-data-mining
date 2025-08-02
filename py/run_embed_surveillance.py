#!/usr/bin/env python3
"""
DEPRECATED: One-time script to embed MOSAIC surveillance data.

NOTE: This script is no longer needed as we now reference the original
file directly to avoid duplication.
"""

from pathlib import Path
import sys

# Add py/ directory to path
sys.path.append('py')

from update_dashboard_data import embed_original_surveillance_data

if __name__ == "__main__":
    base_path = Path(".")
    
    print("=" * 80)
    print("MOSAIC SURVEILLANCE DATA EMBEDDING")
    print("=" * 80)
    
    success = embed_original_surveillance_data(base_path)
    
    if success:
        print("\n✅ EMBEDDING COMPLETED SUCCESSFULLY!")
        print("   The reference/cholera_surveillance_weekly_combined.csv file is now available")
        print("   for CI environments (GitHub Pages, Codespaces, etc.)")
    else:
        print("\n❌ EMBEDDING FAILED!")
        print("   The dashboard will work with AI data only in CI environments")
    
    print("=" * 80)