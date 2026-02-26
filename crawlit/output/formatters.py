#!/usr/bin/env python3
"""
formatters.py - Output formatters for crawler results
"""

import json
import csv
import html as _html
import os
import datetime
from pathlib import Path

_BLOCKED_SCHEMES = ('javascript:', 'data:', 'vbscript:')


def _safe_href(url: object) -> str:
    """Return an HTML-attribute-safe href value, blocking dangerous URL schemes."""
    s = str(url).lstrip()
    if s.lower().startswith(_BLOCKED_SCHEMES):
        return '#'
    return _html.escape(str(url))


def create_output_file(output_path):
    """Create directory for output file if it doesn't exist.
    
    Args:
        output_path (str): Path to the output file.
    """
    # Get the directory part of the file path
    output_dir = os.path.dirname(output_path)
    
    # If there's a directory component and it doesn't exist, create it
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)


def save_results(results, output_format=None, output_file=None, pretty_json=False, format_type=None, pretty=None):
    """Save crawler results to specified file in the requested format.
    
    This function takes the crawler results and saves them to a file in the specified format.
    It supports JSON, CSV, TXT, and HTML output formats.
    
    Args:
        results (dict): Crawler results dictionary containing URL data.
        output_format (str, optional): Format to save results in (json, csv, txt, html). 
            If None, will use the file extension or default to JSON.
        output_file (str, optional): Path to the output file. If None, prints to stdout.
        pretty_json (bool, optional): Whether to format JSON with indentation. Defaults to False.
        format_type (str, optional): Alternative name for output_format (for backward compatibility).
        pretty (bool, optional): Alternative name for pretty_json (for backward compatibility).
        
    Returns:
        bool: True if saving was successful, False otherwise.
    
    Raises:
        ValueError: If an unsupported output format is specified.
    pretty: Alternative name for pretty_json (for backward compatibility)
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Handle parameter aliasing (support both format_type and output_format)
    if format_type is not None and output_format is None:
        output_format = format_type
    
    # Handle pretty parameter (tests use pretty instead of pretty_json)
    if pretty is not None and pretty_json is False:
        pretty_json = pretty
    
    # Default filename if not specified
    if output_file is None:
        # Tests expect 'crawl_results.json' as default
        output_file = f"crawl_results.{output_format.lower()}"
    
    # Make sure the output directory exists
    create_output_file(output_file)
    
    # Choose the appropriate formatter based on format
    if output_format.lower() == "json":
        save_as_json(results, output_file, timestamp, pretty_json)
    elif output_format.lower() == "csv":
        save_as_csv(results, output_file, timestamp)
    elif output_format.lower() == "txt":
        save_as_txt(results, output_file, timestamp)
    elif output_format.lower() == "html":
        save_as_html(results, output_file, timestamp)
    else:
        raise ValueError(f"Unsupported output format: {output_format}")
    
    # Return the path to the file that was created
    return output_file


def save_as_json(results, output_file, timestamp, pretty_json=False):
    """Save crawler results in JSON format"""
    # Create a clean copy of results without HTML content
    clean_results = {}
    for url, data in results.items():
        # Create a copy of the data without html_content
        clean_data = {k: v for k, v in data.items() if k != 'html_content'}
        clean_results[url] = clean_data
    
    # Create output data structure with metadata and results
    output_data = {
        "metadata": {
            "timestamp": timestamp,
            "total_urls": len(results)
        },
        "urls": clean_results
    }
    
    # Write to file with nice formatting
    with open(output_file, 'w', encoding='utf-8') as f:
        if pretty_json:
            json.dump(output_data, f, indent=2, sort_keys=True)
        else:
            json.dump(output_data, f)


def save_as_csv(results, output_file, timestamp):
    """Save crawler results in CSV format"""
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Write header
        writer.writerow(['URL', 'Status', 'Depth', 'Content Type', 'Links Found', 'Success', 'Error', 'Images Found', 'Keywords Found', 'Key Phrases Found', 'Tables Found'])
        
        # Write data rows
        for url, data in results.items():
            images_count = len(data.get('images', []))
            keywords_count = len(data.get('keywords', []))
            keyphrases_count = len(data.get('keyphrases', []))
            tables_count = len(data.get('tables', []))
            
            writer.writerow([
                url,
                data.get('status', 'N/A'),
                data.get('depth', 'N/A'),
                data.get('content_type', 'N/A'),
                len(data.get('links', [])),
                data.get('success', False),
                data.get('error', ''),
                images_count,
                keywords_count,
                keyphrases_count,
                tables_count
            ])
        
        # Write detailed data for images, keywords, etc. after basic info
        writer.writerow([])
        writer.writerow(['# DETAILED DATA'])
        
        for url, data in results.items():
            # Images
            if 'images' in data and data['images']:
                writer.writerow([])
                writer.writerow([f'# Images for {url}'])
                writer.writerow(['Image Source', 'Alt Text', 'Width', 'Height', 'Class'])
                for img in data['images']:
                    writer.writerow([
                        img.get('src', 'N/A'),
                        img.get('alt', 'N/A'),
                        img.get('width', 'N/A'),
                        img.get('height', 'N/A'),
                        img.get('class', 'N/A')
                    ])
            
            # Keywords
            if 'keywords' in data and data['keywords']:
                writer.writerow([])
                writer.writerow([f'# Keywords for {url}'])
                writer.writerow(['Keyword', 'Score'])
                
                keywords = data['keywords']
                keyword_scores = data.get('keyword_scores', {})
                
                for keyword in keywords:
                    score = keyword_scores.get(keyword, 'N/A')
                    writer.writerow([keyword, score])
            
            # Key Phrases
            if 'keyphrases' in data and data['keyphrases']:
                writer.writerow([])
                writer.writerow([f'# Key Phrases for {url}'])
                for phrase in data['keyphrases']:
                    writer.writerow([phrase])
            
            # Tables (in a simplified format)
            if 'tables' in data and data['tables']:
                writer.writerow([])
                writer.writerow([f'# Tables for {url}'])
                for i, table in enumerate(data['tables']):
                    writer.writerow([f'Table {i+1}'])
                    for row in table:
                        writer.writerow(row)
                    writer.writerow([])
        
        # Write metadata at the end
        writer.writerow([])
        writer.writerow(['# Generated at:', timestamp])
        writer.writerow(['# Total URLs:', len(results)])


def save_as_txt(results, output_file, timestamp):
    """Save crawler results in plain text format"""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"Crawl Results - Generated at {timestamp}\n")
        f.write(f"Total URLs: {len(results)}\n")
        f.write("=" * 80 + "\n\n")
        
        # Write one entry per URL
        for url, data in results.items():
            f.write(f"URL: {url}\n")
            f.write(f"Status: {data.get('status', 'N/A')}\n")
            f.write(f"Depth: {data.get('depth', 'N/A')}\n")
            f.write(f"Content Type: {data.get('content_type', 'N/A')}\n")
            f.write(f"Success: {data.get('success', False)}\n")
            
            # Show error if there was one
            if data.get('error'):
                f.write(f"Error: {data.get('error')}\n")
            
            # Show found links
            links = data.get('links', [])
            f.write(f"Links Found: {len(links)}\n")
            
            # Write the first few links if there are any
            if links:
                f.write("Sample Links:\n")
                for link in links[:5]:  # Show at most 5 links
                    f.write(f"  - {link}\n")
                
                if len(links) > 5:
                    f.write(f"  - ... and {len(links) - 5} more\n")
            
            # Add images information
            images = data.get('images', [])
            f.write(f"Images Found: {len(images)}\n")
            if images:
                f.write("Sample Images:\n")
                for img in images[:3]:  # Show at most 3 images
                    src = img.get('src', 'No source')
                    alt = img.get('alt', 'No alt text')
                    f.write(f"  - {src} (Alt: {alt})\n")
                
                if len(images) > 3:
                    f.write(f"  - ... and {len(images) - 3} more\n")
            
            # Add keywords information
            keywords = data.get('keywords', [])
            f.write(f"Keywords Found: {len(keywords)}\n")
            if keywords:
                f.write("Top Keywords:\n")
                # Get top 5 keywords with scores if available
                keyword_scores = data.get('keyword_scores', {})
                if keyword_scores and len(keywords) > 0:
                    sorted_keywords = sorted(keyword_scores.items(), key=lambda x: x[1], reverse=True)
                    for keyword, score in sorted_keywords[:5]:
                        f.write(f"  - {keyword} (Score: {score:.4f})\n")
                else:
                    for keyword in keywords[:5]:
                        f.write(f"  - {keyword}\n")
                
                if len(keywords) > 5:
                    f.write(f"  - ... and {len(keywords) - 5} more\n")
            
            # Add keyphrases
            keyphrases = data.get('keyphrases', [])
            f.write(f"Key Phrases Found: {len(keyphrases)}\n")
            if keyphrases:
                f.write("Sample Key Phrases:\n")
                for phrase in keyphrases[:5]:  # Show at most 5 keyphrases
                    f.write(f"  - {phrase}\n")
                
                if len(keyphrases) > 5:
                    f.write(f"  - ... and {len(keyphrases) - 5} more\n")
            
            # Add tables information
            tables = data.get('tables', [])
            f.write(f"Tables Found: {len(tables)}\n")
            if tables and len(tables) > 0:
                f.write("Sample Table Structure:\n")
                if len(tables) > 0 and len(tables[0]) > 0:
                    sample_table = tables[0]
                    max_rows = min(3, len(sample_table))
                    for i in range(max_rows):
                        row = sample_table[i]
                        max_cols = min(3, len(row))
                        f.write("  | " + " | ".join(str(cell) for cell in row[:max_cols]))
                        if len(row) > 3:
                            f.write(" | ... ")
                        f.write(" |\n")
                    
                    if len(sample_table) > 3:
                        f.write("  | ... |\n")
                    
                if len(tables) > 1:
                    f.write(f"  ... and {len(tables) - 1} more tables\n")
            
            f.write("\n" + "-" * 40 + "\n\n")


def save_as_html(results, output_file, timestamp):
    """Save crawler results in HTML format"""
    # Create HTML structure with a basic responsive design
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Crawlit Results - {timestamp}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            color: #333;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        header {{
            background-color: #f4f4f4;
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 5px;
        }}
        h1 {{
            margin: 0;
            color: #2c3e50;
        }}
        .summary {{
            background-color: #ecf0f1;
            padding: 15px;
            margin-bottom: 20px;
            border-left: 4px solid #3498db;
            border-radius: 0 5px 5px 0;
        }}
        .url-card {{
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 15px;
            margin-bottom: 15px;
            background-color: white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .url-card h3 {{
            margin-top: 0;
            word-break: break-all;
        }}
        .status-success {{
            color: #27ae60;
            font-weight: bold;
        }}
        .status-error {{
            color: #c0392b;
            font-weight: bold;
        }}
        .details {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 10px;
            margin-bottom: 10px;
        }}
        .detail-item {{
            padding: 5px;
        }}
        .links-list {{
            background-color: #f9f9f9;
            padding: 10px;
            border-radius: 5px;
            max-height: 200px;
            overflow-y: auto;
        }}
        footer {{
            text-align: center;
            margin-top: 30px;
            color: #7f8c8d;
            font-size: 0.9rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Crawlit Results</h1>
            <p>Generated at: {timestamp}</p>
        </header>
        
        <div class="summary">
            <h2>Crawl Summary</h2>
            <p>Total URLs: <strong>{len(results)}</strong></p>
            <p>Successful requests: <strong>{sum(1 for data in results.values() if data.get('success', False))}</strong></p>
            <p>Failed requests: <strong>{sum(1 for data in results.values() if not data.get('success', False))}</strong></p>
        </div>
        
        <h2>Results by URL</h2>
"""
    
    # Add each URL as a card
    for url, data in results.items():
        status = data.get('status', 'N/A')
        success = data.get('success', False)
        depth = data.get('depth', 'N/A')
        content_type = data.get('content_type', 'N/A')
        error = data.get('error', '')
        links = data.get('links', [])

        status_class = "status-success" if success else "status-error"

        html += f"""
        <div class="url-card">
            <h3>{_html.escape(str(url))}</h3>
            <div class="details">
                <div class="detail-item">
                    <strong>Status:</strong> <span class="{status_class}">{_html.escape(str(status))}</span>
                </div>
                <div class="detail-item">
                    <strong>Depth:</strong> {_html.escape(str(depth))}
                </div>
                <div class="detail-item">
                    <strong>Content Type:</strong> {_html.escape(str(content_type))}
                </div>
                <div class="detail-item">
                    <strong>Success:</strong> {_html.escape(str(success))}
                </div>
            </div>
"""

        # Add error if there is one
        if error:
            html += f"""
            <div class="detail-item">
                <strong>Error:</strong> <span class="status-error">{_html.escape(str(error))}</span>
            </div>
"""

        # Add links if there are any
        if links:
            html += f"""
            <div>
                <strong>Links Found:</strong> {len(links)}
                <div class="links-list">
                    <ul>
"""
            # Show all links in HTML
            for link in links:
                safe_link_href = _safe_href(link)
                escaped_link = _html.escape(str(link))
                html += f'                        <li><a href="{safe_link_href}" target="_blank">{escaped_link}</a></li>\n'

            html += """
                    </ul>
                </div>
            </div>
"""

        # Add images if there are any
        images = data.get('images', [])
        if images:
            html += f"""
            <div>
                <strong>Images Found:</strong> {len(images)}
                <div class="links-list">
                    <table style="width:100%; border-collapse: collapse;">
                        <tr>
                            <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Source</th>
                            <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Alt Text</th>
                            <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Dimensions</th>
                        </tr>
"""
            for img in images:
                src = img.get('src', 'No source')
                alt = img.get('alt', 'No alt text')
                width = img.get('width', 'N/A')
                height = img.get('height', 'N/A')
                dimensions = f"{width}x{height}" if width != 'N/A' and height != 'N/A' else 'N/A'
                safe_src_href = _safe_href(src)
                escaped_src = _html.escape(str(src))
                escaped_alt = _html.escape(str(alt))
                escaped_dim = _html.escape(str(dimensions))
                escaped_basename = _html.escape(str(src).split('/')[-1])

                html += f"""
                        <tr>
                            <td style="border: 1px solid #ddd; padding: 8px;"><a href="{safe_src_href}" target="_blank">{escaped_basename}</a></td>
                            <td style="border: 1px solid #ddd; padding: 8px;">{escaped_alt}</td>
                            <td style="border: 1px solid #ddd; padding: 8px;">{escaped_dim}</td>
                        </tr>
"""

            html += """
                    </table>
                </div>
            </div>
"""

        # Add keywords if there are any
        keywords = data.get('keywords', [])
        keyword_scores = data.get('keyword_scores', {})
        if keywords:
            html += f"""
            <div>
                <strong>Keywords Found:</strong> {len(keywords)}
                <div class="links-list">
                    <table style="width:100%; border-collapse: collapse;">
                        <tr>
                            <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Keyword</th>
                            <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Score</th>
                        </tr>
"""
            for keyword in keywords:
                score = keyword_scores.get(keyword, 'N/A')
                html += f"""
                        <tr>
                            <td style="border: 1px solid #ddd; padding: 8px;">{_html.escape(str(keyword))}</td>
                            <td style="border: 1px solid #ddd; padding: 8px;">{_html.escape(str(score))}</td>
                        </tr>
"""

            html += """
                    </table>
                </div>
            </div>
"""

        # Add key phrases if there are any
        keyphrases = data.get('keyphrases', [])
        if keyphrases:
            html += f"""
            <div>
                <strong>Key Phrases Found:</strong> {len(keyphrases)}
                <div class="links-list">
                    <ul>
"""
            for phrase in keyphrases:
                html += f'                        <li>{_html.escape(str(phrase))}</li>\n'

            html += """
                    </ul>
                </div>
            </div>
"""

        # Add tables if there are any
        tables = data.get('tables', [])
        if tables:
            html += f"""
            <div>
                <strong>Tables Found:</strong> {len(tables)}
                <div class="links-list">
"""
            for i, table in enumerate(tables):
                html += f"""
                    <h4>Table {i+1}</h4>
                    <table style="width:100%; border-collapse: collapse;">
"""
                for row in table:
                    html += """
                        <tr>
"""
                    for cell in row:
                        html += f"""
                            <td style="border: 1px solid #ddd; padding: 8px;">{_html.escape(str(cell))}</td>
"""
                    html += """
                        </tr>
"""
                html += """
                    </table>
                    <br>
"""

            html += """
                </div>
            </div>
"""
        
        html += """
        </div>
"""
    
    # Close HTML structure
    html += """
        <footer>
            <p>Generated by Crawlit - A Modular, Ethical Python Web Crawler</p>
        </footer>
    </div>
</body>
</html>
"""
    
    # Write HTML to file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)


def generate_summary_report(results):
    """Generate a pretty CLI summary of crawl results"""
    success_count = sum(1 for data in results.values() if data.get('success', False))
    failed_count = len(results) - success_count
    link_count = sum(len(data.get('links', [])) for data in results.values())
    
    depths = {}
    for data in results.values():
        depth = data.get('depth', 0)
        depths[depth] = depths.get(depth, 0) + 1
    
    summary = [
        "Crawl Summary",
        "=" * 40,
        # Change wording to match test expectations
        f"Total URLs crawled: {len(results)}",
        f"Successful requests: {success_count}",
        f"Failed requests: {failed_count}",
        f"Total links discovered: {link_count}",
        "",
        "URLs by depth:",
    ]
    
    for depth in sorted(depths.keys()):
        summary.append(f"  Depth {depth}: {depths[depth]} URLs")
    
    return "\n" .join(summary)