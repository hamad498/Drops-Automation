from selenium.common.exceptions import (
    ElementClickInterceptedException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from config.settings import BASE_URL
from pages.base_page import BasePage


class LoginPage(BasePage):
    USERNAME_FIELD = (By.CSS_SELECTOR, "input[placeholder='Username']")
    PASSWORD_FIELD = (By.CSS_SELECTOR, "input[placeholder='Passowrd']")
    LOGIN_BUTTON = (By.XPATH, "//button[normalize-space()='Login']")
    ERROR_MESSAGE = (
        By.CSS_SELECTOR,
        "div[ng-show=\"ErrorMessage != ''\"]",
    )
    REMEMBER_ME = (By.NAME, "remember")
    FORGOT_PASSWORD = (By.CSS_SELECTOR, "a[href='/Home/ForgetPassword']")
    SUPPORT_BUTTON = (By.CSS_SELECTOR, "button.supportBtn")       
    LOADING_OVERLAY = (By.CSS_SELECTOR, ".splash-loading")

    def open(self):
        self.open_url(f"{BASE_URL}/home/login")

    def login(self, username, password):
        username_field = self.wait_for_visible(self.USERNAME_FIELD)
        username_field.clear()
        username_field.send_keys(username)

        password_field = self.wait_for_visible(self.PASSWORD_FIELD)
        password_field.clear()
        password_field.send_keys(password)

        def click_login(driver):
            try:
                button = driver.find_element(*self.LOGIN_BUTTON)

                if not button.is_displayed() or not button.is_enabled():
                    return False

                button.click()
                return True

            except (
                ElementClickInterceptedException,
                StaleElementReferenceException,
            ):
                return False

        try:
            self.wait.until(
                click_login,
                message="Login button remained blocked or unavailable.",
            )
        except TimeoutException as error:
            from pathlib import Path

            screenshot = Path("screenshots/login_click_failed.png")
            screenshot.parent.mkdir(parents=True, exist_ok=True)
            self.driver.save_screenshot(str(screenshot))

            raise TimeoutException(
                "Could not click Login within the configured timeout. "
                f"Current URL: {self.driver.current_url}. "
                f"Screenshot: {screenshot.resolve()}"
            ) from error
    def get_error_message(self):
        error = self.wait_for_visible(self.ERROR_MESSAGE)
        return " ".join(error.text.split())

    def is_required_value_missing(self, locator):
        field = self.wait_for_visible(locator)
        return self.driver.execute_script(
            "return arguments[0].validity.valueMissing;",
            field,
        )

    def get_password_field_type(self):
        field = self.wait_for_visible(self.PASSWORD_FIELD)
        return field.get_attribute("type")

    def get_current_path(self):
        return self.driver.execute_script(
            "return window.location.pathname;"
        ).rstrip("/").lower()

    def is_remember_me_selected(self):
        checkbox = self.wait_for_visible(self.REMEMBER_ME)
        return checkbox.is_selected()

    def click_remember_me(self):
        self.wait.until(
            EC.element_to_be_clickable(self.REMEMBER_ME)
        ).click()

    def click_forgot_password(self):
        self.wait.until(
            EC.element_to_be_clickable(self.FORGOT_PASSWORD)
        ).click()

    def get_support_button(self):
        return self.wait_for_visible(self.SUPPORT_BUTTON)