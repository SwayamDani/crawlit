# Engineering Audit: crawlit v1.0.0

> **Audited:** 2026-02-26
> **Branch:** `claude/engineering-audit-FeBml`
> **Scope:** Full repository — every source file, test, config, and infrastructure file

---

## PROJECT UNDERSTANDING

**What it does:** `crawlit` is a modular, "ethical" Python web crawler library and CLI tool. It crawls websites by following links to a configurable depth, extracting content (images, keywords, tables, metadata), and respecting robots.txt. It supports both synchronous (requests-based) and asynchronous (aiohttp-based) engines, with optional features: distributed crawling (RabbitMQ/Kafka), database storage (PostgreSQL/MongoDB), JavaScript rendering (Playwright), PDF extraction, crawl scheduling, proxy rotation, authentication, incremental crawling, and more.

**Architecture:**
- `crawlit/crawlit.py` — CLI entry point (argparse, 872 lines, 70+ flags)
- `crawlit/crawler/engine.py` — Sync crawler (BFS, single-threaded or ThreadPoolExecutor, 1103 lines)
- `crawlit/crawler/async_engine.py` — Async crawler (asyncio workers, 821 lines)
- `crawlit/crawler/fetcher.py` / `async_fetcher.py` — HTTP fetching (requests / aiohttp)
- `crawlit/crawler/parser.py` — BeautifulSoup link extraction
- `crawlit/crawler/robots.py` — Robots.txt handling (sync + async, LRU cache)
- `crawlit/crawler/js_renderer.py` — Playwright browser automation (700 lines)
- `crawlit/utils/` — Rate limiting, caching, auth, proxy, budget, deduplication, incremental state, scheduling, download manager, etc.
- `crawlit/extractors/` — Content, image, keyword, table, PDF, structured data, form, language extraction
- `crawlit/output/formatters.py` — JSON, CSV, TXT, HTML report output
- `crawlit/distributed/` — RabbitMQ/Kafka message queue integration
- `crawlit/storage/` — PostgreSQL/MongoDB backends
- `crawlit/security/` — WAF, CAPTCHA, honeypot, CSRF detection, header analysis

**Test infrastructure:** 55+ test files in `tests/`, CI via GitHub Actions (matrix: Python 3.8–3.12, Ubuntu/Windows/macOS), pytest with async/mock/httpserver support, Codecov integration.

---

## CRITICAL ISSUES (Must Fix)

### C1 — XSS in HTML Output Formatter
**File:** `crawlit/output/formatters.py:402–565`
**Severity:** HIGH

`save_as_html()` embeds raw crawled content directly into HTML via f-strings without calling `html.escape()`:

| Line | Raw content embedded |
|------|---------------------|
| 404 | `<h3>{url}</h3>` |
| 408 | `{status}`, `{depth}`, `{content_type}` |
| 424 | `{error}` — error strings can contain server-controlled content |
| 439 | `<a href="{link}">{link}</a>` — both href and text are raw |
| 470 | `<a href="{src}">`, `{alt}`, `{dimensions}` |
| 500 | `{keyword}`, `{score}` |
| 521 | `{phrase}` |
| 548 | `{cell}` — table cell data |

Any website with XSS-style content in titles, alt text, keywords, or link targets will have that content execute when the HTML report is opened in a browser. An attacker controlling a crawled site can inject JavaScript that runs when a user views the report.

**Fix:** Apply `html.escape()` to all user-controlled values in `save_as_html()`.

---

### C2 — `RobotsTxt.get_sitemaps()` Raises AttributeError at Runtime
**File:** `crawlit/crawler/robots.py:440`
**Severity:** HIGH (broken public API)

```python
def get_sitemaps(self):
    return self.parser.sitemap_urls
```

Python's standard `urllib.robotparser.RobotFileParser` does **not** have a `sitemap_urls` attribute. Every call to `get_sitemaps()` will raise `AttributeError`. This is completely untested.

**Fix:** Parse the `Sitemap:` directives manually from `self.handler.robots_txt_content`, or raise `NotImplementedError` with a clear message until it is implemented.

---

### C3 — Stale Temporary Files Committed to Repository
**Files:** `tmpclaude-2275-cwd`, `tmpclaude-2507-cwd`, `tmpclaude-5b5a-cwd`, `tmpclaude-c364-cwd`, `tmpclaude-d551-cwd`, `tmpclaude-e0f0-cwd`, `tmpclaude-f2a6-cwd` (7 files in repo root)
**Also:** `/.DS_Store` and `/docs/.DS_Store`
**Severity:** HIGH (pollutes repo, inflates clone size)

Claude Code session artifacts accidentally committed. `.gitignore` does not exclude them.

**Fix:** Remove from git tracking, purge from history if sensitive, add `tmpclaude-*` and `**/.DS_Store` to `.gitignore`.

---

### C4 — `get_queue_stats()` Destructs and Rebuilds Live asyncio.Queue
**File:** `crawlit/crawler/async_engine.py:792–821`
**Severity:** HIGH (data loss in production)

```python
while not self.queue.empty():
    item = self.queue.get_nowait()   # drains the queue
    queue_list.append(item)
    temp_queue.put_nowait(item)
...
while not temp_queue.empty():
    self.queue.put_nowait(item)      # rebuilds it
```

This is not atomic. Active workers calling `self.queue.get()` concurrently will silently steal items during the drain, causing URLs to be permanently lost. Also creates a new `asyncio.Queue()` (line 801) synchronously outside an async context.

**Fix:** Use `self.queue.qsize()` for size; access `self.queue._queue` (as already done in `save_state`) for snapshot, or maintain a parallel deque for stats.

---

### C5 — Race Condition: Multi-Threaded Engine Can Double-Dispatch URLs
**File:** `crawlit/crawler/engine.py:480–610`
**Severity:** HIGH

In `_crawl_with_threading()`, the visited-URL check and task submission are separated by a non-atomic gap:

```python
# Check (line 487–490):
with self._visited_lock:
    if current_url in self.visited_urls:
        continue
# Gap here — NO add to visited_urls

# Submit (line 494):
future = executor.submit(self._process_url, current_url, depth, session)
```

The URL is only added to `visited_urls` inside `_process_url()` (line 607–610). Between the check and the add, the main loop (or another thread dequeuing from the same deque) can see the same URL as unvisited and submit it again, resulting in a double-fetch.

**Fix:** Add the URL to `visited_urls` atomically inside the `_visited_lock` block, before submitting to the thread pool.

---

### C6 — `save_state()` Accesses Private `asyncio.Queue._queue` Internal
**File:** `crawlit/crawler/async_engine.py:739`
**Severity:** MEDIUM

```python
queue_list = list(self.queue._queue)  # type: ignore[attr-defined]
```

`_queue` is a private attribute of `asyncio.Queue`. The `# type: ignore` comment is a code smell. This will silently break if CPython internals change. It is already flagged in several Python issue trackers.

**Fix:** Maintain a separate `deque` mirror of the queue alongside `asyncio.Queue`, or use `get_nowait()` in a controlled shutdown snapshot.

---

### C7 — HTTP 429 (Too Many Requests) Treated as Non-Retryable
**File:** `crawlit/crawler/fetcher.py:129–132`, `crawlit/crawler/async_fetcher.py` (same logic)
**Severity:** HIGH

```python
else:
    # For client errors (4xx) and other status codes, don't retry
    return False, f"HTTP Error: {response.status_code}", status_code
```

HTTP 429 is a 4xx code and hits the non-retry branch, causing the crawler to permanently give up on a domain after the first rate-limit response. The correct behavior is to retry after the delay specified in the `Retry-After` response header (or with exponential backoff if absent).

**Fix:** Check `response.status_code == 429` before the generic 4xx branch, parse `Retry-After`, and retry with appropriate sleep.

---

## ARCHITECTURAL PROBLEMS

### A1 — Dual Engine With No Shared Abstraction
`crawler/engine.py` (1103 lines) and `crawler/async_engine.py` (821 lines) implement identical crawling logic — BFS, robots.txt, rate limiting, content extraction, budget tracking, caching, deduplication, sitemap discovery, JS rendering — entirely independently. Every new feature requires two implementations. They already drift: incremental crawling (see A7) is implemented in neither; `same_path_only` exists in both but with subtle differences in initialization.

### A2 — Dead `delay` Parameter in Public API
**File:** `crawlit/crawler/parser.py:15`

```python
def extract_links(html_content, base_url, delay: float = 0.1) -> List[str]:
    # Note: The delay parameter is not used here anymore.
```

A public API function with a documented-dead parameter. Callers who set `delay` get no behavior change but no error either.

### A3 — `html5lib` Listed as Mandatory Dependency But Never Imported
**File:** `pyproject.toml:33`

```toml
"html5lib>=1.1",
```

`grep -r "html5lib" crawlit/` returns zero results. `html5lib` (~400KB + lxml transitive dep) is installed for every user of the library for no reason. BeautifulSoup4 defaults to `html.parser` (stdlib) throughout the codebase.

### A4 — Sync RobotsHandler Makes Blocking Network Calls in Thread Workers
**File:** `crawlit/crawler/robots.py:90–93`

In multi-threaded mode, `RobotsHandler.get_robots_parser()` calls `requests.get()` blocking the worker thread. All workers for different domains can simultaneously block on robots.txt fetches, collapsing throughput.

### A5 — `fetch_url()` Exists Only to Keep Old Tests Green
**File:** `crawlit/crawler/fetcher.py:174`

```python
def fetch_url(...):
    """Alias for fetch_page - maintained for backward compatibility with tests"""
```

Test-compatibility shims in production library code bleed test concerns into the public API. Move compatibility to test fixtures.

### A6 — `RobotsHandler` and `AsyncRobotsHandler` Have Inconsistent Fields
Both classes implement LRU-cached robots.txt parsing but use different field names for the same state:
- Sync: `_fetch_times`, `_cache_set()`
- Async: `last_fetch_time`, `_lru_set()`

This makes the two classes harder to understand, maintain, or consolidate.

### A7 — `IncrementalState` / `StateManager` Have No Integration Path
**File:** `crawlit/utils/incremental.py`

`IncrementalState` and `StateManager` implement full ETag/Last-Modified tracking but are not called anywhere in `engine.py` or `async_engine.py`, and the CLI has no `--incremental` flag. This is a feature with tests but no production wiring.

---

## MISSING FEATURES / GAPS

### G1 — `get_crawl_delay()` in Sync Handler Silently Returns None on Content-Type Mismatch
**File:** `crawlit/crawler/robots.py:181`

```python
if domain not in self.robots_txt_content:
    return None
```

`robots_txt_content` is only populated when the content-type check passes (line 103). If robots.txt has an unexpected content-type but valid content, `get_crawl_delay()` returns `None` and Crawl-Delay is ignored.

### G2 — No `Retry-After` Header Parsing
When HTTP 429 carries `Retry-After: 60`, the crawler ignores it. This is required for polite crawling of rate-limited APIs and sites.

### G3 — `--no-verify-ssl` Not Exposed in CLI
`SessionManager` accepts `verify_ssl=False` but no CLI flag surfaces it. Self-signed certificate environments require workarounds (env var or code).

### G4 — No Response Body Size Limit
Neither `fetcher.py` nor `async_fetcher.py` limits the response body size. A server returning an infinite response (`while True: yield b'x'`) will exhaust process memory.

### G5 — Budget Tracker Bandwidth Unreliable for Chunked Transfer
**File:** `crawlit/crawler/async_engine.py:496–503`

```python
try:
    bytes_downloaded = 0
    if hasattr(response, '_body') and response._body:
        bytes_downloaded = len(response._body)
except Exception:
    bytes_downloaded = 0
```

When `Content-Length` is absent and the body hasn't been fully loaded (common with chunked transfer), `bytes_downloaded` is silently 0. The `max_bandwidth_mb` limit is then ineffective.

---

## CODE QUALITY PROBLEMS

### Q1 — Production Code Wording Changed to Match Test Assertions
**File:** `crawlit/output/formatters.py:595`

```python
# Change wording to match test expectations
f"Total URLs crawled: {len(results)}",
```

Production output was edited to satisfy a test's string assertion — inverted TDD that makes production code fragile and tests meaningless.

### Q2 — `save_results()` Has Four Aliased Parameters
**File:** `crawlit/output/formatters.py:27`

`format_type` and `pretty` are backward-compat aliases for `output_format` and `pretty_json` in the same function. This API surface should be cleaned up with a proper deprecation.

### Q3 — `allowed_query_params` Semantics Are "Required", Not "Allowed"
**File:** `crawlit/utils/url_filter.py:113–116`

The parameter name suggests a whitelist of acceptable query parameters, but the implementation rejects URLs that do not contain ALL specified params. The name is misleading; `required_query_params` would be accurate.

### Q4 — `skipped_paths` in Both RobotsHandlers Is Unbounded
**Files:** `crawlit/crawler/robots.py:39, 223`

`self.skipped_paths.append(url)` is called for every disallowed URL. For a large crawl against a restrictive robots.txt, this list grows without bound. No size cap exists.

### Q5 — `skipped_external_urls` Sets Are Unbounded
**Files:** `crawlit/crawler/engine.py:140`, `crawlit/crawler/async_engine.py:132`

Same pattern — every externally-skipped URL is stored in memory forever.

### Q6 — Single `requests.Session` Shared Across All Worker Threads
**File:** `crawlit/crawler/engine.py:596`

In `_crawl_with_threading()`, a single `Session` is passed to all workers. While `requests.Session` is generally thread-safe for reads, concurrent cookie updates (during authenticated crawls) can cause race conditions.

---

## SECURITY REVIEW

| ID | Issue | Severity |
|----|-------|----------|
| S1 | XSS in `save_as_html()` — all crawled values embedded raw (see C1) | HIGH |
| S2 | DB passwords passed as CLI `--db-password` arg, visible in `ps aux` | MEDIUM |
| S3 | No path-traversal check on `--output`, `--db-path`, `--storage-dir` CLI args | MEDIUM |
| S4 | `URLFilter.from_patterns()` compiles user regex without error handling; ReDoS possible | MEDIUM |
| S5 | `docker-compose.yml` uses `guest/guest` RabbitMQ, anonymous Zookeeper, plaintext Kafka | LOW (dev) |
| S6 | No response body size limit; infinite response exhausts memory | MEDIUM |

**S3 detail:** A user passing `--output ../../../etc/cron.d/job` on a misconfigured system could write outside the intended output directory. Fix: `pathlib.Path(output).resolve().is_relative_to(allowed_base)`.

**S4 detail:** `re.compile("(a+)+$")` on a URL of 40+ `a` characters causes catastrophic backtracking. Add `re.compile()` inside `try/except re.error` at minimum; consider `timeout` via `signal` on POSIX.

---

## PERFORMANCE RISKS

| ID | Issue | Impact |
|----|-------|--------|
| P1 | `ThreadPoolExecutor` in sync engine limited by Python GIL for CPU-bound parsing | MEDIUM |
| P2 | `store_html_content=True` (default) holds all HTML in `results` dict (~1 GB for 10K pages at 100 KB avg) | MEDIUM |
| P3 | `get_queue_stats()` drains live asyncio.Queue — O(n) destructive, not concurrent-safe (see C4) | HIGH |
| P4 | Sync `RobotsHandler` makes blocking HTTP calls inline in thread pool workers (see A4) | MEDIUM |
| P5 | `skipped_paths` / `skipped_external_urls` grow without bound (see Q4/Q5) | LOW |
| P6 | Budget tracker bandwidth tracking returns 0 for chunked responses (see G5) | LOW |

---

## TEST COVERAGE REVIEW

| ID | Gap |
|----|-----|
| T1 | No test verifies `save_as_html()` escapes XSS payloads (e.g., `<script>alert(1)</script>` in page title) |
| T2 | `RobotsTxt.get_sitemaps()` bug (C2) is untested — it always raises `AttributeError` |
| T3 | No test for HTTP 429 retry behavior with mock server |
| T4 | `get_queue_stats()` concurrent-safety not tested (called while workers run) |
| T5 | No CLI test for path-traversal attempt via `--output` |
| T6 | `IncrementalState`/`StateManager` tested in isolation; no end-to-end integration test exists (because the integration doesn't exist) |
| T7 | `html5lib` unused dependency not detected by any CI check |
| T8 | Threading race window (C5) not specifically targeted in `test_threading.py` |

---

## DEVOPS / DEPLOYMENT RISKS

| ID | Issue | Priority |
|----|-------|----------|
| D1 | 7 `tmpclaude-*` files + 2 `.DS_Store` committed; not in `.gitignore` | P0 |
| D2 | `html5lib` mandatory but unused — unnecessary install footprint | P1 |
| D3 | All dependencies use `>=` only; no upper bounds; future breaking releases will silently break library | P1 |
| D4 | No linting (`flake8`/`ruff`) or type checking (`mypy`) in CI pipelines | P1 |
| D5 | `.gitignore` missing `**/.DS_Store`, `tmpclaude-*`, `*.tmp` patterns | P1 |
| D6 | `pyproject.toml` classifier `5 - Production/Stable` is premature given critical bugs present | P2 |
| D7 | No `Dockerfile` for the application; `docker-compose.yml` only covers infrastructure | P2 |
| D8 | `publish.sh`/`PUBLISH_INSTRUCTIONS.md` require manual token handling; not automated in CI | P2 |

---

## ACTION PLAN

### P0 — Must Fix Before Production

- [x] **C3**: Remove `tmpclaude-*` and `.DS_Store` files from git; update `.gitignore`
- [x] **C1**: Fix XSS in `save_as_html()` — apply `html.escape()` to all embedded values
- [x] **C2**: Fix `RobotsTxt.get_sitemaps()` — parse `Sitemap:` directives manually or raise `NotImplementedError`
- [x] **C4**: Fix `get_queue_stats()` — replace queue-drain with `self.queue.qsize()` for size
- [x] **C5**: Fix multi-threaded race condition — add URL to `visited_urls` before `executor.submit()`
- [x] **C7**: Handle HTTP 429 — retry with backoff, parse `Retry-After` header

### P1 — Should Fix Soon

- [ ] **C6**: Replace `self.queue._queue` access in `save_state()` with a supported alternative
- [ ] **A3**: Remove `html5lib` from mandatory dependencies
- [ ] **A7**: Integrate `IncrementalState` into crawlers or move to `[experimental]` extras
- [ ] **S3**: Validate file path arguments in CLI
- [ ] **S4**: Add `try/except re.error` in `URLFilter.from_patterns()`; document ReDoS risk
- [ ] **G4**: Add configurable max response size (`max_response_bytes`) to fetchers
- [ ] **D3**: Add upper-bound version constraints to `aiohttp`, `requests`, `beautifulsoup4`
- [ ] **D4**: Add `mypy` and `ruff`/`flake8` to CI
- [ ] **Q4/Q5**: Cap `skipped_paths` and `skipped_external_urls` (e.g., max 10,000 entries)

### P2 — Improvements

- [ ] **A2**: Remove dead `delay` parameter from `extract_links()`
- [ ] **A5**: Remove `fetch_url()` backward-compat alias; update tests
- [ ] **Q3**: Rename `allowed_query_params` → `required_query_params`
- [ ] **Q1**: Refactor `generate_summary_report()` — don't hardcode wording for tests
- [ ] **Q2**: Deprecate `format_type` and `pretty` aliases in `save_results()`
- [ ] **S2**: Remove `--db-password` from CLI; read exclusively from env var
- [ ] **G3**: Add `--no-verify-ssl` CLI flag
- [ ] **G2**: Implement `Retry-After` header parsing
- [ ] **A1**: Extract a shared protocol/base class for sync and async crawlers
- [ ] **D6**: Downgrade classifier to `4 - Beta`
- [ ] **T1**: Add XSS-escape test for HTML formatter
- [ ] **T3**: Add 429 retry test with mock httpserver

---

## Verification Commands

```bash
# Confirm XSS fix applied everywhere in HTML formatter
grep -n "html.escape" crawlit/output/formatters.py

# Confirm tmpclaude files removed
ls tmpclaude-* 2>/dev/null && echo "STILL PRESENT" || echo "CLEAN"

# Confirm html5lib not imported (after removal)
grep -rn "html5lib" crawlit/

# Confirm RobotsTxt.get_sitemaps() no longer raises AttributeError
python -c "from crawlit.crawler.robots import RobotsTxt; r = RobotsTxt('http://example.com'); print(r.get_sitemaps())"

# Baseline test run
pytest tests/ -v --timeout=60 -m "not slow and not integration and not playwright and not distributed"

# Type check (once mypy is added to CI)
mypy crawlit/ --ignore-missing-imports
```
