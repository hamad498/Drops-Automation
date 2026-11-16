from uuid import uuid4

from config.settings import TEST_USERNAME, TEST_PASSWORD
from pages.login_page import LoginPage
from pages.admin_dashboard_page import AdminDashboardPage
from pages.client_page import ClientPage


def test_client_lifecycle(driver):
    login_page = LoginPage(driver)
    login_page.open()
    login_page.login(TEST_USERNAME, TEST_PASSWORD)

    dashboard = AdminDashboardPage(driver)
    assert dashboard.get_heading_text() == "Admin Dashboard"

    clients = ClientPage(driver)
    clients.open()

    name = f"Test_Auto_Client_{uuid4().hex[:12]}"
    updated_name = f"{name}_Edited"

    # Add and search.
    clients.open_add_form()
    clients.fill_form(name, "Islamabad", "Automation Test Address")
    clients.save()
    clients.wait_for_grid()
    clients.search(name)

    assert clients.get_client_details(name) == [
        name,
        "Automation Test Address",
        "Islamabad",
    ], "Created client details do not match."

    # Edit and search.
    clients.edit(name)
    clients.fill_form(
        updated_name,
        "Karachi",
        "Updated Automation Address",
    )
    clients.save()
    clients.wait_for_grid()
    clients.search(updated_name)

    assert clients.get_client_details(updated_name) == [
        updated_name,
        "Updated Automation Address",
        "Karachi",
    ], "Edited client details do not match."

    # Duplicate validation.
    clients.open_add_form()
    clients.fill_form(updated_name, "Karachi", "Duplicate Attempt")
    clients.save()

    message = clients.wait_for_popup_message("Client Already Exists")
    assert message == "Client Already Exists"

    clients.confirm_popup()
    clients.wait.until(
        lambda browser: not browser.find_elements(*clients.POPUP)
    )

    clients.open()
    clients.search(updated_name)

    assert clients.get_client_details(updated_name) == [
        updated_name,
        "Updated Automation Address",
        "Karachi",
    ], "Duplicate attempt changed the existing client."

    # Cancel deletion.
    clients.request_delete(updated_name)

    assert clients.get_popup_message() == (
        "This record should be permanently deleted "
        "are you sure you want to Delete?"
    )

    clients.cancel_delete()

    assert clients.get_client_details(updated_name) == [
        updated_name,
        "Updated Automation Address",
        "Karachi",
    ], "Client disappeared or changed after cancelling deletion."

    # Confirm deletion.
    clients.request_delete(updated_name)
    clients.confirm_popup()

    message = clients.wait_for_popup_message(
        "record deleted successfully..!"
    )
    assert message == "record deleted successfully..!"

    clients.confirm_popup()
    clients.wait.until(
        lambda browser: not browser.find_elements(*clients.POPUP)
    )

    clients.search(updated_name)
    clients.wait_for_client_absent(updated_name)