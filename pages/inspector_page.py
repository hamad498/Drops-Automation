from selenium.common.exceptions import (
    ElementClickInterceptedException,
    NoSuchElementException,
    StaleElementReferenceException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC

from pages.base_page import BasePage


class InspectorPage(BasePage):
    INSPECTORS_MENU = (
        By.XPATH,
        "//a[normalize-space()='Inspectors']",
    )
    DETAILS_MENU = (
        By.CSS_SELECTOR,
        "a[ng-click='LoadInspectorGrid()']",
    )
    ADD_BUTTON = (
        By.CSS_SELECTOR,
        "button[ng-click='openNewInspectorModal()']",
    )

    NAME = (By.ID, "txtInspector")
    EMAIL = (By.ID, "txtEmailAddress")
    QUALIFICATION = (By.ID, "txtQualification")
    SAVE_BUTTON = (
        By.CSS_SELECTOR,
        "button[form='inspectorForm'][type='submit']",
    )

    SEARCH = (
        By.CSS_SELECTOR,
        "input[ng-model='SearchWordInspector']",
    )
    ROWS = (
        By.CSS_SELECTOR,
        "tr[ng-repeat='Inspector in InspectorData']",
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
            message=f"Could not click Inspector element: {locator}",
        )

    def set_text(self, locator, value):
        def attempt(driver):
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
            attempt,
            message=f"Could not fill Inspector field: {locator}",
        )

    def open(self):
        links = self.driver.find_elements(*self.DETAILS_MENU)

        if not any(link.is_displayed() for link in links):
            self.click(self.INSPECTORS_MENU)

        self.click(self.DETAILS_MENU)
        self.wait_for_grid()

    def wait_for_grid(self):
        self.wait.until(
            EC.invisibility_of_element_located(self.NAME),
            message="Inspector modal remained open.",
        )
        self.wait_for_visible(self.ADD_BUTTON)
        self.wait_for_visible(self.SEARCH)

    def open_add_form(self):
        self.click(self.ADD_BUTTON)
        self.wait_for_visible(self.NAME)

        self.wait.until(
            lambda driver: driver.find_element(
                *self.NAME
            ).get_property("value") == "",
            message="Add Inspector form did not open with an empty name.",
        )

    def fill_form(self, name, email, qualification=""):
        self.set_text(self.NAME, name)
        self.set_text(self.EMAIL, email)
        self.set_text(self.QUALIFICATION, qualification)

    def save(self):
        self.click(self.SAVE_BUTTON)
        self.wait_for_grid()

    def search(self, name):
        self.set_text(self.SEARCH, name)

        field = self.wait.until(
            EC.element_to_be_clickable(self.SEARCH)
        )
        field.send_keys(Keys.ENTER)

    def matching_rows(self, name, email):
        matches = []

        for row in self.driver.find_elements(*self.ROWS):
            if not row.is_displayed():
                continue

            cells = row.find_elements(By.TAG_NAME, "td")
            identity = [
                cell.text.strip() for cell in cells[:2]
            ]

            if identity == [name, email]:
                matches.append(row)

        return matches

    def get_details(self, name, email):
        def read_details(driver):
            try:
                rows = self.matching_rows(name, email)

                if not rows:
                    return False

                if len(rows) != 1:
                    raise AssertionError(
                        f"Multiple Inspector rows match: {name} / {email}"
                    )

                cells = rows[0].find_elements(By.TAG_NAME, "td")

                return [
                    cell.text.strip() for cell in cells[:3]
                ]

            except StaleElementReferenceException:
                return False

        return self.wait.until(
            read_details,
            message=f"Inspector not found: {name} / {email}",
        )

    def edit(self, name, email):
        def click_edit(driver):
            try:
                rows = self.matching_rows(name, email)

                if not rows:
                    return False

                if len(rows) != 1:
                    raise AssertionError(
                        f"Multiple Inspector rows match: {name} / {email}"
                    )

                rows[0].find_element(
                    By.CSS_SELECTOR,
                    "span[title='Edit Record']",
                ).click()

                return True

            except (
                ElementClickInterceptedException,
                NoSuchElementException,
                StaleElementReferenceException,
            ):
                return False

        self.wait.until(
            click_edit,
            message=f"Could not open Inspector Edit: {name}",
        )
        self.wait_for_visible(self.NAME)

    def get_form_details(self):
        return {
            "name": self.driver.find_element(
                *self.NAME
            ).get_property("value"),
            "email": self.driver.find_element(
                *self.EMAIL
            ).get_property("value"),
            "qualification": self.driver.find_element(
                *self.QUALIFICATION
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

        return self.wait.until(
            read_details,
            message=f"Inspector form values did not match: {expected}",
        )