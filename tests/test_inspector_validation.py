from uuid import uuid4

import pytest

from config.settings import TEST_USERNAME, TEST_PASSWORD
from pages.admin_dashboard_page import AdminDashboardPage
from pages.inspector_page import InspectorPage
from pages.login_page import LoginPage


@pytest.mark.parametrize(
    "case,name,email",
    [
        ("both_empty", "", ""),
        ("name_empty", "", "qa.validation@example.com"),
        ("email_empty", "QA Validation", ""),
        ("name_spaces", "   ", "qa.validation@example.com"),
        ("email_spaces", "QA Validation", "   "),
        ("email_without_at", "QA Validation", "invalid-email"),
        ("email_without_local_part", "QA Validation", "@example.com"),
        ("email_without_domain", "QA Validation", "qa@"),
        ("email_without_dot", "QA Validation", "qa@example"),
        ("email_short_suffix", "QA Validation", "qa@example.c"),
        ("email_internal_space", "QA Validation", "qa test@example.com"),
    ],
    ids=lambda value: value,
)
def test_inspector_rejects_invalid_input(driver, case, name, email):
    login = LoginPage(driver)
    login.open()
    login.login(TEST_USERNAME, TEST_PASSWORD)

    dashboard = AdminDashboardPage(driver)
    assert dashboard.get_heading_text() == "Admin Dashboard"

    inspectors = InspectorPage(driver)
    inspectors.open()
    inspectors.open_add_form()

    try:
        inspectors.fill_form(name, email, "")

        inspectors.wait_for_save_state(False)

        assert not inspectors.is_save_enabled(), (
            f"{case}: Save should be disabled for invalid Inspector data."
        )
    finally:
        inspectors.close_form()


def test_inspector_optional_fields_are_not_required(driver):
    login = LoginPage(driver)
    login.open()
    login.login(TEST_USERNAME, TEST_PASSWORD)

    dashboard = AdminDashboardPage(driver)
    assert dashboard.get_heading_text() == "Admin Dashboard"

    inspectors = InspectorPage(driver)
    inspectors.open()
    inspectors.open_add_form()

    suffix = uuid4().hex[:12]

    try:
        inspectors.fill_form(
            f"QA_Validation_{suffix}",
            f"qa.validation.{suffix}@example.com",
            "",
        )

        inspectors.wait_for_signature_absent()
        inspectors.wait_for_save_state(True)

        assert inspectors.is_save_enabled(), (
            "Valid Name and Email should enable Save without "
            "Qualification or Signature."
        )
    finally:
        inspectors.close_form()