from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from utils.avatariya_client import AvatariyaClient
from utils.mobile_client import MobileClient


@dataclass(frozen=True)
class NotificationCityOption:
    id: int
    name_ru: str
    name_kz: str


@dataclass(frozen=True)
class PushDispatchResult:
    target: str
    city_id: Optional[int]
    recipients_count: Optional[int]
    notification_id: Optional[int]
    status: str


class PushDispatchService:
    def __init__(
        self,
        *,
        avatariya_client: Optional[AvatariyaClient] = None,
        mobile_client: Optional[MobileClient] = None,
    ) -> None:
        self.avatariya_client = avatariya_client or AvatariyaClient()
        self.mobile_client = mobile_client or MobileClient()

    def list_cities(self, search: str = "") -> List[NotificationCityOption]:
        raw_items = self.avatariya_client.list_cities()
        normalized_search = str(search or "").strip().lower()
        options: List[NotificationCityOption] = []

        for item in raw_items:
            city_id = _to_int(item.get("id"))
            if city_id is None or city_id <= 0:
                continue

            name_ru = str(item.get("name_ru") or "").strip()
            name_kz = str(item.get("name_kz") or "").strip()

            searchable = f"{name_ru} {name_kz}".strip().lower()
            if normalized_search and normalized_search not in searchable:
                continue

            if not (name_ru or name_kz):
                continue

            options.append(
                NotificationCityOption(
                    id=city_id,
                    name_ru=name_ru,
                    name_kz=name_kz,
                )
            )

        options.sort(key=lambda value: (value.name_ru.lower() or value.name_kz.lower(), value.id))
        return options

    def send_mass_push(
        self,
        *,
        target: str,
        title: str,
        body: str,
        title_kz: str = "",
        body_kz: str = "",
        notification_type: str = "default",
        phone_numbers: Optional[List[str]] = None,
        city_id: Optional[int] = None,
        survey_id: Optional[int] = None,
        review_id: Optional[int] = None,
    ) -> PushDispatchResult:
        send_to_city = target == "city"
        if send_to_city:
            if city_id is None:
                raise ValueError('city_id is required for city push dispatch')
            normalized_phone_numbers: Optional[List[str]] = None
            recipients_count: Optional[int] = None
            city_value = str(city_id)
        else:
            normalized_phone_numbers = [str(value).strip() for value in (phone_numbers or []) if str(value).strip()]
            if not normalized_phone_numbers:
                raise ValueError('phone_numbers must not be empty for phones push dispatch')
            recipients_count = len(normalized_phone_numbers)
            city_value = ""

        notification_id = self.mobile_client.send_mass_push(
            phone_numbers=normalized_phone_numbers,
            title=title,
            body=body,
            title_kz=title_kz,
            body_kz=body_kz,
            city=city_value,
            notification_type=notification_type,
            survey_id=survey_id,
            review_id=review_id,
        )

        return PushDispatchResult(
            target=target,
            city_id=city_id if send_to_city else None,
            recipients_count=recipients_count,
            notification_id=notification_id,
            status="accepted",
        )


def _to_int(value) -> Optional[int]:
    try:
        if value is None:
            return None
        return int(value)
    except (TypeError, ValueError):
        return None
