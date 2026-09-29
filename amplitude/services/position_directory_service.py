from __future__ import annotations

import logging
from collections import Counter
from typing import Dict, List, Optional, Tuple

from django.core.cache import cache

from utils.avatracker_client import AvatrackerClient

logger = logging.getLogger(__name__)

_CHOICES_CACHE_KEY = 'position_directory_choices_v1'
_CACHE_TTL_SECONDS = 6 * 60 * 60  # positions/org assignments change rarely


class PositionDirectoryService:
    """Human-readable (guid, label) choices for granting portal page access.

    avatracker's own /position/ list carries only {name, guid_1c} — no
    department/org field — and about 1 in 7 names is shared by several
    distinct GUIDs (e.g. "IT специалист" x5). Ambiguous ones are disambiguated
    by cross-referencing which division/park actually employs each GUID.
    """

    def __init__(self, avatracker_client: Optional[AvatrackerClient] = None) -> None:
        self.avatracker_client = avatracker_client or AvatrackerClient()

    def list_choices(self, force_refresh: bool = False) -> List[Tuple[str, str]]:
        if not force_refresh:
            cached = cache.get(_CHOICES_CACHE_KEY)
            if cached is not None:
                return cached

        choices = self._build_choices()
        cache.set(_CHOICES_CACHE_KEY, choices, _CACHE_TTL_SECONDS)
        return choices

    def _build_choices(self) -> List[Tuple[str, str]]:
        try:
            positions = self.avatracker_client.list_positions()
        except Exception:
            logger.exception('position_directory_list_positions_failed')
            return []

        name_counts = Counter(str(p.get('name') or '') for p in positions)
        duplicate_names = {name for name, count in name_counts.items() if count > 1 and name}

        division_by_guid: Dict[str, Counter] = {}
        if duplicate_names:
            division_by_guid = self._build_division_index()

        choices: List[Tuple[str, str]] = []
        for position in sorted(positions, key=lambda p: (str(p.get('name') or ''), str(p.get('guid_1c') or ''))):
            guid = str(position.get('guid_1c') or '').strip()
            name = str(position.get('name') or '').strip() or '(без названия)'
            if not guid:
                continue

            if name in duplicate_names:
                # avatracker's guid_1c values share a long common tail across
                # many unrelated records (looks like a per-tenant/install
                # segment) — the leading segment is what's actually unique per
                # record, so that's what's shown as the tiebreaker, not the tail.
                guid_hint = guid.split('-', 1)[0] or guid[:8]
                divisions = division_by_guid.get(guid)
                if divisions:
                    top_division, count = divisions.most_common(1)[0]
                    label = f'{name} — {top_division} ({count} чел., {guid_hint})'
                else:
                    label = f'{name} — нет сотрудников на этой должности ({guid_hint})'
            else:
                label = name

            choices.append((guid, label))

        return choices

    def _build_division_index(self) -> Dict[str, Counter]:
        """One-time full employee scan (paginated, 2000+ records) to see which
        division/park each ambiguous position GUID is actually used in."""
        index: Dict[str, Counter] = {}
        try:
            employees = self.avatracker_client.list_all_employees()
        except Exception:
            logger.exception('position_directory_employee_scan_failed')
            return index

        for employee in employees:
            position_guid = str(employee.get('position') or '').strip()
            if not position_guid:
                continue
            label = str(employee.get('division_name') or employee.get('park_name') or '').strip()
            if not label:
                continue
            index.setdefault(position_guid, Counter())[label] += 1

        return index
