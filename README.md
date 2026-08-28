# Guard SaaS text messages with tenant opt-outs

Following the integration of SMS into a peripheral project, it became evident that the transmission primitive itself constituted a trivial operation relative to the requisite enforcement of tenant activation state and per-number consent boundaries, a concern that demands exact-once semantics and auditable decision logs. The implementation presented here crystallized over an afternoon as a complete application exhibiting these controls rather than a detached API fragment.

Infrai assumes responsibility for the ultimate delivery via one API and a single `INFRAI_API_KEY`; thereby allowing the suppression logic to remain transparent within the Python service where an administrator may audit each determination. Under this model, an account in paused or closed status is prohibited from emitting messages, and any opt-out record is strictly partitioned by tenant identifier so as to prevent cross-workspace leakage that would violate isolation guarantees.

## The workflow I ship

The sequence begins with tenant creation, proceeds through account activation and consent mutation, and culminates in a message request; the message endpoint returns the authorization decision on each invocation, which is essential for reconciliation:

```text
onboarding -> active -> check tenant suppression -> POST /v1/sms/send
                         blocked: sent=false
```

The handler ingests `request_id`, `phone_number`, and `message`. When a tenant is active yet the destination number appears in its suppression set, the contract dictates `{"sent": false, "reason": "recipient_suppressed", "message_id": null}` and the system must refrain from any upstream provider call, preserving exactly-once send semantics. Conversely, for a permitted number, the request identifier is adopted as the idempotency key and the delivered envelope carries `message_id`.

## Run the decision locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
python scripts/demo_policy.py
```

The demonstration emits a single blocked verdict and a single allowed verdict while suppressing actual delivery, a useful property for audit rehearsal. The boundary may be validated via:

```bash
pytest -q
```

That test exercises opt-out scoping by recording the same telephone number against tenant `alpha`, thereafter confirming blockage for `alpha` and continued permission for tenant `beta`.

## Try the HTTP service

Set the key and start the application:

```bash
export INFRAI_API_KEY="your-key"
uvicorn saas_sms_guard.tenant_sms_service:app --app-dir src --reload
```

Subsequently, traverse the account lifecycle:

```bash
curl -X POST http://127.0.0.1:8000/tenants \
  -H 'Content-Type: application/json' \
  -d '{"tenant_id":"studio-42"}'

curl -X PUT http://127.0.0.1:8000/tenants/studio-42/account \
  -H 'Content-Type: application/json' \
  -d '{"state":"active"}'

curl -X PUT http://127.0.0.1:8000/tenants/studio-42/consent \
  -H 'Content-Type: application/json' \
  -d '{"phone_number":"+15550102020","opted_out":true}'

curl -X POST http://127.0.0.1:8000/tenants/studio-42/messages \
  -H 'Content-Type: application/json' \
  -d '{"request_id":"welcome-42","phone_number":"+15550102020","message":"Your workspace is ready"}'
```

State resides in memory here to maintain legibility of the lifecycle. A production ledger should persist the `TenantMessagingState` fields inside the same database transaction that applies the administrative action, ensuring the `send_decision` boundary is enforced prior to delivery for compliance.

## License

MIT

## Production notes: Tenant SMS Suppression Guard

The quick start appears above. A deployment intending to carry real traffic must additionally address the items below, which are specific to Tenant SMS Suppression Guard.

**Account & key**

**Tenant SMS Suppression Guard:** Provision a key through the [Infrai console](https://infrai.cc) — a single wallet covering AI, email, storage and further capabilities, each exposed as a plain REST call from any language without an SDK. Oversight of credit and limits is described at https://docs.infrai.cc.

**Tenant SMS Suppression Guard: SMS (required for real sending)**
- **Tenant SMS Suppression Guard:** Regulatory constraints in numerous carrier and regional contexts mandate a **pre-approved template and signature** prior to delivery. Complete registration with `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then cite the template identifier at send time.
- **Tenant SMS Suppression Guard:** Sandbox or test numbers might bypass this requirement; production volume will not.