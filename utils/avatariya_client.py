import math
from concurrent.futures import ThreadPoolExecutor, as_completed
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
        self._raise_for_status(response)
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

    def get_kids_by_dob_day(self, dob_day: str) -> List[Dict]:
        """Return all kids with the given birthday day (format: 'DD-MM', e.g. '16-02')."""
        params = {'dob_day': dob_day}
        response = requests.get(
            f'{self.base_url}/kid/',
            params=params,
            headers=self._headers(),
            timeout=self.timeout_seconds,
        )
        self._raise_for_status(response)
        first_page = response.json()
        return self._collect_get_results_with_pagination(first_page, params=params)

    def get_guest(self, guest_id: int) -> Dict:
        """Return a single guest by ID."""
        response = requests.get(
            f'{self.base_url}/guest/{guest_id}/',
            headers=self._headers(),
            timeout=self.timeout_seconds,
        )
        self._raise_for_status(response)
        return response.json()

    def get_employee_by_iin(self, iin: str) -> Dict:
        """Return employee payload by IIN."""
        normalized = str(iin or '').strip()
        if not normalized:
            raise ValueError('IIN is required')

        response = requests.get(
            f'{self.base_url}/employees/{normalized}/',
            headers=self._headers(),
            timeout=self.timeout_seconds,
        )
        self._raise_for_status(response)
        return response.json()

    def get_position_by_guid(self, guid: str) -> Dict:
        """Return position payload by position GUID."""
        normalized = str(guid or '').strip()
        if not normalized:
            raise ValueError('Position GUID is required')

        response = requests.get(
            f'{self.base_url}/position/{normalized}/',
            headers=self._headers(),
            timeout=self.timeout_seconds,
        )
        self._raise_for_status(response)
        return response.json()

    def list_marketing_sales(self, search: str = '') -> List[Dict]:
        params: Dict[str, str] = {'status': 'true'}
        if search.strip():
            params['search'] = search.strip()

        response = requests.get(
            f'{self.base_url}/marketing_sale/',
            params=params,
            headers=self._headers(),
            timeout=self.timeout_seconds,
        )
        self._raise_for_status(response)
        first_page = response.json()
        return self._collect_get_results_with_pagination(first_page, params=params)

    def list_cities(self) -> List[Dict]:
        response = requests.get(
            f'{self.base_url}/city/',
            headers=self._headers(),
            timeout=self.timeout_seconds,
        )
        self._raise_for_status(response)
        first_page = response.json()
        return self._collect_get_results_with_pagination(first_page, params={})

    def list_coupon_assign_marketing_sales(self) -> List[Dict]:
        response = requests.get(
            f'{self.base_url}/admin/coupon-assign/marketing-sales/',
            headers=self._headers(),
            timeout=self.timeout_seconds,
        )
        self._raise_for_status(response)
        payload = response.json()

        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            results = payload.get('results')
            if isinstance(results, list):
                return results
        return []

    def assign_coupon_via_admin(
        self,
        *,
        marketing_sale_id: int,
        phone_number: str,
        amount: str,
    ) -> Dict:
        payload = {
            'marketing_sale_id': int(marketing_sale_id),
            'phone_number': str(phone_number or '').strip(),
            'amount': str(amount or '').strip(),
        }
        response = requests.post(
            f'{self.base_url}/admin/coupon-assign/assign/',
            json=payload,
            headers=self._headers(),
            timeout=self.timeout_seconds,
        )
        self._raise_for_status(response)
        data = response.json()
        return data if isinstance(data, dict) else {}

    def list_coupons(
        self,
        *,
        marketing_sale_id: Optional[int] = None,
        status: int = 0,
        guest_is_null: bool = True,
        ordering: str = 'id',
    ) -> List[Dict]:
        params: Dict[str, str] = {
            'status': str(status),
            'ordering': ordering,
        }
        if marketing_sale_id is not None:
            params['marketing_sale'] = str(marketing_sale_id)
        if guest_is_null:
            params['guest__isnull'] = 'true'

        response = requests.get(
            f'{self.base_url}/coupon/',
            params=params,
            headers=self._headers(),
            timeout=self.timeout_seconds,
        )
        self._raise_for_status(response)
        first_page = response.json()
        return self._collect_get_results_with_pagination(first_page, params=params)

    def list_coupons_parallel(
        self,
        *,
        marketing_sale_id: int,
        status: int = 0,
        guest_is_null: bool = True,
        ordering: str = 'id',
        max_workers: int = 12,
    ) -> List[Dict]:
        params: Dict[str, str] = {
            'marketing_sale': str(marketing_sale_id),
            'status': str(status),
            'ordering': ordering,
            'page': '1',
        }
        if guest_is_null:
            params['guest__isnull'] = 'true'

        response = requests.get(
            f'{self.base_url}/coupon/',
            params=params,
            headers=self._headers(),
            timeout=self.timeout_seconds,
        )
        self._raise_for_status(response)
        first_page = response.json()

        if isinstance(first_page, list):
            return first_page
        if not isinstance(first_page, dict):
            return []

        first_results = list(first_page.get('results', []))
        if not first_results:
            return []

        count_value = first_page.get('count')
        try:
            total_count = int(count_value)
        except (TypeError, ValueError):
            total_count = len(first_results)

        page_size = len(first_results)
        if page_size <= 0:
            return first_results

        total_pages = max(1, math.ceil(total_count / page_size))
        if total_pages <= 1:
            return first_results

        workers = min(max_workers, total_pages - 1)
        page_results: Dict[int, List[Dict]] = {1: first_results}

        def fetch_page(page_number: int) -> List[Dict]:
            page_params = dict(params)
            page_params['page'] = str(page_number)
            page_response = requests.get(
                f'{self.base_url}/coupon/',
                params=page_params,
                headers=self._headers(),
                timeout=self.timeout_seconds,
            )
            self._raise_for_status(page_response)
            payload = page_response.json()
            if isinstance(payload, dict):
                data = payload.get('results')
                return data if isinstance(data, list) else []
            if isinstance(payload, list):
                return payload
            return []

        with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
            future_map = {
                executor.submit(fetch_page, page_number): page_number
                for page_number in range(2, total_pages + 1)
            }
            for future in as_completed(future_map):
                page_number = future_map[future]
                page_results[page_number] = future.result()

        combined: List[Dict] = []
        for page_number in range(1, total_pages + 1):
            combined.extend(page_results.get(page_number, []))

        return combined

    def iter_coupon_pages(
        self,
        *,
        marketing_sale_id: int,
        status: int = 0,
        guest_is_null: bool = True,
        ordering: str = 'id',
    ) -> Iterable[List[Dict]]:
        params: Dict[str, str] = {
            'marketing_sale': str(marketing_sale_id),
            'status': str(status),
            'ordering': ordering,
        }
        if guest_is_null:
            params['guest__isnull'] = 'true'

        response = requests.get(
            f'{self.base_url}/coupon/',
            params=params,
            headers=self._headers(),
            timeout=self.timeout_seconds,
        )
        self._raise_for_status(response)
        payload = response.json()

        if isinstance(payload, list):
            yield payload
            return

        if not isinstance(payload, dict):
            return

        results = payload.get('results')
        if isinstance(results, list):
            yield results

        next_url = payload.get('next')
        while next_url:
            page_response = requests.get(
                next_url,
                headers=self._headers(),
                timeout=self.timeout_seconds,
            )
            self._raise_for_status(page_response)
            page_payload = page_response.json()

            if isinstance(page_payload, dict):
                page_results = page_payload.get('results')
                if isinstance(page_results, list):
                    yield page_results
                next_url = page_payload.get('next')
                continue

            if isinstance(page_payload, list):
                yield page_payload
            break

    def count_coupons(
        self,
        *,
        marketing_sale_id: Optional[int] = None,
        status: int = 0,
        guest_is_null: bool = True,
        extra_params: Optional[Dict[str, str]] = None,
        timeout_seconds: Optional[int] = None,
    ) -> int:
        params: Dict[str, str] = {
            'status': str(status),
            'page': '1',
            'page_size': '1',
        }
        if marketing_sale_id is not None:
            params['marketing_sale'] = str(marketing_sale_id)
        if guest_is_null:
            params['guest__isnull'] = 'true'
        if extra_params:
            for key, value in extra_params.items():
                params[str(key)] = str(value)

        response = requests.get(
            f'{self.base_url}/coupon/',
            params=params,
            headers=self._headers(),
            timeout=timeout_seconds or self.timeout_seconds,
        )
        self._raise_for_status(response)
        payload = response.json()

        if isinstance(payload, dict):
            count_value = payload.get('count')
            try:
                if count_value is not None:
                    return int(count_value)
            except (TypeError, ValueError):
                pass

            results = payload.get('results')
            if isinstance(results, list):
                return len(results)
            return 0

        if isinstance(payload, list):
            return len(payload)

        return 0

    def find_guest_by_phone(self, phone_number: str) -> Optional[Dict]:
        normalized = ''.join(ch for ch in str(phone_number or '') if ch.isdigit())
        if not normalized:
            return None

        search_variants = [normalized]
        if len(normalized) == 11 and normalized.startswith('7'):
            search_variants.append(f'8{normalized[1:]}')

        for variant in search_variants:
            for params in ({'phone': variant, 'deleted': 'false'}, {'search': variant, 'deleted': 'false'}):
                response = requests.get(
                    f'{self.base_url}/guest/',
                    params=params,
                    headers=self._headers(),
                    timeout=self.timeout_seconds,
                )
                self._raise_for_status(response)
                payload = response.json()

                if isinstance(payload, dict):
                    data = payload.get('results')
                    if isinstance(data, list) and data:
                        return data[0]

        return None

    def create_cashback(self, payload: Dict) -> Dict:
        response = requests.post(
            f'{self.base_url}/cashback/',
            json=payload,
            headers=self._headers(),
            timeout=self.timeout_seconds,
        )
        self._raise_for_status(response)

        if not response.text.strip():
            return {}

        try:
            data = response.json()
            return data if isinstance(data, dict) else {'data': data}
        except ValueError:
            return {'raw': response.text}

    def assign_coupon_to_guest(self, coupon_id: int, guest_id: int) -> Dict:
        payload = {'guest': guest_id}
        response = requests.patch(
            f'{self.base_url}/coupon/{coupon_id}/',
            json=payload,
            headers=self._headers(),
            timeout=self.timeout_seconds,
        )
        self._raise_for_status(response)

        if not response.text.strip():
            return {}

        try:
            return response.json()
        except ValueError:
            return {}

    def _collect_get_results_with_pagination(self, first_page: Dict, params: Dict) -> List[Dict]:
        if isinstance(first_page, list):
            return first_page

        if not isinstance(first_page, dict):
            return []

        results = list(first_page.get('results', []))
        next_url = first_page.get('next')

        while next_url:
            response = requests.get(
                next_url,
                headers=self._headers(),
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            page = response.json()
            results.extend(page.get('results', []))
            next_url = page.get('next')

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

    def _raise_for_status(self, response: requests.Response) -> None:
        try:
            response.raise_for_status()
        except HTTPError as exc:
            detail = response.text.strip()
            if detail:
                raise ValueError(f'Avatariya API error: {detail}') from exc
            raise ValueError('Avatariya API request failed') from exc

    def _headers(self) -> Dict[str, str]:
        return {
            'Authorization': f'Bearer {self.bearer_token}',
            'Content-Type': 'application/json',
        }
