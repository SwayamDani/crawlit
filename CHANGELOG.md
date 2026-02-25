# Changelog

All notable changes to crawlit are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-02-25

First stable release. Public API is now frozen under semantic versioning.
Breaking changes will only occur in future major versions (2.x).

### Added
- `crawlit.RobotsError`, `ParseError`, `ExtractionError` exported from top-level package
- `__version__` exported in `crawlit.__all__`
- `RobotsHandler.get_crawl_delay()` (sync) — mirrors the existing async version
- `_DISTRIBUTED_AVAILABLE` flag so callers can check before using distributed classes
- Python 3.11 and 3.12 PyPI classifiers
- `crawlit.parser`, `crawlit.security`, `crawlit.storage`, `crawlit.distributed`
  are now correctly included in built wheels and source distributions
- `*.db` / `tmpclaude-*/` patterns added to `.gitignore`
- `CHANGELOG.md` (this file)

### Fixed
- **`async_engine.py`**: removed deprecated `asyncio.get_event_loop()` call from
  `AsyncCrawler.__init__`; replaced `self.loop.create_task()` with `asyncio.create_task()`
- **`async_engine.py`**: added missing `from collections import deque` import (caused
  `NameError` in `save_state` / `get_queue_stats`)
- **`async_engine.py` `_worker()`**: budget check previously called
  `queue.task_done()` before `queue.get()`, corrupting the join counter and
  potentially hanging `queue.join()` forever
- **`rate_limiter.py`**: `AsyncRateLimiter._lock` is now lazily initialised inside
  the running event loop instead of at class instantiation time
- **`rate_limiter.py`**: deadlock in `DynamicRateLimiter.record_response` and
  `get_stats` — both called `get/set_domain_delay()` while already holding
  `threading.Lock` (not reentrant); fixed by direct dict access
- **`rate_limiter.py`**: same async deadlock in `AsyncDynamicRateLimiter`
- **`rate_limiter.py`**: `AsyncRateLimiter.wait_if_needed` no longer holds the
  lock across `await asyncio.sleep()`, unblocking other domains from proceeding
- **`rate_limiter.py`**: added missing `List` to typing imports
- **`robots.py`**: removed hardcoded `localhost` / `nonexistent.example.com` test
  logic from the production `RobotsHandler.can_fetch()` code path
- **`robots.py`**: regression introduced in beta — `parser` variable was dropped
  from `can_fetch()`, causing `NameError` on every real crawl; restored
- **`crawler/__init__.py`**: removed private `_process_url` from `__all__`
- **`crawlit/__init__.py`**: distributed conditional import now sets names to
  `None` on `ImportError` instead of leaving them undefined (would have caused
  `NameError` on attribute access)
- **`crawlit/__init__.py`**: stale root-level `__init__.py` deleted (shadowed the
  package in some editable-install configurations)
- **`pyproject.toml`**: `playwright` removed from core dependencies (now optional
  via `pip install crawlit[js]`)
- **`requirements.txt`**: optional heavy deps (`playwright`, `kafka-python`,
  `pypdf2`, `pdfplumber`) removed from the development requirements file
- Removed committed `crawlit_results.db` and `incremental_crawl.db` files from
  version control

### Changed
- Default user-agent updated from `crawlit/2.0` to `crawlit/1.0` across all
  modules to match the semantic version

---

## [0.2.0] - 2026-02-01

See `RELEASE_NOTES.md` for the full 0.2.0 feature list and migration guide.

### Added
- JavaScript rendering via Playwright (`crawlit[js]`)
- Advanced extractors: forms, structured data (JSON-LD / OG / Microdata),
  language detection, PDF text extraction
- Security analysis: CSRF handling, security-header grading, WAF detection,
  honeypot detection, CAPTCHA detection
- Distributed crawling via RabbitMQ / Kafka (`crawlit[distributed]`)
- Database backends: SQLite, PostgreSQL, MongoDB
- Dynamic rate limiter with automatic back-off on 429 / slow responses
- Crawl budget tracker (pages, bandwidth, time, file size)
- URL priority queue with pluggable strategies
- Cookie persistence, download manager, incremental crawling (ETags)
- Cron-like crawl scheduling (`crawlit[scheduler]`)
- Proxy manager with health tracking and rotation strategies
- Enhanced structured JSON logging

---

## [0.1.0] - 2025-06-30

Initial public release.

### Added
- Synchronous (`Crawler`) and asynchronous (`AsyncCrawler`) crawl engines
- BFS crawl with configurable depth and domain filtering
- robots.txt compliance with Crawl-delay support
- Per-domain rate limiting
- HTML table, image, and keyword extraction
- Output formatters: JSON, CSV, TXT, HTML
- CLI (`crawlit --url ...`)
- Session management with Basic / Digest / OAuth / API-key auth
- Page caching and crawl-state resume
- Content deduplication (SHA-256)
- Sitemap auto-discovery and parsing
