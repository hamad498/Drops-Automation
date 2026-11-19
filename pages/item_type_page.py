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


class ItemTypePage(BasePage):
    SETTINGS = (
        By.XPATH,
        "//a[normalize-space()='Settings']",
    )
    MENU = (
        By.CSS_SELECTOR,
        "a[ng-click='LoadItemTypeGrid()']",
    )
    ADD = (
        By.CSS_SELECTOR,
        "button[ng-click='LoadItemType()']",
    )
    NAME = (
        By.CSS_SELECTOR,
        "input[ng-model='ItemTypeControls.Name']",
    )
    ADD_PROMPT = (
        By.CSS_SELECTOR,
        "button[ng-click='AddInspectionPrompt()']",
    )
    PROMPT_ROWS = (
        By.CSS_SELECTOR,
        "div[ng-repeat='prompt in ItemTypeControls.InspectionPrompt']",
    )
    PROMPT_INPUT = (
        By.CSS_SELECTOR,
        "input[ng-model='prompt.Prompt']",
    )
    PROMPT_DELETE = (
        By.CSS_SELECTOR,
        "button[title='Delete Inspection Prompt']",
    )
    SAVE = (
        By.CSS_SELECTOR,
        "button[ng-disabled='itemTypeform.$invalid']",
    )

    SEARCH = (
        By.CSS_SELECTOR,
        "input[ng-model='SearchWord']",
    )
    SEARCH_BUTTON = (
        By.CSS_SELECTOR,
        "button[ng-click='GetSearchByItemtypeandSearchBox()']",
    )
    FILTER = (
        By.CSS_SELECTOR,
        "select[ng-model='ItemType']",
    )
    ROWS = (
        By.CSS_SELECTOR,
        "tr[ng-repeat-start='item in itemTypes']",
    )

    REF_ADD = (
        By.CSS_SELECTOR,
        "span[ng-click='StandardModel()']",
    )
    REF_ROWS = (
        By.CSS_SELECTOR,
        "tr[ng-repeat='standard in StandardData']",
    )
    REF_TYPE = (
        By.CSS_SELECTOR,
        "select[ng-model='StandardControls.Standardtypeid']",
    )
    REF_NAME = (
        By.CSS_SELECTOR,
        "input[ng-model='StandardControls.Name']",
    )
    REF_SAVE = (
        By.CSS_SELECTOR,
        "button[ng-disabled='standardForm.$invalid']",
    )
    REF_CLOSE = (
        By.CSS_SELECTOR,
        "button[ng-click='StandardCloseFormModel()']",
    )

    POPUP = (
        By.CSS_SELECTOR,
        ".sweet-alert.visible",
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
            return driver.execute_script(
                """
                const loading = Array.from(
                    document.querySelectorAll('.splash-loading')
                ).some(el => el.getClientRects().length > 0
                    && getComputedStyle(el).visibility !== 'hidden');

                if (loading) return false;

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
                    // Fall back to the visible loading indicator.
                }

                return true;
                """
            )

        self.wait.until(
            idle,
            message="Item Type page remained busy.",
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
            message=f"Could not click Item Type element: {locator}",
        )

    def set_text(self, locator, value, verify=True):
        value = str(value)
        self.wait_idle()

        def attempt(driver):
            try:
                matches = [
                    field
                    for field in driver.find_elements(*locator)
                    if field.is_displayed() and field.is_enabled()
                ]
                if len(matches) != 1:
                    return False

                field = matches[0]
                self.scroll_to(field)
                field.send_keys(Keys.CONTROL, "a")
                field.send_keys(Keys.BACKSPACE)

                if value:
                    field.send_keys(value)

                field.send_keys(Keys.TAB)

                if not verify:
                    return True

                return field.get_property("value") == value

            except self.RETRY_ERRORS:
                return False

        self.wait.until(
            attempt,
            message=f"Could not fill Item Type field: {locator}",
        )

    def select_text(self, locator, text):
        self.wait_idle()

        def attempt(driver):
            try:
                element = driver.find_element(*locator)
                if not element.is_displayed() or not element.is_enabled():
                    return False

                self.scroll_to(element)
                dropdown = Select(element)
                options = [
                    option
                    for option in dropdown.options
                    if option.text.strip() == text
                ]
                if not options:
                    return False

                assert len(options) == 1, (
                    f"Multiple options match: {text}"
                )
                dropdown.select_by_visible_text(text)

                return (
                    dropdown.first_selected_option.text.strip() == text
                )

            except self.RETRY_ERRORS:
                return False

        self.wait.until(
            attempt,
            message=f"Could not select {text!r} in {locator}",
        )
        self.wait_idle()

    def open(self):
        menus = self.driver.find_elements(*self.MENU)

        if not any(menu.is_displayed() for menu in menus):
            self.click(self.SETTINGS)

        self.click(self.MENU)
        self.wait_for_visible(self.ADD)
        self.wait_for_visible(self.SEARCH)
        self.wait_idle()

    def open_add_form(self):
        self.click(self.ADD)
        self.wait_for_visible(self.NAME)

        self.wait.until(
            lambda driver: driver.find_element(
                *self.NAME
            ).get_property("value") == "",
            message="Add Item Type form was not empty.",
        )

    def save_enabled(self):
        return self.wait_for_visible(self.SAVE).is_enabled()

    def save(self):
        self.click(self.SAVE)

        # Save stays on the same page.
        self.wait_for_visible(self.REF_ADD)
        self.wait_idle()

    def form_details(self):
        return {
            "name": self.wait_for_visible(
                self.NAME
            ).get_property("value"),
            "prompts": [
                row.find_element(
                    *self.PROMPT_INPUT
                ).get_property("value")
                for row in self.driver.find_elements(*self.PROMPT_ROWS)
                if row.is_displayed()
            ],
        }

    def prompt_count(self):
        return len([
            row
            for row in self.driver.find_elements(*self.PROMPT_ROWS)
            if row.is_displayed()
        ])

    def add_prompt(self, text=None):
        previous = self.prompt_count()
        self.click(self.ADD_PROMPT)

        self.wait.until(
            lambda driver: self.prompt_count() == previous + 1,
            message="New Inspection Prompt row did not appear.",
        )

        if text is not None:
            self.set_prompt(previous, text)

    def set_prompt(self, index, text, verify=True):
        text = str(text)

        def attempt(driver):
            try:
                rows = [
                    row
                    for row in driver.find_elements(*self.PROMPT_ROWS)
                    if row.is_displayed()
                ]
                if index >= len(rows):
                    return False

                field = rows[index].find_element(*self.PROMPT_INPUT)
                self.scroll_to(field)
                field.send_keys(Keys.CONTROL, "a")
                field.send_keys(Keys.BACKSPACE)

                if text:
                    field.send_keys(text)

                field.send_keys(Keys.TAB)

                return (
                    True if not verify
                    else field.get_property("value") == text
                )

            except self.RETRY_ERRORS:
                return False

        self.wait.until(
            attempt,
            message=f"Could not fill Inspection Prompt index {index}.",
        )

    def request_prompt_delete(self, index):
        def attempt(driver):
            try:
                rows = [
                    row
                    for row in driver.find_elements(*self.PROMPT_ROWS)
                    if row.is_displayed()
                ]
                if index >= len(rows):
                    return False

                button = rows[index].find_element(*self.PROMPT_DELETE)
                self.scroll_to(button)
                button.click()
                return True

            except self.RETRY_ERRORS:
                return False

        self.wait.until(
            attempt,
            message=f"Could not delete Inspection Prompt index {index}.",
        )
        return self.popup_message()

    def popup_message(self):
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
                message = self.popup_message()
                return (
                    message
                    if message == self.DELETE_SUCCESS
                    else False
                )

            except self.RETRY_ERRORS:
                return False

        message = self.wait.until(
            success,
            message="Deletion success message did not appear.",
        )
        self.click(self.CONFIRM)

        self.wait.until(
            EC.invisibility_of_element_located(self.POPUP)
        )
        self.wait_idle()
        return message

    def search(self, text, enter=False):
        self.set_text(self.SEARCH, text)

        if enter:
            self.wait_for_visible(self.SEARCH).send_keys(Keys.ENTER)
        else:
            self.click(self.SEARCH_BUTTON)

        self.wait_idle()

    def filter_item_type(self, name=None):
        if name is not None:
            self.select_text(self.FILTER, name)
            return

        element = self.wait_for_visible(self.FILTER)
        Select(element).select_by_value("")
        self.wait_idle()

    def visible_names(self):
        return [
            row.find_element(
                By.CSS_SELECTOR,
                "span[ng-bind='item.Name']",
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
                "span[ng-bind='item.Name']",
            ).text.strip() == name
        ]

    def grid_details(self, name):
        def read(driver):
            try:
                rows = self.matching_rows(name)
                if not rows:
                    return False

                assert len(rows) == 1, (
                    f"Multiple Item Types match: {name}"
                )
                count = rows[0].find_element(
                    By.CSS_SELECTOR,
                    "span[ng-bind='item.CHECKLIST']",
                ).text.strip()

                if not count.isdigit():
                    return False

                return {
                    "name": name,
                    "checklist_count": int(count),
                }

            except self.RETRY_ERRORS:
                return False

        return self.wait.until(
            read,
            message=f"Item Type row unavailable: {name}",
        )

    def row_action(self, name, title):
        def attempt(driver):
            try:
                rows = self.matching_rows(name)
                if not rows:
                    return False

                assert len(rows) == 1, (
                    f"Multiple Item Types match: {name}"
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
            message=f"Could not click {title} for Item Type: {name}",
        )

    def edit(self, name):
        self.row_action(name, "Edit Record")
        self.wait_for_visible(self.NAME)

        self.wait.until(
            lambda driver: driver.find_element(
                *self.NAME
            ).get_property("value") == name,
            message=f"Edit form did not load Item Type: {name}",
        )
        self.wait_idle()

    def request_item_delete(self, name):
        self.row_action(name, "Delete Record")
        return self.popup_message()

    def set_expanded(self, name, expanded):
        def attempt(driver):
            try:
                rows = self.matching_rows(name)
                if not rows:
                    return False

                assert len(rows) == 1
                toggle = rows[0].find_element(
                    By.CSS_SELECTOR,
                    "span[ng-click='SectionHideShow(item.Name)']",
                )
                classes = toggle.get_attribute("class").split()
                current = "fa-minus" in classes

                if current == expanded:
                    return True

                self.scroll_to(toggle)
                toggle.click()
                return False

            except self.RETRY_ERRORS:
                return False

        self.wait.until(
            attempt,
            message=f"Could not change expansion for: {name}",
        )

    def expanded_prompts(self, name):
        rows = self.matching_rows(name)

        assert len(rows) == 1, (
            f"Expected one Item Type row: {name}"
        )

        detail = rows[0].find_element(
            By.XPATH,
            "./following-sibling::tr[1]",
        )

        if not detail.is_displayed():
            return None

        return [
            label.text.strip()
            for label in detail.find_elements(
                By.CSS_SELECTOR,
                "div[ng-repeat='prompt in item.InspectionPrompt'] label",
            )
        ]

    def references(self):
        self.wait_idle()
        result = []

        for row in self.driver.find_elements(*self.REF_ROWS):
            if not row.is_displayed():
                continue

            cells = row.find_elements(By.TAG_NAME, "td")
            result.append([
                cell.text.strip()
                for cell in cells[:3]
            ])

        return result

    def reference_action(self, reference_name, title):
        def attempt(driver):
            try:
                matches = []

                for row in driver.find_elements(*self.REF_ROWS):
                    if not row.is_displayed():
                        continue

                    name = row.find_element(
                        By.CSS_SELECTOR,
                        "span[ng-bind='standard.Name']",
                    ).text.strip()

                    if name == reference_name:
                        matches.append(row)

                if not matches:
                    return False

                assert len(matches) == 1, (
                    f"Multiple references match: {reference_name}"
                )

                action = matches[0].find_element(
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
            message=f"Could not {title}: {reference_name}",
        )

    def open_reference_add(self):
        self.click(self.REF_ADD)
        self.wait_for_visible(self.REF_NAME)

        self.wait.until(
            lambda driver: driver.find_element(
                *self.REF_NAME
            ).get_property("value") == "",
            message="New Standard Reference form was not empty.",
        )

    def edit_reference(self, name):
        self.reference_action(name, "Edit Record")
        self.wait_for_visible(self.REF_NAME)

        self.wait.until(
            lambda driver: driver.find_element(
                *self.REF_NAME
            ).get_property("value") == name,
            message=f"Reference Edit did not load: {name}",
        )

    def reference_form_details(self):
        name_field = self.wait_for_visible(self.REF_NAME)
        modal = name_field.find_element(
            By.XPATH,
            "./ancestor::div["
            "contains(concat(' ', normalize-space(@class), ' '),"
            " ' modal ')][1]",
        )

        item_fields = [
            field
            for field in modal.find_elements(
                By.CSS_SELECTOR,
                "input[disabled]",
            )
            if field.is_displayed()
        ]

        assert len(item_fields) == 1, (
            "Expected one disabled Item Type field in Reference form."
        )

        return {
            "name": name_field.get_property("value"),
            "standard_type": Select(
                self.wait_for_visible(self.REF_TYPE)
            ).first_selected_option.text.strip(),
            "item_type": item_fields[0].get_property("value"),
            "item_type_disabled": not item_fields[0].is_enabled(),
        }

    def reference_save_enabled(self):
        return self.wait_for_visible(self.REF_SAVE).is_enabled()

    def fill_reference(self, name, standard_type):
        self.select_text(self.REF_TYPE, standard_type)
        self.set_text(self.REF_NAME, name)

    def save_reference(self):
        self.click(self.REF_SAVE)
        self.wait.until(
            EC.invisibility_of_element_located(self.REF_NAME)
        )
        self.wait_idle()

    def close_reference(self):
        self.click(self.REF_CLOSE)
        self.wait.until(
            EC.invisibility_of_element_located(self.REF_NAME)
        )

    def request_reference_delete(self, name):
        self.reference_action(name, "Delete Record")
        return self.popup_message()