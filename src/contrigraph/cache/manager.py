"""Local caching system for contribution calendars."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from contrigraph.models.calendar import ContributionCalendar
from contrigraph.utils.platform import PlatformPaths


class CacheManager:
    """Manages local JSON cache for contribution data with TTL expiration."""

    def __init__(self, cache_dir: Path | None = None) -> None:
        self.cache_dir = cache_dir or PlatformPaths.get_cache_dir()

    def _get_cache_file(self, username: str, year: int | None) -> Path:
        """Derive cache file path for given username and year."""
        safe_user = "".join(c for c in username.lower() if c.isalnum() or c in ("-", "_"))
        year_str = str(year) if year is not None else "recent"
        return self.cache_dir / f"contributions_{safe_user}_{year_str}.json"

    def get(
        self,
        username: str,
        year: int | None = None,
        ttl_hours: int = 4,
    ) -> ContributionCalendar | None:
        """Retrieve cached ContributionCalendar if present and valid."""
        cache_file = self._get_cache_file(username, year)
        if not cache_file.exists():
            return None

        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                payload = json.load(f)

            fetched_at_str = payload.get("fetched_at")
            if not fetched_at_str:
                return None

            fetched_at = datetime.fromisoformat(fetched_at_str)
            now = datetime.now(timezone.utc)
            if fetched_at.tzinfo is None:
                fetched_at = fetched_at.replace(tzinfo=timezone.utc)

            # Historical completed years do not expire unless explicitly invalidated
            current_year = now.year
            is_past_year = year is not None and year < current_year

            if not is_past_year:
                age_seconds = (now - fetched_at).total_seconds()
                if age_seconds > (ttl_hours * 3600):
                    return None

            data = payload.get("data", {})
            return ContributionCalendar.from_dict(data)
        except Exception:
            return None

    def set(self, calendar: ContributionCalendar) -> None:
        """Save ContributionCalendar to disk cache."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = self._get_cache_file(calendar.username, calendar.year)

        payload = {
            "username": calendar.username,
            "year": calendar.year,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "data": calendar.to_dict(),
        }

        temp_file = cache_file.with_suffix(".tmp")
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            temp_file.replace(cache_file)
        except Exception:
            if temp_file.exists():
                temp_file.unlink(missing_ok=True)

    def invalidate(self, username: str, year: int | None = None) -> None:
        """Invalidate specific cached dataset."""
        cache_file = self._get_cache_file(username, year)
        if cache_file.exists():
            cache_file.unlink()

    def clear_all(self) -> int:
        """Remove all contrigraph cache files."""
        count = 0
        if not self.cache_dir.exists():
            return 0
        for f in self.cache_dir.glob("contributions_*.json"):
            try:
                f.unlink()
                count += 1
            except OSError:
                pass
        return count

    def get_cache_entries(self) -> list[dict[str, Any]]:
        """List summary of all cached calendar files."""
        entries = []
        if not self.cache_dir.exists():
            return entries

        for path in self.cache_dir.glob("contributions_*.json"):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    payload = json.load(f)
                entries.append(
                    {
                        "path": str(path),
                        "username": payload.get("username", "unknown"),
                        "year": payload.get("year"),
                        "fetched_at": payload.get("fetched_at", ""),
                        "size_bytes": path.stat().st_size,
                    }
                )
            except Exception:
                continue
        return entries
