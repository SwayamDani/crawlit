"""
Table extractor for Crawlit.
Extracts HTML tables without external dependencies.
"""

import re
import html
from typing import List, Dict, Any, Union, Optional, Tuple
from bs4 import BeautifulSoup

def clean_cell_content(content: str) -> str:
    """
    Enhanced cleaning function for table cell content using BeautifulSoup.
    
    Args:
        content: Raw cell content with possible HTML tags
        
    Returns:
        Cleaned text content
    """
    # Use BeautifulSoup to handle HTML tags properly
    soup = BeautifulSoup(content, 'html.parser')
    clean_content = soup.get_text()
    
    # Additional cleanup for numeric brackets from Wikipedia references
    clean_content = re.sub(r'\[\d+\]', '', clean_content)
    
    # Handle non-breaking spaces and other special whitespace
    clean_content = clean_content.replace('\xa0', ' ')
    
    # Normalize whitespace (convert multiple spaces/tabs/newlines to a single space)
    clean_content = re.sub(r'\s+', ' ', clean_content).strip()
    
    return clean_content

def extract_tables(html_content: str, min_rows: int = 1, min_columns: int = 1) -> List[List[List[str]]]:
    """
    Extract all tables from HTML content using BeautifulSoup for robust parsing.
    
    Args:
        html_content: The HTML content to parse
        min_rows: Minimum number of rows required for a table to be included
        min_columns: Minimum number of columns required for a table to be included
        
    Returns:
        List of tables, where each table is represented as a list of rows,
        and each row is a list of cell values with proper handling of merged cells
    """
    tables = []
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Find only top-level tables (not nested inside other tables)
    all_tables = soup.find_all('table')
    top_level_tables = []
    
    for table in all_tables:
        # Check if this table is nested inside another table
        is_nested = False
        parent = table.parent
        while parent:
            if parent.name == 'table':
                is_nested = True
                break
            parent = parent.parent
        
        if not is_nested:
            top_level_tables.append(table)
    
    for table in top_level_tables:
        # Extract the raw table structure including rowspan/colspan information
        raw_table_data = _extract_raw_table_structure(str(table))
        
        # Process the rowspan and colspan attributes to get the final table
        processed_table = _process_table_spans(raw_table_data)
        
        # Add the table if it meets the minimum size requirements
        if processed_table and len(processed_table) >= min_rows and any(len(r) >= min_columns for r in processed_table):
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
    Extract raw table structure including rowspan and colspan attributes using BeautifulSoup.
    
    Args:
        table_content: HTML content inside <table> tags
        
    Returns:
        List of rows, where each row contains a list of cell dictionaries with
        content, rowspan, and colspan information
    """
    raw_rows = []
    
    # Create a BeautifulSoup object from the table content
    soup = BeautifulSoup(table_content, 'html.parser')
    
    # Process all rows from the table, whether in thead or tbody
    # If there's no explicit thead or tbody, BeautifulSoup will find tr elements directly
    for row in soup.find_all('tr'):
        cells = []
        
        # Process each cell (th or td)
        for cell in row.find_all(['td', 'th']):
            # Get cell type
            cell_type = cell.name
            
            # Extract rowspan and colspan attributes
            rowspan = 1
            if cell.has_attr('rowspan'):
                try:
                    rowspan = int(cell['rowspan'])
                except (ValueError, TypeError):
                    pass  # Keep default value if conversion fails
            
            colspan = 1
            if cell.has_attr('colspan'):
                try:
                    colspan = int(cell['colspan'])
                except (ValueError, TypeError):
                    pass  # Keep default value if conversion fails
            
            # Clean the content
            clean_content = clean_cell_content(str(cell.decode_contents()))
            
            # Store cell with its span information
            cells.append({
                'content': clean_content,
                'rowspan': rowspan,
                'colspan': colspan,
                'is_header': cell_type == 'th'
            })
        
        # Add row if it has cells
        if cells:
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
            # Clean the header using BeautifulSoup
            soup = BeautifulSoup(f"<span>{header}</span>", 'html.parser')
            clean_header = soup.get_text()
            # Remove any remaining special characters
            clean_header = re.sub(r'[^\w\s]', '', clean_header)
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
                                      min_columns: int = 1,
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
