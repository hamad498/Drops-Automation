from selenium.common.exceptions import (
    ElementClickInterceptedException,
    NoSuchElementException,
    StaleElementReferenceException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC

from pages.base_page import BasePage


class StandardTypePage(BasePage):
    SETTINGS = (
        By.XPATH,
        "//a[normalize-space()='Settings']",
    )
    MENU = (
        By.CSS_SELECTOR,
        "a[ng-click='LoadStandardTypeGrid()']",
    )
    ADD = (
        By.CSS_SELECTOR,
        "button[ng-click='openNewStandardTypeModal()']",
    )
    NAME = (
        By.CSS_SELECTOR,
        "input[ng-model='StandardType.StandardName']",
    )
    SAVE = (
        By.CSS_SELECTOR,
        "button[ng-disabled='StandardTypeForm.$invalid']",
    )

    SEARCH = (
        By.CSS_SELECTOR,
        "input[ng-model='SearchWord']"
        "[ng-change='OnChangeOfSearchStandardType()']",
    )
    SEARCH_BUTTON = (
        By.CSS_SELECTOR,
        "button[ng-click='GetStandardTypeSearch()']",
    )
    ROWS = (
        By.CSS_SELECTOR,
        "tr[ng-repeat='m in StandardTypeList']",
    )

    POPUP = (
        By.CSS_SELECTOR,
        ".sweet-alert.visible",
    )
    POPUP_TITLE = (
        By.CSS_SELECTOR,
        ".sweet-alert.visible > h2",
    )
    POPUP_MESSAGE = (
        By.CSS_SELECTOR,
        ".sweet-alert.visible > p",
    )
    CONFIRM = (
        By.CSS_SELECTOR,
        ".sweet-alert.visible button.confirm",
    )
    CANCEL = (
        By.CSS_SELECTOR,
        ".sweet-alert.visible button.cancel",
    )

    DUPLICATE_MESSAGE = "Standard Type Already Exists"
    DELETE_MESSAGE = (
        "This record should be permanently deleted "
        "are you sure you want to Delete?"
    )
    DELETE_SUCCESS = "record deleted successfully..!"

    RETRY_ERRORS = (
        ElementClickInterceptedException,
        NoSuchElementException,
        StaleElementReferenceException,
    )

    def wait_idle(self):
        def idle(driver):
            try:
                return driver.execute_script(
                    """
                    const busy = Array.from(
                        document.querySelectorAll('.splash-loading')
                    ).some(el =>
                        el.getClientRects().length > 0 &&
                        getComputedStyle(el).visibility !== 'hidden'
                    );

                    if (busy) return false;

                    try {
                        if (window.angular) {
                            const injector = angular.element(
                                document.body
                            ).injector();

                            if (injector) {
                                return injector.get('$http')
                                    .pendingRequests.length === 0;
                            }
                        }
                    } catch (error) {
                        // Use the loading indicator as fallback.
                    }

                    return true;
                    """
                )

            except StaleElementReferenceException:
                return False

        self.wait.until(
            idle,
            message="Standard Type page remained busy.",
        )

    def scroll_to(self, element):
        self.driver.execute_script(
            """
            arguments[0].scrollIntoView({
                block: 'center',
                inline: 'nearest',
                behavior: 'instant'
            });
            """,
            element,
        )

    def click(self, locator):
        self.wait_idle()

        def attempt(driver):
            try:
                matches = [
                    element
                    for element in driver.find_elements(*locator)
                    if element.is_displayed() and element.is_enabled()
                ]

                if len(matches) != 1:
                    return False

                self.scroll_to(matches[0])
                matches[0].click()
                return True

            except self.RETRY_ERRORS:
                return False

        self.wait.until(
            attempt,
            message=f"Could not click Standard Type element: {locator}",
        )

    def set_text(self, locator, value, verify=True):
        value = str(value)
        self.wait_idle()

        def attempt(driver):
            try:
                fields = [
                    field
                    for field in driver.find_elements(*locator)
                    if field.is_displayed() and field.is_enabled()
                ]

                if len(fields) != 1:
                    return False

                field = fields[0]
                self.scroll_to(field)
                field.send_keys(Keys.CONTROL, "a")
                field.send_keys(Keys.BACKSPACE)

                if value:
                    field.send_keys(value)

                field.send_keys(Keys.TAB)

                return (
                    True if not verify
                    else field.get_property("value") == value
                )

            except self.RETRY_ERRORS:
                return False

        self.wait.until(
            attempt,
            message=f"Could not fill Standard Type field: {locator}",
        )

    def open(self):
        links = self.driver.find_elements(*self.MENU)

        if not any(link.is_displayed() for link in links):
            self.click(self.SETTINGS)

        self.click(self.MENU)
        self.wait_for_grid()

    def wait_for_grid(self):
        self.wait.until(
            EC.invisibility_of_element_located(self.NAME),
            message="Standard Type modal remained open.",
        )
        self.wait_for_visible(self.ADD)
        self.wait_for_visible(self.SEARCH)
        self.wait_idle()

    def open_add_form(self):
        self.click(self.ADD)
        self.wait_for_visible(self.NAME)

        self.wait.until(
            lambda driver: self.read_name() == "",
            message="Add Standard Type form did not open empty.",
        )

    def read_name(self):
        return self.wait_for_visible(
            self.NAME
        ).get_property("value")

    def save_enabled(self):
        return self.wait_for_visible(self.SAVE).is_enabled()

    def modal_visible(self):
        return any(
            field.is_displayed()
            for field in self.driver.find_elements(*self.NAME)
        )

    def popup_visible(self):
        return any(
            popup.is_displayed()
            for popup in self.driver.find_elements(*self.POPUP)
        )

    def popup_details(self):
        return {
            "title": self.wait_for_visible(
                self.POPUP_TITLE
            ).text.strip(),
            "message": self.wait_for_visible(
                self.POPUP_MESSAGE
            ).text.strip(),
        }

    def submit(self):
        self.click(self.SAVE)
        self.wait_idle()

        def result(driver):
            try:
                if self.popup_visible():
                    details = self.popup_details()

                    if not details["message"]:
                        return False

                    return {
                        "status": "popup",
                        **details,
                    }

                if self.modal_visible():
                    return False

                # A popup may appear while the loading request finishes.
                # Check it again before classifying the result as saved.
                self.wait_idle()

                if self.popup_visible():
                    details = self.popup_details()

                    if not details["message"]:
                        return False

                    return {
                        "status": "popup",
                        **details,
                    }

                if self.modal_visible():
                    return False

                add_visible = any(
                    element.is_displayed()
                    for element in driver.find_elements(*self.ADD)
                )
                search_visible = any(
                    element.is_displayed()
                    for element in driver.find_elements(*self.SEARCH)
                )

                if add_visible and search_visible:
                    return {"status": "saved"}

                return False

            except self.RETRY_ERRORS:
                return False

        return self.wait.until(
            result,
            message="Standard Type Save produced no result.",
        )

    def save(self):
        result = self.submit()

        assert result["status"] == "saved", (
            f"Standard Type Save returned an unexpected popup: {result}"
        )

        self.wait_for_grid()

    def close_form(self, cancel=False):
        def attempt(driver):
            try:
                field = driver.find_element(*self.NAME)

                modal = field.find_element(
                    By.XPATH,
                    "./ancestor::div["
                    "contains(concat(' ', normalize-space(@class), ' '),"
                    " ' modal ')][1]",
                )

                selector = (
                    "button.modern-btn-secondary[ng-click='cancel()']"
                    if cancel
                    else "button.close[ng-click='cancel()']"
                )

                buttons = [
                    button
                    for button in modal.find_elements(
                        By.CSS_SELECTOR,
                        selector,
                    )
                    if button.is_displayed() and button.is_enabled()
                ]

                if len(buttons) != 1:
                    return False

                self.scroll_to(buttons[0])
                buttons[0].click()
                return True

            except self.RETRY_ERRORS:
                return False

        self.wait.until(
            attempt,
            message="Could not close Standard Type form.",
        )

        self.wait_for_grid()

    def acknowledge_popup(self):
        self.click(self.CONFIRM)

        self.wait.until(
            EC.invisibility_of_element_located(self.POPUP)
        )
        self.wait_idle()

    def search(self, name, enter=False):
        self.set_text(self.SEARCH, name)

        if enter:
            self.wait_for_visible(
                self.SEARCH
            ).send_keys(Keys.ENTER)
        else:
            self.click(self.SEARCH_BUTTON)

        self.wait_idle()

    def visible_names(self):
        return [
            row.find_element(
                By.CSS_SELECTOR,
                "span[ng-bind='m.StandardName']",
            ).text.strip()
            for row in self.driver.find_elements(*self.ROWS)
            if row.is_displayed()
        ]

    def matching_rows(self, name):
        return [
            row
            for row in self.driver.find_elements(*self.ROWS)
            if row.is_displayed()
            and row.find_element(
                By.CSS_SELECTOR,
                "span[ng-bind='m.StandardName']",
            ).text.strip() == name
        ]

    def row_action(self, name, title):
        self.wait_idle()

        def attempt(driver):
            try:
                rows = self.matching_rows(name)

                if not rows:
                    return False

                assert len(rows) == 1, (
                    f"Multiple Standard Types match: {name}"
                )

                action = rows[0].find_element(
                    By.CSS_SELECTOR,
                    f"span[title='{title}']",
                )

                self.scroll_to(action)
                action.click()
                return True

            except self.RETRY_ERRORS:
                return False

        self.wait.until(
            attempt,
            message=f"Could not {title} for Standard Type: {name}",
        )

    def edit(self, name):
        self.row_action(name, "Edit Record")
        self.wait_for_visible(self.NAME)

        self.wait.until(
            lambda driver: self.read_name() == name,
            message=f"Standard Type Edit did not load: {name}",
        )

    def request_delete(self, name):
        self.row_action(name, "Delete Record")

        return self.wait_for_visible(
            self.POPUP_MESSAGE
        ).text.strip()

    def cancel_delete(self):
        self.click(self.CANCEL)

        self.wait.until(
            EC.invisibility_of_element_located(self.POPUP)
        )

    def confirm_delete(self):
        self.click(self.CONFIRM)

        def success(driver):
            try:
                message = self.wait_for_visible(
                    self.POPUP_MESSAGE
                ).text.strip()

                return (
                    message
                    if message == self.DELETE_SUCCESS
                    else False
                )

            except self.RETRY_ERRORS:
                return False

        message = self.wait.until(
            success,
            message="Standard Type deletion success did not appear.",
        )

        self.acknowledge_popup()
        self.wait_idle()

        return message