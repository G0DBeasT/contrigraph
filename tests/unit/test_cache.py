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


def test_historical_year_cache_permanence_rules(temp_dir):
    """Verify historical year caching only bypasses TTL if fetched after that year concluded."""
    import json
    cache_dir = temp_dir / "cache"
    mgr = CacheManager(cache_dir=cache_dir)
    payload = make_mock_calendar_payload("histuser", total_contributions=100)

    # 1. Year 2024 fetched in 2025 (completed year) -> should NOT expire
    cal_2024 = ContributionNormalizer.normalize_graphql_response(payload, "histuser", 2024)
    mgr.set(cal_2024)
    cache_file_2024 = mgr._get_cache_file("histuser", 2024)
    with open(cache_file_2024, "r", encoding="utf-8") as f:
        data_2024 = json.load(f)
    data_2024["fetched_at"] = "2025-01-15T12:00:00+00:00"
    with open(cache_file_2024, "w", encoding="utf-8") as f:
        json.dump(data_2024, f)

    cached_2024 = mgr.get("histuser", 2024, ttl_hours=4)
    assert cached_2024 is not None
    assert cached_2024.year == 2024

    # 2. Year 2025 fetched mid-year in 2025 (partial year) -> SHOULD expire when queried in 2026
    cal_2025 = ContributionNormalizer.normalize_graphql_response(payload, "histuser", 2025)
    mgr.set(cal_2025)
    cache_file_2025 = mgr._get_cache_file("histuser", 2025)
    with open(cache_file_2025, "r", encoding="utf-8") as f:
        data_2025 = json.load(f)
    data_2025["fetched_at"] = "2025-06-15T12:00:00+00:00"
    with open(cache_file_2025, "w", encoding="utf-8") as f:
        json.dump(data_2025, f)

    cached_2025 = mgr.get("histuser", 2025, ttl_hours=4)
    assert cached_2025 is None


def test_concurrent_cache_writes(temp_dir):
    """Verify concurrent write operations do not collide or corrupt cache files."""
    import concurrent.futures
    cache_dir = temp_dir / "cache"
    mgr = CacheManager(cache_dir=cache_dir)
    payload = make_mock_calendar_payload("concurrentuser", total_contributions=300)
    cal = ContributionNormalizer.normalize_graphql_response(payload, "concurrentuser", 2026)

    def write_op(idx: int):
        mgr.set(cal)
        return True

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(write_op, i) for i in range(20)]
        results = [f.result() for f in futures]

    assert all(results)
    cached = mgr.get("concurrentuser", 2026, ttl_hours=4)
    assert cached is not None
    assert cached.username == "concurrentuser"
    assert cached.total_contributions == 300


def test_cache_allow_stale(temp_dir):
    """Verify expired cache returns None by default but returns calendar with allow_stale=True."""
    import json
    cache_dir = temp_dir / "cache"
    mgr = CacheManager(cache_dir=cache_dir)
    payload = make_mock_calendar_payload("staleuser", total_contributions=150)
    cal = ContributionNormalizer.normalize_graphql_response(payload, "staleuser", 2026)

    mgr.set(cal)
    cache_file = mgr._get_cache_file("staleuser", 2026)
    with open(cache_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Set timestamp to 24 hours ago
    data["fetched_at"] = "2020-01-01T00:00:00+00:00"
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(data, f)

    # Standard get with 4h TTL should return None (expired)
    assert mgr.get("staleuser", 2026, ttl_hours=4) is None
    assert mgr.get("staleuser", 2026, ttl_hours=4, allow_stale=False) is None

    # Stale get should successfully return the calendar
    stale_cal = mgr.get("staleuser", 2026, ttl_hours=4, allow_stale=True)
    assert stale_cal is not None
    assert stale_cal.username == "staleuser"
    assert stale_cal.total_contributions == 150



