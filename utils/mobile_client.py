from typing import IO, Any, Dict, List, Optional

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
            self._url(path),
            params=params,
            headers=self._headers(),
            timeout=self.timeout_seconds,
        )
        self._raise_for_status(response)
        return response.json()

    def post(self, path: str, payload: Optional[Dict[str, Any]] = None) -> Any:
        last_response: Optional[requests.Response] = None

        for candidate in self._build_post_candidates(path):
            response = self._post_json(self._url(candidate), payload)
            last_response = response

            if response.status_code < 400:
                return self._json_or_empty(response)

            # Keep trying path variants for common deployment mismatches.
            if response.status_code in {404, 405}:
                continue

            self._raise_for_status(response)

        if last_response is None:
            raise ValueError('Mobile API request failed: no request candidates were generated')

        self._raise_for_status(last_response)
        return self._json_or_empty(last_response)

    def send_mass_push(
        self,
        phone_numbers: Optional[List[str]],
        title: str,
        body: str,
        title_kz: str = '',
        body_kz: str = '',
        city: str = '',
        park: str = '',
        notification_type: str = 'default',
        survey_id: Optional[int] = None,
        review_id: Optional[int] = None,
    ) -> Optional[int]:
        """Send a mass push notification and return notification id when API provides it."""
        normalized_city = str(city).strip()
        normalized_phones: Optional[List[str]]
        if phone_numbers is None:
            if not normalized_city:
                raise ValueError('phone_numbers cannot be null when city is empty')
            normalized_phones = None
        else:
            normalized_phones = [str(value).strip() for value in phone_numbers if str(value).strip()]
            if not normalized_phones and not normalized_city:
                raise ValueError('phone_numbers cannot be empty when city is empty')

        payload: Dict[str, Any] = {
            'phone_numbers': normalized_phones,
            'title': title,
            'body': body,
            'title_kz': title_kz,
            'body_kz': body_kz,
            'city': normalized_city,
            'park': park,
            'notification_type': notification_type,
        }
        if survey_id is not None:
            payload['survey_id'] = survey_id
        if review_id is not None:
            payload['review_id'] = review_id

        parsed = self.post('/api/notifications/send-mass-push/', payload)
        return self._extract_notification_id(parsed)

    def create_story(
        self,
        logo: IO[bytes],
        city: int,
        start_date: str,
        end_date: str,
        title: str = '',
        is_active: bool = True,
        story_type: str = 'DEFAULT',
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Create a Story. Returns the created story dict (including its id)."""
        data: Dict[str, Any] = {
            'city': city,
            'start_date': start_date,
            'end_date': end_date,
            'is_active': str(is_active).lower(),
            'story_type': story_type,
        }
        if title:
            data['title'] = title
        if user_id is not None:
            data['user_id'] = user_id

        response = requests.post(
            f'{self.base_url}/api/stories/',
            data=data,
            files={'logo': logo},
            headers=self._auth_headers(),
            timeout=self.timeout_seconds,
        )
        self._raise_for_status(response)
        return response.json()

    def create_story_display(
        self,
        story: int,
        display_type: str,
        title: str = '',
        text: str = '',
        image: Optional[IO[bytes]] = None,
        video: Optional[IO[bytes]] = None,
        park: Optional[int] = None,
        link: str = '',
        season: Optional[int] = None,
        advertisement: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Create a Display screen for an existing Story."""
        data: Dict[str, Any] = {
            'story': story,
            'display_type': display_type,
        }
        if title:
            data['title'] = title
        if text:
            data['text'] = text
        if park is not None:
            data['park'] = park
        if link:
            data['link'] = link
        if season is not None:
            data['season'] = season
        if advertisement is not None:
            data['advertisement'] = advertisement

        files: Dict[str, IO[bytes]] = {}
        if image is not None:
            files['image'] = image
        if video is not None:
            files['video'] = video

        response = requests.post(
            f'{self.base_url}/api/stories/displays/',
            data=data,
            files=files if files else None,
            headers=self._auth_headers(),
            timeout=self.timeout_seconds,
        )
        self._raise_for_status(response)
        return response.json()

    def create_story_recipient(
        self,
        phone_number: str,
        story_id: int,
        notification_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            'phone_number': phone_number,
            'story_id': story_id,
            'notification_id': notification_id,
        }

        response = requests.post(
            f'{self.base_url}/api/stories/recipients/',
            json=payload,
            headers=self._headers(),
            timeout=self.timeout_seconds,
        )
        self._raise_for_status(response)
        return response.json()

    def _auth_headers(self) -> Dict[str, str]:
        """Auth-only headers for multipart requests (no Content-Type — requests sets it automatically)."""
        return {'Authorization': f'Token {self.token}'}

    def _url(self, path: str) -> str:
        return f'{self.base_url}/{path.lstrip("/")}'

    def _post_json(self, url: str, payload: Optional[Dict[str, Any]]) -> requests.Response:
        return requests.post(
            url,
            json=payload,
            headers=self._headers(),
            timeout=self.timeout_seconds,
        )

    def _json_or_empty(self, response: requests.Response) -> Any:
        raw = response.text.strip()
        if not raw:
            return {}
        try:
            return response.json()
        except ValueError:
            return {'raw': raw}

    def _extract_notification_id(self, payload: Any) -> Optional[int]:
        if isinstance(payload, dict):
            value = payload.get('notification_id', payload.get('id'))
            if value is None:
                return None
            try:
                return int(value)
            except (TypeError, ValueError):
                return None

        if isinstance(payload, list) and payload:
            first = payload[0]
            if isinstance(first, dict):
                value = first.get('notification_id', first.get('id'))
                if value is None:
                    return None
                try:
                    return int(value)
                except (TypeError, ValueError):
                    return None

        return None

    def _build_post_candidates(self, path: str) -> List[str]:
        normalized = str(path or '').strip().lstrip('/')
        if not normalized:
            return []

        variants = [normalized]

        if normalized.startswith('api/v1/'):
            stripped = normalized[len('api/v1/'):]
            if stripped:
                variants.append(stripped)
                variants.append(f'api/{stripped}')
        elif normalized.startswith('api/'):
            stripped = normalized[len('api/'):]
            if stripped:
                variants.append(stripped)
                variants.append(f'api/v1/{stripped}')
        else:
            variants.insert(0, f'api/{normalized}')
            variants.append(f'api/v1/{normalized}')

        candidates: List[str] = []
        seen = set()
        for variant in variants:
            if not variant:
                continue
            for candidate in (variant.rstrip('/') + '/', variant.rstrip('/')):
                if candidate and candidate not in seen:
                    seen.add(candidate)
                    candidates.append(candidate)

        return candidates

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
