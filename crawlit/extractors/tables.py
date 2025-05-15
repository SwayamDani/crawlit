"""
Table extractor for Crawlit.
Extracts HTML tables without external dependencies.
"""

import re
import html
from typing import List, Dict, Any, Union, Optional, Tuple

def clean_cell_content(content: str) -> str:
    """
    Enhanced cleaning function for table cell content.
    
    Args:
        content: Raw cell content with possible HTML tags
        
    Returns:
        Cleaned text content
    """
    # Basic HTML tag removal 
    clean_content = re.sub(r'<[^>]+>', '', content)
    
    # Handle HTML entities with the html module
    clean_content = html.unescape(clean_content)
    
    # Additional cleanup for numeric brackets from Wikipedia references
    clean_content = re.sub(r'\[\d+\]', '', clean_content)
    
    # Handle non-breaking spaces and other special whitespace
    clean_content = clean_content.replace('\xa0', ' ')
    
    # Normalize whitespace (convert multiple spaces/tabs/newlines to a single space)
    clean_content = re.sub(r'\s+', ' ', clean_content).strip()
    
    return clean_content

def extract_tables(html_content: str, min_rows: int = 1, min_columns: int = 2) -> List[List[List[str]]]:
    """
    Extract all tables from HTML content with advanced features.
    
    Features include:
    - Proper handling of thead and tbody sections
    - Support for rowspan and colspan attributes
    - Consistent column count across all rows
    - Clean cell content extraction
    
    Args:
        html_content: The HTML content to parse
        min_rows: Minimum number of rows required for a table to be included
        min_columns: Minimum number of columns required for a table to be included
        
    Returns:
        List of tables, where each table is represented as a list of rows,
        and each row is a list of cell values with proper handling of merged cells
    """
    tables = []
    
    # First find all table tags
    table_pattern = r'<table[^>]*>(.*?)</table>'
    table_tags = re.finditer(table_pattern, html_content, re.DOTALL)
    
    for table_match in table_tags:
        table_content = table_match.group(1)
        
        # Step 1: Extract table structure with cell spans
        raw_table_data = _extract_raw_table_structure(table_content)
        
        # Step 2: Process table to handle rowspan and colspan
        processed_table = _process_table_spans(raw_table_data)
        
        if processed_table and len(processed_table) >= min_rows and any(len(row) >= min_columns for row in processed_table):
            tables.append(processed_table)
    
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

def _extract_raw_table_structure(table_content: str) -> List[List[Dict[str, Any]]]:
    """
    Extract raw table structure including rowspan and colspan attributes.
    
    Args:
        table_content: HTML content inside <table> tags
        
    Returns:
        List of rows, where each row contains a list of cell dictionaries with
        content, rowspan, and colspan information
    """
    raw_rows = []
    
    # Handle both thead and tbody sections
    sections = []
    
    # Try to find thead section
    thead_pattern = r'<thead[^>]*>(.*?)</thead>'
    thead_match = re.search(thead_pattern, table_content, re.DOTALL)
    if thead_match:
        sections.append(thead_match.group(1))
    
    # Try to find tbody section(s)
    tbody_pattern = r'<tbody[^>]*>(.*?)</tbody>'
    tbody_matches = re.finditer(tbody_pattern, table_content, re.DOTALL)
    for tbody_match in tbody_matches:
        sections.append(tbody_match.group(1))
    
    # If no sections found, use the whole table content
    if not sections:
        sections.append(table_content)
    
    # Process all sections
    for section_content in sections:
        # Extract rows
        row_pattern = r'<tr[^>]*>(.*?)</tr>'
        row_matches = re.finditer(row_pattern, section_content, re.DOTALL)
        
        for row_match in row_matches:
            row_content = row_match.group(1)
            cells = []
            
            # Extract cells with their attributes
            cell_pattern = r'<t([dh])([^>]*)>(.*?)</t[dh]>'
            cell_matches = re.finditer(cell_pattern, row_content, re.DOTALL)
            
            for cell_match in cell_matches:
                cell_type = cell_match.group(1)  # 'd' or 'h'
                attrs = cell_match.group(2)
                content = cell_match.group(3)
                
                # Extract rowspan and colspan
                rowspan = 1
                colspan = 1
                
                rowspan_match = re.search(r'rowspan\s*=\s*["\']?(\d+)["\']?', attrs)
                if rowspan_match:
                    rowspan = int(rowspan_match.group(1))
                    
                colspan_match = re.search(r'colspan\s*=\s*["\']?(\d+)["\']?', attrs)
                if colspan_match:
                    colspan = int(colspan_match.group(1))
                
                # Clean the content
                clean_content = clean_cell_content(content)
                
                # Store cell with its span information
                cells.append({
                    'content': clean_content,
                    'rowspan': rowspan,
                    'colspan': colspan,
                    'is_header': cell_type == 'h'
                })
            
            raw_rows.append(cells)
    
    return raw_rows

def _process_table_spans(raw_table_data: List[List[Dict[str, Any]]]) -> List[List[str]]:
    """
    Process table data to handle rowspan and colspan attributes.
    
    Args:
        raw_table_data: Raw table structure with cell span information
        
    Returns:
        Processed table as a list of rows with cells expanded according to spans
    """
    if not raw_table_data:
        return []
    
    # Find the maximum number of columns
    max_cols = 0
    for row in raw_table_data:
        col_count = sum(cell['colspan'] for cell in row)
        max_cols = max(max_cols, col_count)
    
    if max_cols == 0:
        return []
    
    # Create a grid to track occupied cells
    num_rows = len(raw_table_data)
    grid = [[None for _ in range(max_cols)] for _ in range(num_rows)]
    
    # Fill the grid with cell contents, taking spans into account
    for row_idx, row in enumerate(raw_table_data):
        col_idx = 0
        for cell in row:
            # Find the next available column in this row
            while col_idx < max_cols and grid[row_idx][col_idx] is not None:
                col_idx += 1
            
            if col_idx >= max_cols:
                break
            
            # Place the cell content in the grid
            content = cell['content']
            rowspan = cell['rowspan']
            colspan = cell['colspan']
            
            # Fill the grid cells covered by this cell's spans
            for r in range(row_idx, min(row_idx + rowspan, num_rows)):
                for c in range(col_idx, min(col_idx + colspan, max_cols)):
                    if r == row_idx and c == col_idx:
                        grid[r][c] = content  # Main cell gets the content
                    else:
                        grid[r][c] = ""  # Spanned cells get empty string
            
            # Move to the next position
            col_idx += colspan
    
    # Convert grid to table rows, filtering out None values
    result_table = []
    for grid_row in grid:
        # Replace any None values (unfilled cells) with empty strings
        processed_row = [cell if cell is not None else "" for cell in grid_row]
        if any(processed_row):  # Skip rows that are all empty
            result_table.append(processed_row)
    
    return result_table

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
