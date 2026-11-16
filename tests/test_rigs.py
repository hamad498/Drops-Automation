from datetime import date, timedelta
from pathlib import Path
from uuid import uuid4

from selenium.common.exceptions import (
    ElementClickInterceptedException,
    StaleElementReferenceException,
)
from selenium.webdriver.common.by import By

from config.settings import TEST_USERNAME, TEST_PASSWORD
from pages.admin_dashboard_page import AdminDashboardPage
from pages.client_page import ClientPage
from pages.inspector_certificate_page import InspectorCertificatePage
from pages.inspector_page import InspectorPage
from pages.job_page import JobPage
from pages.login_page import LoginPage
from pages.rig_page import RigPage


def test_client_to_rig_flow(driver):
    # Check files before creating records.
    test_data = Path(__file__).resolve().parent.parent / "test_data"

    certificate_file = test_data / "inspector_certificate.pdf"
    report_file = test_data / "Additional_Inspection_Report.pdf"
    contract_file = test_data / "Contract_Completion.pdf"

    for attachment in (certificate_file, report_file, contract_file):
        assert attachment.is_file(), f"Missing PDF: {attachment}"
        assert attachment.stat().st_size > 0, (
            f"PDF is empty: {attachment}"
        )

    # Login.
    login_page = LoginPage(driver)
    login_page.open()
    login_page.login(TEST_USERNAME, TEST_PASSWORD)

    dashboard = AdminDashboardPage(driver)
    assert dashboard.get_heading_text() == "Admin Dashboard"

    # Keep related records identifiable.
    suffix = uuid4().hex[:12]
    client_name = f"Test_Auto_Client_{suffix}"
    rig_name = f"Test_Auto_Rig_{suffix}"
    rig_type = "Barges"

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

    # Create Rig under the same Client.
    rigs = RigPage(driver)
    rigs.open()
    rigs.open_add_form()
    rigs.fill_form(
        client_name=client_name,
        rig_type=rig_type,
        rig_name=rig_name,
        location="Karachi",
    )
    rigs.save()
    rigs.search(rig_name)

    assert rigs.get_rig_details(client_name, rig_name) == [
        client_name,
        rig_name,
        rig_type,
    ], "Rig was not saved under the expected Client and Rig Type."

    # Verify original Rig values.
    rigs.edit(client_name, rig_name)

    original_rig = {
        "client": client_name,
        "rig_type": rig_type,
        "rig_name": rig_name,
        "location": "Karachi",
    }

    assert rigs.wait_for_form_details(original_rig) == original_rig

    # Update Rig.
    updated_rig_name = f"{rig_name}_Edited"
    updated_rig_type = "Land rig"
    updated_location = "Lahore"

    rigs.fill_form(
        client_name=client_name,
        rig_type=updated_rig_type,
        rig_name=updated_rig_name,
        location=updated_location,
    )
    rigs.save()
    rigs.search(updated_rig_name)

    assert rigs.get_rig_details(client_name, updated_rig_name) == [
        client_name,
        updated_rig_name,
        updated_rig_type,
    ], "Updated Rig details did not appear in the grid."

    # Reopen Rig Edit.
    rigs.edit(client_name, updated_rig_name)

    updated_rig = {
        "client": client_name,
        "rig_type": updated_rig_type,
        "rig_name": updated_rig_name,
        "location": updated_location,
    }

    assert rigs.wait_for_form_details(updated_rig) == updated_rig, (
        "Saved Rig changes did not persist in the Edit form."
    )

    rigs.open()
    rigs.search(updated_rig_name)

    # Verify Rig Delete Cancel.
    rigs.request_delete(client_name, updated_rig_name)

    assert rigs.get_delete_message() == (
        "This record should be permanently deleted "
        "are you sure you want to Delete?"
    )

    rigs.cancel_delete()

    assert rigs.get_rig_details(client_name, updated_rig_name) == [
        client_name,
        updated_rig_name,
        updated_rig_type,
    ], "Rig disappeared or changed after cancelling deletion."

    rig_name = updated_rig_name

    print(f"Client retained for next steps: {client_name}")
    print(f"Rig retained for next steps: {rig_name}")

    # Create Inspector.
    inspectors = InspectorPage(driver)
    inspector_name = f"Test_Auto_Inspector_{suffix}"
    inspector_email = f"test.auto.{suffix}@example.com"

    inspectors.open()
    inspectors.open_add_form()
    inspectors.fill_form(
        inspector_name,
        inspector_email,
        "BS",
    )
    inspectors.save()
    inspectors.search(inspector_name)

    assert inspectors.get_details(inspector_name, inspector_email) == [
        inspector_name,
        inspector_email,
        "BS",
    ], "Created Inspector details do not match."

    # Verify original Inspector values.
    inspectors.edit(inspector_name, inspector_email)

    original_inspector = {
        "name": inspector_name,
        "email": inspector_email,
        "qualification": "BS",
    }

    assert inspectors.wait_for_form_details(
        original_inspector
    ) == original_inspector

    # Update Inspector.
    updated_inspector_name = f"{inspector_name}_Edited"
    updated_inspector_email = f"test.auto.edited.{suffix}@example.com"

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

    # Reopen Inspector Edit.
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

    inspector_name = updated_inspector_name
    inspector_email = updated_inspector_email

    print(f"Inspector for Job assignment: {inspector_name}")
    print(f"Inspector email: {inspector_email}")

    # Close Inspector Edit.
    inspectors.click((
        By.CSS_SELECTOR,
        "button.close[ng-click='cancel()']",
    ))
    inspectors.wait_for_grid()
    inspectors.search(inspector_name)

    # Open Certificates for this Inspector.
    certificates = InspectorCertificatePage(driver)
    certificates.open_for_inspector(
        inspector_name,
        inspector_email,
    )

    certificate_name = f"Test_Auto_Certificate_{suffix}"

    # Create Certificate.
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
    ], "Created Certificate details or attachment name do not match."

    # Verify original Certificate values.
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

    assert certificates.get_details(updated_certificate_name) == [
        updated_certificate_name,
        "20-Feb-26",
        "20-Feb-27",
        certificate_file.name,
    ], "Edited Certificate values or retained attachment do not match."

    # Reopen Certificate Edit.
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

    # Verify Certificate Delete Cancel.
    message = certificates.request_delete(updated_certificate_name)

    assert message == (
        "This record should be permanently deleted "
        "are you sure you want to Delete?"
    )

    certificates.cancel_delete()

    assert certificates.get_details(updated_certificate_name) == [
        updated_certificate_name,
        "20-Feb-26",
        "20-Feb-27",
        certificate_file.name,
    ], "Certificate changed or disappeared after Delete Cancel."

    print(f"Certificate retained: {updated_certificate_name}")

    # Find the Certificate list modal through its own Add control.
    certificate_modal_locator = (
        By.XPATH,
        "//span[@title='Add Inspector Certificate']"
        "/ancestor::div["
        "contains(concat(' ', normalize-space(@class), ' '), ' modal ')"
        "][1]",
    )

    def close_certificate_list(browser):
        try:
            modals = browser.find_elements(*certificate_modal_locator)

            for modal in modals:
                if not modal.is_displayed():
                    continue

                buttons = modal.find_elements(
                    By.CSS_SELECTOR,
                    "button.close[aria-label='Close'][data-dismiss='modal']",
                )

                for button in buttons:
                    if not button.is_displayed() or not button.is_enabled():
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
        message="Certificate list modal remained visible after clicking Close.",
    )

    # Open Job creation.
    jobs = JobPage(driver)
    jobs.open()
    jobs.open_add_form()

    job_number = f"Test_Auto_Job_{suffix}"
    job_description = "Automation end-to-end inspection job"

    inspection_day = date.today()
    next_inspection_day = inspection_day + timedelta(days=365)

    inspection_date = inspection_day.strftime("%m/%d/%Y")
    next_inspection = next_inspection_day.strftime("%m/%d/%Y")

    # Use the same Client and edited Rig.
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

    jobs.set_checkbox(jobs.ONGOING_ACCESS, True)
    jobs.set_checkbox(jobs.AUTO_REFERENCE, True)

    jobs.save_and_assign()

    # Assign the same Inspector.
    jobs.assign_inspector(inspector_name)

    # Upload attachments after initial Job save.
    section_name = f"Automation_Report_{suffix}"
    report_details = jobs.upload_report(section_name, report_file)

    assert report_details["link_text"] == "Additional_Inspection_Report"

    contract_link_text = jobs.upload_contract(contract_file)
    assert contract_link_text, "Contract attachment link is empty."

    jobs.update()

    # Return through Jobs List; no browser refresh.
    jobs.open()
    jobs.search(job_number)

    expected_grid = {
        "number": job_number,
        "description": job_description,
        "inspectors": [inspector_name],
        "inspection_date": inspection_day.strftime("%d-%b-%y"),
        "client": client_name,
        "rig": rig_name,
    }

    assert jobs.wait_for_job_details(expected_grid) == expected_grid

    # Reopen Job and verify persisted values.
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
    }

    assert jobs.wait_for_form_details(expected_form) == expected_form

    jobs.wait_for_inspector(inspector_name)

    assert jobs.wait_for_report(
        section_name,
        order=report_details["order"],
    ) == report_details, "Additional report changed after reopening Job."

    assert (
        jobs.visible(jobs.CONTRACT_LINK).text.strip() == contract_link_text
    ), "Contract attachment changed or disappeared after reopening Job."

    # Update Job description.
    updated_description = "Updated automation inspection job"

    jobs.set_text(jobs.DESCRIPTION, updated_description)
    jobs.update()

    jobs.open()
    jobs.search(job_number)

    expected_grid["description"] = updated_description
    assert jobs.wait_for_job_details(expected_grid) == expected_grid

    # Reopen again to verify saved changes.
    jobs.edit(job_number)

    expected_form["description"] = updated_description
    assert jobs.wait_for_form_details(expected_form) == expected_form

    jobs.wait_for_inspector(inspector_name)

    assert jobs.wait_for_report(
        section_name,
        order=report_details["order"],
    ) == report_details

    assert (
        jobs.visible(jobs.CONTRACT_LINK).text.strip() == contract_link_text
    ), "Contract attachment disappeared after updating Job."

    # Retain records for the inspection flow.
    print(f"Job retained for inspection: {job_number}")
    print(f"Client: {client_name}")
    print(f"Rig: {rig_name}")
    print(f"Assigned Inspector: {inspector_name}")