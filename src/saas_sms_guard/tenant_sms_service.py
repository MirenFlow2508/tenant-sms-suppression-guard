from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .infrai_sms import Infrai, InfraiError, InfraiSmsClient
from .suppression_policy import AccountState, TenantRegistry


class OnboardTenant(BaseModel):
    tenant_id: str = Field(min_length=1)


class AccountUpdate(BaseModel):
    state: Literal["active", "paused", "closed"]


class ConsentUpdate(BaseModel):
    phone_number: str = Field(min_length=7)
    opted_out: bool


class SmsRequest(BaseModel):
    request_id: str = Field(min_length=1)
    phone_number: str = Field(min_length=7)
    message: str = Field(min_length=1, max_length=480)


class SmsDecision(BaseModel):
    sent: bool
    reason: str
    message_id: str | None = None


registry = TenantRegistry()
app = FastAPI(title="Tenant SMS Guard")


def require_tenant(tenant_id: str):
    tenant = registry.get(tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="tenant not found")
    return tenant


@app.post("/tenants", status_code=201)
def onboard_tenant(body: OnboardTenant) -> dict[str, str]:
    tenant = registry.onboard(body.tenant_id)
    return {"tenant_id": body.tenant_id, "state": tenant.account_state.value}


@app.put("/tenants/{tenant_id}/account")
def update_account(tenant_id: str, body: AccountUpdate) -> dict[str, str]:
    tenant = require_tenant(tenant_id)
    transition = {
        "active": tenant.activate,
        "paused": tenant.pause,
        "closed": tenant.close,
    }[body.state]
    transition()
    return {"tenant_id": tenant_id, "state": tenant.account_state.value}


@app.put("/tenants/{tenant_id}/consent")
def update_consent(tenant_id: str, body: ConsentUpdate) -> dict[str, object]:
    tenant = require_tenant(tenant_id)
    if body.opted_out:
        tenant.suppress(body.phone_number)
    else:
        tenant.restore_consent(body.phone_number)
    return {"tenant_id": tenant_id, "phone_number": body.phone_number, "opted_out": body.opted_out}


@app.post("/tenants/{tenant_id}/messages", response_model=SmsDecision)
def send_message(tenant_id: str, body: SmsRequest) -> SmsDecision:
    tenant = require_tenant(tenant_id)
    allowed, reason = tenant.send_decision(body.phone_number)
    if not allowed:
        return SmsDecision(sent=False, reason=reason)

    infrai = Infrai(InfraiSmsClient())
    try:
        result = infrai.sms.send(body.phone_number, body.message, body.request_id)
    except InfraiError as exc:
        caller_status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(status_code=caller_status, detail=exc.detail) from exc
    return SmsDecision(sent=True, reason="allowed", message_id=result.get("message_id"))

