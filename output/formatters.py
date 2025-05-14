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


def save_results(results, output_format, output_file):
    """Save crawler results to specified file in the requested format"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Make sure the output directory exists
    create_output_file(output_file)
    
    # Choose the appropriate formatter based on format
    if output_format.lower() == "json":
        save_as_json(results, output_file, timestamp)
    elif output_format.lower() == "csv":
        save_as_csv(results, output_file, timestamp)
    elif output_format.lower() == "txt":
        save_as_txt(results, output_file, timestamp)
    else:
        raise ValueError(f"Unsupported output format: {output_format}")
    
    # Return the path to the file that was created
    return output_file


def save_as_json(results, output_file, timestamp):
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
        json.dump(output_data, f, indent=2, sort_keys=True)


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
        f"Total URLs processed: {len(results)}",
        f"Successful requests: {success_count}",
        f"Failed requests: {failed_count}",
        f"Total links discovered: {link_count}",
        "",
        "URLs by depth:",
    ]
    
    for depth in sorted(depths.keys()):
        summary.append(f"  Depth {depth}: {depths[depth]} URLs")
    
    return "\n".join(summary)