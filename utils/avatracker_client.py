import logging
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

    def update_employee_phone(self, employee_id, new_phone: str) -> Dict:
        response = requests.patch(
            f'{self.base_url}/employees/{employee_id}/',
            json={'phone': new_phone},
            headers=self._headers(),
            timeout=self.timeout_seconds,
        )
        self._raise_for_status(response)
        if not response.text.strip():
            return {}
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
