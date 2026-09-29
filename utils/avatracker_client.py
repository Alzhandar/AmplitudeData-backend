import logging
import math
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional

import requests
from requests import HTTPError
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

_IIN_NOT_FOUND = '__not_found__'


class AvatrackerClient:
    """HTTP-client for avatracker.online — the employee database (replaces
    bigdata's own employee tables). Used to look up an employee and to let
    them switch which phone number they use for the employee discount."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        token: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
    ) -> None:
        self.base_url = (base_url or settings.AVATRACKER_BASE_URL).rstrip('/')
        self.token = token or settings.AVATRACKER_TOKEN
        self.timeout_seconds = timeout_seconds or settings.AVATRACKER_TIMEOUT_SECONDS

    def find_employee_by_phone(self, phone_number: str) -> Optional[Dict]:
        response = requests.get(
            f'{self.base_url}/employees/',
            params={'phone': phone_number},
            headers=self._headers(),
            timeout=self.timeout_seconds,
        )
        self._raise_for_status(response)
        employees = self._extract_employees(response.json())
        return employees[0] if employees else None

    def find_employee_by_iin(self, iin: str) -> Optional[Dict]:
        """/employees/<id>/ also accepts the ИИН directly in place of the numeric
        id (confirmed live: GET /employees/<iin>/ returns that employee's detail,
        a 404 for an unknown one) — a single request, no need to page through the
        list endpoint (whose own ?iin= filter is ignored server-side)."""
        normalized_iin = str(iin or '').strip()
        if not normalized_iin:
            return None

        cache_key = f'avatracker_iin_{normalized_iin}'
        cached = cache.get(cache_key)
        if cached is not None:
            return None if cached == _IIN_NOT_FOUND else cached

        response = requests.get(
            f'{self.base_url}/employees/{normalized_iin}/',
            headers=self._headers(),
            timeout=self.timeout_seconds,
        )
        if response.status_code == 404:
            cache.set(cache_key, _IIN_NOT_FOUND, 60)
            return None

        self._raise_for_status(response)
        payload = response.json()
        employee = payload.get('data') if isinstance(payload, dict) else None
        if not isinstance(employee, dict) and isinstance(payload, dict):
            employee = payload

        cache.set(cache_key, employee if employee else _IIN_NOT_FOUND, 300 if employee else 60)
        return employee

    def update_employee_phone(self, iin: str, new_phone: str) -> Dict:
        """The detail routes (GET/PATCH/PUT/DELETE) resolve only by ИИН — the
        numeric `id` a list/search response also carries does NOT work here
        (confirmed live: /employees/<numeric id>/ 404s with "Сотрудник с ИИН
        '<id>' не найден", same as any other unknown ИИН)."""
        response = requests.patch(
            f'{self.base_url}/employees/{iin}/',
            json={'phone': new_phone},
            headers=self._headers(),
            timeout=self.timeout_seconds,
        )
        self._raise_for_status(response)
        if not response.text.strip():
            return {}
        return response.json()

    def list_positions(self) -> List[Dict]:
        """All positions ({name, guid_1c}), ~350 of them across a handful of
        pages. Position names are not unique — about 1 in 7 is shared by
        several distinct GUIDs (no department/org field on Position itself)."""
        return self._list_all_pages(f'{self.base_url}/position/')

    def list_all_employees(self, max_workers: int = 12) -> List[Dict]:
        """Full employee directory (2000+ records, paginated) — expensive,
        callers should cache the result. Used to disambiguate positions that
        share a name, by seeing which division/park each GUID is actually
        used in."""
        return self._list_all_pages(f'{self.base_url}/employees/', max_workers=max_workers)

    def _list_all_pages(self, url: str, max_workers: int = 12) -> List[Dict]:
        first_page = self._get_page(url, page=1)
        items = self._extract_employees(first_page)

        total_count = int(first_page.get('count') or 0)
        page_size = len(items) or 50
        total_pages = math.ceil(total_count / page_size) if page_size else 1

        if total_pages <= 1:
            return items

        pages: Dict[int, List[Dict]] = {1: items}
        with ThreadPoolExecutor(max_workers=min(max_workers, total_pages - 1)) as executor:
            futures = {
                executor.submit(self._get_page, url, page): page
                for page in range(2, total_pages + 1)
            }
            for future in as_completed(futures):
                page_number = futures[future]
                pages[page_number] = self._extract_employees(future.result())

        ordered: List[Dict] = []
        for page_number in range(1, total_pages + 1):
            ordered.extend(pages.get(page_number, []))
        return ordered

    def _get_page(self, url: str, page: int) -> Dict:
        response = requests.get(
            url,
            params={'page': page},
            headers=self._headers(),
            timeout=self.timeout_seconds,
        )
        self._raise_for_status(response)
        return response.json()

    def _extract_employees(self, payload) -> List[Dict]:
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            results = payload.get('results')
            if isinstance(results, dict):
                data = results.get('data')
                return data if isinstance(data, list) else []
            if isinstance(results, list):
                return results
            data = payload.get('data')
            return data if isinstance(data, list) else []
        return []

    def _headers(self) -> Dict[str, str]:
        return {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json',
        }

    def _raise_for_status(self, response: requests.Response) -> None:
        try:
            response.raise_for_status()
        except HTTPError as exc:
            detail = response.text.strip()
            logger.warning(
                'avatracker_api_error',
                extra={'status_code': response.status_code, 'url': response.url, 'detail': detail[:500]},
            )
            if detail:
                raise ValueError(f'Avatracker API error: {detail}') from exc
            raise ValueError('Avatracker API request failed') from exc
