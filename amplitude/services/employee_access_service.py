from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from amplitude.models import AllowedEmployeePageAccess, EmployeePortalPage
from utils.avatracker_client import AvatrackerClient


@dataclass(frozen=True)
class EmployeeProfile:
    iin: str
    full_name: str
    email: str
    position_guid: str
    position_name: str


class EmployeeAccessService:
    """Who can log into the portal, and what can they see.

    Employees live in avatracker.online now — its employee-by-ИИН detail
    response already carries `position`/`position_name` inline, so there's no
    need for a separate position lookup (unlike the old bigdata-backed flow).
    """

    def __init__(self, avatracker_client: Optional[AvatrackerClient] = None) -> None:
        self.avatracker_client = avatracker_client or AvatrackerClient()

    def can_access_site(self, iin: str) -> bool:
        return self.get_employee_profile(iin) is not None

    def get_employee_profile(self, iin: str) -> Optional[EmployeeProfile]:
        normalized_iin = (iin or '').strip()
        if not normalized_iin:
            return None

        try:
            data = self.avatracker_client.find_employee_by_iin(normalized_iin)
        except Exception:
            return None

        if not data:
            return None

        if data.get('active') is False:
            return None

        return EmployeeProfile(
            iin=str(data.get('iin') or normalized_iin).strip(),
            full_name=str(data.get('full_name') or '').strip(),
            email=str(data.get('email') or '').strip().lower(),
            position_guid=str(data.get('position') or '').strip(),
            position_name=str(data.get('position_name') or '').strip(),
        )

    def allowed_pages_for_iin(self, iin: str) -> List[str]:
        profile = self.get_employee_profile(iin)
        if profile is None:
            return []
        return self.allowed_pages_for_position(profile.position_guid)

    def allowed_pages_for_position(self, position_guid: str) -> List[str]:
        normalized = (position_guid or '').strip()
        if not normalized:
            return []

        allowed_set = set(
            AllowedEmployeePageAccess.objects.filter(position_guid=normalized, is_active=True)
            .values_list('page', flat=True)
        )
        if not allowed_set:
            return []

        ordered = [value for value, _ in EmployeePortalPage.choices if value in allowed_set]
        return ordered

    def can_access_page(self, iin: str, page: str) -> bool:
        return page in self.allowed_pages_for_iin(iin)
