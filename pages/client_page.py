from pathlib import Path

from selenium.common.exceptions import (
    ElementClickInterceptedException,
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC

from pages.base_page import BasePage


class ClientPage(BasePage):
    SETTINGS_MENU = (By.XPATH, "//a[normalize-space()='Settings']")
    CLIENTS_MENU = (By.CSS_SELECTOR, "a[ng-click='LoadClientGrid()']")
    ADD_BUTTON = (By.CSS_SELECTOR, "button[ng-click='LoadClient()']")

    CLIENT_NAME = (By.ID, "txtClient")
    LOCATION = (By.ID, "txtLocation")
    ADDRESS = (By.ID, "txtAddress")
    SAVE_BUTTON = (
        By.CSS_SELECTOR,
        "button[type='submit'][ng-disabled='clientForm.$invalid']",
    )

    SEARCH_FIELD = (By.CSS_SELECTOR, "input[ng-model='SearchWord']")
    SEARCH_BUTTON = (By.CSS_SELECTOR, "button[ng-click='GetSearch()']")
    ROWS = (By.CSS_SELECTOR, "tr[ng-repeat='client in ClientData']")

    POPUP = (By.CSS_SELECTOR, ".sweet-alert.visible")
    POPUP_MESSAGE = (By.CSS_SELECTOR, ".sweet-alert.visible > p")
    CONFIRM_BUTTON = (
        By.CSS_SELECTOR,
        ".sweet-alert.visible button.confirm",
    )
    CANCEL_BUTTON = (
        By.CSS_SELECTOR,
        ".sweet-alert.visible button.cancel",
    )

    def click(self, locator):
        def attempt(driver):
            try:
                element = driver.find_element(*locator)

                if not element.is_displayed() or not element.is_enabled():
                    return False

                element.click()
                return True
            except (
                ElementClickInterceptedException,
                NoSuchElementException,
                StaleElementReferenceException,
            ):
                return False

        self.wait.until(
            attempt,
            message=f"Could not click element: {locator}",
        )

    def set_text(self, locator, value):
        field = self.wait.until(EC.element_to_be_clickable(locator))

        field.click()
        field.send_keys(Keys.CONTROL, "a")
        field.send_keys(Keys.BACKSPACE)

        if value:
            field.send_keys(value)

        field.send_keys(Keys.TAB)

        self.wait.until(
            lambda driver: driver.find_element(
                *locator
            ).get_property("value") == value,
            message=f"Field did not contain the intended value: {locator}",
        )

    def open(self):
        menus = self.driver.find_elements(*self.CLIENTS_MENU)

        if not any(menu.is_displayed() for menu in menus):
            self.click(self.SETTINGS_MENU)

        self.click(self.CLIENTS_MENU)
        self.wait_for_grid()

    def open_add_form(self):
        self.click(self.ADD_BUTTON)
        self.wait_for_visible(self.CLIENT_NAME)

        self.wait.until(
            lambda driver: driver.find_element(
                *self.CLIENT_NAME
            ).get_property("value") == "",
            message="New Client form did not open with an empty name.",
        )

    def fill_form(self, name, location="", address=""):
        self.set_text(self.CLIENT_NAME, name)
        self.set_text(self.LOCATION, location)
        self.set_text(self.ADDRESS, address)

    def save(self):
        self.click(self.SAVE_BUTTON)

    def wait_for_grid(self):
        self.wait.until(
            EC.invisibility_of_element_located(self.CLIENT_NAME),
            message="Client form remained open instead of showing the grid.",
        )
        self.wait_for_visible(self.ADD_BUTTON)
        self.wait_for_visible(self.SEARCH_FIELD)

    def is_save_enabled(self):
        return self.wait_for_visible(self.SAVE_BUTTON).is_enabled()

    def search(self, name):
        self.wait_for_grid()
        self.set_text(self.SEARCH_FIELD, name)
        self.click(self.SEARCH_BUTTON)

    def matching_rows(self, name):
        matches = []

        for row in self.driver.find_elements(*self.ROWS):
            cells = row.find_elements(By.TAG_NAME, "td")

            if cells and cells[0].text.strip() == name:
                matches.append(row)

        return matches

    def get_client_details(self, name):
        def read_details(driver):
            try:
                rows = self.matching_rows(name)

                if not rows:
                    return False

                if len(rows) != 1:
                    raise AssertionError(
                        f"Expected one client named {name}, "
                        f"found {len(rows)}."
                    )

                cells = rows[0].find_elements(By.TAG_NAME, "td")
                return [cell.text.strip() for cell in cells[:3]]

            except StaleElementReferenceException:
                return False

        try:
            return self.wait.until(
                read_details,
                message=f"Client not found in grid: {name}",
            )
        except TimeoutException as error:
            screenshot = Path("screenshots/client_grid_failed.png")
            screenshot.parent.mkdir(parents=True, exist_ok=True)
            self.driver.save_screenshot(str(screenshot))

            visible_rows = self.driver.execute_script(
                """
                return Array.from(document.querySelectorAll(
                    "tr[ng-repeat='client in ClientData']"
                )).map(row => row.innerText);
                """
            )

            raise AssertionError(
                f"Expected client: {name}\n"
                f"Current URL: {self.driver.current_url}\n"
                f"Grid rows: {visible_rows}\n"
                f"Screenshot: {screenshot.resolve()}"
            ) from error

    def click_row_action(self, name, title):
        self.get_client_details(name)

        def attempt(driver):
            try:
                rows = self.matching_rows(name)

                if len(rows) != 1:
                    return False

                action = rows[0].find_element(
                    By.CSS_SELECTOR,
                    f"span[title='{title}']",
                )
                action.click()
                return True

            except (
                ElementClickInterceptedException,
                NoSuchElementException,
                StaleElementReferenceException,
            ):
                return False

        self.wait.until(
            attempt,
            message=f"Could not perform {title} for client: {name}",
        )

    def edit(self, name):
        self.click_row_action(name, "Edit Record")
        self.wait_for_visible(self.CLIENT_NAME)

        self.wait.until(
            lambda driver: driver.find_element(
                *self.CLIENT_NAME
            ).get_property("value") == name,
            message=f"Edit form did not load client: {name}",
        )

    def request_delete(self, name):
        self.click_row_action(name, "Delete Record")
        self.wait_for_visible(self.POPUP)

    def get_popup_message(self):
        message = self.wait_for_visible(self.POPUP_MESSAGE)
        return message.text.strip()

    def cancel_delete(self):
        self.click(self.CANCEL_BUTTON)
        self.wait.until(
            EC.invisibility_of_element_located(self.POPUP)
        )

    def confirm_popup(self):
        self.click(self.CONFIRM_BUTTON)

    def wait_for_popup_message(self, expected):
        self.wait.until(
            EC.text_to_be_present_in_element(
                self.POPUP_MESSAGE,
                expected,
            )
        )
        return self.get_popup_message()

    def wait_for_client_absent(self, name):
        self.wait_for_grid()

        def client_is_absent(driver):
            try:
                return not self.matching_rows(name)
            except StaleElementReferenceException:
                return False

        self.wait.until(
            client_is_absent,
            message=f"Deleted client remains in grid: {name}",
        )