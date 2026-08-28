from saas_sms_guard.suppression_policy import TenantRegistry


registry = TenantRegistry()
tenant = registry.onboard("studio-42")
tenant.activate()
tenant.suppress("+15550102020")

for phone in ("+15550102020", "+15550103030"):
    allowed, reason = tenant.send_decision(phone)
    print({"phone_number": phone, "sent": allowed, "reason": reason})

