#!/bin/bash
# ========================================================================
# crawlit_examples.sh - Demo of crawlit CLI usage on Unix systems
# ========================================================================

# Add project root to PYTHONPATH to ensure imports work correctly
export PYTHONPATH="$(dirname "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)")":$PYTHONPATH

# Set the target URL
TARGET_URL="https://swayamdani.com"

# ========================================================================
echo
echo "================================================================================"
echo "EXAMPLE 1: BASIC CRAWLING"
echo "================================================================================"
echo

# Run basic crawl with custom parameters
python3 -m crawlit.crawlit --url "$TARGET_URL" \
        --depth 1 \
        --user-agent "MyCustomBot/2.0" \
        --delay 0.5 \
        --output basic_crawl_results.json \
        --output-format json \
        --pretty-json \
        --summary

echo "Results saved to basic_crawl_results.json"

# ========================================================================
echo
echo "================================================================================"
echo "EXAMPLE 2: TABLE EXTRACTION"
echo "================================================================================"
echo

# Run table extraction with custom parameters
python3 -m crawlit.crawlit --url "$TARGET_URL" \
        --depth 1 \
        --user-agent "crawlit/2.0" \
        --extract-tables \
        --tables-output "table_output" \
        --tables-format csv \
        --min-rows 1 \
        --min-columns 2 \
        --output table_extraction_results.json \
        --output-format json \
        --pretty-json

echo "Table extraction complete. Results saved to table_extraction_results.json"

# ========================================================================
echo
echo "================================================================================"
echo "EXAMPLE 3: IMAGE EXTRACTION"
echo "================================================================================"
echo

# Run image extraction with custom parameters
python3 -m crawlit.crawlit --url "$TARGET_URL" \
        --depth 1 \
        --user-agent "crawlit/2.0" \
        --extract-images \
        --images-output "image_output" \
        --output image_extraction_results.json \
        --output-format json \
        --pretty-json

echo "Image extraction complete. Results saved to image_extraction_results.json"

# ========================================================================
echo
echo "================================================================================"
echo "EXAMPLE 4: KEYWORD EXTRACTION"
echo "================================================================================"
echo

# Run keyword extraction with custom parameters
python3 -m crawlit.crawlit --url "$TARGET_URL" \
        --depth 1 \
        --user-agent "crawlit/2.0" \
        --extract-keywords \
        --keywords-output "keywords.json" \
        --max-keywords 15 \
        --min-word-length 4 \
        --output keyword_extraction_results.json \
        --output-format json \
        --pretty-json

echo "Keyword extraction complete. Results saved to keyword_extraction_results.json and keywords.json"

echo
echo "================================================================================"
echo "All examples completed successfully!"
echo "================================================================================"
