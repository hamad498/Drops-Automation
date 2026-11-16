from pathlib import Path

from selenium.common.exceptions import (
    ElementClickInterceptedException,
    NoSuchElementException,
    StaleElementReferenceException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from pages.base_page import BasePage
from pages.inspector_page import InspectorPage


class InspectorCertificatePage(BasePage):
    ADD_BUTTON = (
        By.CSS_SELECTOR,
        "span[title='Add Inspector Certificate']",
    )
    NAME = (By.ID, "txtCertificateName")
    ISSUE_DATE = (By.ID, "txtCertificateIssueDate")
    EXPIRY_DATE = (By.ID, "txtCertificateExpiryDate")
    ATTACHMENT = (By.ID, "PdfInspectorCertifciate")
    SAVE_BUTTON = (
        By.CSS_SELECTOR,
        "button[ng-disabled='inspectorCertificateForm.$invalid']",
    )
    CANCEL_BUTTON = (
        By.CSS_SELECTOR,
        "button[ng-click='GetInspectorCertificate(Getinspecor)']"
        ":not(.close)",
    )
    ROWS = (
        By.CSS_SELECTOR,
        "tr[ng-repeat='n in InspectorCertificateData']",
    )

    POPUP = (By.CSS_SELECTOR, ".sweet-alert.visible")
    POPUP_MESSAGE = (
        By.CSS_SELECTOR,
        ".sweet-alert.visible > p",
    )
    POPUP_CONFIRM = (
        By.CSS_SELECTOR,
        ".sweet-alert.visible button.confirm",
    )
    POPUP_CANCEL = (
        By.CSS_SELECTOR,
        ".sweet-alert.visible button.cancel",
    )

    def __init__(self, driver):
        super().__init__(driver)
        self.inspectors = InspectorPage(driver)

    def open_for_inspector(self, name, email):
        def click_certificate(driver):
            try:
                rows = self.inspectors.matching_rows(name, email)

                if not rows:
                    return False

                if len(rows) != 1:
                    raise AssertionError(
                        f"Multiple Inspectors match: {name} / {email}"
                    )

                rows[0].find_element(
                    By.CSS_SELECTOR,
                    "span[title='Inspector Certificate']",
                ).click()
                return True

            except (
                ElementClickInterceptedException,
                NoSuchElementException,
                StaleElementReferenceException,
            ):
                return False

        self.wait.until(
            click_certificate,
            message=f"Could not open certificates for: {name}",
        )
        self.wait_for_list()

    def wait_for_list(self):
        self.wait.until(
            EC.invisibility_of_element_located(self.NAME)
        )
        self.wait_for_visible(self.ADD_BUTTON)

    def open_add_form(self):
        self.inspectors.click(self.ADD_BUTTON)
        self.wait_for_visible(self.NAME)

        self.wait.until(
            lambda driver: driver.find_element(
                *self.NAME
            ).get_property("value") == "",
            message="Certificate Add form did not open empty.",
        )

    def fill_form(self, name, issue_date, expiry_date):
        self.inspectors.set_text(self.NAME, name)
        self.inspectors.set_text(self.ISSUE_DATE, issue_date)
        self.inspectors.set_text(self.EXPIRY_DATE, expiry_date)

    def upload_attachment(self, file_path):
        path = Path(file_path).resolve()

        if not path.is_file():
            raise FileNotFoundError(
                f"Certificate test file missing: {path}"
            )

        field = self.wait.until(
            EC.presence_of_element_located(self.ATTACHMENT)
        )
        field.send_keys(str(path))

        self.wait.until(
            lambda driver: driver.execute_script(
                "return arguments[0].files.length;",
                driver.find_element(*self.ATTACHMENT),
            ) == 1,
            message="Certificate file was not selected.",
        )

    def save(self):
        self.inspectors.click(self.SAVE_BUTTON)
        self.wait_for_list()

    def matching_rows(self, name):
        matches = []

        for row in self.driver.find_elements(*self.ROWS):
            if not row.is_displayed():
                continue

            cells = row.find_elements(By.TAG_NAME, "td")

            if cells and cells[0].text.strip() == name:
                matches.append(row)

        return matches

    def get_details(self, name):
        def read_details(driver):
            try:
                rows = self.matching_rows(name)

                if not rows:
                    return False

                if len(rows) != 1:
                    raise AssertionError(
                        f"Multiple certificates match: {name}"
                    )

                cells = rows[0].find_elements(By.TAG_NAME, "td")
                return [
                    cell.text.strip() for cell in cells[:4]
                ]

            except StaleElementReferenceException:
                return False

        return self.wait.until(
            read_details,
            message=f"Certificate not found: {name}",
        )

    def click_row_action(self, name, title):
        def attempt(driver):
            try:
                rows = self.matching_rows(name)

                if not rows:
                    return False

                if len(rows) != 1:
                    raise AssertionError(
                        f"Multiple certificates match: {name}"
                    )

                rows[0].find_element(
                    By.CSS_SELECTOR,
                    f"span[title='{title}']",
                ).click()
                return True

            except (
                ElementClickInterceptedException,
                NoSuchElementException,
                StaleElementReferenceException,
            ):
                return False

        self.wait.until(
            attempt,
            message=f"Could not click {title}: {name}",
        )

    def edit(self, name):
        self.click_row_action(name, "Edit Inspector Certificate")
        self.wait_for_visible(self.NAME)

        self.wait.until(
            lambda driver: driver.find_element(
                *self.NAME
            ).get_property("value") == name,
            message=f"Certificate Edit did not load: {name}",
        )

    def wait_for_form_details(self, expected):
        def read_details(driver):
            try:
                details = {
                    "name": driver.find_element(
                        *self.NAME
                    ).get_property("value"),
                    "issue_date": driver.find_element(
                        *self.ISSUE_DATE
                    ).get_property("value"),
                    "expiry_date": driver.find_element(
                        *self.EXPIRY_DATE
                    ).get_property("value"),
                }

                return details if details == expected else False

            except (
                NoSuchElementException,
                StaleElementReferenceException,
            ):
                return False

        return self.wait.until(
            read_details,
            message=f"Certificate saved values did not match: {expected}",
        )

    def cancel_form(self):
        self.inspectors.click(self.CANCEL_BUTTON)
        self.wait_for_list()

    def request_delete(self, name):
        self.click_row_action(name, "Delete Inspector Certificate")
        return self.wait_for_visible(self.POPUP_MESSAGE).text.strip()

    def cancel_delete(self):
        self.inspectors.click(self.POPUP_CANCEL)
        self.wait.until(
            EC.invisibility_of_element_located(self.POPUP)
        )

    def confirm_delete(self):
        self.inspectors.click(self.POPUP_CONFIRM)

        self.wait.until(
            EC.text_to_be_present_in_element(
                self.POPUP_MESSAGE,
                "record deleted successfully..!",
            )
        )

        message = self.wait_for_visible(self.POPUP_MESSAGE).text.strip()

        if message != "record deleted successfully..!":
            raise AssertionError(
                f"Unexpected deletion message: {message}"
            )

        self.inspectors.click(self.POPUP_CONFIRM)
        self.wait.until(
            EC.invisibility_of_element_located(self.POPUP)
        )