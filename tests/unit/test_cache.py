"""Unit tests for cache manager."""

from contrigraph.cache.manager import CacheManager
from contrigraph.data.normalizer import ContributionNormalizer
from tests.fixtures.mock_data import make_mock_calendar_payload


def test_cache_set_and_get(temp_dir):
    """Verify storing and retrieving calendar from cache."""
    cache_dir = temp_dir / "cache"
    mgr = CacheManager(cache_dir=cache_dir)

    payload = make_mock_calendar_payload("cacheuser", total_contributions=250)
    cal = ContributionNormalizer.normalize_graphql_response(payload, "cacheuser", 2026)

    assert mgr.get("cacheuser", 2026) is None

    mgr.set(cal)
    cached = mgr.get("cacheuser", 2026, ttl_hours=4)
    assert cached is not None
    assert cached.username == "cacheuser"
    assert cached.total_contributions == 250

    # Invalidation
    mgr.invalidate("cacheuser", 2026)
    assert mgr.get("cacheuser", 2026) is None


def test_cache_clear_all_and_list(temp_dir):
    """Verify cache entries listing and clearing."""
    cache_dir = temp_dir / "cache"
    mgr = CacheManager(cache_dir=cache_dir)

    payload1 = make_mock_calendar_payload("user1", total_contributions=50)
    cal1 = ContributionNormalizer.normalize_graphql_response(payload1, "user1", 2025)
    payload2 = make_mock_calendar_payload("user2", total_contributions=75)
    cal2 = ContributionNormalizer.normalize_graphql_response(payload2, "user2", 2026)

    mgr.set(cal1)
    mgr.set(cal2)

    entries = mgr.get_cache_entries()
    assert len(entries) == 2

    cleared_count = mgr.clear_all()
    assert cleared_count == 2
    assert len(mgr.get_cache_entries()) == 0
