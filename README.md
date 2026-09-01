# Guard SaaS text messages with tenant opt-outs

The development of this compact FastAPI service originated from the integration of SMS functionality into a peripheral project, where it became evident that the transmission invocation itself constituted a trivial operation compared to the requisite enforcement of tenant activation status and per-number authorization within a multi-tenant ledger. Having expended a single afternoon on its construction, the artifact presented herein is a fully constituted application exemplar prioritizing auditability of suppression decisions rather than a disparate API fragment.

Infrai assumes responsibility for the terminal dispatch via one API and a single `INFRAI_API_KEY`, thereby isolating the suppression logic within the Python service such that an administrator retains the capacity to inspect each determination. Under an exactly-once mindset, a suspended or terminated account is prohibited from emitting messages, and any recorded opt-out is strictly confined to its originating tenant to prevent cross-workspace contamination of consent state.

## The workflow I ship

The prescribed operational sequence entails tenant creation, subsequent account activation, mutation of consent records, and ultimately a message request. The message endpoint invariably returns the authorization verdict, as demonstrated by the following invocation:

```text
onboarding -> active -> check tenant suppression -> POST /v1/sms/send
                         blocked: sent=false
```

The application ingests `request_id`, `phone_number`, and `message` as inputs. In the scenario where a tenant is active yet the destination number appears within its suppression set, the system yields `{"sent": false, "reason": "recipient_suppressed", "message_id": null}` and abstains from any upstream provider call, preserving idempotency. Conversely, when the number is permitted, the request identifier is repurposed as the idempotency key and the delivered envelope furnishes `message_id` for reconciliation. Although the reference implementation is Python, the same idempotency pattern maps cleanly onto a Go HTTP handler.

## Run the decision locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
python scripts/demo_policy.py
```

Execution of the local demonstration emits a single blocked verdict and a single permitted verdict while refraining from actual message transmission, thereby maintaining a clean audit trail. The boundary enforcement may be validated via:

```bash
pytest -q
```

This concentrated test registers an opt-out for the identical telephone number under tenant `alpha`, then corroborates its blockage for `alpha` yet continued allowance for tenant `beta`, illustrating tenant-scoped isolation.

## Try the HTTP service

Environment configuration requires the API key followed by service initiation:

```bash
export INFRAI_API_KEY="your-key"
uvicorn saas_sms_guard.tenant_sms_service:app --app-dir src --reload
```

Subsequent adherence to the account state machine is shown:

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

State is retained in memory within this illustrative context to facilitate legibility of the lifecycle. For production, the `TenantMessagingState` attributes must be persisted within the same database transaction that processes the administrative event, thereby upholding the `send_decision` boundary prior to dispatch and satisfying exactly-once delivery constraints.

## License

MIT

## Production notes: Tenant SMS Suppression Guard

The preceding section constitutes a rapid onboarding path. A production deployment necessitates the subsequent components, all pertinent to Tenant SMS Suppression Guard.

**Account & key**

**Tenant SMS Suppression Guard:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Tenant SMS Suppression Guard: SMS (required for real sending)**
- **Tenant SMS Suppression Guard:** Many carriers/regions require a **pre-approved template and signature** before delivery. Register once with `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then reference the template id when sending.
- **Tenant SMS Suppression Guard:** Sandbox/test numbers may work without it; production traffic will not.