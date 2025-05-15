"""
Table extractor for Crawlit.
Extracts HTML tables without external dependencies.
"""

import re
import html
from typing import List, Dict, Any, Union

def extract_tables(html_content: str, min_rows: int = 1, min_columns: int = 2) -> List[List[List[str]]]:
    """
    Extract all tables from HTML content.
    
    Args:
        html_content: The HTML content to parse
        min_rows: Minimum number of rows required for a table to be included
        min_columns: Minimum number of columns required for a table to be included
        
    Returns:
        List of tables, where each table is represented as a list of rows,
        and each row is a list of cell values
    """
    tables = []
    
    # First find all table tags
    table_pattern = r'<table[^>]*>(.*?)</table>'
    table_tags = re.finditer(table_pattern, html_content, re.DOTALL)
    
    for table_match in table_tags:
        table_content = table_match.group(1)
        
        # Extract rows
        rows = []
        row_pattern = r'<tr[^>]*>(.*?)</tr>'
        row_matches = re.finditer(row_pattern, table_content, re.DOTALL)
        
        for row_match in row_matches:
            row_content = row_match.group(1)
            
            # Extract header cells and data cells
            cell_pattern = r'<t[dh][^>]*>(.*?)</t[dh]>'
            cells = re.finditer(cell_pattern, row_content, re.DOTALL)
            
            row_data = []
            for cell in cells:
                # Clean up cell content (remove nested tags, handle entities, etc.)
                cell_content = cell.group(1)
                
                # Basic HTML tag removal (can be enhanced)
                clean_content = re.sub(r'<[^>]+>', '', cell_content)
                
                # Handle HTML entities with the html module
                clean_content = html.unescape(clean_content)
                
                # Additional cleanup for numeric brackets from Wikipedia references
                clean_content = re.sub(r'\[\d+\]', '', clean_content)
                
                # Remove extra whitespace
                clean_content = re.sub(r'\s+', ' ', clean_content).strip()
                
                # Add the cleaned cell content to the row
                row_data.append(clean_content)
            
            if row_data and len(row_data) >= min_columns:  # Only add rows with enough cells
                rows.append(row_data)
        
        if rows and len(rows) >= min_rows:  # Only add tables with enough rows
            tables.append(rows)
    
    return tables

def filter_tables(tables: List[List[List[str]]], min_rows: int = 2, min_cols: int = 2) -> List[List[List[str]]]:
    """
    Filter tables based on minimum size requirements.
    
    Args:
        tables: List of tables to filter
        min_rows: Minimum number of rows required
        min_cols: Minimum number of columns required
        
    Returns:
        Filtered list of tables
    """
    result = []
    
    for table in tables:
        if len(table) >= min_rows:
            # Check if at least one row has enough columns
            if any(len(row) >= min_cols for row in table):
                result.append(table)
    
    return result

def tables_to_csv(tables: List[List[List[str]]], base_filename: str = "table", 
                 output_dir: str = None) -> List[str]:
    """
    Convert extracted tables to CSV files.
    
    Args:
        tables: List of tables (as returned by extract_tables)
        base_filename: Base name for the CSV files
        output_dir: Directory to save the CSV files (default: current directory)
        
    Returns:
        List of saved CSV file paths
    """
    import csv
    import os
    
    saved_files = []
    
    # Create output directory if it doesn't exist
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    for i, table in enumerate(tables):
        # Skip empty tables
        if not table:
            continue
            
        # Create filename
        if output_dir:
            filename = os.path.join(output_dir, f"{base_filename}_{i+1}.csv")
        else:
            filename = f"{base_filename}_{i+1}.csv"
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            for row in table:
                writer.writerow(row)
        
        saved_files.append(filename)
    
    return saved_files

def tables_to_dict(tables: List[List[List[str]]]) -> List[List[Dict[str, str]]]:
    """
    Convert tables to a list of dictionaries, using the first row as headers.
    
    Args:
        tables: List of tables (as returned by extract_tables)
        
    Returns:
        List of tables where each table is a list of row dictionaries
    """
    result = []
    
    for table in tables:
        if not table or len(table) < 2:  # Need at least a header row and one data row
            continue
            
        headers = table[0]
        # Clean and normalize header keys
        clean_headers = []
        for header in headers:
            # Remove any remaining special characters from the header
            clean_header = re.sub(r'[^\w\s]', '', header)
            # Normalize whitespace
            clean_header = re.sub(r'\s+', '_', clean_header.strip().lower())
            if not clean_header:
                clean_header = f"column_{len(clean_headers) + 1}"
            clean_headers.append(clean_header)
            
        rows_as_dicts = []
        
        for row_idx in range(1, len(table)):
            row_dict = {}
            row = table[row_idx]
            
            # Map each cell to its corresponding header
            for col_idx, value in enumerate(row):
                if col_idx < len(clean_headers):
                    header_key = clean_headers[col_idx]
                    row_dict[header_key] = value
                else:
                    # Handle case where row has more columns than header
                    row_dict[f"column_{col_idx+1}"] = value
                    
            rows_as_dicts.append(row_dict)
            
        result.append(rows_as_dicts)
        
    return result

def tables_to_json(tables: List[List[List[str]]], base_filename: str = "table", 
                  output_dir: str = None) -> List[str]:
    """
    Convert extracted tables to JSON files.
    
    Args:
        tables: List of tables (as returned by extract_tables)
        base_filename: Base name for the JSON files
        output_dir: Directory to save the JSON files (default: current directory)
        
    Returns:
        List of saved JSON file paths
    """
    import json
    import os
    
    saved_files = []
    
    # Create output directory if it doesn't exist
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    for i, table in enumerate(tables):
        # Skip empty tables
        if not table:
            continue
            
        # Create filename
        if output_dir:
            filename = os.path.join(output_dir, f"{base_filename}_{i+1}.json")
        else:
            filename = f"{base_filename}_{i+1}.json"
        
        # Convert table to JSON format
        # First row as headers, rest as data
        if len(table) > 0:
            headers = table[0]
            data = []
            
            # Process data rows
            for row_idx in range(1, len(table)):
                row_dict = {}
                row = table[row_idx]
                
                # Map each cell to its corresponding header
                for col_idx, value in enumerate(row):
                    if col_idx < len(headers):
                        header_key = headers[col_idx]
                        row_dict[header_key] = value
                    else:
                        # Handle case where row has more columns than header
                        row_dict[f"column_{col_idx+1}"] = value
                
                data.append(row_dict)
            
            # Write to file
            with open(filename, 'w', encoding='utf-8') as jsonfile:
                json.dump({"headers": headers, "data": data}, jsonfile, indent=2, ensure_ascii=False)
            
            saved_files.append(filename)
    
    return saved_files

def get_url_safe_filename(url: str, depth: int = 0) -> str:
    """
    Generate a safe filename from a URL and depth.
    
    Args:
        url: The URL to convert to a filename
        depth: The crawl depth of the page
        
    Returns:
        A safe filename derived from the URL and depth
    """
    from urllib.parse import urlparse
    import re
    
    parsed_url = urlparse(url)
    domain = parsed_url.netloc.replace('.', '_')
    path = parsed_url.path.replace('/', '_')
    
    # Clean the path
    path = re.sub(r'[^\w\-_]', '', path).strip('_')
    if not path:
        path = "index"
    
    # Ensure the filename doesn't get too long
    if len(path) > 50:
        path = path[:50]
    
    return f"{domain}_{path}_depth{depth}"

def extract_and_save_tables_from_crawl(results: Dict[str, Any], 
                                      output_dir: str,
                                      output_format: str = "csv",
                                      min_rows: int = 1,
                                      min_columns: int = 2,
                                      max_depth: int = None) -> Dict[str, Any]:
    """
    Extract tables from all pages in a crawl result and save them to files.
    
    Args:
        results: Crawl results dictionary from crawler.get_results()
        output_dir: Directory to save the table files
        output_format: Format to save tables ('csv' or 'json')
        min_rows: Minimum number of rows for a table to be included
        min_columns: Minimum number of columns for a table to be included
        max_depth: Maximum depth to extract tables from (None for all depths)
        
    Returns:
        Dictionary with statistics about extracted tables
    """
    import os
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    stats = {
        "total_pages_with_tables": 0,
        "total_tables_found": 0,
        "total_files_saved": 0,
        "tables_by_depth": {},
        "urls_with_tables": []
    }
    
    for url, data in results.items():
        content = data.get('html_content')
        depth = data.get('depth', 0)
        
        # Skip if no content or beyond max_depth
        if not content or (max_depth is not None and depth > max_depth):
            continue
            
        # Extract tables from the page
        tables = extract_tables(content, min_rows, min_columns)
        tables_found = len(tables)
        
        if tables_found > 0:
            # Update statistics
            stats["total_pages_with_tables"] += 1
            stats["total_tables_found"] += tables_found
            stats["urls_with_tables"].append(url)
            
            # Track tables by depth
            if depth not in stats["tables_by_depth"]:
                stats["tables_by_depth"][depth] = 0
            stats["tables_by_depth"][depth] += tables_found
            
            # Create base filename from URL
            base_name = get_url_safe_filename(url, depth)
            base_filename = os.path.join(output_dir, base_name)
            
            # Save tables in the specified format
            if output_format.lower() == "json":
                saved_files = tables_to_json(tables, base_filename)
            else:  # Default to CSV
                saved_files = tables_to_csv(tables, base_filename)
                
            stats["total_files_saved"] += len(saved_files)
    
    return stats
