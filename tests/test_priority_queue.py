"""Tests for crawlit.utils.priority_queue module."""

import pytest
from crawlit.utils.priority_queue import (
    PrioritizedURL,
    BreadthFirstStrategy,
    DepthFirstStrategy,
    SitemapPriorityStrategy,
    URLPatternStrategy,
    CompositeStrategy,
    URLPriorityQueue,
    get_strategy,
)


class TestPrioritizedURL:
    def test_construction(self):
        pu = PrioritizedURL(url="https://example.com", depth=2, priority=0.5)
        assert pu.url == "https://example.com"
        assert pu.depth == 2

    def test_to_tuple(self):
        pu = PrioritizedURL(url="https://example.com", depth=3, priority=0.0)
        t = pu.to_tuple()
        assert t == ("https://example.com", 3)


class TestBreadthFirstStrategy:
    def test_priority_increases_with_depth(self):
        s = BreadthFirstStrategy()
        p0 = s.calculate_priority("https://example.com", depth=0)
        p1 = s.calculate_priority("https://example.com/a", depth=1)
        p2 = s.calculate_priority("https://example.com/a/b", depth=2)
        assert p0 < p1 < p2


class TestDepthFirstStrategy:
    def test_priority_decreases_with_depth(self):
        s = DepthFirstStrategy()
        p0 = s.calculate_priority("https://example.com", depth=0)
        p1 = s.calculate_priority("https://example.com/a", depth=1)
        assert p0 > p1


class TestSitemapPriorityStrategy:
    def test_with_sitemap_priority(self):
        s = SitemapPriorityStrategy()
        p = s.calculate_priority(
            "https://example.com", depth=0,
            metadata={"sitemap_priority": 0.9}
        )
        assert p < 1.0

    def test_without_metadata(self):
        s = SitemapPriorityStrategy()
        p = s.calculate_priority("https://example.com", depth=0)
        assert isinstance(p, float)


class TestURLPatternStrategy:
    def test_high_priority_pattern(self):
        s = URLPatternStrategy(high_priority_patterns=[r"/important/"])
        p_important = s.calculate_priority("https://example.com/important/page", depth=1)
        p_normal = s.calculate_priority("https://example.com/other/page", depth=1)
        assert p_important <= p_normal

    def test_low_priority_pattern(self):
        s = URLPatternStrategy(low_priority_patterns=[r"\.pdf$"])
        p_pdf = s.calculate_priority("https://example.com/doc.pdf", depth=1)
        p_html = s.calculate_priority("https://example.com/page.html", depth=1)
        assert p_pdf >= p_html


class TestCompositeStrategy:
    def test_weighted_combination(self):
        bfs = BreadthFirstStrategy()
        dfs = DepthFirstStrategy()
        composite = CompositeStrategy([(bfs, 0.5), (dfs, 0.5)])
        p = composite.calculate_priority("https://example.com", depth=1)
        assert isinstance(p, float)


class TestURLPriorityQueue:
    def test_put_and_get(self):
        q = URLPriorityQueue()
        q.put("https://example.com", depth=0)
        url, depth = q.get()
        assert url == "https://example.com"
        assert depth == 0

    def test_priority_ordering(self):
        q = URLPriorityQueue(strategy=BreadthFirstStrategy())
        q.put("https://example.com/deep", depth=5)
        q.put("https://example.com/shallow", depth=0)
        url, depth = q.get()
        assert depth == 0

    def test_empty(self):
        q = URLPriorityQueue()
        assert q.empty() is True
        q.put("https://example.com", depth=0)
        assert q.empty() is False

    def test_qsize(self):
        q = URLPriorityQueue()
        assert q.qsize() == 0
        q.put("https://example.com", depth=0)
        assert q.qsize() == 1


class TestGetStrategy:
    def test_breadth_first(self):
        s = get_strategy("breadth-first")
        assert isinstance(s, BreadthFirstStrategy)

    def test_depth_first(self):
        s = get_strategy("depth-first")
        assert isinstance(s, DepthFirstStrategy)

    def test_sitemap(self):
        s = get_strategy("sitemap-priority")
        assert isinstance(s, SitemapPriorityStrategy)

    def test_unknown_falls_back_to_bfs(self):
        s = get_strategy("nonexistent_strategy")
        assert isinstance(s, BreadthFirstStrategy)
