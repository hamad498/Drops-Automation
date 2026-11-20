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

from config.settings import TEST_PASSWORD, TEST_USERNAME
from pages.login_page import LoginPage
from pages.rig_items_locations_page import RigItemsLocationsPage


class LocationChecks:
    def __init__(self, driver):
        self.driver = driver
        self.rows = []
        self.saved = False
        self.folder = (
            Path("reports")
            / f"rig_location_checks_{uuid4().hex[:12]}"
        ).resolve()
        self.folder.mkdir(parents=True, exist_ok=True)

    def check(self, label, actual, expected):
        error = ""

        try:
            actual = actual() if callable(actual) else actual
        except (
            AssertionError,
            NoSuchElementException,
            StaleElementReferenceException,
            TimeoutException,
        ) as exc:
            actual = None
            error = str(exc)

        passed = not error and actual == expected
        screenshot = ""

        if not passed:
            target = self.folder / (
                f"failure_{len(self.rows) + 1:03d}.png"
            )
            try:
                if self.driver.save_screenshot(str(target)):
                    screenshot = str(target)
            except Exception as exc:
                error = (
                    f"{error}\nScreenshot unavailable: {exc}"
                ).strip()

        self.rows.append(
            {
                "check": label,
                "expected": expected,
                "actual": actual,
                "result": "PASS" if passed else "FAIL",
                "error": error,
                "screenshot": screenshot,
            }
        )
        self.saved = False

        print(
            f"[{'PASS' if passed else 'FAIL'}] {label}: "
            f"expected={expected!r}; actual={actual!r}"
        )

    def save_report(self):
        csv_path = self.folder / "field_results.csv"

        with csv_path.open(
            "w", newline="", encoding="utf-8-sig"
        ) as output:
            writer = csv.DictWriter(
                output,
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

        (self.folder / "field_results.json").write_text(
            json.dumps(
                self.rows,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        failed = sum(
            row["result"] == "FAIL"
            for row in self.rows
        )

        print(
            "\nCollected Rig Items Locations checks: "
            f"{len(self.rows) - failed} passed; {failed} failed."
        )
        print(f"Detailed results: {csv_path}")
        self.saved = True

    def finish(self):
        self.save_report()
        failures = [
            row
            for row in self.rows
            if row["result"] == "FAIL"
        ]

        if failures:
            pytest.fail(
                "Rig Items Locations verification failures:\n"
                + "\n".join(
                    f"- {row['check']}: "
                    f"expected={row['expected']!r}; "
                    f"actual={row['actual']!r}"
                    for row in failures
                ),
                pytrace=False,
            )


@pytest.fixture
def location_checks(driver):
    checks = LocationChecks(driver)
    yield checks

    # Preserve collected results if an unexpected blocker stops the test.
    if not checks.saved:
        checks.save_report()


def check_form_validation(page, checks, kind):
    checks.check(
        f"{kind} / empty form Save disabled",
        lambda: page.form_save_enabled(kind),
        False,
    )

    if kind != "level":
        page.fill_field(kind, "order", "10")

    # Validation inputs are checked separately, so a changed value
    # becomes a reported failure rather than an exact-value timeout.
    page.fill_field(
        kind,
        "name",
        "   ",
        verify=False,
    )
    checks.check(
        f"{kind} / whitespace name rejected",
        lambda: page.form_save_enabled(kind),
        False,
    )

    page.fill_field(kind, "name", "Validation name")

    if kind != "level":
        for value, expected in [
            ("", False),
            ("0", False),
            ("101", False),
            ("1.5", False),
            ("1", True),
            ("100", True),
        ]:
            page.fill_field(
                kind,
                "order",
                value,
                verify=False,
            )

            if expected:
                checks.check(
                    f"{kind} / valid order {value!r} retained",
                    lambda: page.form_details(kind)["order"],
                    value,
                )

            checks.check(
                f"{kind} / order {value!r} Save enabled",
                lambda: page.form_save_enabled(kind),
                expected,
            )

        page.fill_field(kind, "order", "10")

    # Important: do not wait for an exact match here.
    # Record the actual value and continue the lifecycle.
    page.fill_field(
        kind,
        "name",
        "X" * 100,
        verify=False,
    )

    checks.check(
        f"{kind} / 100 character name retained",
        lambda: page.form_details(kind)["name"],
        "X" * 100,
    )
    checks.check(
        f"{kind} / 100 character name Save enabled",
        lambda: page.form_save_enabled(kind),
        True,
    )


def reopen_and_check(page, checks, kind, path, expected):
    page.edit_node(kind, path)

    checks.check(
        f"{kind} / reopened values",
        lambda: page.form_details(kind),
        expected,
    )

    page.close_form(kind)


def test_rig_items_locations_lifecycle(driver, location_checks):
    checks = location_checks
    page = RigItemsLocationsPage(driver)

    login = LoginPage(driver)
    login.open()
    login.login(TEST_USERNAME, TEST_PASSWORD)

    page.open()

    suffix = uuid4().hex[:12]

    zone = f"Auto_Default_Zone_{suffix}"
    area = f"Auto_Default_Area_{suffix}"
    level = f"Auto_Default_Level_{suffix}"

    edited_zone = f"{zone}_Edited"
    edited_area = f"{area}_Edited"
    edited_level = f"{level}_Edited"

    print(f"\nTest Zone: {zone}")
    print(f"Test Area: {area}")
    print(f"Test Level: {level}")

    # Create our own Zone.
    page.open_add("zone")
    check_form_validation(page, checks, "zone")

    page.fill_field("zone", "name", zone)
    page.fill_field("zone", "order", "90")
    page.save_form("zone")
    page.wait_for_node([zone])

    reopen_and_check(
        page,
        checks,
        "zone",
        [zone],
        {"name": zone, "order": "90"},
    )

    # Create our own Area inside that Zone.
    page.open_add("area", [zone])
    check_form_validation(page, checks, "area")

    page.fill_field("area", "name", area)
    page.fill_field("area", "order", "90")
    page.save_form("area")
    page.wait_for_node([zone, area])

    reopen_and_check(
        page,
        checks,
        "area",
        [zone, area],
        {"name": area, "order": "90"},
    )

    # Create our own Level inside that Area.
    page.open_add("level", [zone, area])
    check_form_validation(page, checks, "level")

    page.fill_field("level", "name", level)
    page.save_form("level")
    page.wait_for_node([zone, area, level])

    reopen_and_check(
        page,
        checks,
        "level",
        [zone, area, level],
        {"name": level},
    )

    # Edit the same Zone.
    page.edit_node("zone", [zone])
    page.fill_field("zone", "name", edited_zone)
    page.fill_field("zone", "order", "91")
    page.save_form("zone")
    page.wait_for_node([edited_zone, area, level])

    # Edit the same Area.
    page.edit_node("area", [edited_zone, area])
    page.fill_field("area", "name", edited_area)
    page.fill_field("area", "order", "91")
    page.save_form("area")
    page.wait_for_node([edited_zone, edited_area, level])

    # Edit the same Level.
    page.edit_node(
        "level",
        [edited_zone, edited_area, level],
    )
    page.fill_field("level", "name", edited_level)
    page.save_form("level")

    full_path = [
        edited_zone,
        edited_area,
        edited_level,
    ]
    page.wait_for_node(full_path)

    # Return through the sidebar and verify saved values.
    page.open()
    page.wait_for_node(full_path)

    reopen_and_check(
        page,
        checks,
        "zone",
        [edited_zone],
        {"name": edited_zone, "order": "91"},
    )
    reopen_and_check(
        page,
        checks,
        "area",
        [edited_zone, edited_area],
        {"name": edited_area, "order": "91"},
    )
    reopen_and_check(
        page,
        checks,
        "level",
        full_path,
        {"name": edited_level},
    )

    # Parent deletion must be blocked while children exist.
    for kind, path in [
        ("zone", [edited_zone]),
        ("area", [edited_zone, edited_area]),
    ]:
        message = page.parent_delete_response(kind, path)

        checks.check(
            f"{kind} / parent deletion blocked",
            page.normalize(message),
            page.normalize(page.BLOCKED_MESSAGE),
        )
        checks.check(
            f"{kind} / hierarchy retained after blocked delete",
            lambda: page.exists(full_path),
            True,
        )

        assert page.exists(full_path), (
            "Parent deletion unexpectedly removed our hierarchy. "
            "Review the saved report."
        )

    # Delete only our own records: Level, then Area, then Zone.
    for kind, path in [
        ("level", full_path),
        ("area", [edited_zone, edited_area]),
        ("zone", [edited_zone]),
    ]:
        details = page.request_node_delete(kind, path)

        checks.check(
            f"{kind} / delete confirmation displayed",
            details["confirmation"],
            True,
        )
        assert details["confirmation"], (
            f"Expected delete confirmation for {kind}: {details}"
        )

        page.dismiss_popup(cancel=True)

        checks.check(
            f"{kind} / Cancel preserves record",
            lambda: page.exists(path),
            True,
        )

        details = page.request_node_delete(kind, path)

        assert details["confirmation"], (
            f"Expected delete confirmation for {kind}: {details}"
        )

        message = page.confirm_node_delete()

        checks.check(
            f"{kind} / delete success message",
            message,
            page.SUCCESS_MESSAGE,
        )

        page.wait_for_absence(path)

        checks.check(
            f"{kind} / removed from hierarchy",
            lambda: page.exists(path),
            False,
        )

    # Verify deletion persists after opening the page again.
    page.open()

    checks.check(
        "Edited Zone absent after reopening",
        lambda: page.exists([edited_zone]),
        False,
    )
    checks.check(
        "Original Zone name absent after reopening",
        lambda: page.exists([zone]),
        False,
    )

    print(
        "\nOwn Zone → Area → Level lifecycle completed: "
        "created, edited, reopened and deleted."
    )

    checks.finish()