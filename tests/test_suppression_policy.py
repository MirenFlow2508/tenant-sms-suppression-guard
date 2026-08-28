from saas_sms_guard.suppression_policy import TenantRegistry


def test_opt_out_blocks_send_for_only_that_tenant() -> None:
    registry = TenantRegistry()
    alpha = registry.onboard("alpha")
    beta = registry.onboard("beta")
    alpha.activate()
    beta.activate()

    phone = "+15550102020"
    alpha.suppress(phone)

    assert alpha.send_decision(phone) == (False, "recipient_suppressed")
    assert beta.send_decision(phone) == (True, "allowed")


def test_paused_account_blocks_even_consented_recipient() -> None:
    tenant = TenantRegistry().onboard("alpha")
    tenant.activate()
    tenant.pause()

    assert tenant.send_decision("+15550103030") == (False, "account_paused")

