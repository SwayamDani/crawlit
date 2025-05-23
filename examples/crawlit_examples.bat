@echo off
REM ========================================================================
REM crawlit_examples.bat - Demo of crawlit CLI usage on Windows
REM ========================================================================

REM Add project root to PYTHONPATH to ensure imports work correctly
set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%\..
set PYTHONPATH=%PROJECT_ROOT%;%PYTHONPATH%

REM Set the target URL
SET TARGET_URL=https://swayamdani.com

REM ========================================================================
ECHO.
ECHO ================================================================================
ECHO EXAMPLE 1: BASIC CRAWLING
ECHO ================================================================================
ECHO.

REM Run basic crawl with custom parameters
python -m crawlit --url %TARGET_URL% ^
        --depth 1 ^
        --internal-only ^
        --user-agent "MyCustomBot/2.0" ^
        --delay 0.5 ^
        --output basic_crawl_results.json ^
        --output-format json ^
        --pretty-json ^
        --summary

ECHO Results saved to basic_crawl_results.json

REM ========================================================================
ECHO.
ECHO ================================================================================
ECHO EXAMPLE 2: TABLE EXTRACTION
ECHO ================================================================================
ECHO.

REM Run table extraction with custom parameters
python -m crawlit --url %TARGET_URL% ^
        --depth 1 ^
        --user-agent "crawlit/2.0" ^
        --extract-tables ^
        --tables-output "table_output" ^
        --tables-format csv ^
        --min-rows 1 ^
        --min-columns 2 ^
        --output table_extraction_results.json ^
        --output-format json ^
        --pretty-json

ECHO Table extraction complete. Results saved to table_extraction_results.json

REM ========================================================================
ECHO.
ECHO ================================================================================
ECHO EXAMPLE 3: IMAGE EXTRACTION
ECHO ================================================================================
ECHO.

REM Run image extraction with custom parameters
python -m crawlit --url %TARGET_URL% ^
        --depth 1 ^
        --user-agent "crawlit/2.0" ^
        --extract-images ^
        --images-output "image_output" ^
        --output image_extraction_results.json ^
        --output-format json ^
        --pretty-json

ECHO Image extraction complete. Results saved to image_extraction_results.json

REM ========================================================================
ECHO.
ECHO ================================================================================
ECHO EXAMPLE 4: KEYWORD EXTRACTION
ECHO ================================================================================
ECHO.

REM Run keyword extraction with custom parameters
python -m crawlit --url %TARGET_URL% ^
        --depth 1 ^
        --user-agent "crawlit/2.0" ^
        --extract-keywords ^
        --keywords-output "keywords.json" ^
        --max-keywords 15 ^
        --min-word-length 4 ^
        --output keyword_extraction_results.json ^
        --output-format json ^
        --pretty-json

ECHO Keyword extraction complete. Results saved to keyword_extraction_results.json and keywords.json

ECHO.
ECHO ================================================================================
ECHO All examples completed successfully!
ECHO ================================================================================
