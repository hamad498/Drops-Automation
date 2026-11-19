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
from pages.item_type_page import ItemTypePage
from pages.login_page import LoginPage


class ItemTypeChecks:
    def __init__(self, driver):
        self.driver = driver
        self.rows = []
        self.saved = False
        self.folder = (
            Path("reports")
            / f"item_type_checks_{uuid4().hex[:12]}"
        )
        self.folder.mkdir(parents=True, exist_ok=True)

    def check(self, label, reader, expected):
        state = {"actual": "Not read", "error": ""}
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
            WebDriverWait(self.driver, TIMEOUT).until(compare)
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
        json_path = self.folder / "field_results.json"
        csv_path = self.folder / "field_results.csv"

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
            row for row in self.rows if row["result"] == "FAIL"
        ]

        self.saved = True

        print(
            "\nCollected Item Type checks: "
            f"{len(self.rows) - len(failures)} passed; "
            f"{len(failures)} failed."
        )
        print(f"Detailed results: {csv_path.resolve()}")

    def finish(self):
        self.save_report()
        failures = [
            row for row in self.rows if row["result"] == "FAIL"
        ]

        if failures:
            summary = "\n".join(
                f"- {row['check']}: "
                f"expected={row['expected']!r}; "
                f"actual={row['actual']!r}"
                for row in failures
            )
            pytest.fail(
                f"Item Type verification failures:\n{summary}",
                pytrace=False,
            )


@pytest.fixture
def item_type_checks(driver):
    checks = ItemTypeChecks(driver)

    try:
        yield checks
    finally:
        if not checks.saved:
            checks.save_report()


def login_to_item_types(driver):
    login = LoginPage(driver)
    login.open()
    login.login(TEST_USERNAME, TEST_PASSWORD)

    dashboard = AdminDashboardPage(driver)
    assert dashboard.get_heading_text() == "Admin Dashboard"

    page = ItemTypePage(driver)
    page.open()
    return page


def reopen_item(page, name):
    page.open()
    page.filter_item_type()
    page.search(name)
    page.edit(name)


def verify_saved_item(page, checks, name, prompts, label):
    page.open()
    page.filter_item_type()
    page.search(name)

    checks.check(
        f"{label} / grid name and checklist count",
        lambda: page.grid_details(name),
        {
            "name": name,
            "checklist_count": len(prompts),
        },
    )

    if prompts:
        page.set_expanded(name, True)
        checks.check(
            f"{label} / expanded prompt text and order",
            lambda: page.expanded_prompts(name),
            prompts,
        )

        page.set_expanded(name, False)
        checks.check(
            f"{label} / collapsed checklist",
            lambda: page.expanded_prompts(name),
            None,
        )

    page.edit(name)
    checks.check(
        f"{label} / reopened form",
        page.form_details,
        {
            "name": name,
            "prompts": prompts,
        },
    )


def delete_all_item_references(page, checks, item_name):
    # Only rows belonging to the disposable Item Type are allowed.
    while page.references():
        before = page.references()
        reference_name, standard_type, owner = before[0]

        assert owner == item_name, (
            "Reference owner does not match the disposable Item Type: "
            f"{owner!r} / {item_name!r}"
        )

        message = page.request_reference_delete(reference_name)
        checks.check(
            f"Reference {reference_name} / delete confirmation",
            lambda text=message: text,
            page.DELETE_MESSAGE,
        )

        page.cancel_delete()
        checks.check(
            f"Reference {reference_name} / Delete Cancel",
            page.references,
            before,
        )

        page.request_reference_delete(reference_name)
        success = page.confirm_delete()

        checks.check(
            f"Reference {reference_name} / deletion success",
            lambda text=success: text,
            page.DELETE_SUCCESS,
        )

        expected = [
            row
            for row in before
            if row != [reference_name, standard_type, owner]
        ]
        checks.check(
            f"Reference {reference_name} / row removed",
            page.references,
            expected,
        )

        assert len(page.references()) < len(before), (
            "Reference deletion did not reduce the number of rows."
        )


def test_item_type_lifecycle(driver, item_type_checks):
    checks = item_type_checks
    page = login_to_item_types(driver)
    suffix = uuid4().hex[:12]

    name = f"Test_Auto_ItemType_{suffix}"
    prompt_one = f"Check primary securing connections {suffix}"
    prompt_two = f"Check secondary retention devices {suffix}"

    # Required field and maximum-length validations.
    page.open_add_form()

    checks.check(
        "Empty Item Type / Save disabled",
        page.save_enabled,
        False,
    )

    page.set_text(page.NAME, " " * 5, verify=False)
    checks.check(
        "Whitespace Item Type / Save disabled",
        page.save_enabled,
        False,
    )

    name_250 = "N" * 250
    page.set_text(page.NAME, name_250)

    checks.check(
        "250-character Item Type retained",
        lambda: page.form_details()["name"],
        name_250,
    )
    checks.check(
        "250-character Item Type allowed",
        page.save_enabled,
        True,
    )

    page.set_text(page.NAME, name_250 + "X", verify=False)
    checks.check(
        "Item Type limited to 250 characters",
        lambda: page.form_details()["name"],
        name_250,
    )

    page.set_text(page.NAME, name)
    page.add_prompt()

    checks.check(
        "Empty added prompt / Save disabled",
        page.save_enabled,
        False,
    )

    page.set_prompt(0, " " * 5, verify=False)
    checks.check(
        "Whitespace prompt / Save disabled",
        page.save_enabled,
        False,
    )

    prompt_250 = "P" * 250
    page.set_prompt(0, prompt_250)

    checks.check(
        "250-character prompt retained",
        lambda: page.form_details()["prompts"][0],
        prompt_250,
    )
    checks.check(
        "250-character prompt allowed",
        page.save_enabled,
        True,
    )

    page.set_prompt(0, prompt_250 + "X", verify=False)
    checks.check(
        "Prompt limited to 250 characters",
        lambda: page.form_details()["prompts"][0],
        prompt_250,
    )

    page.set_prompt(0, prompt_one)
    page.add_prompt()

    checks.check(
        "Second empty prompt / Save disabled",
        page.save_enabled,
        False,
    )

    page.set_prompt(1, prompt_two)
    page.set_text(page.NAME, "")

    checks.check(
        "Prompts present but Item Type empty / Save disabled",
        page.save_enabled,
        False,
    )

    page.set_text(page.NAME, name)
    page.save()

    # Snapshot automatic references without assuming a default name.
    initial_references = page.references()
    print(f"Automatically loaded references: {initial_references}")

    verify_saved_item(
        page,
        checks,
        name,
        [prompt_one, prompt_two],
        "Created Item Type",
    )

    # Search and dropdown filtering.
    page.open()
    page.filter_item_type()
    page.search(name, enter=True)

    checks.check(
        "Search using Enter",
        page.visible_names,
        [name],
    )

    page.search("")
    page.filter_item_type(name)

    checks.check(
        "Item Type dropdown filter",
        page.visible_names,
        [name],
    )

    missing_name = f"No_ItemType_{suffix}"
    page.search(missing_name)

    checks.check(
        "Dropdown combined with nonmatching search",
        page.visible_names,
        [],
    )

    page.search("")
    checks.check(
        "Clearing search restores filtered Item Type",
        page.visible_names,
        [name],
    )

    page.filter_item_type()
    page.search(missing_name)

    checks.check(
        "Nonmatching search returns no Item Types",
        page.visible_names,
        [],
    )

    page.search(name)
    page.edit(name)

    # Edit name and prompts, add a prompt, verify Delete Cancel.
    updated_name = f"{name}_Edited"
    edited_prompt = f"Updated primary securing inspection {suffix}"
    added_prompt = f"Check corrosion and loose fittings {suffix}"

    page.set_text(page.NAME, updated_name)
    page.set_prompt(0, edited_prompt)
    page.add_prompt(added_prompt)

    before_cancel = page.form_details()
    message = page.request_prompt_delete(1)

    checks.check(
        "Prompt delete confirmation",
        lambda: message,
        page.DELETE_MESSAGE,
    )

    page.cancel_delete()
    checks.check(
        "Prompt Delete Cancel preserves form",
        page.form_details,
        before_cancel,
    )

    page.request_prompt_delete(1)
    success = page.confirm_delete()

    checks.check(
        "Prompt deletion success",
        lambda: success,
        page.DELETE_SUCCESS,
    )
    checks.check(
        "Selected prompt removed and others retained",
        lambda: page.form_details()["prompts"],
        [edited_prompt, added_prompt],
    )

    page.save()
    name = updated_name
    expected_prompts = [edited_prompt, added_prompt]

    verify_saved_item(
        page,
        checks,
        name,
        expected_prompts,
        "Edited Item Type",
    )

    # Standard Reference validations.
    references_before_add = page.references()
    page.open_reference_add()

    checks.check(
        "Empty Standard Reference / Save disabled",
        page.reference_save_enabled,
        False,
    )
    checks.check(
        "Reference Item Type is correct and disabled",
        lambda: {
            "item_type": page.reference_form_details()["item_type"],
            "disabled": page.reference_form_details()[
                "item_type_disabled"
            ],
        },
        {
            "item_type": name,
            "disabled": True,
        },
    )

    page.set_text(page.REF_NAME, f"Validation_Standard_{suffix}")

    checks.check(
        "Standard Type required",
        page.reference_save_enabled,
        False,
    )

    page.select_text(page.REF_TYPE, "API")
    page.set_text(page.REF_NAME, "")

    checks.check(
        "Standard name required",
        page.reference_save_enabled,
        False,
    )

    page.set_text(page.REF_NAME, " " * 5, verify=False)
    checks.check(
        "Whitespace Standard name / Save disabled",
        page.reference_save_enabled,
        False,
    )

    standard_250 = "S" * 250
    page.set_text(page.REF_NAME, standard_250)

    checks.check(
        "250-character Standard name allowed",
        page.reference_save_enabled,
        True,
    )

    page.set_text(
        page.REF_NAME,
        standard_250 + "X",
        verify=False,
    )
    checks.check(
        "Standard name limited to 250 characters",
        lambda: page.reference_form_details()["name"],
        standard_250,
    )

    page.close_reference()
    checks.check(
        "Reference Add Close does not create a record",
        page.references,
        references_before_add,
    )

    # Create custom reference.
    reference_name = f"Test_Auto_Standard_{suffix}"
    page.open_reference_add()
    page.fill_reference(reference_name, "API")
    page.save_reference()

    expected_references = references_before_add + [
        [reference_name, "API", name]
    ]

    checks.check(
        "Created Standard Reference",
        lambda: sorted(page.references()),
        sorted(expected_references),
    )

    reopen_item(page, name)
    checks.check(
        "Standard Reference persisted after navigation",
        lambda: sorted(page.references()),
        sorted(expected_references),
    )

    page.edit_reference(reference_name)
    checks.check(
        "Reference Edit initial values",
        page.reference_form_details,
        {
            "name": reference_name,
            "standard_type": "API",
            "item_type": name,
            "item_type_disabled": True,
        },
    )

    # Discard a reference edit.
    page.fill_reference(f"Cancelled_Standard_{suffix}", "ASMI")
    page.close_reference()
    page.edit_reference(reference_name)

    checks.check(
        "Reference Edit Close discards changes",
        page.reference_form_details,
        {
            "name": reference_name,
            "standard_type": "API",
            "item_type": name,
            "item_type_disabled": True,
        },
    )

    # Save edited reference.
    edited_reference = f"{reference_name}_Edited"
    page.fill_reference(edited_reference, "ASMI")
    page.save_reference()

    reopen_item(page, name)
    page.edit_reference(edited_reference)

    checks.check(
        "Edited Reference persisted after reopening",
        page.reference_form_details,
        {
            "name": edited_reference,
            "standard_type": "ASMI",
            "item_type": name,
            "item_type_disabled": True,
        },
    )
    page.close_reference()

    # Delete our custom reference; retain automatic references.
    before_ref_delete = page.references()
    message = page.request_reference_delete(edited_reference)

    checks.check(
        "Reference delete confirmation",
        lambda: message,
        page.DELETE_MESSAGE,
    )

    page.cancel_delete()
    checks.check(
        "Reference Delete Cancel",
        page.references,
        before_ref_delete,
    )

    page.request_reference_delete(edited_reference)
    page.confirm_delete()

    # Do not click the main Item Type Save after reference deletion.
    reopen_item(page, name)

    expected_remaining = [
        row
        for row in before_ref_delete
        if row[0] != edited_reference
    ]
    checks.check(
        "Reference deletion persisted without main Save",
        lambda: sorted(page.references()),
        sorted(expected_remaining),
    )
    checks.check(
        "Reference operations preserved Item Type prompts",
        page.form_details,
        {
            "name": name,
            "prompts": expected_prompts,
        },
    )

    print(f"Item Type retained for inspection: {name}")
    print(f"Retained prompts: {expected_prompts}")

    # Disposable Item Type for confirmed deletion.
    disposable = f"Test_Delete_ItemType_{suffix}"
    disposable_prompt = f"Disposable inspection prompt {suffix}"

    page.open()
    page.open_add_form()
    page.set_text(page.NAME, disposable)
    page.add_prompt(disposable_prompt)
    page.save()

    verify_saved_item(
        page,
        checks,
        disposable,
        [disposable_prompt],
        "Disposable Item Type",
    )

    # Remove procedures first and save.
    while page.prompt_count():
        previous_count = page.prompt_count()
        page.request_prompt_delete(0)
        page.confirm_delete()

        page.wait.until(
            lambda driver: page.prompt_count() == previous_count - 1,
            message="Prompt deletion did not remove the selected row.",
        )

    page.save()

    verify_saved_item(
        page,
        checks,
        disposable,
        [],
        "Disposable Item Type after removing procedures",
    )

    # Remove references after reopening.
    # Navigate directly to the grid afterwards; do not main-Save.
    delete_all_item_references(page, checks, disposable)

    page.open()
    page.filter_item_type()
    page.search(disposable)

    message = page.request_item_delete(disposable)
    checks.check(
        "Item Type delete confirmation",
        lambda: message,
        page.DELETE_MESSAGE,
    )

    page.cancel_delete()
    checks.check(
        "Item Type Delete Cancel retains record",
        lambda: page.grid_details(disposable),
        {
            "name": disposable,
            "checklist_count": 0,
        },
    )

    page.request_item_delete(disposable)
    success = page.confirm_delete()

    checks.check(
        "Item Type deletion success",
        lambda: success,
        page.DELETE_SUCCESS,
    )

    page.search(disposable)
    checks.check(
        "Deleted Item Type absent",
        page.visible_names,
        [],
    )

    page.open()
    page.filter_item_type()
    page.search(disposable)

    checks.check(
        "Deleted Item Type absent after navigation",
        page.visible_names,
        [],
    )

    # Main record remains available for the following inspection flow.
    verify_saved_item(
        page,
        checks,
        name,
        expected_prompts,
        "Retained Item Type after disposable deletion",
    )

    checks.finish()


def test_duplicate_item_type_preserves_existing(
    driver,
    item_type_checks,
):
    checks = item_type_checks
    page = login_to_item_types(driver)
    suffix = uuid4().hex[:12]

    name = f"Test_Duplicate_ItemType_{suffix}"
    original_prompt = f"Original prompt {suffix}"
    replacement_prompt = f"Duplicate attempt prompt {suffix}"

    page.open_add_form()
    page.set_text(page.NAME, name)
    page.add_prompt(original_prompt)
    page.save()

    verify_saved_item(
        page,
        checks,
        name,
        [original_prompt],
        "Duplicate test original",
    )

    # Attempt a new record using exactly the same name.
    page.open()
    page.open_add_form()
    page.set_text(page.NAME, name)
    page.add_prompt(replacement_prompt)
    page.click(page.SAVE)
    page.wait_idle()

    # A rejection popup may appear after a future fix.
    popups = [
        popup
        for popup in driver.find_elements(*page.POPUP)
        if popup.is_displayed()
    ]

    if popups:
        message = page.popup_message()
        print(f"Duplicate Item Type response: {message}")

        cancel_buttons = [
            button
            for button in driver.find_elements(*page.CANCEL)
            if button.is_displayed()
        ]

        if cancel_buttons:
            page.cancel_delete()
        else:
            page.click(page.CONFIRM)
            page.wait.until(
                lambda browser: not any(
                    popup.is_displayed()
                    for popup in browser.find_elements(*page.POPUP)
                )
            )

    page.open()
    page.filter_item_type()
    page.search(name)

    checks.check(
        "Duplicate Item Type / exactly one matching record",
        lambda: page.visible_names().count(name),
        1,
    )

    # Stop if identity is ambiguous; do not edit an arbitrary row.
    assert len(page.matching_rows(name)) == 1, (
        f"Duplicate attempt created multiple matching records: {name}"
    )

    page.edit(name)

    checks.check(
        "Duplicate Item Type / original data preserved",
        page.form_details,
        {
            "name": name,
            "prompts": [original_prompt],
        },
    )

    print(f"Duplicate test record retained for investigation: {name}")
    checks.finish()