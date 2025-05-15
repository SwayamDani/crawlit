#!/usr/bin/env python3
"""
Enhanced Table Extraction Example

This example shows how to use the enhanced table extraction features
that support proper table structure and cell spanning attributes.
"""

import sys
import os
import requests

# Add the parent directory to the path so we can import the package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawlit.extractors.tables import (
    extract_tables, 
    tables_to_csv,
    tables_to_dict
)

def main():
    # Example URL with tables that include rowspan/colspan
    url = "https://en.wikipedia.org/wiki/Comparison_of_programming_languages"
    print(f"Fetching tables from {url}")
    
    response = requests.get(
        url,
        headers={"User-Agent": "crawlit/example-script"}
    )
    
    if response.status_code != 200:
        print(f"Failed to fetch URL: {response.status_code}")
        return
    
    html_content = response.text
    print("HTML content fetched successfully")
    
    # Extract tables with advanced features (thead/tbody handling, rowspan/colspan support)
    print("\n===== Advanced Table Extraction =====")
    tables = extract_tables(html_content, min_rows=3, min_columns=3)
    print(f"Found {len(tables)} tables")
    
    if tables:
        print("\nFirst table sample:")
        for i, row in enumerate(tables[0][:3]):  # Print first 3 rows of first table
            print(f"Row {i+1}: {row[:3]}...")  # Show first 3 cells
    
    # Save tables to CSV
    if tables:
        print("\nSaving tables to CSV...")
        saved_files = tables_to_csv(tables, base_filename="extracted_table")
        print(f"Saved {len(saved_files)} tables to CSV files:")
        for file in saved_files:
            print(f"  - {file}")

if __name__ == "__main__":
    main()
