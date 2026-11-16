from selenium.common.exceptions import (
    ElementClickInterceptedException,
    NoSuchElementException,
    StaleElementReferenceException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select

from pages.base_page import BasePage


class RigPage(BasePage):
    SETTINGS_MENU = (By.XPATH, "//a[normalize-space()='Settings']")
    RIG_MENU = (By.CSS_SELECTOR, "a[ng-click='LoadSiteGrid()']")
    ADD_BUTTON = (By.CSS_SELECTOR, "button[ng-click='LoadSite()']")

    CLIENT = (By.ID, "ddlClient")
    RIG_TYPE = (By.ID, "dllRigType")
    RIG_NAME = (
        By.CSS_SELECTOR,
        "input[ng-model='SiteControls.RigName']",
    )
    LOCATION = (By.ID, "txtRigLocation")
    SAVE_BUTTON = (
        By.CSS_SELECTOR,
        "button[ng-disabled='siteForm.$invalid']",
    )

    SEARCH_FIELD = (By.CSS_SELECTOR, "input[ng-model='SearchWord']")
    SEARCH_BUTTON = (By.CSS_SELECTOR, "button[ng-click='GetSearch()']")
    ROWS = (By.CSS_SELECTOR, "tr[ng-repeat='rig in SiteData']")

    POPUP = (By.CSS_SELECTOR, ".sweet-alert.visible")
    POPUP_MESSAGE = (By.CSS_SELECTOR, ".sweet-alert.visible > p")
    DELETE_CONFIRM = (
        By.CSS_SELECTOR,
        ".sweet-alert.visible button.confirm",
    )
    DELETE_CANCEL = (
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
            message=f"Could not click Rig page element: {locator}",
        )

    def set_text(self, locator, value):
        def enter_text(driver):
            try:
                field = driver.find_element(*locator)

                if not field.is_displayed() or not field.is_enabled():
                    return False

                field.click()
                field.send_keys(Keys.CONTROL, "a")
                field.send_keys(Keys.BACKSPACE)

                if value:
                    field.send_keys(value)

                field.send_keys(Keys.TAB)

                return driver.find_element(
                    *locator
                ).get_property("value") == value

            except (
                ElementClickInterceptedException,
                NoSuchElementException,
                StaleElementReferenceException,
            ):
                return False

        self.wait.until(
            enter_text,
            message=f"Could not enter text into Rig field: {locator}",
        )

    def open(self):
        menus = self.driver.find_elements(*self.RIG_MENU)

        if not any(menu.is_displayed() for menu in menus):
            self.click(self.SETTINGS_MENU)

        self.click(self.RIG_MENU)
        self.wait_for_grid()

    def open_add_form(self):
        self.click(self.ADD_BUTTON)
        self.wait_for_visible(self.RIG_NAME)

        self.wait.until(
            lambda driver: driver.find_element(
                *self.RIG_NAME
            ).get_property("value") == "",
            message="New Rig form did not open with an empty Rig Name.",
        )

    def select_option(self, locator, text):
        def attempt(driver):
            try:
                element = driver.find_element(*locator)

                if not element.is_displayed() or not element.is_enabled():
                    return False

                dropdown = Select(element)
                matching = [
                    option for option in dropdown.options
                    if option.text.strip() == text
                ]

                if not matching:
                    return False

                if len(matching) != 1:
                    raise AssertionError(
                        f"Multiple dropdown options match: {text}"
                    )

                dropdown.select_by_visible_text(text)
                return dropdown.first_selected_option.text.strip() == text

            except (
                ElementClickInterceptedException,
                NoSuchElementException,
                StaleElementReferenceException,
            ):
                return False

        self.wait.until(
            attempt,
            message=f"Could not select dropdown option: {text}",
        )

    def fill_form(self, client_name, rig_type, rig_name, location):
        self.select_option(self.CLIENT, client_name)
        self.select_option(self.RIG_TYPE, rig_type)
        self.set_text(self.RIG_NAME, rig_name)
        self.set_text(self.LOCATION, location)

    def save(self):
        self.click(self.SAVE_BUTTON)
        self.wait_for_grid()

    def wait_for_grid(self):
        self.wait.until(
            EC.invisibility_of_element_located(self.RIG_NAME),
            message="Rig form remained open after saving or navigation.",
        )
        self.wait_for_visible(self.ADD_BUTTON)
        self.wait_for_visible(self.SEARCH_FIELD)

    def search(self, rig_name):
        self.set_text(self.SEARCH_FIELD, rig_name)
        self.click(self.SEARCH_BUTTON)

    def get_rig_details(self, client_name, rig_name):
        def read_details(driver):
            try:
                matches = []

                for row in driver.find_elements(*self.ROWS):
                    cells = row.find_elements(By.TAG_NAME, "td")
                    details = [
                        cell.text.strip() for cell in cells[:3]
                    ]

                    if details[:2] == [client_name, rig_name]:
                        matches.append(details)

                if len(matches) > 1:
                    raise AssertionError(
                        f"Duplicate Rig rows found: {client_name} / {rig_name}"
                    )

                return matches[0] if matches else False

            except StaleElementReferenceException:
                return False

        return self.wait.until(
            read_details,
            message=(
                f"Rig not found under expected Client: "
                f"{client_name} / {rig_name}"
            ),
        )
    def click_row_action(self, client_name, rig_name, title):
        def attempt(driver):
            try:
                matches = []

                for row in driver.find_elements(*self.ROWS):
                    cells = row.find_elements(By.TAG_NAME, "td")
                    identity = [
                        cell.text.strip() for cell in cells[:2]
                    ]

                    if identity == [client_name, rig_name]:
                        matches.append(row)

                if not matches:
                    return False

                if len(matches) != 1:
                    raise AssertionError(
                        f"Multiple rigs match: {client_name} / {rig_name}"
                    )

                action = matches[0].find_element(
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
            message=f"Could not click {title} for Rig: {rig_name}",
        )

    def edit(self, client_name, rig_name):
        self.click_row_action(client_name, rig_name, "Edit Record")

        self.wait.until(
            lambda driver: driver.find_element(
                *self.RIG_NAME
            ).get_property("value") == rig_name,
            message=f"Edit form did not load Rig: {rig_name}",
        )

    def get_form_details(self):
        return {
            "client": Select(
                self.driver.find_element(*self.CLIENT)
            ).first_selected_option.text.strip(),
            "rig_type": Select(
                self.driver.find_element(*self.RIG_TYPE)
            ).first_selected_option.text.strip(),
            "rig_name": self.driver.find_element(
                *self.RIG_NAME
            ).get_property("value"),
            "location": self.driver.find_element(
                *self.LOCATION
            ).get_property("value"),
        }

    def wait_for_form_details(self, expected):
        def read_details(driver):
            try:
                details = self.get_form_details()
                return details if details == expected else False

            except (
                NoSuchElementException,
                StaleElementReferenceException,
            ):
                return False

        self.wait.until(
            read_details,
            message=f"Rig form did not load expected saved values: {expected}",
        )

        return self.get_form_details()

    def request_delete(self, client_name, rig_name):
        self.click_row_action(client_name, rig_name, "Delete Record")
        self.wait_for_visible(self.POPUP)

    def get_delete_message(self):
        return self.wait_for_visible(self.POPUP_MESSAGE).text.strip()

    def cancel_delete(self):
        self.click(self.DELETE_CANCEL)
        self.wait.until(
            EC.invisibility_of_element_located(self.POPUP)
        )

    def confirm_delete(self):
        self.click(self.DELETE_CONFIRM)