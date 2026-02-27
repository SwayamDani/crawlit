# Crawlit Production Architecture Review

**Reviewer:** Senior Distributed Systems Architect
**Date:** 2026-02-27
**Scope:** Production code only (no tests). Architecture for FinanceCrawler use case.
**Codebase:** ~24,700 lines across 73 production Python files

---

## 1. Architectural Strengths

### 1.1 The PageArtifact Model Is Genuinely Well-Designed

`models/page_artifact.py` is the strongest part of the codebase. Concrete evidence:

- **Schema versioning enforced at construction time.** `SCHEMA_VERSION = "1"` is checked in `validate_minimal()`, which means downstream consumers (your quant ingestion system) can reject artifacts from incompatible crawler versions at the boundary. This is exactly what you need for a long-lived pipeline.

- **`copy()` method creates independent mutable containers.** Every sub-dataclass (`HTTPInfo`, `ContentInfo`, `CrawlMeta`, `ArtifactSource`) is `dataclasses.replace()`'d. Lists and dicts are shallow-copied. This means pipeline stages can mutate artifacts without corrupting upstream state — the snapshot/restore pattern in `_run_pipelines()` depends on this and it works correctly.

- **`CrawlError` is typed, not stringly-typed.** Error codes are an explicit set (`ERROR_CODES`), factory methods (`CrawlError.fetch()`, `.extractor()`, `.pipeline()`, `.pdf()`, `.not_modified()`) enforce consistent creation. This means your quant alerting system can `GROUP BY error.code` reliably across millions of artifacts.

- **`ArtifactSource` enables multi-source routing.** The `type` field (`seed`/`sitemap`/`html_link`/`api`) with `site` domain means FinanceCrawler can route artifacts to different processing pipelines based on how they were discovered. This is critical for investor relations sites where PDFs come from sitemaps but earnings HTML comes from link traversal.

- **`to_dict()` handles recursive dataclass serialisation correctly.** The nested `_convert()` function handles datetime, CrawlError, nested dataclasses, lists, and dicts. No silent data loss.

### 1.2 Plugin Architecture Is Clean

The ABC hierarchy (`Fetcher`/`AsyncFetcher`, `Extractor`/`AsyncExtractor`, `Pipeline`/`AsyncPipeline`) in `interfaces.py` has the right granularity:

- **Sync engine rejects async plugins at construction time** (lines 388-400 in `engine.py`). This is a `TypeError`, not a silent fallback. Good.
- **Async engine accepts both sync and async plugins** via `inspect.iscoroutinefunction()` dispatch (line 1031 in `async_engine.py`). This is the correct direction of compatibility.
- **FetchRequest/FetchResult dataclasses decouple engines from HTTP libraries.** Custom fetchers can swap in authenticated sessions, rotating proxies, or mock responses without touching engine internals.

### 1.3 Pipeline Chain Is Safe

`_run_pipelines()` (both engines):
- Takes a `copy()` snapshot before each stage.
- On exception: restores the snapshot, logs, emits `PIPELINE_ERROR` event.
- On `None` return: emits `PIPELINE_DROP`, stops the chain.
- Final artifact stored only if non-None and `retain_artifacts=True`.

This is correct. A failing BlobStore write cannot corrupt the artifact that the JSONLWriter receives.

### 1.4 ArtifactStore Contract Is Explicit and Documented

`pipelines/artifact_store.py` defines the layout as class constants:
```
RUN_MANIFEST  = "run.json"
ARTIFACTS_LOG = "artifacts.jsonl"
EDGES_LOG     = "edges.jsonl"
BLOBS_DIR     = "blobs"
EVENTS_LOG    = "events.jsonl"
```

The `run.json` manifest includes `store_layout_version`, `config_snapshot_sha256` (16-char prefix), and an `outputs` dict listing which files are present. Downstream tools (DuckDB, Spark) can rely on this without inspecting crawler code. The `config_snapshot_sha256` enables detecting configuration drift between runs — essential for quant reproducibility.

### 1.5 Content-Addressed Blob Store With Cross-Run Dedup

`BlobStore` uses `sha256[:2]/sha256.ext` directory sharding. `ContentHashStore` backs this with SQLite (WAL mode, `busy_timeout=5000`). The blob path is checked before writing, and stale paths are detected with `Path.exists()`. This means your daily crawl with 80% unchanged content will skip ~80% of disk writes.

### 1.6 Observability Is Well-Structured

`CrawlEventLog` with 10 typed events covers the operational events that matter. Events are append-only JSONL with `run_id`, ISO timestamp, level, and typed details. This is sufficient for building SLA dashboards (fetch error rate, incremental hit rate, pipeline drop rate per run).

### 1.7 DynamicRateLimiter Adapts to Server Behavior

`DynamicRateLimiter` tracks per-domain response times, error rates, and handles HTTP 429 with `Retry-After` header respect. This is critical for crawling investor relations sites that enforce rate limits.

---

## 2. Architectural Risks

### 2.1 CRITICAL: `RateLimiter.wait_if_needed()` Holds Lock While Sleeping

**File:** `utils/rate_limiter.py:82-92`

```python
def wait_if_needed(self, url: str) -> None:
    ...
    with self._lock:
        ...
        if time_since_last_request < delay:
            sleep_time = delay - time_since_last_request
            time.sleep(sleep_time)        # <-- BLOCKS while holding lock
        self._domain_last_request[domain] = time.time()
```

This is a **global lock**, not per-domain. When thread A sleeps for 2 seconds holding this lock (because Retry-After says so), threads B, C, D targeting *different domains* are all blocked. With `max_workers=10` and a 5-second Retry-After from one domain, you've effectively serialised your entire crawler.

The `AsyncRateLimiter` does this correctly (lines 221-234): it calculates sleep time under the lock, stamps the next-allowed time, releases the lock, *then* sleeps. The sync version needs the same pattern.

**Impact for FinanceCrawler:** When SEC.gov returns 429, your threads crawling Bloomberg IR pages will stall. At 50K pages/run this is a showstopper.

### 2.2 CRITICAL: In-Memory State Grows Without Bound

Several data structures grow monotonically during a crawl with no eviction:

| Structure | Location | Growth |
|---|---|---|
| `self.results` | `engine.py:169` | One dict entry per URL visited |
| `self.visited_urls` | `engine.py:167` | One string per URL visited |
| `self._discovered_from` | `engine.py:383` | One entry per URL enqueued |
| `self._discovery_method` | `engine.py:384` | One entry per URL enqueued |
| `ContentDeduplicator._content_hashes` | `deduplication.py:45` | One SHA-256 per unique page |
| `ContentDeduplicator._content_to_urls` | `deduplication.py:46` | One set per unique hash |

At 50K pages with average URL length 120 bytes:
- `visited_urls`: ~6 MB
- `results`: ~50-200 MB (stores `html_content`, headers, links per page)
- `_discovered_from` + `_discovery_method`: ~12 MB
- ContentDeduplicator: ~10 MB

**The `results` dict is the real problem.** It stores `html_content` (full HTML) for every visited URL. At 50K pages averaging 100KB each, that's ~5 GB of RAM just for `results`.

`retain_artifacts=False` only controls the `artifacts` dict, not `results`. The legacy `results` dict is always populated.

**Impact for FinanceCrawler:** 50K pages/run will OOM on a standard 8GB container. You must either remove the legacy `results` dict or add a flag to disable it.

### 2.3 CRITICAL: Dual State — `results` Dict vs `artifacts` Dict

The engine maintains two parallel representations of the same data:

1. `self.results[url]` — legacy dict with `status`, `headers`, `links`, `html_content`, `error`, etc.
2. `self.artifacts[url]` — `PageArtifact` instances

Both are populated in `_process_url()`. The `results` dict is deprecated (per `get_results()` docstring) but still written to on every URL. This doubles memory usage and creates a consistency risk: if a pipeline modifies the artifact, the `results` dict doesn't reflect the change.

### 2.4 HIGH: `ContentHashStore._connect()` Creates a New Connection Per Operation

**File:** `utils/content_hash_store.py:176-181`

```python
def _connect(self) -> sqlite3.Connection:
    conn = sqlite3.connect(self._db_path, check_same_thread=False)
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn
```

Every call to `record()`, `is_duplicate()`, or `get_blob_path()` opens a new SQLite connection, sets PRAGMAs, executes the query, and implicitly closes via `with` statement. At 50K pages this means 50K+ connection open/close cycles.

The same pattern exists in `IncrementalCrawler._connect()`.

SQLite connections are cheap, but PRAGMA execution on every call is wasteful, and `journal_mode = WAL` only needs to be set once per database (it's persistent). More importantly, this prevents SQLite's page cache from being reused across queries.

### 2.5 HIGH: `_apply_config()` Has a Fragile Attribute-Mapping Bug

**File:** `engine.py:472-494`

```python
for flag in (
    "enable_image_extraction", ...
):
    if hasattr(config, flag):
        setattr(self, flag.replace("enable_", "") + "_enabled"
                if flag.endswith("_extraction") or flag.endswith("_deduplication")
                else flag, getattr(config, flag))
```

This string-manipulation approach to mapping config flags to instance attributes is brittle. The logic is: if the flag ends with `_extraction` or `_deduplication`, transform `enable_X_extraction` → `X_extraction_enabled`. But `enable_pdf_extraction` would become `pdf_extraction_enabled`, while the actual instance attribute is `enable_pdf_extraction` (line 365). The code then *re-applies* the correct mapping on lines 483-494, overwriting the buggy result.

This works today by accident. Adding a new extraction flag will require updating two code paths.

### 2.6 HIGH: `BlobStore._save_pdf()` Relies on `raw_html` for PDF Bytes

**File:** `pipelines/blob_store.py:113-115`

```python
def _save_pdf(self, artifact: PageArtifact):
    data = artifact.content.raw_html.encode("latin-1", errors="replace")
```

PDF binary content is stored in `ContentInfo.raw_html` as a latin-1 decoded string (set in `engine.py:1057`). This round-trip (`bytes → str via latin-1 → bytes via latin-1`) is lossless for bytes 0x00-0xFF, but:

1. The field name `raw_html` for PDF binary content is semantically wrong and confusing.
2. If anyone ever changes the encoding or applies text normalization to `raw_html`, PDF blobs will silently corrupt.
3. `errors="replace"` in the decode path (engine.py:1057) means bytes that aren't valid latin-1 (there aren't any, since latin-1 maps all 256 byte values, but the `errors` flag signals uncertainty).

### 2.7 MEDIUM: `IncrementalState` Is In-Memory Only (Not Used by Engine)

`utils/incremental.py` contains two implementations:
1. `IncrementalState` — in-memory dict, no persistence across runs.
2. `IncrementalCrawler` — SQLite-backed, persistent.

The engine accepts `incremental=` which expects `IncrementalCrawler` (it calls `get_conditional_headers()` and `record_response()`). But `IncrementalState` has a completely different API (`set_url_state()`, `should_crawl()`). This creates a confusing API surface where two classes in the same file solve the same problem with incompatible interfaces.

### 2.8 MEDIUM: No Backpressure in Async Engine

`AsyncCrawler` uses `asyncio.Semaphore(max_concurrent_requests)` to limit concurrent fetches, but there's no backpressure mechanism between the queue consumer and pipeline writers. If the BlobStore disk is slow, the engine will keep fetching and building artifacts in memory until the semaphore limit. With `max_concurrent_requests=50` and large pages, this could spike memory before the pipelines catch up.

### 2.9 MEDIUM: `__init__.py` Exports 130+ Names

The top-level `__init__.py` eagerly imports everything: all extractors, all utilities, all security modules, all storage backends, all distributed crawling components. This means `import crawlit` loads ~25K lines of code, including BeautifulSoup, NLTK, aiohttp, and conditional imports for PostgreSQL, MongoDB, RabbitMQ, and Kafka.

For a library, this import overhead is significant. Users who only need `Crawler` + `ArtifactStore` shouldn't pay the cost of loading `WAFDetector` and `CaptchaDetector`.

### 2.10 LOW: No Context Manager Protocol on ArtifactStore

`ArtifactStore` opens file handles in `__init__` and requires `.close()` to be called. It implements `__del__` as a safety net, but `__del__` is not guaranteed to run (especially in interpreter shutdown). There's no `__enter__`/`__exit__`, so users can't use `with ArtifactStore(...)`. Same issue with `JSONLWriter` and `CrawlEventLog`.

---

## 3. Publish Readiness Checklist

| Item | Status | Notes |
|---|---|---|
| Stable data model with versioning | PASS | `PageArtifact` v1 with `validate_minimal()` |
| Clean plugin interfaces (ABCs) | PASS | `Fetcher`, `Extractor`, `Pipeline` well-defined |
| Type safety (sync rejects async) | PASS | `TypeError` at construction time |
| Thread safety on shared state | PASS with caveat | Locks present, but sync RateLimiter holds lock during sleep |
| Pipeline snapshot/restore | PASS | `copy()` before each stage, restore on failure |
| Incremental crawling (ETag/Last-Modified) | PASS | Conditional headers → 304 → skip |
| Cross-run deduplication | PASS | SQLite-backed ContentHashStore |
| Observability | PASS | CrawlEventLog with 10 typed events |
| Storage contract documented | PASS | ArtifactStore layout as class constants |
| Memory safety at scale | **FAIL** | Legacy `results` dict stores full HTML, no eviction |
| Dependency hygiene | WARN | `nltk` is a required dependency but only used by `KeywordExtractor` |
| API surface size | WARN | 130+ exports from `__init__.py` |
| Resource cleanup | WARN | No context manager protocol on file-owning classes |
| Python version support | PASS | `>=3.8` (but test with 3.12+; `asyncio.Lock()` behavior changed) |
| No secrets in code | PASS | No hardcoded credentials found |
| License | PASS | MIT |

### What Will Break When External Users Extend It

1. **Custom Fetcher implementations that return `raw_bytes` for PDFs.** The engine expects `response.content` (requests-style), not `FetchResult.raw_bytes`. The `FetchRequest`/`FetchResult` dataclasses exist but the engine's `_process_url()` still calls `fetch_page()` directly instead of going through `self.fetcher.fetch()`. The fetcher abstraction is only partially wired.

2. **Pipeline stages that modify `artifact.content.raw_html`.** The `copy()` method does `dataclasses.replace(self.content)` which is a *shallow* copy of `ContentInfo`. Since `raw_html` is a string (immutable), this is safe. But `extracted` is `dict(self.extracted)` — a shallow copy. If an extractor stores a mutable object (e.g., a list of dicts), a pipeline stage that mutates it will affect the snapshot. This is a latent bug waiting for a user to write a pipeline that modifies extracted data in-place.

3. **Users who subclass `Crawler`.** The `__init__` method is 300+ lines with 40+ parameters. There's no intermediate layer or builder pattern. Subclassing requires calling `super().__init__()` with the full parameter list, and any new parameter added to `Crawler.__init__` will break subclasses.

---

## 4. FinanceCrawler Stress Test

### Scenario A: Site Returns Intermittent 429s

**Handling:** `fetch_page()` in `crawler/fetcher.py` handles 429:
- Reads `Retry-After` header, caps at 120 seconds.
- Falls back to exponential backoff: `2^retry_count` seconds (max 32s).
- `DynamicRateLimiter.record_response()` doubles the per-domain delay on 429.
- `CrawlEventLog` emits `FETCH_RETRY` per attempt.

**Verdict: PASS with one issue.** The `DynamicRateLimiter` recovery is asymmetric: delay increases by `2x * adjustment_factor` on 429 but only decreases by `~10%` when responses are fast. After a burst of 429s, the crawler will be throttled for a long time even after the server recovers. For daily financial crawls with tight windows, consider adding a delay-reset-after-N-successes mechanism.

### Scenario B: Site Returns Malformed Content-Type

**Handling:** `ContentRouter._normalise()` does `content_type.split(";")[0].strip().lower()`. The engine checks `content_type_base == 'text/html'` after this normalisation.

**Problem:** If a server returns `Content-Type: ` (empty) or `Content-Type: text/plain` for HTML, the page won't be parsed for links. No warning is logged. The artifact's `content.raw_html` won't be populated. PDFs served as `application/octet-stream` won't trigger PDF extraction.

**Verdict: PARTIAL FAIL.** FinanceCrawler should register a custom pipeline that sniffs content (e.g., check for `<!DOCTYPE` or `%PDF-` magic bytes) when content-type is missing or generic.

### Scenario C: Same PDF Published at Different URLs

**Handling:** `BlobStore` uses content-addressed storage (`sha256.pdf`), so the same bytes produce the same blob path regardless of URL. `ContentHashStore` records the first URL that produced each hash.

**Problem:** Two different URLs both produce artifacts. Both artifacts get `blob_path` pointing to the same file. The `artifacts.jsonl` will contain two entries. Downstream consumers will see two artifacts with identical `content.blob_sha256` but different URLs.

**Verdict: PASS.** The architecture handles this correctly. Downstream dedup can `GROUP BY blob_sha256`. The blob is only written once to disk. However, note that `ContentDeduplicator` (in-memory) will skip the second URL entirely (`return` on line 948 in engine.py), meaning the second artifact won't be created at all. Whether this is desired depends on whether you want the URL→blob mapping in your artifact log. For FinanceCrawler, you probably want both URLs recorded — disable `ContentDeduplicator` and rely on `ContentHashStore` for blob-level dedup instead.

### Scenario D: Daily Crawl With 80% Unchanged Content

**Handling:** `IncrementalCrawler` sends `If-None-Match` / `If-Modified-Since` headers. On 304, the engine skips processing and emits `INCREMENTAL_HIT`.

**Efficiency:**
- 80% of pages → 304 response → no HTML parsing, no extraction, no blob write.
- 20% of pages → full processing.
- SQLite records updated per fetch regardless.
- `CrawlEventLog` records `INCREMENTAL_HIT` for observability.

**Problem:** `IncrementalCrawler` still fetches conditional headers from SQLite on every URL. At 50K URLs, that's 50K SQLite queries with connection open/close overhead. And 50K visited URLs are still held in memory.

**Verdict: PASS for correctness, WARN for performance.** The savings from skipping 80% of content processing far outweigh the SQLite overhead, but connection pooling would help.

### Scenario E: JS-Heavy SPA Site

**Handling:** `use_js_rendering=True` triggers Playwright-based rendering. The engine creates a new browser context per request to avoid threading issues.

**Problem 1:** Creating a new browser context per request is expensive. At 50K pages, this means 50K browser launches. Playwright contexts take ~100-500ms to create. This adds 1.4-7 hours of overhead.

**Problem 2:** The `JSEmbeddedDataExtractor` regex patterns (`\{.+?\}` with `DOTALL | MULTILINE`) use non-greedy matching on deeply nested JSON. For large `__NEXT_DATA__` payloads (common on financial dashboards with table data), this regex can exhibit catastrophic backtracking. The `_MAX_SCRIPT_CHARS = 500_000` guard helps but doesn't eliminate the risk.

**Problem 3:** If Playwright isn't installed, `use_js_rendering` silently falls back to `False` (line 348). FinanceCrawler should fail loudly if JS rendering is required but unavailable.

**Verdict: PARTIAL FAIL.** JS rendering works but the per-request browser context is too expensive for scale. The JSEmbeddedDataExtractor is the correct approach for extracting server-rendered state — this is exactly how modern earnings pages embed data. But the implementation needs browser context reuse.

### Scenario F: 50K Pages Per Run

**Memory:** With `retain_artifacts=True` and the legacy `results` dict, expect 5-10 GB RAM usage. Set `retain_artifacts=False` and fix the `results` dict issue.

**Disk:** BlobStore with content-addressed storage and cross-run dedup. Daily crawl writes only changed blobs. Efficient.

**SQLite:** `ContentHashStore` and `IncrementalCrawler` both create connections per query. At 50K pages with 2 queries each (incremental check + record), that's ~100K connection cycles. Expect ~10-20 seconds of overhead.

**Threading:** `max_workers=10` with the global-lock rate limiter means effective concurrency is limited by the slowest domain's Retry-After. Use the async engine instead.

**Verdict: FEASIBLE but needs the memory fix.** Use `AsyncCrawler`, `retain_artifacts=False`, `ArtifactStore` for persistence, and disable the legacy `results` dict.

---

## 5. Long-Term Maintainability Risks

### 5.1 Engine God-Class (6-12 month debt)

`Crawler.__init__` takes 40+ parameters. `_process_url` is ~450 lines with deeply nested conditionals (HTML vs PDF, cached vs fresh, incremental vs full). This is the most likely place where future feature additions will introduce bugs.

**Specific risk:** Adding a new content type (e.g., XML RSS feeds for financial filings) requires modifying `_process_url` directly. The `ContentRouter` exists but is not wired into the engine — the engine still uses hardcoded `if content_type_base == 'text/html'` / `elif content_type_base == 'application/pdf'` branches.

**6-month prediction:** Someone will add XBRL extraction (SEC filings) by adding another `elif` branch in `_process_url`. Then someone will add XML sitemap news extension parsing. Then someone will add RSS feed support. Each branch will duplicate the pattern of "parse content, run extractors, update artifact, run pipelines." By month 12 `_process_url` will be 800+ lines.

**Fix:** Wire `ContentRouter` into the engine. Each content type gets a handler method. `_process_url` becomes: fetch → route → extract → pipeline. New types are added by registering a handler, not modifying engine code.

### 5.2 Sync/Async Code Duplication (Already Debt)

`engine.py` (1,520 lines) and `async_engine.py` (1,193 lines) are ~80% identical. Every bug fix or feature addition must be applied to both files. The config application, URL filtering, extraction, pipeline execution, and result storage logic is duplicated.

**6-month prediction:** Features will drift. One engine will get a fix the other doesn't. Integration tests will pass for one engine and fail for the other.

### 5.3 Legacy `results` Dict Cannot Be Removed Without Breaking Users

`get_results()` is deprecated but `results` is a public attribute. External code that accesses `crawler.results[url]['html_content']` will break when you remove it. You need a deprecation cycle:
1. Log a warning when `results` is accessed.
2. Add `__getattr__` deprecation on `results`.
3. Remove in v2.0.

### 5.4 `__init__.py` Import Cascade

Every `import crawlit` triggers imports of all extractors, all utilities, all security modules. If any optional dependency is missing (e.g., `pdfplumber`), the import chain must handle it gracefully. Currently `PDFExtractor` does (it checks `is_pdf_available()`), but adding a new extractor with a mandatory import will break `import crawlit` for all users.

### 5.5 SQLite Contention Under Multi-Process Deployment

`ContentHashStore` and `IncrementalCrawler` use SQLite with WAL mode. WAL allows concurrent readers but only one writer. If FinanceCrawler runs multiple crawler processes against the same SQLite DB (e.g., one per source domain), writers will block on SQLite's write lock with `busy_timeout=5000ms`. After 5 seconds, the operation raises `OperationalError: database is locked`.

For a daily cron job with one crawler process, this is fine. For parallel multi-process deployment, you'll need to either shard the SQLite DB per process or switch to PostgreSQL.

---

## 6. Final Verdict

### Ready to Publish? **Yes, with two mandatory fixes.**

The core architecture (PageArtifact, plugin ABCs, pipeline chain, ArtifactStore contract, CrawlEventLog) is production-quality and well-designed for its purpose. The separation of concerns is clean at the data model and interface level. The incremental crawling, cross-run deduplication, and structured observability are exactly what FinanceCrawler needs.

### Mandatory Before Publish (blocks correctness at scale):

1. **Fix the sync `RateLimiter` lock-while-sleeping bug.** Adopt the pattern from `AsyncRateLimiter`: calculate sleep time under lock, stamp next-allowed time, release lock, then sleep. Without this, multi-threaded crawling is effectively serialised.

2. **Add a flag to disable the legacy `results` dict population in `_process_url()`.** Currently there's no way to avoid storing full HTML content in `self.results` even when `retain_artifacts=False`. At 50K pages this causes OOM. Either gate the `results` writes behind a flag (`populate_legacy_results=False`) or make the artifact system the single source of truth and stop populating `results` entirely.

### Strongly Recommended Before FinanceCrawler (blocks performance at target scale):

3. **Wire `ContentRouter` into the engine** to replace hardcoded content-type branches. This is a ~2 hour refactor that pays for itself immediately when you need to add XBRL/XML content handling.

4. **Pool SQLite connections** in `ContentHashStore` and `IncrementalCrawler`. Keep a single connection per instance instead of creating one per query.

5. **Add `__enter__`/`__exit__`** to `ArtifactStore`, `JSONLWriter`, and `CrawlEventLog` for proper resource cleanup.

### Does NOT Need Major Redesign

The architecture is sound. The data model is correct. The plugin system works. The storage contract is stable. The sync/async duplication is debt but not blocking. The engine god-class is the main refactor target, but it works correctly today.

**Ship it.** Fix items 1-2, then publish. Fix items 3-5 before the first FinanceCrawler production run.
