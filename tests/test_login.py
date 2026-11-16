import pytest

from config.settings import TEST_USERNAME, TEST_PASSWORD
from pages.login_page import LoginPage
from pages.admin_dashboard_page import AdminDashboardPage
from urllib.parse import urlsplit

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from config.settings import BASE_URL, TIMEOUT


def test_valid_login(driver):
    login_page = LoginPage(driver)
    login_page.open()
    login_page.login(TEST_USERNAME, TEST_PASSWORD)

    dashboard_page = AdminDashboardPage(driver)

    assert dashboard_page.get_heading_text() == "Admin Dashboard"


@pytest.mark.parametrize(
    "username,password",
    [
        (TEST_USERNAME, TEST_PASSWORD + "_incorrect"),
        (TEST_USERNAME + "_incorrect", TEST_PASSWORD),
        (TEST_USERNAME + "_incorrect", TEST_PASSWORD + "_incorrect"),
    ],
    ids=[
        "wrong_password",
        "wrong_username",
        "both_wrong",
    ],
)
def test_invalid_credentials(driver, username, password):
    login_page = LoginPage(driver)
    login_page.open()
    login_page.login(username, password)

    actual_error = login_page.get_error_message()

    assert actual_error == "Error! Invalid login Id or password.", (
        f"Unexpected error message: {actual_error}"
    )
    assert login_page.get_current_path() == "/home/login", (
        "Invalid credentials should keep the user on the login page."
    )


@pytest.mark.parametrize(
    "username,password,required_field",
    [
        ("", "", LoginPage.USERNAME_FIELD),
        ("", TEST_PASSWORD, LoginPage.USERNAME_FIELD),
        (TEST_USERNAME, "", LoginPage.PASSWORD_FIELD),
    ],
    ids=[
        "both_empty",
        "username_empty",
        "password_empty",
    ],
)
def test_required_fields(driver, username, password, required_field):
    login_page = LoginPage(driver)
    login_page.open()
    login_page.login(username, password)

    assert login_page.is_required_value_missing(required_field), (
        "The empty field should trigger required-field validation."
    )
    assert login_page.get_current_path() == "/home/login", (
        "An incomplete login should remain on the login page."
    )


def test_password_is_masked(driver):
    login_page = LoginPage(driver)
    login_page.open()

    assert login_page.get_password_field_type() == "password", (
        "Password field should mask entered characters."
    )


def test_remember_me_can_be_checked_and_unchecked(driver):
    login_page = LoginPage(driver)
    login_page.open()

    # Start from an unchecked checkbox.
    if login_page.is_remember_me_selected():
        login_page.click_remember_me()

    login_page.click_remember_me()

    assert login_page.is_remember_me_selected(), (
        "Remember Me should be checked after clicking."
    )

    login_page.click_remember_me()

    assert not login_page.is_remember_me_selected(), (
        "Remember Me should be unchecked after clicking again."
    )


def test_forgot_password_opens_reset_page_in_new_tab(driver):
    login_page = LoginPage(driver)
    login_page.open()

    original_tab = driver.current_window_handle
    existing_tabs = set(driver.window_handles)

    login_page.click_forgot_password()

    wait = WebDriverWait(driver, TIMEOUT)
    wait.until(EC.new_window_is_opened(list(existing_tabs)))

    new_tab = next(
        tab for tab in driver.window_handles
        if tab not in existing_tabs
    )
    driver.switch_to.window(new_tab)

    expected_url = f"{BASE_URL}/Home/ForgetPassword"
    wait.until(EC.url_to_be(expected_url))

    assert urlsplit(driver.current_url).path == "/Home/ForgetPassword"

    driver.close()
    driver.switch_to.window(original_tab)

    assert login_page.get_current_path() == "/home/login"


def test_support_button_is_visible_and_enabled(driver):
    login_page = LoginPage(driver)
    login_page.open()

    button = login_page.get_support_button()

    assert button.is_displayed(), "Support button should be visible."
    assert button.is_enabled(), "Support button should be enabled."
    assert button.text.strip() == "Sky Support System"