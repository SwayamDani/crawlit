# JavaScript Rendering in Crawlit

This guide covers crawlit's powerful JavaScript rendering capabilities for crawling modern Single Page Applications (SPAs) and JavaScript-heavy websites using Playwright.

## Table of Contents

1. [Overview](#overview)
2. [Installation & Setup](#installation--setup)
3. [Playwright Integration](#playwright-integration)
4. [Configuration Options](#configuration-options)
5. [Wait Strategies](#wait-strategies)
6. [Page Interaction Capabilities](#page-interaction-capabilities)
7. [Performance Considerations](#performance-considerations)
8. [Common SPA Patterns](#common-spa-patterns)
9. [Troubleshooting](#troubleshooting)
10. [Advanced Scenarios](#advanced-scenarios)

## Overview

Modern web applications increasingly rely on JavaScript to render content dynamically. Traditional HTTP crawlers that only parse initial HTML miss this rendered content. Crawlit's JavaScript rendering capabilities solve this by:

- **Full Browser Automation**: Using real browser engines (Chromium, Firefox, WebKit) via Playwright
- **Dynamic Content Capture**: Waiting for JavaScript to execute and render final content
- **SPA Support**: Handling client-side routing in React, Vue, Angular, and other frameworks
- **Interactive Crawling**: Supporting clicks, form submissions, and user interactions
- **Screenshot Capture**: Visual debugging and content verification

### When to Use JavaScript Rendering

Use JavaScript rendering when:
- Content is loaded dynamically via AJAX/fetch requests
- Site uses client-side routing (single-page applications)
- Important content is only available after user interactions
- You need to capture the final rendered state, not just the initial HTML
- Working with modern frameworks: React, Vue, Angular, Svelte, etc.

## Installation & Setup

### Basic Installation

```bash
# Install crawlit with Playwright support
pip install "crawlit[playwright]"

# Install browser engines
python -m playwright install chromium
```

### Verify Installation

```python
from crawlit.crawler.js_renderer import is_playwright_available

if is_playwright_available():
    print("✓ JavaScript rendering available")
else:
    print("✗ Playwright not available")
```

## Playwright Integration

Crawlit integrates with Playwright to provide robust browser automation:

### Supported Browser Engines

| Engine | Description | Use Cases |
|--------|-------------|-----------|
| **Chromium** | Google Chrome engine (default) | Best compatibility, most widely used |
| **Firefox** | Mozilla Firefox engine | Testing cross-browser compatibility |
| **WebKit** | Safari engine | iOS/macOS specific testing |

### Browser Configuration

```python
from crawlit.crawler.js_renderer import JavaScriptRenderer

# Configure browser settings
renderer = JavaScriptRenderer(
    browser_type="chromium",  # or "firefox", "webkit"
    headless=True,           # Run without GUI
    timeout=30000,           # 30-second timeout
    user_agent="MyBot/1.0",  # Custom user agent
    viewport={"width": 1920, "height": 1080},  # Screen size
    ignore_https_errors=True,  # Skip SSL verification
    extra_http_headers={      # Additional headers
        "Authorization": "Bearer token123"
    }
)
```

## Configuration Options

### Crawler-Level Configuration

```python
from crawlit import Crawler

# Enable JS rendering for entire crawl
crawler = Crawler(
    start_url="https://spa-example.com",
    use_js_rendering=True,
    js_browser_type="chromium",
    js_wait_for_selector="#content",
    js_wait_for_timeout=2000,
    max_depth=2
)

results = crawler.crawl()
```

### Configuration via Config Objects

```python
from crawlit import Crawler, FetchConfig, CrawlerConfig

fetch_config = FetchConfig(
    use_js_rendering=True,
    js_browser_type="firefox",
    js_wait_for_selector="#app",
    js_wait_for_timeout=3000,
    timeout=30
)

crawler_config = CrawlerConfig(
    start_url="https://vue-app.com",
    max_depth=3,
    fetch=fetch_config
)

crawler = Crawler(config=crawler_config)
results = crawler.crawl()
```

### Command Line Interface

```bash
# Basic JavaScript rendering
crawlit --url https://react-app.com --use-js

# With browser selection and wait strategies
crawlit --url https://spa-site.com \
    --use-js \
    --js-browser firefox \
    --js-wait-selector "#content" \
    --js-wait-timeout 5000

# Full example with output
crawlit --url https://angular-app.com \
    --use-js \
    --js-browser chromium \
    --js-wait-selector ".loaded" \
    --max-depth 2 \
    --output spa_content.json
```

## Wait Strategies

Proper wait strategies ensure content is fully loaded before extraction:

### 1. Network Idle Strategy

Wait until network requests settle (default behavior):

```python
renderer = JavaScriptRenderer(wait_until="networkidle")

# Or explicitly in render call
result = renderer.render(url, wait_for_network_idle=True)
```

### 2. Selector-Based Waiting

Wait for specific elements to appear:

```python
# Wait for content container
result = renderer.render(
    url="https://spa-app.com",
    wait_for_selector="#main-content"
)

# Wait for multiple conditions
result = renderer.render(
    url="https://complex-app.com",
    wait_for_selector=".data-loaded, .ready-state",  # CSS selector
    wait_for_timeout=2000  # Additional 2s after selector found
)
```

### 3. Timeout-Based Waiting

Add fixed delays after page load:

```python
# Wait additional 3 seconds after initial load
result = renderer.render(
    url="https://slow-app.com",
    wait_for_timeout=3000  # milliseconds
)
```

### 4. Combined Strategies

```python
# Comprehensive wait strategy
result = renderer.render(
    url="https://complex-spa.com",
    wait_for_selector="#content .article",  # Wait for content
    wait_for_timeout=1000,                  # Extra 1s buffer
    wait_for_network_idle=True              # Ensure requests complete
)
```

## Page Interaction Capabilities

### Custom JavaScript Execution

Execute custom JavaScript on pages:

```python
# Extract data with custom JavaScript
js_code = """
() => {
    return {
        title: document.title,
        itemCount: document.querySelectorAll('.item').length,
        currentUser: window.currentUser || null
    };
}
"""

result = renderer.render(
    url="https://interactive-app.com",
    execute_script=js_code
)

# Access JavaScript results
if result["success"]:
    js_data = result["js_result"]
    print(f"Found {js_data['itemCount']} items")
```

### Screenshot Capture

Visual verification and debugging:

```python
# Capture screenshots during rendering
result = renderer.render(
    url="https://visual-app.com",
    screenshot_path="app_screenshot.png",
    full_page_screenshot=True  # Capture entire scrollable page
)

# Dedicated screenshot method
screenshot_result = renderer.capture_screenshot(
    url="https://dashboard.com",
    filepath="dashboard.png",
    wait_for_selector="#charts",
    full_page=True,
    screenshot_type="png"  # or "jpeg"
)
```

### Advanced Interactions

For complex interactions, use the Playwright page object directly:

```python
from crawlit.crawler.js_renderer import JavaScriptRenderer

class InteractiveRenderer(JavaScriptRenderer):
    def render_with_interaction(self, url):
        """Custom method with page interactions"""
        if not self.browser:
            self.start()
        
        page = self.context.new_page()
        
        try:
            # Navigate to page
            page.goto(url)
            
            # Wait for initial load
            page.wait_for_selector("#app")
            
            # Perform interactions
            page.click("#load-more-btn")
            page.fill("#search-input", "test query")
            page.press("#search-input", "Enter")
            
            # Wait for results
            page.wait_for_selector(".search-results")
            
            # Extract final content
            return {
                "success": True,
                "html": page.content(),
                "url": page.url
            }
        finally:
            page.close()

# Usage
renderer = InteractiveRenderer()
result = renderer.render_with_interaction("https://search-app.com")
```

## Performance Considerations

### 1. Browser Lifecycle Management

```python
# Reuse renderer across multiple pages
from crawlit.crawler.js_renderer import JavaScriptRenderer

# Context manager automatically handles cleanup
with JavaScriptRenderer() as renderer:
    for url in urls:
        result = renderer.render(url)
        process_result(result)
# Browser automatically closed
```

### 2. Async Operations

For high-concurrency scenarios:

```python
import asyncio
from crawlit.crawler.js_renderer import AsyncJavaScriptRenderer

async def crawl_spa_sites(urls):
    async with AsyncJavaScriptRenderer() as renderer:
        tasks = []
        for url in urls:
            task = asyncio.create_task(renderer.render(url))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results

# Usage
urls = ["https://spa1.com", "https://spa2.com", "https://spa3.com"]
results = asyncio.run(crawl_spa_sites(urls))
```

### 3. Resource Optimization

```python
# Optimize for speed
renderer = JavaScriptRenderer(
    browser_type="chromium",
    headless=True,           # Faster than headed mode
    timeout=15000,           # Shorter timeouts for failed pages
    viewport={"width": 1366, "height": 768},  # Smaller viewport
    javascript_enabled=True,  # Ensure JS is enabled
    ignore_https_errors=True  # Skip SSL verification
)
```

### 4. Memory Management

```python
# Monitor memory usage in long-running crawls
class ManagedRenderer:
    def __init__(self, max_pages=100):
        self.max_pages = max_pages
        self.page_count = 0
        self.renderer = None
    
    def render_page(self, url):
        if not self.renderer or self.page_count >= self.max_pages:
            # Recreate renderer periodically
            if self.renderer:
                self.renderer.close()
            self.renderer = JavaScriptRenderer()
            self.renderer.start()
            self.page_count = 0
        
        result = self.renderer.render(url)
        self.page_count += 1
        return result
```

## Common SPA Patterns

### React Applications

```python
# React apps often use client-side routing
crawler = Crawler(
    start_url="https://react-app.com",
    use_js_rendering=True,
    js_wait_for_selector="#root .app-loaded",  # Wait for app initialization
    js_wait_for_timeout=2000,  # Buffer for async data loading
    internal_only=True,        # Stay within React app
    max_depth=3
)

# Custom JavaScript for React data extraction
react_extractor = """
() => {
    const app = document.querySelector('#root');
    if (app && app.__reactInternalInstance) {
        // Extract React component data
        return {
            reactVersion: React.version,
            components: Object.keys(app.__reactInternalInstance)
        };
    }
    return null;
}
"""

results = crawler.crawl()
```

### Vue.js Applications

```python
# Vue apps with vue-router
crawler = Crawler(
    start_url="https://vue-app.com",
    use_js_rendering=True,
    js_wait_for_selector="#app[data-server-rendered='false']",  # Wait for hydration
    js_browser_type="chromium"
)

# Extract Vue component data
vue_script = """
() => {
    if (window.Vue && window.Vue.version) {
        return {
            vueVersion: window.Vue.version,
            components: Object.keys(Vue.options.components || {})
        };
    }
    return null;
}
"""
```

### Angular Applications

```python
# Angular with lazy loading
crawler = Crawler(
    start_url="https://angular-app.com",
    use_js_rendering=True,
    js_wait_for_selector="app-root .content-loaded",  # Wait for app bootstrap
    js_wait_for_timeout=3000,  # Allow for lazy loading
    js_browser_type="chromium"
)

# Extract Angular data
angular_script = """
() => {
    const ng = window.ng;
    if (ng && ng.version) {
        return {
            angularVersion: ng.version.full,
            modules: ng.ɵZONE_SYMBOL_PREFIX || 'angular-loaded'
        };
    }
    return null;
}
"""
```

### Next.js Applications

Next.js embeds data in `__NEXT_DATA__` scripts:

```python
from crawlit import Crawler
from crawlit.extractors import JSEmbeddedDataExtractor

# Crawl Next.js app and extract embedded data
crawler = Crawler(
    start_url="https://nextjs-app.com",
    use_js_rendering=True,
    js_wait_for_selector="[id='__next']",
    extractors=[JSEmbeddedDataExtractor()],  # Extracts __NEXT_DATA__
    enable_js_embedded_data=True
)

results = crawler.crawl()

# Access extracted Next.js data
for artifact in results:
    if 'js_embedded_data' in artifact.extracted:
        next_data = artifact.extracted['js_embedded_data']
        print(f"Page props: {next_data.get('props', {})}")
```

## Troubleshooting

### Common Issues and Solutions

#### 1. Content Not Loading

**Problem**: Page appears blank or incomplete
```python
# Solution: Increase timeout and add specific wait conditions
result = renderer.render(
    url="https://slow-app.com",
    wait_for_selector=".content-ready",  # Wait for specific element
    wait_for_timeout=5000,               # Extra wait time
    wait_for_network_idle=True           # Ensure all requests complete
)
```

#### 2. JavaScript Errors

**Problem**: JavaScript execution failures
```python
# Solution: Handle errors gracefully and add debugging
js_code = """
(() => {
    try {
        // Your extraction code
        return document.querySelector('.data').textContent;
    } catch (error) {
        console.error('Extraction error:', error);
        return null;
    }
})()
"""

result = renderer.render(url, execute_script=js_code)
if not result["success"]:
    print(f"Rendering failed: {result['error']}")
```

#### 3. Memory Issues

**Problem**: High memory usage or browser crashes
```python
# Solution: Implement renderer recycling
class MemoryEfficientCrawler:
    def __init__(self, pages_per_browser=50):
        self.pages_per_browser = pages_per_browser
        self.current_count = 0
        self.renderer = None
    
    def crawl_page(self, url):
        if self.current_count >= self.pages_per_browser or not self.renderer:
            if self.renderer:
                self.renderer.close()
            self.renderer = JavaScriptRenderer()
            self.renderer.start()
            self.current_count = 0
        
        result = self.renderer.render(url)
        self.current_count += 1
        return result
```

#### 4. Timeout Issues

**Problem**: Pages timing out frequently
```python
# Solution: Implement progressive timeout strategy
def render_with_fallback(url, timeouts=[15000, 30000, 60000]):
    """Try rendering with progressively longer timeouts"""
    for timeout in timeouts:
        try:
            renderer = JavaScriptRenderer(timeout=timeout)
            with renderer:
                result = renderer.render(url)
                if result["success"]:
                    return result
        except Exception as e:
            print(f"Timeout {timeout}ms failed: {e}")
    
    return {"success": False, "error": "All timeouts exhausted"}
```

### Debugging Tools

#### 1. Screenshot Debugging

```python
# Capture screenshots at different stages
def debug_render(url):
    with JavaScriptRenderer() as renderer:
        # Initial page load
        result1 = renderer.render(
            url, 
            screenshot_path="debug_initial.png",
            wait_for_timeout=1000
        )
        
        # After waiting for content
        result2 = renderer.render(
            url,
            wait_for_selector=".content",
            screenshot_path="debug_content.png",
            wait_for_timeout=2000
        )
        
        return result2
```

#### 2. Console Log Capture

```python
# Monitor browser console for errors
console_logs = """
(() => {
    const logs = [];
    const originalConsole = console.log;
    console.log = function(...args) {
        logs.push(args.join(' '));
        originalConsole.apply(console, args);
    };
    
    // Wait a bit for logs to accumulate
    setTimeout(() => window._debug_logs = logs, 2000);
    
    return "Console monitoring started";
})()
"""

result = renderer.render(url, execute_script=console_logs)
```

### Performance Monitoring

```python
import time

def monitor_render_performance(urls):
    """Monitor rendering performance across multiple URLs"""
    stats = []
    
    with JavaScriptRenderer() as renderer:
        for url in urls:
            start_time = time.time()
            result = renderer.render(url)
            end_time = time.time()
            
            stats.append({
                "url": url,
                "success": result["success"],
                "render_time": end_time - start_time,
                "content_size": len(result.get("html", "")),
                "status_code": result.get("status_code", 0)
            })
    
    return stats
```

## Advanced Scenarios

### 1. Multi-Step Workflows

Implement complex user journeys:

```python
class WorkflowRenderer(JavaScriptRenderer):
    def login_and_crawl(self, login_url, protected_url, username, password):
        """Login then access protected content"""
        if not self.browser:
            self.start()
        
        page = self.context.new_page()
        
        try:
            # Step 1: Navigate to login
            page.goto(login_url)
            
            # Step 2: Fill and submit login form
            page.fill("#username", username)
            page.fill("#password", password)
            page.click("#login-button")
            
            # Step 3: Wait for login to complete
            page.wait_for_selector(".user-menu", timeout=10000)
            
            # Step 4: Navigate to protected content
            page.goto(protected_url)
            page.wait_for_selector(".protected-content")
            
            return {
                "success": True,
                "html": page.content(),
                "url": page.url
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            page.close()

# Usage
renderer = WorkflowRenderer()
result = renderer.login_and_crawl(
    "https://app.com/login",
    "https://app.com/dashboard",
    "user@example.com",
    "password123"
)
```

### 2. Infinite Scroll Handling

```python
def crawl_infinite_scroll(url, max_scrolls=10):
    """Handle infinite scroll interfaces"""
    
    infinite_scroll_script = f"""
    async () => {{
        let scrolls = 0;
        const maxScrolls = {max_scrolls};
        
        while (scrolls < maxScrolls) {{
            const beforeHeight = document.body.scrollHeight;
            window.scrollTo(0, document.body.scrollHeight);
            
            // Wait for new content to load
            await new Promise(resolve => setTimeout(resolve, 2000));
            
            const afterHeight = document.body.scrollHeight;
            if (beforeHeight === afterHeight) {{
                break; // No more content
            }}
            
            scrolls++;
        }}
        
        return {{
            scrollsPerformed: scrolls,
            finalHeight: document.body.scrollHeight
        }};
    }}
    """
    
    with JavaScriptRenderer(timeout=60000) as renderer:  # Longer timeout
        result = renderer.render(
            url,
            execute_script=infinite_scroll_script,
            wait_for_timeout=3000  # Buffer after scrolling
        )
        
        if result["success"]:
            scroll_result = result.get("js_result", {})
            print(f"Performed {scroll_result.get('scrollsPerformed', 0)} scrolls")
        
        return result
```

### 3. Dynamic Form Handling

```python
def fill_dynamic_form(url, form_data):
    """Handle dynamic forms with validation"""
    
    form_script = f"""
    async () => {{
        const formData = {form_data};
        const results = {{}};
        
        for (const [field, value] of Object.entries(formData)) {{
            const element = document.querySelector(`[name="${{field}}"]`);
            if (element) {{
                element.value = value;
                
                // Trigger change events for validation
                element.dispatchEvent(new Event('change', {{ bubbles: true }}));
                element.dispatchEvent(new Event('input', {{ bubbles: true }}));
                
                // Wait for any async validation
                await new Promise(resolve => setTimeout(resolve, 500));
                
                results[field] = 'filled';
            }} else {{
                results[field] = 'field_not_found';
            }}
        }}
        
        return results;
    }}
    """
    
    with JavaScriptRenderer() as renderer:
        return renderer.render(
            url,
            execute_script=form_script,
            wait_for_selector="form",
            wait_for_timeout=2000
        )

# Usage
form_result = fill_dynamic_form(
    "https://complex-form.com",
    {"email": "test@example.com", "name": "Test User"}
)
```

### 4. A/B Test Detection

```python
def detect_ab_tests(url, num_samples=5):
    """Detect A/B tests by sampling multiple renders"""
    variants = []
    
    with JavaScriptRenderer() as renderer:
        for i in range(num_samples):
            result = renderer.render(
                url,
                execute_script="""
                () => {
                    return {
                        title: document.title,
                        bodyClasses: document.body.className,
                        abTestData: window.abTestData || null,
                        experiments: window.experiments || null
                    };
                }
                """,
                wait_for_timeout=2000
            )
            
            if result["success"]:
                variants.append(result["js_result"])
    
    # Analyze variants for differences
    unique_variants = []
    for variant in variants:
        if variant not in unique_variants:
            unique_variants.append(variant)
    
    return {
        "total_samples": len(variants),
        "unique_variants": len(unique_variants),
        "variants": unique_variants
    }
```

### 5. Real-time Data Monitoring

```python
def monitor_realtime_updates(url, duration_seconds=60):
    """Monitor real-time data updates"""
    
    monitoring_script = f"""
    (() => {{
        const updates = [];
        const startTime = Date.now();
        const duration = {duration_seconds * 1000};
        
        // Monitor DOM mutations
        const observer = new MutationObserver((mutations) => {{
            mutations.forEach((mutation) => {{
                if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {{
                    updates.push({{
                        timestamp: Date.now() - startTime,
                        type: 'content_added',
                        target: mutation.target.tagName || 'unknown'
                    }});
                }}
            }});
        }});
        
        observer.observe(document.body, {{
            childList: true,
            subtree: true
        }});
        
        // Return promise that resolves after monitoring period
        return new Promise((resolve) => {{
            setTimeout(() => {{
                observer.disconnect();
                resolve({{
                    totalUpdates: updates.length,
                    updates: updates,
                    monitoringDuration: duration
                }});
            }}, duration);
        }});
    }})()
    """
    
    with JavaScriptRenderer(timeout=(duration_seconds + 10) * 1000) as renderer:
        return renderer.render(
            url,
            execute_script=monitoring_script,
            wait_for_timeout=1000
        )
```

## Integration Examples

### With Async Crawler

```python
import asyncio
from crawlit import AsyncCrawler

async def crawl_spa_site():
    crawler = AsyncCrawler(
        start_url="https://spa-example.com",
        use_js_rendering=True,
        js_wait_for_selector="#app-ready",
        max_depth=3,
        max_concurrent_requests=2  # Limit concurrency for browser resources
    )
    
    results = await crawler.crawl_async()
    return results

# Run the async crawler
results = asyncio.run(crawl_spa_site())
```

### With Content Extraction

```python
from crawlit import Crawler
from crawlit.extractors import ContentExtractor, JSEmbeddedDataExtractor

# Combine JS rendering with content extraction
crawler = Crawler(
    start_url="https://news-spa.com",
    use_js_rendering=True,
    js_wait_for_selector=".article-content",
    extractors=[
        ContentExtractor(),         # Extract main content
        JSEmbeddedDataExtractor()   # Extract embedded JSON data
    ],
    enable_content_extraction=True,
    enable_js_embedded_data=True
)

results = crawler.crawl()

for artifact in results:
    if artifact.extracted.get('content'):
        print(f"Title: {artifact.extracted['content']['title']}")
        print(f"Text: {artifact.extracted['content']['text'][:200]}...")
    
    if artifact.extracted.get('js_embedded_data'):
        print(f"Embedded data: {artifact.extracted['js_embedded_data']}")
```

---

This comprehensive guide covers crawlit's JavaScript rendering capabilities. The system provides powerful tools for crawling modern web applications while maintaining simplicity and performance. For specific use cases not covered here, consult the API documentation or examine the test suite for additional examples.

## Next Steps

- Explore [Content Extraction](content_extractor.md) for processing rendered content
- Learn about [Async Crawling](async-crawling.md) for high-performance scenarios  
- Check [Configuration](configuration.md) for fine-tuning crawler behavior
- Review [CLI Reference](cli-reference.md) for command-line usage