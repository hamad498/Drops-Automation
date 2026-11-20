from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

from pages.standard_type_page import StandardTypePage


class StandardReferencePage(StandardTypePage):
    MENU = (
        By.CSS_SELECTOR,
        "a[ng-click='LoadStandardGrid()']",
    )
    ADD = (
        By.CSS_SELECTOR,
        "button[ng-click='LoadStandard()']",
    )

    ITEM_TYPE = (
        By.CSS_SELECTOR,
        "select[ng-model='StandardControls.ItemtypeID']",
    )
    STANDARD_TYPE = (
        By.CSS_SELECTOR,
        "select[ng-model='StandardControls.Standardtypeid']",
    )
    NAME = (
        By.CSS_SELECTOR,
        "input[ng-model='StandardControls.Name']",
    )
    SAVE = (
        By.CSS_SELECTOR,
        "button[ng-disabled='standardForm.$invalid']",
    )

    SEARCH = (
        By.CSS_SELECTOR,
        "input[ng-model='SearchWord']"
        "[ng-keyup*='GetStandardSearch()']",
    )
    SEARCH_BUTTON = (
        By.CSS_SELECTOR,
        "button[ng-click='GetStandardSearch()']",
    )
    ROWS = (
        By.CSS_SELECTOR,
        "tr[ng-repeat='standard in StandardData']",
    )

    DUPLICATE_MESSAGE = "Standard Already Exist"

    def open_add_form(self):
        self.click(self.ADD)
        self.wait_for_visible(self.NAME)
        self.wait_for_visible(self.ITEM_TYPE)
        self.wait_for_visible(self.STANDARD_TYPE)

        self.wait.until(
            lambda driver: self.read_name() == "",
            message="New Standard Reference form did not open empty.",
        )

    def select_option(self, locator, text):
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
                dropdown = Select(field)

                options = [
                    option
                    for option in dropdown.options
                    if option.text.strip() == text
                ]

                if not options:
                    return False

                assert len(options) == 1, (
                    f"Multiple dropdown options match: {text}"
                )

                self.scroll_to(field)
                dropdown.select_by_visible_text(text)

                return (
                    dropdown.first_selected_option.text.strip() == text
                )

            except self.RETRY_ERRORS:
                return False

        self.wait.until(
            attempt,
            message=f"Dropdown option unavailable: {text} in {locator}",
        )
        self.wait_idle()

    def fill_form(self, item_type, standard_type, name):
        self.select_option(self.ITEM_TYPE, item_type)
        self.select_option(self.STANDARD_TYPE, standard_type)
        self.set_text(self.NAME, name)

    def form_details(self):
        return {
            "name": self.read_name(),
            "standard_type": Select(
                self.wait_for_visible(self.STANDARD_TYPE)
            ).first_selected_option.text.strip(),
            "item_type": Select(
                self.wait_for_visible(self.ITEM_TYPE)
            ).first_selected_option.text.strip(),
        }

    def save(self):
        result = self.submit()

        assert result["status"] == "saved", (
            "Standard Reference Save did not return to the grid: "
            f"{result}"
        )

        self.wait_for_grid()

    def visible_names(self):
        return [
            row.find_element(
                By.CSS_SELECTOR,
                "span[ng-bind='standard.Name']",
            ).text.strip()
            for row in self.driver.find_elements(*self.ROWS)
            if row.is_displayed()
        ]

    def matching_rows(self, identity):
        matches = []

        for row in self.driver.find_elements(*self.ROWS):
            if not row.is_displayed():
                continue

            actual = {
                "name": row.find_element(
                    By.CSS_SELECTOR,
                    "span[ng-bind='standard.Name']",
                ).text.strip(),
                "standard_type": row.find_element(
                    By.CSS_SELECTOR,
                    "span[ng-bind='standard.StandardTypeName']",
                ).text.strip(),
                "item_type": row.find_element(
                    By.CSS_SELECTOR,
                    "span[ng-bind='standard.ItemTypeName']",
                ).text.strip(),
            }

            if actual == identity:
                matches.append(row)

        return matches

    def grid_details(self, identity):
        def read(driver):
            try:
                matches = self.matching_rows(identity)

                if not matches:
                    return False

                assert len(matches) == 1, (
                    f"Multiple Standard References match: {identity}"
                )

                cells = matches[0].find_elements(By.TAG_NAME, "td")

                return {
                    "name": cells[0].text.strip(),
                    "standard_type": cells[1].text.strip(),
                    "item_type": cells[2].text.strip(),
                }

            except self.RETRY_ERRORS:
                return False

        return self.wait.until(
            read,
            message=f"Standard Reference grid values missing: {identity}",
        )

    def row_action(self, identity, title):
        self.wait_idle()

        def attempt(driver):
            try:
                rows = self.matching_rows(identity)

                if not rows:
                    return False

                assert len(rows) == 1, (
                    f"Multiple Standard References match: {identity}"
                )

                action = rows[0].find_element(
                    By.CSS_SELECTOR,
                    f"span[title='{title}']",
                )

                if not action.is_displayed() or not action.is_enabled():
                    return False

                self.scroll_to(action)
                action.click()
                return True

            except self.RETRY_ERRORS:
                return False

        self.wait.until(
            attempt,
            message=f"Could not {title} for reference: {identity}",
        )

    def edit(self, identity):
        self.row_action(identity, "Edit Record")
        self.wait_for_visible(self.NAME)
        self.wait_idle()

        def correct_form(driver):
            try:
                return self.form_details() == identity
            except self.RETRY_ERRORS:
                return False

        self.wait.until(
            correct_form,
            message=f"Reference Edit values did not load: {identity}",
        )

    def request_delete(self, identity):
        self.row_action(identity, "Delete Record")

        return self.wait_for_visible(
            self.POPUP_MESSAGE
        ).text.strip()