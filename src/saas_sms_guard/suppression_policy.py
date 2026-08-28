from dataclasses import dataclass, field
from enum import StrEnum


class AccountState(StrEnum):
    ONBOARDING = "onboarding"
    ACTIVE = "active"
    PAUSED = "paused"
    CLOSED = "closed"


@dataclass
class TenantMessagingState:
    account_state: AccountState = AccountState.ONBOARDING
    suppressed_numbers: set[str] = field(default_factory=set)

    def activate(self) -> None:
        self.account_state = AccountState.ACTIVE

    def pause(self) -> None:
        self.account_state = AccountState.PAUSED

    def close(self) -> None:
        self.account_state = AccountState.CLOSED

    def suppress(self, phone_number: str) -> None:
        self.suppressed_numbers.add(phone_number)

    def restore_consent(self, phone_number: str) -> None:
        self.suppressed_numbers.discard(phone_number)

    def send_decision(self, phone_number: str) -> tuple[bool, str]:
        if self.account_state != AccountState.ACTIVE:
            return False, f"account_{self.account_state.value}"
        if phone_number in self.suppressed_numbers:
            return False, "recipient_suppressed"
        return True, "allowed"


class TenantRegistry:
    def __init__(self) -> None:
        self._tenants: dict[str, TenantMessagingState] = {}

    def onboard(self, tenant_id: str) -> TenantMessagingState:
        return self._tenants.setdefault(tenant_id, TenantMessagingState())

    def get(self, tenant_id: str) -> TenantMessagingState | None:
        return self._tenants.get(tenant_id)

