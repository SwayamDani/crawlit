#!/usr/bin/env python3
"""
Test module for table extraction functionality
"""

import pytest
import os
import tempfile
import csv
import json
import re
from pathlib import Path

from crawlit.extractors.tables import (
    extract_tables, 
    tables_to_csv, 
    tables_to_dict, 
    tables_to_json, 
    filter_tables,
    clean_cell_content,
    get_url_safe_filename,
    extract_and_save_tables_from_crawl
)

# Sample HTML with simple table
SIMPLE_TABLE_HTML = """
<html>
    <body>
        <table>
            <tr>
                <th>Name</th>
                <th>Age</th>
                <th>City</th>
            </tr>
            <tr>
                <td>John</td>
                <td>28</td>
                <td>New York</td>
            </tr>
            <tr>
                <td>Jane</td>
                <td>32</td>
                <td>Chicago</td>
            </tr>
        </table>
    </body>
</html>
"""

# HTML with complex tables including rowspan and colspan
COMPLEX_TABLE_HTML = """
<html>
    <body>
        <table>
            <thead>
                <tr>
                    <th rowspan="2">Product</th>
                    <th colspan="2">Sales</th>
                    <th rowspan="2">Total</th>
                </tr>
                <tr>
                    <th>Q1</th>
                    <th>Q2</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>Widget A</td>
                    <td>150</td>
                    <td>200</td>
                    <td>350</td>
                </tr>
                <tr>
                    <td>Widget B</td>
                    <td>100</td>
                    <td>125</td>
                    <td>225</td>
                </tr>
            </tbody>
        </table>
    </body>
</html>
"""

# HTML with multiple tables
MULTIPLE_TABLES_HTML = """
<html>
    <body>
        <h1>User Information</h1>
        <table id="userTable">
            <tr>
                <th>User ID</th>
                <th>Username</th>
                <th>Email</th>
            </tr>
            <tr>
                <td>1</td>
                <td>johndoe</td>
                <td>john@example.com</td>
            </tr>
            <tr>
                <td>2</td>
                <td>janedoe</td>
                <td>jane@example.com</td>
            </tr>
        </table>
        
        <h1>Product Information</h1>
        <table id="productTable">
            <tr>
                <th>Product ID</th>
                <th>Product Name</th>
                <th>Price</th>
            </tr>
            <tr>
                <td>101</td>
                <td>Laptop</td>
                <td>$999.99</td>
            </tr>
            <tr>
                <td>102</td>
                <td>Smartphone</td>
                <td>$499.99</td>
            </tr>
        </table>
    </body>
</html>
"""

# HTML with nested tables
NESTED_TABLES_HTML = """
<html>
    <body>
        <table id="outerTable">
            <tr>
                <th>Category</th>
                <th>Details</th>
            </tr>
            <tr>
                <td>Electronics</td>
                <td>
                    <table id="innerTable">
                        <tr>
                            <th>Item</th>
                            <th>Price</th>
                        </tr>
                        <tr>
                            <td>TV</td>
                            <td>$799</td>
                        </tr>
                        <tr>
                            <td>Radio</td>
                            <td>$49</td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
</html>
"""

# HTML with malformed tables
MALFORMED_TABLE_HTML = """
<html>
    <body>
        <table>
            <tr>
                <th>Header 1</th>
                <th>Header 2</th>
            </tr>
            <tr>
                <td>Data 1</td>
                <td>Data 2</td>
            </tr>
            <tr>
                <td>Data 3</td>
                <td>Data 4</td>
                <td>Extra column</td>
            </tr>
        </table>
    </body>
</html>
"""

# HTML with empty tables
EMPTY_TABLE_HTML = """
<html>
    <body>
        <table></table>
        <table>
            <tr></tr>
        </table>
        <table>
            <thead></thead>
            <tbody></tbody>
        </table>
    </body>
</html>
"""

# HTML with tables containing special characters and HTML entities
SPECIAL_CHARS_TABLE_HTML = """
<html>
    <body>
        <table>
            <tr>
                <th>Symbol</th>
                <th>Description</th>
            </tr>
            <tr>
                <td>&lt; &gt; &amp; &quot; &apos;</td>
                <td>HTML entities</td>
            </tr>
            <tr>
                <td>€ £ ¥ ₹</td>
                <td>Currency symbols</td>
            </tr>
            <tr>
                <td>α β γ δ</td>
                <td>Greek letters</td>
            </tr>
            <tr>
                <td>Café Résumé Señor</td>
                <td>Accented characters</td>
            </tr>
        </table>
    </body>
</html>
"""

# Mock crawl results for testing extract_and_save_tables_from_crawl function
MOCK_CRAWL_RESULTS = {
    "https://example.com": {
        "html_content": SIMPLE_TABLE_HTML,
        "depth": 0
    },
    "https://example.com/page1": {
        "html_content": COMPLEX_TABLE_HTML,
        "depth": 1
    },
    "https://example.com/page2": {
        "html_content": MULTIPLE_TABLES_HTML,
        "depth": 1
    },
    "https://example.com/page3": {
        "html_content": "<html><body><p>No tables here</p></body></html>",
        "depth": 2
    }
}


class TestTableExtractor:
    """Test suite for the table extraction functionality"""
    
    def test_extract_simple_table(self):
        """Test extraction of a simple table with no special attributes"""
        tables = extract_tables(SIMPLE_TABLE_HTML)
        
        # Check that we got the expected table
        assert len(tables) == 1
        
        # Check rows and columns
        table = tables[0]
        assert len(table) == 3  # Header row + 2 data rows
        assert len(table[0]) == 3  # 3 columns
        
        # Check header and data content
        assert table[0] == ["Name", "Age", "City"]
        assert table[1] == ["John", "28", "New York"]
        assert table[2] == ["Jane", "32", "Chicago"]
    
    def test_extract_complex_table(self):
        """Test extraction of a complex table with rowspan and colspan attributes"""
        tables = extract_tables(COMPLEX_TABLE_HTML)
        
        # Check that we got the expected table
        assert len(tables) == 1
        
        # Check the table structure after rowspan/colspan processing
        table = tables[0]
        
        # The table should have 4 rows: 2 header rows (from thead) + 2 data rows (from tbody)
        assert len(table) == 4
        
        # First row should have 4 columns (Product, Sales (spanning 2 cols), Total)
        assert len(table[0]) == 4
        assert table[0][0] == "Product"
        assert table[0][1] == "Sales"  # colspan=2 cell
        assert table[0][2] == ""       # Empty cell due to colspan
        assert table[0][3] == "Total"
        
        # Second row should have 4 columns (empty due to rowspan, Q1, Q2, empty due to rowspan)
        assert len(table[1]) == 4
        assert table[1][0] == ""  # Empty due to rowspan from "Product"
        assert table[1][1] == "Q1"
        assert table[1][2] == "Q2"
        assert table[1][3] == ""  # Empty due to rowspan from "Total"
        
        # Check data rows
        assert table[2] == ["Widget A", "150", "200", "350"]
        assert table[3] == ["Widget B", "100", "125", "225"]
    
    def test_extract_multiple_tables(self):
        """Test extraction of multiple tables from a single HTML document"""
        tables = extract_tables(MULTIPLE_TABLES_HTML)
        
        # Check that we got two tables
        assert len(tables) == 2
        
        # Check first table (User Information)
        user_table = tables[0]
        assert len(user_table) == 3  # Header + 2 data rows
        assert user_table[0] == ["User ID", "Username", "Email"]
        assert user_table[1] == ["1", "johndoe", "john@example.com"]
        assert user_table[2] == ["2", "janedoe", "jane@example.com"]
        
        # Check second table (Product Information)
        product_table = tables[1]
        assert len(product_table) == 3  # Header + 2 data rows
        assert product_table[0] == ["Product ID", "Product Name", "Price"]
        assert product_table[1] == ["101", "Laptop", "$999.99"]
        assert product_table[2] == ["102", "Smartphone", "$499.99"]
    
    def test_extract_nested_tables(self):
        """Test extraction of nested tables"""
        tables = extract_tables(NESTED_TABLES_HTML)
        
        # The current implementation merges nested tables rather than extracting them separately
        assert len(tables) == 1
        
        # Check the merged table structure
        merged_table = tables[0]
        
        # The merged table should have 4 rows: header row + 3 data rows (combined from both tables)
        assert len(merged_table) >= 4
        
        # First row should be the outer table header
        assert merged_table[0][0] == "Category"
        assert merged_table[0][1] == "Details"
        
        # We should see the inner table data has been merged into the outer table structure
        # Check for inner table content somewhere in the table
        inner_table_data_found = False
        for row in merged_table:
            if "TV" in row and "$799" in row:
                inner_table_data_found = True
                break
        
        assert inner_table_data_found, "Inner table data not found in the merged table"
    
    def test_filter_tables(self):
        """Test filtering tables based on size criteria"""
        # Create sample tables of different sizes
        small_table = [["Header"], ["Data"]]
        medium_table = [["H1", "H2"], ["D1", "D2"], ["D3", "D4"]]
        large_table = [["H1", "H2", "H3"], ["D1", "D2", "D3"], ["D4", "D5", "D6"]]
        uneven_table = [["H1", "H2", "H3"], ["D1"], ["D4", "D5"]]
        
        tables = [small_table, medium_table, large_table, uneven_table]
        
        # Test with min_rows=3, min_cols=2
        filtered = filter_tables(tables, min_rows=3, min_cols=2)
        assert len(filtered) == 3  # medium_table, large_table and uneven_table meet criteria
        assert filtered[0] == medium_table
        assert filtered[1] == large_table
        assert filtered[2] == uneven_table  # uneven_table has 3 rows and at least one row has 2+ columns
        
        # Test with min_rows=3, min_cols=3
        filtered = filter_tables(tables, min_rows=3, min_cols=3)
        assert len(filtered) == 2  # large_table and uneven_table meet criteria
        assert large_table in filtered
        assert uneven_table in filtered  # uneven_table has at least one row with 3+ columns
        
        # Test with min_rows=2, min_cols=2
        filtered = filter_tables(tables, min_rows=2, min_cols=2)
        assert len(filtered) == 3  # small_table fails, others pass
        
        # Test with min_rows=1, min_cols=1 (all should pass)
        filtered = filter_tables(tables, min_rows=1, min_cols=1)
        assert len(filtered) == 4
    
    def test_extract_malformed_table(self):
        """Test handling of malformed tables"""
        tables = extract_tables(MALFORMED_TABLE_HTML)
        
        # Should still extract the table despite minor malformation (extra column in a row)
        assert len(tables) == 1
        
        table = tables[0]
        # Check that we have some rows at least
        assert len(table) > 0
        
        # First row should have headers
        assert "Header 1" in table[0]
        
        # The extractor should handle the row with an extra column
        assert len(table) >= 3  # Should have at least 3 rows
        
        # Test with more severely malformed HTML
        severely_malformed_html = """
        <html>
            <body>
                <table>
                    <tr>
                        <th>Header 1
                    <tr>
                        <td>Data 1
                </table>
            </body>
        </html>
        """
        
        # The extractor might skip severely malformed tables or handle them gracefully
        try:
            severe_tables = extract_tables(severely_malformed_html)
            # We don't assert on the number of tables extracted, just ensure no crash
        except Exception as e:
            pytest.fail(f"Table extractor crashed on severely malformed HTML: {str(e)}")
    
    def test_empty_tables(self):
        """Test handling of empty tables"""
        tables = extract_tables(EMPTY_TABLE_HTML)
        
        # The module might extract empty table structures or skip them
        # The important thing is that it doesn't crash
        
        # If empty tables are extracted, they should be properly structured
        if tables:
            for table in tables:
                # Each table should be a list (possibly empty)
                assert isinstance(table, list)
    
    def test_special_characters(self):
        """Test handling of special characters and HTML entities in tables"""
        tables = extract_tables(SPECIAL_CHARS_TABLE_HTML)
        
        assert len(tables) == 1
        table = tables[0]
        
        # Check that HTML entities are properly decoded
        assert "< > & \" '" in table[1][0]
        
        # Check that special characters are preserved
        assert "€ £ ¥ ₹" in table[2][0]
        assert "α β γ δ" in table[3][0]
        assert "Café Résumé Señor" in table[4][0]
    
    def test_clean_cell_content(self):
        """Test the clean_cell_content function with various inputs"""
        # Test HTML entity decoding
        assert clean_cell_content("&lt;script&gt;") == "<script>"
        
        # Test HTML tag removal
        assert clean_cell_content("<b>Bold</b> text") == "Bold text"
        
        # Test handling references like [1], common in Wikipedia tables
        assert clean_cell_content("Content[1][2]") == "Content"
        
        # Test handling non-breaking spaces
        assert clean_cell_content("Space\xa0between") == "Space between"
        
        # Test normalizing whitespace
        assert clean_cell_content("Multiple    spaces\n\nand\t\ttabs") == "Multiple spaces and tabs"
    
    def test_tables_to_csv(self):
        """Test conversion of tables to CSV files"""
        tables = extract_tables(SIMPLE_TABLE_HTML)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Convert to CSV
            csv_files = tables_to_csv(tables, "test_table", output_dir=tmpdir)
            
            # Check that files were created
            assert len(csv_files) == len(tables)
            assert os.path.exists(csv_files[0])
            
            # Verify CSV content
            with open(csv_files[0], 'r', newline='', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)
                rows = list(reader)
                
                # Check content against original table
                assert rows[0] == tables[0][0]  # Header row
                assert rows[1] == tables[0][1]  # First data row
                assert rows[2] == tables[0][2]  # Second data row
    
    def test_tables_to_dict(self):
        """Test conversion of tables to dictionary format"""
        tables = extract_tables(SIMPLE_TABLE_HTML)
        dict_tables = tables_to_dict(tables)
        
        # Should have the same number of tables
        assert len(dict_tables) == len(tables)
        
        # Check dictionary structure for first table
        dict_table = dict_tables[0]
        
        # Should have 2 rows (not counting header)
        assert len(dict_table) == 2
        
        # Check structure of first row
        first_row = dict_table[0]
        assert isinstance(first_row, dict)
        
        # Keys should be lowercase, underscored versions of headers
        assert "name" in first_row
        assert "age" in first_row
        assert "city" in first_row
        
        # Check values
        assert first_row["name"] == "John"
        assert first_row["age"] == "28"
        assert first_row["city"] == "New York"
    
    def test_tables_to_json(self):
        """Test conversion of tables to JSON files"""
        tables = extract_tables(SIMPLE_TABLE_HTML)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Convert to JSON
            json_files = tables_to_json(tables, "test_table", output_dir=tmpdir)
            
            # Check that files were created
            assert len(json_files) == len(tables)
            assert os.path.exists(json_files[0])
            
            # Verify JSON content
            with open(json_files[0], 'r', encoding='utf-8') as jsonfile:
                data = json.load(jsonfile)
                
                # Check structure
                assert "headers" in data
                assert "data" in data
                
                # Check content
                assert data["headers"] == tables[0][0]  # Header row
                assert len(data["data"]) == 2  # Two data rows
                
                # Check first data row
                first_row = data["data"][0]
                assert first_row["Name"] == "John"
                assert first_row["Age"] == "28"
                assert first_row["City"] == "New York"
    
    def test_get_url_safe_filename(self):
        """Test generation of safe filenames from URLs"""
        # Test basic URL
        url = "https://example.com/page"
        filename = get_url_safe_filename(url, depth=1)
        assert "example_com" in filename
        assert "page" in filename
        assert "depth1" in filename
        
        # Test URL with query parameters
        url = "https://example.com/search?q=test&page=2"
        filename = get_url_safe_filename(url, depth=2)
        assert "example_com" in filename
        assert "search" in filename
        assert "depth2" in filename
        
        # Test URL with long path (should be truncated)
        long_path = "/".join([f"segment{i}" for i in range(20)])
        url = f"https://example.com/{long_path}"
        filename = get_url_safe_filename(url, depth=0)
        assert len(filename) < len(url)  # Should be truncated
        assert "example_com" in filename
        assert "depth0" in filename
    
    def test_extract_and_save_tables_from_crawl(self):
        """Test extracting and saving tables from crawl results"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Run extraction from mock crawl results
            stats = extract_and_save_tables_from_crawl(
                MOCK_CRAWL_RESULTS,
                output_dir=tmpdir,
                output_format="csv",
                min_rows=2,
                min_columns=2
            )
            
            # Check statistics
            assert stats["total_pages_with_tables"] > 0
            assert stats["total_tables_found"] > 0
            assert stats["total_files_saved"] > 0
            assert len(stats["urls_with_tables"]) > 0
            assert 0 in stats["tables_by_depth"]  # Depth 0
            assert 1 in stats["tables_by_depth"]  # Depth 1
            
            # Check that files were created
            files = os.listdir(tmpdir)
            assert len(files) > 0
            assert all(file.endswith('.csv') for file in files)
            
            # Run again with JSON format
            stats_json = extract_and_save_tables_from_crawl(
                MOCK_CRAWL_RESULTS,
                output_dir=tmpdir,
                output_format="json",
                min_rows=2,
                min_columns=2
            )
            
            # Check that JSON files were created
            files = os.listdir(tmpdir)
            assert any(file.endswith('.json') for file in files)
    
    def test_table_extraction_performance(self):
        """Test performance with a large HTML document containing many tables"""
        # Generate a large HTML document with multiple tables
        large_html = "<html><body>"
        for i in range(10):  # 10 tables
            large_html += f"<table id='table{i}'><tr><th>Header 1</th><th>Header 2</th></tr>"
            for j in range(50):  # 50 rows per table
                large_html += f"<tr><td>Data {i}-{j}-1</td><td>Data {i}-{j}-2</td></tr>"
            large_html += "</table>"
        large_html += "</body></html>"
        
        # Measure extraction time
        import time
        start_time = time.time()
        tables = extract_tables(large_html)
        end_time = time.time()
        
        # Assert that extraction completes in a reasonable time (adjust as needed)
        assert end_time - start_time < 10, "Table extraction took too long"
        
        # Check that we got all tables
        assert len(tables) == 10
        
        # Check that each table has the expected number of rows
        for table in tables:
            assert len(table) == 51  # 1 header + 50 data rows


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
