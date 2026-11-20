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
from pages.standard_type_page import StandardTypePage


class StandardTypeChecks:
    def __init__(self, driver):
        self.driver = driver
        self.rows = []
        self.saved = False
        self.folder = (
            Path("reports")
            / f"standard_type_checks_{uuid4().hex[:12]}"
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

        self.saved = True

        failures = [
            row
            for row in self.rows
            if row["result"] == "FAIL"
        ]

        print(
            "\nCollected Standard Type checks: "
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
                f"Standard Type verification failures:\n{summary}",
                pytrace=False,
            )


@pytest.fixture
def standard_type_checks(driver):
    checks = StandardTypeChecks(driver)

    try:
        yield checks
    finally:
        if not checks.saved:
            checks.save_report()


def test_standard_type_lifecycle(driver, standard_type_checks):
    checks = standard_type_checks

    # Login once.
    login = LoginPage(driver)
    login.open()
    login.login(TEST_USERNAME, TEST_PASSWORD)

    dashboard = AdminDashboardPage(driver)
    assert dashboard.get_heading_text() == "Admin Dashboard"

    page = StandardTypePage(driver)
    page.open()

    suffix = uuid4().hex[:12]
    name = f"Auto_StandardType_{suffix}"
    edited_name = f"{name}_Edited"

    # Validate fields on the same Add form.
    page.open_add_form()

    checks.check(
        "Empty Standard Type / Save disabled",
        page.save_enabled,
        False,
    )

    page.set_text(page.NAME, " " * 5, verify=False)

    checks.check(
        "Whitespace Standard Type / Save disabled",
        page.save_enabled,
        False,
    )

    page.set_text(page.NAME, "A")

    checks.check(
        "One-character Standard Type / Save enabled",
        page.save_enabled,
        True,
    )

    boundary_name = f"Boundary_{suffix}_".ljust(50, "X")
    page.set_text(page.NAME, boundary_name)

    checks.check(
        "50-character Standard Type retained",
        page.read_name,
        boundary_name,
    )

    checks.check(
        "50-character Standard Type / Save enabled",
        page.save_enabled,
        True,
    )

    page.set_text(
        page.NAME,
        boundary_name + "Y",
        verify=False,
    )

    checks.check(
        "Standard Type limited to 50 characters",
        page.read_name,
        boundary_name,
    )

    # 1. Add one actual record.
    page.set_text(page.NAME, name)
    page.save()
    page.search(name)

    checks.check(
        "Created Standard Type / one grid record",
        page.visible_names,
        [name],
    )

    # 2. Edit that same record.
    page.edit(name)

    checks.check(
        "Edit form / original value",
        page.read_name,
        name,
    )

    page.set_text(page.NAME, edited_name)
    page.save()
    page.search(edited_name)

    checks.check(
        "Edited Standard Type / grid value",
        page.visible_names,
        [edited_name],
    )

    # Reopen once to verify that the change persisted.
    page.edit(edited_name)

    checks.check(
        "Edited Standard Type / reopened saved value",
        page.read_name,
        edited_name,
    )

    page.close_form()

    # 3. Attempt Add using the same edited name.
    page.open_add_form()
    page.set_text(page.NAME, edited_name)
    page.click(page.SAVE)

    # Wait specifically for the duplicate popup.
    # Do not accept a closed form as proof of duplicate rejection.
    def duplicate_response():
        if page.popup_visible():
            return page.popup_details()

        return {
            "title": "",
            "message": "Duplicate rejection popup not visible",
        }

    checks.check(
        "Duplicate Standard Type / Already Exists message",
        duplicate_response,
        {
            "title": "Error",
            "message": page.DUPLICATE_MESSAGE,
        },
    )

    if page.popup_visible():
        print(f"Duplicate response: {page.popup_details()}")
        page.acknowledge_popup()

    page.wait_idle()

    if page.modal_visible():
        page.close_form(cancel=True)

    page.search(edited_name)

    checks.check(
        "Duplicate attempt / only one matching record",
        page.visible_names,
        [edited_name],
    )

    # Stop if identity is ambiguous.
    assert len(page.matching_rows(edited_name)) == 1, (
        "Expected exactly one Standard Type after duplicate attempt: "
        f"{edited_name}"
    )

    # 4. Delete Cancel must retain the same record.
    delete_message = page.request_delete(edited_name)

    checks.check(
        "Standard Type delete confirmation",
        lambda: delete_message,
        page.DELETE_MESSAGE,
    )

    page.cancel_delete()

    checks.check(
        "Delete Cancel / record retained",
        page.visible_names,
        [edited_name],
    )

    # 5. Confirm deletion.
    page.request_delete(edited_name)
    success_message = page.confirm_delete()

    checks.check(
        "Standard Type deletion success",
        lambda: success_message,
        page.DELETE_SUCCESS,
    )

    page.search(edited_name)

    checks.check(
        "Deleted Standard Type / absent from grid",
        page.visible_names,
        [],
    )

    print(
        "Standard Type flow completed: "
        f"{name} -> {edited_name} -> deleted"
    )

    checks.finish()