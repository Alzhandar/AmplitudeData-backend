from typing import Any, Dict, List, Optional

import requests
from requests import HTTPError
from django.conf import settings


class MobileClient:
    def __init__(
        self,
        base_url: Optional[str] = None,
        token: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
    ) -> None:
        self.base_url = (base_url or settings.MOBILE_CLIENT_BASE_URL).rstrip('/')
        self.token = token or settings.MOBILE_CLIENT_TOKEN
        self.timeout_seconds = timeout_seconds or settings.MOBILE_CLIENT_TIMEOUT_SECONDS

    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        response = requests.get(
            f'{self.base_url}/{path.lstrip("/")}',
            params=params,
            headers=self._headers(),
            timeout=self.timeout_seconds,
        )
        self._raise_for_status(response)
        return response.json()

    def post(self, path: str, payload: Optional[Dict[str, Any]] = None) -> Any:
        response = requests.post(
            f'{self.base_url}/{path.lstrip("/")}',
            json=payload,
            headers=self._headers(),
            timeout=self.timeout_seconds,
        )
        self._raise_for_status(response)
        return response.json()

    def send_mass_push(
        self,
        phone_numbers: List[str],
        title: str,
        body: str,
        title_kz: str = '',
        body_kz: str = '',
        city: str = '',
        park: str = '',
        notification_type: str = 'default',
        survey_id: Optional[int] = None,
        review_id: Optional[int] = None,
    ) -> None:
        """Send a mass push notification. Returns None on success (204 No Content)."""
        payload: Dict[str, Any] = {
            'phone_numbers': phone_numbers,
            'title': title,
            'body': body,
            'title_kz': title_kz,
            'body_kz': body_kz,
            'city': city,
            'park': park,
            'notification_type': notification_type,
        }
        if survey_id is not None:
            payload['survey_id'] = survey_id
        if review_id is not None:
            payload['review_id'] = review_id

        response = requests.post(
            f'{self.base_url}/api/notifications/send-mass-push/',
            json=payload,
            headers=self._headers(),
            timeout=self.timeout_seconds,
        )
        self._raise_for_status(response)

    def _headers(self) -> Dict[str, str]:
        return {
            'Authorization': f'Token {self.token}',
            'Content-Type': 'application/json',
        }

    def _raise_for_status(self, response: requests.Response) -> None:
        try:
            response.raise_for_status()
        except HTTPError as exc:
            detail = response.text.strip()
            if detail:
                raise ValueError(f'Mobile API error: {detail}') from exc
            raise ValueError('Mobile API request failed') from exc
