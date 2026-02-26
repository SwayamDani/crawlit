"""crawlit.fetchers - Built-in Fetcher implementations."""

from .http_fetcher import DefaultFetcher, DefaultAsyncFetcher

__all__ = [
    "DefaultFetcher",
    "DefaultAsyncFetcher",
]
