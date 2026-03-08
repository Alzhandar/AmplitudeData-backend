from typing import Dict, Iterable, List, Optional

import requests
from requests import HTTPError
from django.conf import settings


class AvatariyaClient:
    def __init__(
        self,
        base_url: Optional[str] = None,
        bearer_token: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
        phones_batch_size: Optional[int] = None,
    ) -> None:
        self.base_url = (base_url or settings.AVATARIYA_BASE_URL).rstrip('/')
        self.bearer_token = bearer_token or settings.AVATARIYA_BEARER_TOKEN
        self.timeout_seconds = timeout_seconds or settings.AVATARIYA_TIMEOUT_SECONDS
        self.phones_batch_size = phones_batch_size or settings.AVATARIYA_PHONES_BATCH_SIZE

    def visit_search_by_date_phones(self, start_date: str, end_date: str, phones: List[str]) -> Dict:
        if not self.bearer_token:
            raise ValueError('AVATARIYA_BEARER_TOKEN must be set')

        payload = {
            'start_date': start_date,
            'end_date': end_date,
            'phones': phones,
        }

        response = requests.post(
            f'{self.base_url}/visit-search-by-date-phones/',
            json=payload,
            headers=self._headers(),
            timeout=self.timeout_seconds,
        )
        try:
            response.raise_for_status()
        except HTTPError as exc:
            detail = response.text.strip()
            if detail:
                raise ValueError(f'Avatariya API error: {detail}') from exc
            raise ValueError('Avatariya API request failed') from exc
        return response.json()

    def visit_search_all_by_date_phones(self, start_date: str, end_date: str, phones: List[str]) -> List[Dict]:
        unique_phones = list(dict.fromkeys(phones))
        if not unique_phones:
            return []

        results: List[Dict] = []
        for phone_chunk in self._chunked(unique_phones, self.phones_batch_size):
            payload = {
                'start_date': start_date,
                'end_date': end_date,
                'phones': phone_chunk,
            }
            data = self.visit_search_by_date_phones(start_date=start_date, end_date=end_date, phones=phone_chunk)
            results.extend(self._collect_results_with_pagination(data, payload=payload))

        return results

    def _collect_results_with_pagination(self, first_page: Dict, payload: Dict) -> List[Dict]:
        results = list(first_page.get('results', []))
        next_url = first_page.get('next')

        while next_url:
            response = requests.post(
                next_url,
                json=payload,
                headers=self._headers(),
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            page = response.json()
            results.extend(page.get('results', []))
            next_url = page.get('next')

        return results

    def _chunked(self, items: List[str], size: int) -> Iterable[List[str]]:
        if size <= 0:
            size = 100

        for index in range(0, len(items), size):
            yield items[index:index + size]

    def _headers(self) -> Dict[str, str]:
        return {
            'Authorization': f'Bearer {self.bearer_token}',
            'Content-Type': 'application/json',
        }
