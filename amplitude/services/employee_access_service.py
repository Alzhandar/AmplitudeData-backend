from typing import Optional

import requests
from django.conf import settings

from amplitude.models import AllowedEmployeePosition


class EmployeeAccessService:
    def __init__(self) -> None:
        self.base_url = (settings.AVATARIYA_BASE_URL or '').rstrip('/')
        self.bearer_token = settings.AVATARIYA_BEARER_TOKEN
        self.timeout_seconds = settings.AVATARIYA_TIMEOUT_SECONDS
    def can_access_site(self, iin: str) -> bool:
        normalized = (iin or '').strip()
        if not normalized:
            return False
        return self._has_allowed_position(normalized)

    def _has_allowed_position(self, iin: str) -> bool:
        if not self.base_url:
            return False

        headers = {'Content-Type': 'application/json'}
        if self.bearer_token:
            headers['Authorization'] = f'Bearer {self.bearer_token}'

        endpoint = f'{self.base_url}/employees/{iin}/'
        try:
            response = requests.get(endpoint, headers=headers, timeout=self.timeout_seconds)
        except requests.RequestException:
            return False

        if response.status_code == 404:
            return False
        if response.status_code >= 400:
            return False

        try:
            payload = response.json()
        except ValueError:
            return False

        if not bool(payload.get('success')):
            return False

        data = payload.get('data') or {}
        position_guid = str(data.get('position') or '').strip()
        if not position_guid:
            return False

        return AllowedEmployeePosition.objects.filter(
            position_guid=position_guid,
            is_active=True,
        ).exists()
