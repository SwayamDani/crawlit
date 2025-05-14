#!/usr/bin/env python3
"""
formatters.py - Output formatters for crawler results
"""

import json
import csv
import os
import datetime
from pathlib import Path


def create_output_file(output_path):
    """Create directory for output file if it doesn't exist"""
    # Get the directory part of the file path
    output_dir = os.path.dirname(output_path)
    
    # If there's a directory component and it doesn't exist, create it
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)


def save_results(results, output_format=None, output_file=None, pretty_json=False, format_type=None, pretty=None):
    """Save crawler results to specified file in the requested format
    
    Args:
        results: Crawler results dictionary
        output_format: Format to save results in (json, csv, txt, html)
        output_file: Path to the output file
        pretty_json: Whether to format JSON with indentation
        format_type: Alternative name for output_format (for backward compatibility)
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
    # Create output data structure with metadata and results
    output_data = {
        "metadata": {
            "timestamp": timestamp,
            "total_urls": len(results)
        },
        "urls": results
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
        writer.writerow(['URL', 'Status', 'Depth', 'Content Type', 'Links Found', 'Success', 'Error'])
        
        # Write data rows
        for url, data in results.items():
            writer.writerow([
                url,
                data.get('status', 'N/A'),
                data.get('depth', 'N/A'),
                data.get('content_type', 'N/A'),
                len(data.get('links', [])),
                data.get('success', False),
                data.get('error', '')
            ])
        
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
            <h3>{url}</h3>
            <div class="details">
                <div class="detail-item">
                    <strong>Status:</strong> <span class="{status_class}">{status}</span>
                </div>
                <div class="detail-item">
                    <strong>Depth:</strong> {depth}
                </div>
                <div class="detail-item">
                    <strong>Content Type:</strong> {content_type}
                </div>
                <div class="detail-item">
                    <strong>Success:</strong> {success}
                </div>
            </div>
"""

        # Add error if there is one
        if error:
            html += f"""
            <div class="detail-item">
                <strong>Error:</strong> <span class="status-error">{error}</span>
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
                html += f'                        <li><a href="{link}" target="_blank">{link}</a></li>\n'
                
            html += """
                    </ul>
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