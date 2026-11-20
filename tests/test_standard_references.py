import csv
import json

from pathlib import Path
from uuid import uuid4

import pytest

from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.support.ui import WebDriverWait

from config.settings import TEST_USERNAME, TEST_PASSWORD, TIMEOUT
from pages.admin_dashboard_page import AdminDashboardPage
from pages.login_page import LoginPage
from pages.standard_reference_page import StandardReferencePage


# Existing dropdown options supplied in the portal HTML.
# These records are only selected, never edited or deleted.
ITEM_TYPE = '"A" Frame and Gin Pole framework'
EDITED_ITEM_TYPE = "Access Ladder"

STANDARD_TYPE = "API"
EDITED_STANDARD_TYPE = "ASMI"


class StandardReferenceChecks:
    def __init__(self, driver):
        self.driver = driver
        self.rows = []
        self.saved = False

        self.folder = (
            Path("reports")
            / f"standard_reference_checks_{uuid4().hex[:12]}"
        )
        self.folder.mkdir(parents=True, exist_ok=True)

    def check(self, label, reader, expected):
        state = {
            "actual": "Not read",
            "error": "",
        }
        passed = False

        def compare(driver):
            try:
                state["actual"] = reader()
                state["error"] = ""
                return state["actual"] == expected

            except (
                NoSuchElementException,
                StaleElementReferenceException,
            ) as error:
                state["error"] = type(error).__name__
                return False

        try:
            WebDriverWait(
                self.driver,
                TIMEOUT,
            ).until(compare)

            passed = True

        except (TimeoutException, AssertionError) as error:
            state["error"] = (
                state["error"]
                or str(error).split("Stacktrace:")[0]
            )

        screenshot = ""

        if not passed:
            target = (
                self.folder
                / f"failure_{len(self.rows) + 1:03d}.png"
            )

            if self.driver.save_screenshot(str(target)):
                screenshot = str(target.resolve())

        row = {
            "check": label,
            "expected": expected,
            "actual": state["actual"],
            "result": "PASS" if passed else "FAIL",
            "error": state["error"],
            "screenshot": screenshot,
        }

        self.rows.append(row)
        self.saved = False

        print(
            f"[{row['result']}] {label}: "
            f"expected={expected!r}; actual={state['actual']!r}"
        )

    def save_report(self):
        csv_path = self.folder / "field_results.csv"
        json_path = self.folder / "field_results.json"

        json_path.write_text(
            json.dumps(self.rows, indent=2, default=str),
            encoding="utf-8",
        )

        with csv_path.open(
            "w",
            newline="",
            encoding="utf-8-sig",
        ) as stream:
            writer = csv.DictWriter(
                stream,
                fieldnames=[
                    "check",
                    "expected",
                    "actual",
                    "result",
                    "error",
                    "screenshot",
                ],
            )

            writer.writeheader()
            writer.writerows(self.rows)

        failures = [
            row
            for row in self.rows
            if row["result"] == "FAIL"
        ]

        self.saved = True

        print(
            "\nCollected Standard Reference checks: "
            f"{len(self.rows) - len(failures)} passed; "
            f"{len(failures)} failed."
        )
        print(f"Detailed results: {csv_path.resolve()}")

    def finish(self):
        self.save_report()

        failures = [
            row
            for row in self.rows
            if row["result"] == "FAIL"
        ]

        if failures:
            summary = "\n".join(
                f"- {row['check']}: "
                f"expected={row['expected']!r}; "
                f"actual={row['actual']!r}"
                for row in failures
            )

            pytest.fail(
                f"Standard Reference verification failures:\n{summary}",
                pytrace=False,
            )


@pytest.fixture
def standard_reference_checks(driver):
    checks = StandardReferenceChecks(driver)

    try:
        yield checks
    finally:
        if not checks.saved:
            checks.save_report()


def test_standard_reference_lifecycle(
    driver,
    standard_reference_checks,
):
    checks = standard_reference_checks

    # Login once.
    login = LoginPage(driver)
    login.open()
    login.login(TEST_USERNAME, TEST_PASSWORD)

    dashboard = AdminDashboardPage(driver)
    assert dashboard.get_heading_text() == "Admin Dashboard"

    page = StandardReferencePage(driver)
    page.open()
    page.open_add_form()

    suffix = uuid4().hex[:12]
    name = f"Auto_StandardReference_{suffix}"
    edited_name = f"{name}_Edited"

    # Required fields on the same Add form.
    checks.check(
        "Empty Reference form / Save disabled",
        page.save_enabled,
        False,
    )

    page.select_option(page.ITEM_TYPE, ITEM_TYPE)
    page.set_text(page.NAME, name)

    checks.check(
        "Standard Type required",
        page.save_enabled,
        False,
    )

    page.set_text(page.NAME, "")
    page.select_option(page.STANDARD_TYPE, STANDARD_TYPE)

    checks.check(
        "Standard name required",
        page.save_enabled,
        False,
    )

    page.set_text(page.NAME, " " * 5, verify=False)

    checks.check(
        "Whitespace Standard name / Save disabled",
        page.save_enabled,
        False,
    )

    boundary_name = "S" * 250
    page.set_text(page.NAME, boundary_name)

    checks.check(
        "250-character Standard name retained",
        page.read_name,
        boundary_name,
    )

    checks.check(
        "250-character Standard name / Save enabled",
        page.save_enabled,
        True,
    )

    page.set_text(
        page.NAME,
        boundary_name + "X",
        verify=False,
    )

    checks.check(
        "Standard name limited to 250 characters",
        page.read_name,
        boundary_name,
    )

    # Check Item Type is required using a fresh, unsaved form.
    # There is no Cancel button, so return through the sidebar.
    page.open()
    page.open_add_form()
    page.select_option(page.STANDARD_TYPE, STANDARD_TYPE)
    page.set_text(page.NAME, name)

    checks.check(
        "Item Type required",
        page.save_enabled,
        False,
    )

    # Create one actual Reference.
    page.select_option(page.ITEM_TYPE, ITEM_TYPE)
    page.save()
    page.search(name)

    original = {
        "name": name,
        "standard_type": STANDARD_TYPE,
        "item_type": ITEM_TYPE,
    }

    checks.check(
        "Created Reference / grid values",
        lambda: page.grid_details(original),
        original,
    )

    # Edit the same Reference.
    page.edit(original)

    checks.check(
        "Created Reference / reopened form",
        page.form_details,
        original,
    )

    page.fill_form(
        item_type=EDITED_ITEM_TYPE,
        standard_type=EDITED_STANDARD_TYPE,
        name=edited_name,
    )
    page.save()
    page.search(edited_name)

    edited = {
        "name": edited_name,
        "standard_type": EDITED_STANDARD_TYPE,
        "item_type": EDITED_ITEM_TYPE,
    }

    checks.check(
        "Edited Reference / grid values",
        lambda: page.grid_details(edited),
        edited,
    )

    # Reopen once to verify all three saved fields.
    page.edit(edited)

    checks.check(
        "Edited Reference / reopened saved values",
        page.form_details,
        edited,
    )

    # No Cancel/Close button: navigate using the sidebar.
    page.open()

    # Attempt exactly the same combination again.
    page.open_add_form()
    page.fill_form(
        item_type=EDITED_ITEM_TYPE,
        standard_type=EDITED_STANDARD_TYPE,
        name=edited_name,
    )
    page.click(page.SAVE)

    def duplicate_response():
        if page.popup_visible():
            return page.popup_details()

        return {
            "title": "",
            "message": "Duplicate rejection popup not visible",
        }

    checks.check(
        "Duplicate Reference / Already Exist message",
        duplicate_response,
        {
            "title": "Error",
            "message": "Standard Already Exist",
        },
    )

    if page.popup_visible():
        print(f"Duplicate response: {page.popup_details()}")
        page.acknowledge_popup()

    page.wait_idle()
    page.open()
    page.search(edited_name)

    checks.check(
        "Duplicate attempt / one Reference retained",
        page.visible_names,
        [edited_name],
    )

    assert len(page.matching_rows(edited)) == 1, (
        "Expected exactly one matching test Reference: "
        f"{edited}"
    )

    # Delete Cancel.
    message = page.request_delete(edited)

    checks.check(
        "Reference delete confirmation",
        lambda: message,
        page.DELETE_MESSAGE,
    )

    page.cancel_delete()

    checks.check(
        "Reference Delete Cancel / row unchanged",
        lambda: page.grid_details(edited),
        edited,
    )

    # Confirm deletion of our Reference only.
    page.request_delete(edited)
    success_message = page.confirm_delete()

    checks.check(
        "Reference deletion success",
        lambda: success_message,
        page.DELETE_SUCCESS,
    )

    page.search(edited_name)

    checks.check(
        "Deleted Reference / absent from grid",
        page.visible_names,
        [],
    )

    print(
        "Standard Reference flow completed: "
        f"{name} -> {edited_name} -> deleted"
    )

    checks.finish()