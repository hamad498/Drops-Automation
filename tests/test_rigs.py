import csv
import json

from datetime import date, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from selenium.common.exceptions import (
    ElementClickInterceptedException,
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from config.settings import TEST_USERNAME, TEST_PASSWORD, TIMEOUT
from pages.admin_dashboard_page import AdminDashboardPage
from pages.client_page import ClientPage
from pages.inspector_certificate_page import InspectorCertificatePage
from pages.inspector_page import InspectorPage
from pages.job_page import JobPage
from pages.login_page import LoginPage
from pages.rig_page import RigPage


class FlowChecks:
    """Collect independent verification failures without stopping the flow."""

    def __init__(self, driver, timeout):
        self.driver = driver
        self.timeout = timeout
        self.rows = []
        self.report_saved = False
        self.folder = Path("reports") / f"flow_checks_{uuid4().hex[:12]}"
        self.folder.mkdir(parents=True, exist_ok=True)

    def check(self, label, reader, expected):
        state = {"actual": "Not read", "error": ""}

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

        passed = False

        try:
            WebDriverWait(self.driver, self.timeout).until(compare)
            passed = True

        except (TimeoutException, AssertionError) as error:
            state["error"] = (
                state["error"]
                or str(error).split("Stacktrace:")[0]
            )

        screenshot = ""

        if not passed:
            target = self.folder / f"failure_{len(self.rows) + 1:03d}.png"
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
        self.report_saved = False

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
            "w", newline="", encoding="utf-8-sig"
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
        self.report_saved = True

        print(
            "\nCollected field checks: "
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
                f"- {row['check']}: expected={row['expected']!r}; "
                f"actual={row['actual']!r}"
                for row in failures
            )
            pytest.fail(
                f"Flow verification failures:\n{summary}",
                pytrace=False,
            )


@pytest.fixture
def flow_checks(driver):
    checks = FlowChecks(driver, TIMEOUT)

    try:
        yield checks
    finally:
        if not checks.report_saved:
            checks.save_report()


def exercise_rig_hierarchy(
    rigs,
    checks,
    client_name,
    rig_name,
    suffix,
):
    """Exercise only the hierarchy created by this test."""

    zone = f"Auto_Zone_{suffix}"
    area = f"Auto_Area_{suffix}"
    level = f"Auto_Level_{suffix}"

    def reopen_rig():
        rigs.save()
        rigs.search(rig_name)
        rigs.edit(client_name, rig_name)

    def expected_tree(zone_name, area_name, level_name):
        return {
            "name": zone_name,
            "children": [
                {
                    "name": area_name,
                    "children": [
                        {
                            "name": level_name,
                            "children": [],
                        }
                    ],
                }
            ],
        }

    def validate_add_form(kind, parent_path):
        parent_before = (
            rigs.tree_snapshot(parent_path)
            if parent_path else None
        )
        rigs.open_tree_form(kind, parent_path=parent_path)
        fields = rigs.TREE_FIELDS[kind]

        # Explicitly clear fields in case the UI supplies defaults.
        rigs.set_text(fields["name"], "")
        if "order" in fields:
            rigs.set_text(fields["order"], "")

        checks.check(
            f"{kind} validation / empty required fields",
            lambda: rigs.tree_save_enabled(kind),
            False,
        )

        if "order" in fields:
            rigs.set_text(fields["order"], "10")
            checks.check(
                f"{kind} validation / empty name",
                lambda: rigs.tree_save_enabled(kind),
                False,
            )

        rigs.set_text(fields["name"], f"Validation_{kind}")

        if "order" in fields:
            rigs.set_text(fields["order"], "")
            checks.check(
                f"{kind} validation / empty order",
                lambda: rigs.tree_save_enabled(kind),
                False,
            )

            for invalid_order in ("-1", "0", "101", "1.5"):
                rigs.set_text(fields["order"], invalid_order)
                checks.check(
                    f"{kind} validation / order {invalid_order}",
                    lambda: rigs.tree_save_enabled(kind),
                    False,
                )

            for valid_order in ("1", "100"):
                rigs.set_text(fields["order"], valid_order)
                checks.check(
                    f"{kind} validation / order boundary {valid_order}",
                    lambda: rigs.tree_save_enabled(kind),
                    True,
                )

            rigs.set_text(fields["order"], "10")

        name_100 = "N" * 100
        rigs.set_text(fields["name"], name_100)

        checks.check(
            f"{kind} validation / 100-character name retained",
            lambda: rigs.read_tree_field(kind, "name"),
            name_100,
        )
        checks.check(
            f"{kind} validation / 100-character name allowed",
            lambda: rigs.tree_save_enabled(kind),
            True,
        )

        # Do not demand exact entry of 101 characters: maxlength should limit it.
        rigs.set_text(
            fields["name"],
            name_100 + "X",
            verify=False,
        )
        checks.check(
            f"{kind} validation / name limited to 100 characters",
            lambda: rigs.read_tree_field(kind, "name"),
            name_100,
        )

        # Zone has an explicit Cancel; Area/Level use their Close button.
        rigs.close_tree_form(kind, cancel=(kind == "zone"))

        if parent_path:
            checks.check(
                f"{kind} add cancelled / parent unchanged",
                lambda: rigs.tree_snapshot(parent_path),
                parent_before,
            )

    def create_node(kind, name, parent_path=(), order=None):
        rigs.open_tree_form(kind, parent_path=parent_path)
        rigs.fill_tree_form(kind, name, order)
        rigs.save_tree_form(kind)

        path = tuple(parent_path) + (name,)
        rigs.wait.until(
            lambda driver: rigs.find_tree_node(path) is not None,
            message=f"New {kind} missing: {path}",
        )

    # Never enable Default Locations or copy existing server records here.
    assert rigs.find_tree_node((zone,)) is None

    validate_add_form("zone", ())
    checks.check(
        "Zone add cancelled / validation name absent",
        lambda: rigs.find_tree_node(("N" * 100,)) is None,
        True,
    )
    create_node("zone", zone, order="10")

    validate_add_form("area", (zone,))
    create_node("area", area, (zone,), order="20")

    validate_add_form("level", (zone, area))
    create_node("level", level, (zone, area))

    original = expected_tree(zone, area, level)

    checks.check(
        "Created Rig hierarchy / correct parent relationships",
        lambda: rigs.tree_snapshot((zone,)),
        original,
    )

    reopen_rig()
    checks.check(
        "Created Rig hierarchy / save and reopen",
        lambda: rigs.tree_snapshot((zone,)),
        original,
    )

    # Check saved field values, then discard edits using Cancel/Close.
    for kind, path, saved_order in (
        ("zone", (zone,), "10"),
        ("area", (zone, area), "20"),
        ("level", (zone, area, level), None),
    ):
        rigs.open_tree_form(kind, edit_path=path)

        checks.check(
            f"{kind} reopened / name",
            lambda k=kind: rigs.read_tree_field(k, "name"),
            path[-1],
        )
        if saved_order is not None:
            checks.check(
                f"{kind} reopened / order",
                lambda k=kind: rigs.read_tree_field(k, "order"),
                saved_order,
            )

        rigs.fill_tree_form(
            kind,
            f"Cancelled_{kind}_{suffix}",
            "30" if saved_order is not None else None,
        )
        rigs.close_tree_form(kind, cancel=(kind == "zone"))

        checks.check(
            f"{kind} edit cancelled / hierarchy unchanged",
            lambda: rigs.tree_snapshot((zone,)),
            original,
        )

    # Edit from leaf upward, so parent paths remain valid while editing.
    edited_zone = f"{zone}_Edited"
    edited_area = f"{area}_Edited"
    edited_level = f"{level}_Edited"

    rigs.open_tree_form(
        "level",
        edit_path=(zone, area, level),
    )
    rigs.fill_tree_form("level", edited_level)
    rigs.save_tree_form("level")

    rigs.open_tree_form(
        "area",
        edit_path=(zone, area),
    )
    rigs.fill_tree_form("area", edited_area, "21")
    rigs.save_tree_form("area")

    rigs.open_tree_form("zone", edit_path=(zone,))
    rigs.fill_tree_form("zone", edited_zone, "11")
    rigs.save_tree_form("zone")

    zone, area, level = edited_zone, edited_area, edited_level
    edited = expected_tree(zone, area, level)

    reopen_rig()
    checks.check(
        "Edited Rig hierarchy / save and reopen",
        lambda: rigs.tree_snapshot((zone,)),
        edited,
    )

    for kind, path, order in (
        ("zone", (zone,), "11"),
        ("area", (zone, area), "21"),
        ("level", (zone, area, level), None),
    ):
        rigs.open_tree_form(kind, edit_path=path)
        checks.check(
            f"Edited {kind} reopened / name",
            lambda k=kind: rigs.read_tree_field(k, "name"),
            path[-1],
        )
        if order is not None:
            checks.check(
                f"Edited {kind} reopened / order",
                lambda k=kind: rigs.read_tree_field(k, "order"),
                order,
            )
        rigs.close_tree_form(kind)

    # Parents with children must remain unchanged after Delete.
    for kind, path in (
        ("Zone", (zone,)),
        ("Area", (zone, area)),
    ):
        message = rigs.check_parent_delete_response(path)

        checks.check(
            f"{kind} deletion with children / warning",
            lambda text=message: text,
            rigs.RELATED_RECORDS_MESSAGE,
        )
        checks.check(
            f"{kind} deletion blocked / hierarchy unchanged",
            lambda: rigs.tree_snapshot((zone,)),
            edited,
        )

        # A missing parent blocks safe continuation of the hierarchy flow.
        assert rigs.find_tree_node(path) is not None, (
            f"{kind} was incorrectly deleted while it had children."
        )

    # Delete only our test nodes: Level -> Area -> Zone.
    for kind, path in (
        ("level", (zone, area, level)),
        ("area", (zone, area)),
        ("zone", (zone,)),
    ):
        before_cancel = rigs.tree_snapshot((zone,))
        response = rigs.request_tree_delete(path)

        has_confirmation = (
            response["popup"] and response["cancel"]
        )
        checks.check(
            f"{kind} delete / Cancel confirmation available",
            lambda actual=has_confirmation: actual,
            True,
        )

        if has_confirmation:
            rigs.cancel_delete()
            checks.check(
                f"{kind} delete cancelled / hierarchy unchanged",
                lambda: rigs.tree_snapshot((zone,)),
                before_cancel,
            )

            response = rigs.request_tree_delete(path)

        if response["popup"]:
            if response["cancel"]:
                rigs.confirm_tree_delete(path)
            else:
                # Direct deletion may show only an informational result.
                rigs.acknowledge_popup()

        checks.check(
            f"{kind} confirmed deletion / node absent",
            lambda p=path: rigs.find_tree_node(p) is None,
            True,
        )

        assert rigs.find_tree_node(path) is None, (
            f"Could not delete test {kind}: {path}"
        )

    reopen_rig()
    checks.check(
        "Deleted Rig hierarchy / absent after save and reopen",
        lambda: rigs.find_tree_node((zone,)) is None,
        True,
    )

    # Restore our hierarchy for the following inspection flow.
    create_node("zone", zone, order="11")
    create_node("area", area, (zone,), order="21")
    create_node("level", level, (zone, area))

    reopen_rig()
    checks.check(
        "Retained Rig hierarchy / save and reopen",
        lambda: rigs.tree_snapshot((zone,)),
        edited,
    )

    print(f"Zone retained for inspection: {zone}")
    print(f"Area retained for inspection: {area}")
    print(f"Level retained for inspection: {level}")


def test_client_to_rig_flow(driver, flow_checks):
    test_data = (
        Path(__file__).resolve().parent.parent / "test_data"
    )
    certificate_file = test_data / "inspector_certificate.pdf"
    report_file = test_data / "Additional_Inspection_Report.pdf"
    contract_file = test_data / "Contract_Completion.pdf"
    signature_file = test_data / "signature.png"

    for attachment in (
        certificate_file,
        report_file,
        contract_file,
    ):
        assert attachment.is_file(), f"Missing PDF: {attachment}"
        assert attachment.stat().st_size > 0, (
            f"PDF is empty: {attachment}"
        )

    assert signature_file.is_file(), (
        f"Signature image missing: {signature_file}"
    )
    assert 0 < signature_file.stat().st_size <= 1024 * 1024, (
        "signature.png must contain a real image no larger than 1 MB."
    )

    # Login.
    login_page = LoginPage(driver)
    login_page.open()
    login_page.login(TEST_USERNAME, TEST_PASSWORD)

    dashboard = AdminDashboardPage(driver)
    assert dashboard.get_heading_text() == "Admin Dashboard"

    suffix = uuid4().hex[:12]
    client_name = f"Test_Auto_Client_{suffix}"
    rig_name = f"Test_Auto_Rig_{suffix}"
    rig_type = "Barges"
    today = date.today()

    rig_start = today.strftime("%m/%d/%Y")
    rig_end = (
        today + timedelta(days=365)
    ).strftime("%m/%d/%Y")

    print(f"Test Client: {client_name}")
    print(f"Test Rig: {rig_name}")

    # Create Client.
    clients = ClientPage(driver)
    clients.open()
    clients.open_add_form()
    clients.fill_form(
        client_name,
        "Islamabad",
        "Automation Test Address",
    )
    clients.save()
    clients.wait_for_grid()
    clients.search(client_name)

    assert clients.get_client_details(client_name) == [
        client_name,
        "Automation Test Address",
        "Islamabad",
    ], "Client was not saved with the expected details."

    # Create Rig.
    rigs = RigPage(driver)
    rigs.open()
    rigs.open_add_form()
    rigs.fill_form(
        client_name=client_name,
        rig_type=rig_type,
        rig_name=rig_name,
        location="Karachi",
    )
    rigs.set_license_dates(rig_start, rig_end)
    rigs.save()
    rigs.search(rig_name)

    assert rigs.get_rig_details(client_name, rig_name) == [
        client_name,
        rig_name,
        rig_type,
    ], "Rig was not saved under the expected Client and Rig Type."

    rigs.edit(client_name, rig_name)
    original_rig = {
        "client": client_name,
        "rig_type": rig_type,
        "rig_name": rig_name,
        "location": "Karachi",
    }
    assert rigs.wait_for_form_details(original_rig) == original_rig

    flow_checks.check(
        "Created Rig / License Start Date",
        lambda: rigs.read_license_date("license_start"),
        rig_start,
    )
    flow_checks.check(
        "Created Rig / License End Date",
        lambda: rigs.read_license_date("license_end"),
        rig_end,
    )

    # Update Rig.
    updated_rig_name = f"{rig_name}_Edited"
    updated_rig_type = "Land rig"
    updated_location = "Lahore"
    updated_rig_start = (
        today + timedelta(days=1)
    ).strftime("%m/%d/%Y")
    updated_rig_end = (
        today + timedelta(days=730)
    ).strftime("%m/%d/%Y")

    rigs.fill_form(
        client_name=client_name,
        rig_type=updated_rig_type,
        rig_name=updated_rig_name,
        location=updated_location,
    )
    rigs.set_license_dates(updated_rig_start, updated_rig_end)
    rigs.save()
    rigs.search(updated_rig_name)

    assert rigs.get_rig_details(
        client_name, updated_rig_name
    ) == [
        client_name,
        updated_rig_name,
        updated_rig_type,
    ], "Updated Rig details did not appear in the grid."

    rigs.edit(client_name, updated_rig_name)
    updated_rig = {
        "client": client_name,
        "rig_type": updated_rig_type,
        "rig_name": updated_rig_name,
        "location": updated_location,
    }
    assert rigs.wait_for_form_details(updated_rig) == updated_rig

    flow_checks.check(
        "Updated Rig / License Start Date",
        lambda: rigs.read_license_date("license_start"),
        updated_rig_start,
    )
    flow_checks.check(
        "Updated Rig / License End Date",
        lambda: rigs.read_license_date("license_end"),
        updated_rig_end,
    )

    rig_name = updated_rig_name

    # Custom Zone / Area / Level checks.
    # Returns with the saved Rig Edit form open.
    exercise_rig_hierarchy(
        rigs,
        flow_checks,
        client_name,
        rig_name,
        suffix,
    )

    # Rig Delete Cancel.
    rigs.open()
    rigs.search(rig_name)
    rigs.request_delete(client_name, rig_name)

    assert rigs.get_delete_message() == (
        "This record should be permanently deleted "
        "are you sure you want to Delete?"
    )
    rigs.cancel_delete()

    assert rigs.get_rig_details(client_name, rig_name) == [
        client_name,
        rig_name,
        updated_rig_type,
    ], "Rig disappeared or changed after cancelling deletion."

    print(f"Client retained for next steps: {client_name}")
    print(f"Rig retained for next steps: {rig_name}")

    # Create Inspector with signature.
    inspectors = InspectorPage(driver)
    inspector_name = f"Test_Auto_Inspector_{suffix}"
    inspector_email = f"test.auto.{suffix}@example.com"

    inspectors.open()
    inspectors.open_add_form()
    inspectors.wait_for_signature_absent()
    inspectors.fill_form(inspector_name, inspector_email, "BS")
    inspectors.upload_signature(signature_file)
    inspectors.save()
    inspectors.search(inspector_name)

    assert inspectors.get_details(
        inspector_name, inspector_email
    ) == [
        inspector_name,
        inspector_email,
        "BS",
    ], "Created Inspector details do not match."

    inspectors.edit(inspector_name, inspector_email)
    original_inspector = {
        "name": inspector_name,
        "email": inspector_email,
        "qualification": "BS",
    }
    assert inspectors.wait_for_form_details(
        original_inspector
    ) == original_inspector

    inspectors.wait_for_signature()
    print("Signature upload and save/reopen verified.")

    # Remove signature, save and reopen.
    inspectors.remove_signature()
    inspectors.save()
    inspectors.search(inspector_name)
    inspectors.edit(inspector_name, inspector_email)

    assert inspectors.wait_for_form_details(
        original_inspector
    ) == original_inspector
    inspectors.wait_for_signature_absent()
    print("Signature removal and save/reopen verified.")

    # Restore signature and update Inspector.
    inspectors.upload_signature(signature_file)
    updated_inspector_name = f"{inspector_name}_Edited"
    updated_inspector_email = (
        f"test.auto.edited.{suffix}@example.com"
    )

    inspectors.fill_form(
        updated_inspector_name,
        updated_inspector_email,
        "BS Software Engineering",
    )
    inspectors.save()
    inspectors.search(updated_inspector_name)

    assert inspectors.get_details(
        updated_inspector_name,
        updated_inspector_email,
    ) == [
        updated_inspector_name,
        updated_inspector_email,
        "BS Software Engineering",
    ], "Updated Inspector details do not match."

    inspectors.edit(
        updated_inspector_name,
        updated_inspector_email,
    )
    updated_inspector = {
        "name": updated_inspector_name,
        "email": updated_inspector_email,
        "qualification": "BS Software Engineering",
    }
    assert inspectors.wait_for_form_details(
        updated_inspector
    ) == updated_inspector
    inspectors.wait_for_signature()

    inspector_name = updated_inspector_name
    inspector_email = updated_inspector_email

    print(f"Inspector for Job assignment: {inspector_name}")
    print(f"Inspector email: {inspector_email}")

    inspectors.close_form()
    inspectors.search(inspector_name)

    # Create Certificate.
    certificates = InspectorCertificatePage(driver)
    certificates.open_for_inspector(inspector_name, inspector_email)
    certificate_name = f"Test_Auto_Certificate_{suffix}"

    certificates.open_add_form()
    certificates.fill_form(
        certificate_name,
        "01/15/2026",
        "01/15/2027",
    )
    certificates.upload_attachment(certificate_file)
    certificates.save()

    assert certificates.get_details(certificate_name) == [
        certificate_name,
        "15-Jan-26",
        "15-Jan-27",
        certificate_file.name,
    ], "Created Certificate details or attachment do not match."

    certificates.edit(certificate_name)
    original_certificate = {
        "name": certificate_name,
        "issue_date": "01/15/2026",
        "expiry_date": "01/15/2027",
    }
    assert certificates.wait_for_form_details(
        original_certificate
    ) == original_certificate

    # Update Certificate.
    updated_certificate_name = f"{certificate_name}_Edited"
    certificates.fill_form(
        updated_certificate_name,
        "02/20/2026",
        "02/20/2027",
    )
    certificates.save()

    expected_certificate_row = [
        updated_certificate_name,
        "20-Feb-26",
        "20-Feb-27",
        certificate_file.name,
    ]
    assert certificates.get_details(
        updated_certificate_name
    ) == expected_certificate_row

    certificates.edit(updated_certificate_name)
    updated_certificate = {
        "name": updated_certificate_name,
        "issue_date": "02/20/2026",
        "expiry_date": "02/20/2027",
    }
    assert certificates.wait_for_form_details(
        updated_certificate
    ) == updated_certificate
    certificates.cancel_form()

    message = certificates.request_delete(updated_certificate_name)
    assert message == (
        "This record should be permanently deleted "
        "are you sure you want to Delete?"
    )
    certificates.cancel_delete()

    assert certificates.get_details(
        updated_certificate_name
    ) == expected_certificate_row

    print(f"Certificate retained: {updated_certificate_name}")

    # Close Certificate list modal.
    certificate_modal_locator = (
        By.XPATH,
        "//span[@title='Add Inspector Certificate']"
        "/ancestor::div["
        "contains(concat(' ', normalize-space(@class), ' '), ' modal ')"
        "][1]",
    )

    def close_certificate_list(browser):
        try:
            for modal in browser.find_elements(
                *certificate_modal_locator
            ):
                if not modal.is_displayed():
                    continue

                buttons = modal.find_elements(
                    By.CSS_SELECTOR,
                    "button.close[aria-label='Close'][data-dismiss='modal']",
                )
                for button in buttons:
                    if (
                        not button.is_displayed()
                        or not button.is_enabled()
                    ):
                        continue

                    browser.execute_script(
                        """
                        arguments[0].scrollIntoView({
                            block: 'center',
                            inline: 'nearest',
                            behavior: 'instant'
                        });
                        """,
                        button,
                    )
                    button.click()
                    return True

            return False

        except (
            ElementClickInterceptedException,
            StaleElementReferenceException,
        ):
            return False

    def certificate_list_closed(browser):
        try:
            return not any(
                modal.is_displayed()
                for modal in browser.find_elements(
                    *certificate_modal_locator
                )
            )
        except StaleElementReferenceException:
            return False

    inspectors.wait.until(
        close_certificate_list,
        message="Could not close the Certificate list modal.",
    )
    inspectors.wait.until(
        certificate_list_closed,
        message="Certificate list modal remained visible.",
    )

    # Create Job using the same Client, Rig and Inspector.
    jobs = JobPage(driver)
    jobs.open()
    jobs.open_add_form()

    job_number = f"Test_Auto_Job_{suffix}"
    job_description = "Automation end-to-end inspection job"
    inspection_day = today
    inspection_date = inspection_day.strftime("%m/%d/%Y")
    next_inspection = (
        inspection_day + timedelta(days=365)
    ).strftime("%m/%d/%Y")

    jobs.fill_form(
        number=job_number,
        description=job_description,
        inspection_date=inspection_date,
        next_inspection=next_inspection,
        client_name=client_name,
        rig_name=rig_name,
        status="Current",
        stage="Job Created",
    )

    additional_fields = {
        "po_number": f"PO_AUTO_{suffix}",
        "report_issue_date": inspection_date,
        "report_number": f"REPORT_AUTO_{suffix}",
        "inspection_reference": f"INSP_AUTO_{suffix}",
        "paid_status": "Paid",
        "reporting_office": "DUBAI",
        "technical_manager": "Ather Sky",
    }

    jobs.fill_additional_fields(additional_fields)
    jobs.set_checkbox(jobs.ONGOING_ACCESS, True)
    jobs.set_checkbox(jobs.AUTO_REFERENCE, True)
    jobs.save_and_assign()
    jobs.assign_inspector(inspector_name)

    section_name = f"Automation_Report_{suffix}"
    report_details = jobs.upload_report(section_name, report_file)

    flow_checks.check(
        "Uploaded report link text",
        lambda: report_details["link_text"],
        "Additional_Inspection_Report",
    )

    contract_link_text = jobs.upload_contract(contract_file)
    assert contract_link_text, "Contract attachment link is empty."

    jobs.update()
    jobs.open()
    jobs.search(job_number)

    expected_grid = {
        "number": job_number,
        "description": job_description,
        "inspectors": [inspector_name],
        "inspection_date": inspection_day.strftime("%d-%b-%y"),
        "client": client_name,
        "rig": rig_name,
        "paid_status": "Paid",
    }

    jobs.get_job_grid_details(job_number)

    for field_name, expected_value in expected_grid.items():
        flow_checks.check(
            f"Created Job grid / {field_name}",
            lambda key=field_name: (
                jobs.get_job_grid_details(job_number)[key]
            ),
            expected_value,
        )

    jobs.edit(job_number)
    expected_form = {
        "number": job_number,
        "description": job_description,
        "inspection_date": inspection_date,
        "next_inspection": next_inspection,
        "status": "Current",
        "stage": "Job Created",
        "client": client_name,
        "rig": rig_name,
        "ongoing_access": True,
        "auto_reference": True,
        **additional_fields,
    }

    for field_name, expected_value in expected_form.items():
        flow_checks.check(
            f"Created Job reopened / {field_name}",
            lambda key=field_name: jobs.read_field(key),
            expected_value,
        )

    def assigned_inspector_present():
        jobs.wait_for_inspector(inspector_name)
        return True

    flow_checks.check(
        "Assigned Inspector after reopening",
        assigned_inspector_present,
        True,
    )
    flow_checks.check(
        "Additional report after reopening",
        lambda: jobs.wait_for_report(section_name),
        report_details,
    )
    flow_checks.check(
        "Contract attachment after reopening",
        lambda: jobs.visible(jobs.CONTRACT_LINK).text.strip(),
        contract_link_text,
    )

    # Update Job optional fields and checkboxes.
    updated_description = "Updated automation inspection job"
    jobs.set_text(jobs.DESCRIPTION, updated_description)

    updated_additional_fields = {
        **additional_fields,
        "po_number": f"PO_EDITED_{suffix}",
        "report_issue_date": (
            inspection_day + timedelta(days=1)
        ).strftime("%m/%d/%Y"),
        "report_number": f"REPORT_EDITED_{suffix}",
        "inspection_reference": f"INSP_EDITED_{suffix}",
        "paid_status": "UnPaid",
    }

    jobs.fill_additional_fields(updated_additional_fields)
    jobs.set_checkbox(jobs.ONGOING_ACCESS, False)
    jobs.set_checkbox(jobs.AUTO_REFERENCE, False)
    jobs.update()

    jobs.open()
    jobs.search(job_number)

    expected_grid["description"] = updated_description
    expected_grid["paid_status"] = "UnPaid"
    jobs.get_job_grid_details(job_number)

    for field_name, expected_value in expected_grid.items():
        flow_checks.check(
            f"Updated Job grid / {field_name}",
            lambda key=field_name: (
                jobs.get_job_grid_details(job_number)[key]
            ),
            expected_value,
        )

    jobs.edit(job_number)
    expected_form.update(updated_additional_fields)
    expected_form["description"] = updated_description
    expected_form["ongoing_access"] = False
    expected_form["auto_reference"] = False

    for field_name, expected_value in expected_form.items():
        flow_checks.check(
            f"Updated Job reopened / {field_name}",
            lambda key=field_name: jobs.read_field(key),
            expected_value,
        )

    flow_checks.check(
        "Assigned Inspector after Job update",
        assigned_inspector_present,
        True,
    )
    flow_checks.check(
        "Additional report after Job update",
        lambda: jobs.wait_for_report(section_name),
        report_details,
    )
    flow_checks.check(
        "Contract attachment after Job update",
        lambda: jobs.visible(jobs.CONTRACT_LINK).text.strip(),
        contract_link_text,
    )

    print(f"Job retained for inspection: {job_number}")
    print(f"Client: {client_name}")
    print(f"Rig: {rig_name}")
    print(f"Assigned Inspector: {inspector_name}")

    flow_checks.finish()