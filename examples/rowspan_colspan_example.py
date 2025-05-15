#!/usr/bin/env python3
"""
Colspan and Rowspan Handling Example

This example demonstrates the difference between standard table extraction
and enhanced extraction that properly handles rowspan and colspan attributes.
"""

import sys
import os
import requests
from pprint import pprint

# Add the parent directory to the path so we can import the package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawlit.extractors.tables import extract_tables

# HTML table with rowspan and colspan attributes for demonstration
SAMPLE_HTML = """
<html>
<body>
    <h1>Sample Table with Rowspan and Colspan</h1>
    <table border="1">
        <thead>
            <tr>
                <th rowspan="2">Category</th>
                <th colspan="3">Products</th>
            </tr>
            <tr>
                <th>Name</th>
                <th>Price</th>
                <th>Rating</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td rowspan="2">Electronics</td>
                <td>Laptop</td>
                <td>$1200</td>
                <td>4.5/5</td>
            </tr>
            <tr>
                <td>Smartphone</td>
                <td>$800</td>
                <td>4.7/5</td>
            </tr>
            <tr>
                <td rowspan="2">Clothing</td>
                <td>Jacket</td>
                <td>$120</td>
                <td>4.2/5</td>
            </tr>
            <tr>
                <td>Jeans</td>
                <td>$60</td>
                <td>4.0/5</td>
            </tr>
        </tbody>
    </table>
</body>
</html>
"""

def main():
    print("Demonstrating advanced table extraction with rowspan and colspan support\n")
    
    # Extract tables with advanced features
    print("===== Advanced Table Extraction =====")
    tables = extract_tables(SAMPLE_HTML)
    
    if tables:
        print("Extraction result:")
        for i, row in enumerate(tables[0]):
            print(f"Row {i+1}: {row}")
        
        # Count cells in each row
        print("\nCell counts per row:")
        for i, row in enumerate(tables[0]):
            print(f"Row {i+1}: {len(row)} cells")
    else:
        print("No tables found.")
    
    print("\n===== Features Demonstrated =====")
    print("Notice how our table extraction properly handles:")
    print("1. The colspan=3 in the first row header")
    print("2. The rowspan=2 for Category cells")
    print("3. Consistent column count across all rows")
    print("4. Proper structure with thead/tbody sections")

if __name__ == "__main__":
    main()
