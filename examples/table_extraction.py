"""
Example usage of the table extractor module in Crawlit.
"""

import os
import sys
import requests

from crawlit.extractors.tables import extract_tables, tables_to_csv, tables_to_dict, filter_tables

def main():
    # Example URL with tables - Wikipedia pages often have tables
    url = "https://en.wikipedia.org/wiki/List_of_countries_by_population"
    
    print(f"Fetching tables from: {url}")
    response = requests.get(url)
    html_content = response.text
    
    # Extract tables with at least 5 rows and 3 columns to filter out small tables
    tables = extract_tables(html_content, min_rows=5, min_columns=3)
    print(f"Found {len(tables)} tables on the page")
    
    # Print the first few rows of the first table
    if tables:
        first_table = tables[0]
        print("\nFirst table preview:")
        for i, row in enumerate(first_table[:3]):  # Show first 3 rows
            print(f"Row {i}: {row}")
        
        if len(first_table) > 3:
            print("... (more rows) ...")
    
    # Create an output directory for CSV files
    output_dir = "table_output"
    os.makedirs(output_dir, exist_ok=True)
    
    # Save tables to CSV
    csv_files = tables_to_csv(tables, "wikipedia_table", output_dir=output_dir)
    print(f"\nSaved {len(csv_files)} tables to CSV files in the {output_dir} directory:")
    for file in csv_files:
        print(f"- {file}")
    
    # Convert tables to dictionaries
    tables_dict = tables_to_dict(tables)
    if tables_dict:
        first_table_dict = tables_dict[0]
        print("\nFirst table as dictionaries (first 2 rows):")
        for i, row in enumerate(first_table_dict[:2]):
            print(f"Row {i}: {row}")

if __name__ == "__main__":
    main()
