from selenium.common.exceptions import (
    ElementClickInterceptedException,
    NoSuchElementException,
    StaleElementReferenceException,
)
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select

from pages.base_page import BasePage


class RigPage(BasePage):
    SETTINGS_MENU = (
        By.XPATH,
        "//a[normalize-space()='Settings']",
    )
    RIG_MENU = (
        By.CSS_SELECTOR,
        "a[ng-click='LoadSiteGrid()']",
    )
    ADD_BUTTON = (
        By.CSS_SELECTOR,
        "button[ng-click='LoadSite()']",
    )

    CLIENT = (By.ID, "ddlClient")
    RIG_TYPE = (By.ID, "dllRigType")
    RIG_NAME = (
        By.CSS_SELECTOR,
        "input[ng-model='SiteControls.RigName']",
    )
    LOCATION = (By.ID, "txtRigLocation")

    LICENSE_START = (
        By.CSS_SELECTOR,
        "input[ng-model='SiteControls.licenseStartDate']",
    )
    LICENSE_END = (
        By.CSS_SELECTOR,
        "input[ng-model='SiteControls.LicenseEndDate']",
    )
    SAVE_BUTTON = (
        By.CSS_SELECTOR,
        "button[ng-disabled='siteForm.$invalid']",
    )

    SEARCH_FIELD = (
        By.CSS_SELECTOR,
        "input[ng-model='SearchWord']",
    )
    SEARCH_BUTTON = (
        By.CSS_SELECTOR,
        "button[ng-click='GetSearch()']",
    )
    ROWS = (
        By.CSS_SELECTOR,
        "tr[ng-repeat='rig in SiteData']",
    )
    OVERLAY = (By.CSS_SELECTOR, ".splash-loading")

    POPUP = (
        By.CSS_SELECTOR,
        ".sweet-alert.visible",
    )
    POPUP_MESSAGE = (
        By.CSS_SELECTOR,
        ".sweet-alert.visible > p",
    )
    DELETE_CONFIRM = (
        By.CSS_SELECTOR,
        ".sweet-alert.visible button.confirm",
    )
    DELETE_CANCEL = (
        By.CSS_SELECTOR,
        ".sweet-alert.visible button.cancel",
    )

    TREE_REPEATS = (
        "zone in SiteControls.InspectionZones",
        "area in zone.Inspection_Areas",
        "level in area.Inspection_Levels",
    )
    TREE_KINDS = ("zone", "area", "level")
    TREE_EDIT_TITLES = (
        "Edit Zone",
        "Edit Area",
        "Edit level",
    )
    TREE_DELETE_TITLES = (
        "Delete zone",
        "Delete Area",
        "Delete level",
    )

    TREE_FIELDS = {
        "zone": {
            "name": (
                By.CSS_SELECTOR,
                "input[ng-model='Inspection_Zones.ZoneName']",
            ),
            "order": (
                By.CSS_SELECTOR,
                "input[ng-model='Inspection_Zones.ZoneOrder']",
            ),
        },
        "area": {
            "name": (
                By.CSS_SELECTOR,
                "input[ng-model='Inspection_Areas.AreaName']",
            ),
            "order": (
                By.CSS_SELECTOR,
                "input[ng-model='Inspection_Areas.AreaOrder']",
            ),
        },
        "level": {
            "name": (
                By.CSS_SELECTOR,
                "input[ng-model='Inspection_Levels.LevelName']",
            ),
        },
    }

    TREE_SAVE = {
        "zone": (
            By.CSS_SELECTOR,
            "button[ng-disabled='InspectionZoneForm.$invalid']",
        ),
        "area": (
            By.CSS_SELECTOR,
            "button[ng-disabled='InspectionAreaForm.$invalid']",
        ),
        "level": (
            By.CSS_SELECTOR,
            "button[ng-disabled='InspectionLevelForm.$invalid']",
        ),
    }

    RELATED_RECORDS_MESSAGE = (
        "You can't delete this record. because related records are exists"
    )

    RETRY_ERRORS = (
        ElementClickInterceptedException,
        NoSuchElementException,
        StaleElementReferenceException,
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

    def escape(self):
        ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()

    def loading_visible(self, driver):
        return any(
            element.is_displayed()
            for element in driver.find_elements(*self.OVERLAY)
        )

    def click(self, locator):
        # Escape can dismiss SweetAlert, so preserve an open popup.
        if not self.popup_visible():
            self.escape()

        last_issue = {"detail": "Element was not ready."}

        def attempt(driver):
            try:
                if self.loading_visible(driver):
                    last_issue["detail"] = "Loading overlay is visible."
                    return False

                elements = [
                    element
                    for element in driver.find_elements(*locator)
                    if element.is_displayed() and element.is_enabled()
                ]

                if len(elements) != 1:
                    last_issue["detail"] = (
                        "Visible and enabled matches: "
                        f"{len(elements)}"
                    )
                    return False

                element = elements[0]
                self.scroll_to(element)
                element.click()
                return True

            except self.RETRY_ERRORS as error:
                last_issue["detail"] = (
                    f"{type(error).__name__}: "
                    f"{str(error).split('Stacktrace:')[0]}"
                )
                return False

        self.wait.until(
            attempt,
            message=f"Could not click Rig page element: {locator}",
        )

    def set_text(self, locator, value, verify=True):
        value = str(value)
        self.escape()

        def enter_text(driver):
            try:
                if self.loading_visible(driver):
                    return False

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

                field.send_keys(Keys.ESCAPE)
                field.send_keys(Keys.TAB)
                self.escape()

                if not verify:
                    return True

                return driver.find_element(
                    *locator
                ).get_property("value") == value

            except self.RETRY_ERRORS:
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

        def empty_form(driver):
            try:
                field = driver.find_element(*self.RIG_NAME)
                return (
                    field.is_displayed()
                    and field.get_property("value") == ""
                )

            except self.RETRY_ERRORS:
                return False

        self.wait.until(
            empty_form,
            message="New Rig form did not open with an empty Rig Name.",
        )

    def select_option(self, locator, text):
        self.escape()

        def attempt(driver):
            try:
                if self.loading_visible(driver):
                    return False

                element = driver.find_element(*locator)

                if (
                    not element.is_displayed()
                    or not element.is_enabled()
                ):
                    return False

                self.scroll_to(element)
                dropdown = Select(element)

                matching = [
                    option
                    for option in dropdown.options
                    if option.text.strip() == text
                ]

                if not matching:
                    return False

                assert len(matching) == 1, (
                    f"Multiple dropdown options match: {text}"
                )

                dropdown.select_by_visible_text(text)

                return (
                    dropdown.first_selected_option.text.strip() == text
                )

            except self.RETRY_ERRORS:
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

    def set_license_dates(self, start_date, end_date):
        self.set_text(self.LICENSE_START, start_date)
        self.set_text(self.LICENSE_END, end_date)

    def read_license_date(self, key):
        locators = {
            "license_start": self.LICENSE_START,
            "license_end": self.LICENSE_END,
        }

        if key not in locators:
            raise KeyError(f"Unknown Rig date field: {key}")

        return self.wait_for_visible(
            locators[key]
        ).get_property("value")

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

    def matching_rows(self, client_name, rig_name):
        matches = []

        for row in self.driver.find_elements(*self.ROWS):
            if not row.is_displayed():
                continue

            cells = row.find_elements(By.TAG_NAME, "td")
            identity = [
                cell.text.strip()
                for cell in cells[:2]
            ]

            if identity == [client_name, rig_name]:
                matches.append(row)

        return matches

    def get_rig_details(self, client_name, rig_name):
        def read_details(driver):
            try:
                matches = self.matching_rows(client_name, rig_name)

                if not matches:
                    return False

                assert len(matches) == 1, (
                    f"Duplicate Rig rows: {client_name} / {rig_name}"
                )

                cells = matches[0].find_elements(By.TAG_NAME, "td")

                if len(cells) < 3:
                    return False

                return [
                    cell.text.strip()
                    for cell in cells[:3]
                ]

            except StaleElementReferenceException:
                return False

        return self.wait.until(
            read_details,
            message=f"Rig not found: {client_name} / {rig_name}",
        )

    def click_row_action(self, client_name, rig_name, title):
        def attempt(driver):
            try:
                if self.loading_visible(driver):
                    return False

                matches = self.matching_rows(client_name, rig_name)

                if not matches:
                    return False

                assert len(matches) == 1, (
                    f"Multiple rigs match: {client_name} / {rig_name}"
                )

                action = matches[0].find_element(
                    By.CSS_SELECTOR,
                    f"span[title='{title}']",
                )

                if (
                    not action.is_displayed()
                    or not action.is_enabled()
                ):
                    return False

                self.scroll_to(action)
                action.click()
                return True

            except self.RETRY_ERRORS:
                return False

        self.wait.until(
            attempt,
            message=f"Could not click {title} for Rig: {rig_name}",
        )

    def edit(self, client_name, rig_name):
        self.click_row_action(
            client_name,
            rig_name,
            "Edit Record",
        )

        def correct_form(driver):
            try:
                field = driver.find_element(*self.RIG_NAME)

                return (
                    field.is_displayed()
                    and field.get_property("value") == rig_name
                )

            except self.RETRY_ERRORS:
                return False

        self.wait.until(
            correct_form,
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

            except self.RETRY_ERRORS:
                return False

        return self.wait.until(
            read_details,
            message=f"Rig form values did not match: {expected}",
        )

    def request_delete(self, client_name, rig_name):
        self.click_row_action(
            client_name,
            rig_name,
            "Delete Record",
        )
        self.wait_for_visible(self.POPUP)

    def get_delete_message(self):
        return self.wait_for_visible(
            self.POPUP_MESSAGE
        ).text.strip()

    def cancel_delete(self):
        self.click(self.DELETE_CANCEL)
        self.wait.until(
            EC.invisibility_of_element_located(self.POPUP)
        )

    def confirm_delete(self):
        self.click(self.DELETE_CONFIRM)

    # Zone / Area / Level helpers.

    def node_name(self, node):
        # Read only this LI's own text, excluding nested children.
        text = self.driver.execute_script(
            """
            return Array.from(arguments[0].childNodes)
                .filter(node => node.nodeType === Node.TEXT_NODE)
                .map(node => node.textContent)
                .join(' ');
            """,
            node,
        )
        return " ".join(text.split())

    def find_tree_node(self, path):
        path = tuple(path)

        if not 1 <= len(path) <= 3:
            raise ValueError(
                "Tree path must contain Zone, Area, or Level."
            )

        parent = None

        for depth, name in enumerate(path):
            repeat = self.TREE_REPEATS[depth]

            if depth == 0:
                candidates = self.driver.find_elements(
                    By.CSS_SELECTOR,
                    f"li[ng-repeat='{repeat}']",
                )
            else:
                candidates = parent.find_elements(
                    By.XPATH,
                    f"./ul/li[@ng-repeat='{repeat}']",
                )

            matches = [
                node
                for node in candidates
                if node.is_displayed() and self.node_name(node) == name
            ]

            if not matches:
                return None

            assert len(matches) == 1, (
                f"Multiple tree nodes match path: {path[:depth + 1]}"
            )

            parent = matches[0]

        return parent

    def tree_snapshot(self, path):
        node = self.find_tree_node(path)

        if node is None:
            return None

        def read_node(element, depth):
            children = []

            if depth < 2:
                repeat = self.TREE_REPEATS[depth + 1]

                children = [
                    read_node(child, depth + 1)
                    for child in element.find_elements(
                        By.XPATH,
                        f"./ul/li[@ng-repeat='{repeat}']",
                    )
                    if child.is_displayed()
                ]

            return {
                "name": self.node_name(element),
                "children": children,
            }

        return read_node(node, len(path) - 1)

    def click_tree_action(self, path, locator):
        def attempt(driver):
            try:
                if self.loading_visible(driver):
                    return False

                node = self.find_tree_node(path)

                if node is None:
                    return False

                action = node.find_element(*locator)

                if (
                    not action.is_displayed()
                    or not action.is_enabled()
                ):
                    return False

                self.scroll_to(action)
                action.click()
                return True

            except self.RETRY_ERRORS:
                return False

        self.wait.until(
            attempt,
            message=f"Could not click tree action: {path} / {locator}",
        )

    def open_tree_form(self, kind, parent_path=(), edit_path=None):
        depth = self.TREE_KINDS.index(kind)

        if edit_path is not None:
            assert len(edit_path) == depth + 1
            title = self.TREE_EDIT_TITLES[depth]

            self.click_tree_action(
                edit_path,
                (By.XPATH, f"./div/button[@title='{title}']"),
            )

        elif kind == "zone":
            self.click((
                By.CSS_SELECTOR,
                "button[ng-click='OpenInspectionZoneDailog(null)']",
            ))

        else:
            assert len(parent_path) == depth

            title = (
                "Create New Area"
                if kind == "area"
                else "Create New level"
            )

            self.click_tree_action(
                parent_path,
                (By.XPATH, f"./span[@title='{title}']"),
            )

        self.wait_for_visible(self.TREE_FIELDS[kind]["name"])

    def fill_tree_form(self, kind, name, order=None):
        self.set_text(self.TREE_FIELDS[kind]["name"], name)

        if "order" in self.TREE_FIELDS[kind]:
            if order is None:
                raise ValueError(f"{kind} requires an order.")

            self.set_text(
                self.TREE_FIELDS[kind]["order"],
                order,
            )

    def read_tree_field(self, kind, field):
        return self.wait_for_visible(
            self.TREE_FIELDS[kind][field]
        ).get_property("value")

    def tree_save_enabled(self, kind):
        return self.wait_for_visible(
            self.TREE_SAVE[kind]
        ).is_enabled()

    def save_tree_form(self, kind):
        self.click(self.TREE_SAVE[kind])

        self.wait.until(
            EC.invisibility_of_element_located(
                self.TREE_FIELDS[kind]["name"]
            ),
            message=f"{kind} form remained open after Save.",
        )

    def close_tree_form(self, kind, cancel=False):
        def attempt(driver):
            try:
                field = driver.find_element(
                    *self.TREE_FIELDS[kind]["name"]
                )

                if not field.is_displayed():
                    return True

                modal = field.find_element(
                    By.XPATH,
                    "./ancestor::div["
                    "contains(concat(' ', normalize-space(@class), ' '),"
                    " ' modal ')][1]",
                )

                if cancel:
                    buttons = modal.find_elements(
                        By.XPATH,
                        ".//button[@data-dismiss='modal'"
                        " and normalize-space()='Cancel']",
                    )
                else:
                    buttons = modal.find_elements(
                        By.CSS_SELECTOR,
                        "button.close[data-dismiss='modal']",
                    )

                visible = [
                    button
                    for button in buttons
                    if button.is_displayed() and button.is_enabled()
                ]

                if len(visible) != 1:
                    return False

                self.scroll_to(visible[0])
                visible[0].click()
                return True

            except self.RETRY_ERRORS:
                return False

        self.wait.until(
            attempt,
            message=f"Could not close {kind} form.",
        )

        self.wait.until(
            EC.invisibility_of_element_located(
                self.TREE_FIELDS[kind]["name"]
            )
        )

    def popup_visible(self):
        return any(
            popup.is_displayed()
            for popup in self.driver.find_elements(*self.POPUP)
        )

    def popup_has_cancel(self):
        return any(
            button.is_displayed()
            for button in self.driver.find_elements(
                *self.DELETE_CANCEL
            )
        )

    def acknowledge_popup(self):
        self.click(self.DELETE_CONFIRM)

        self.wait.until(
            EC.invisibility_of_element_located(self.POPUP)
        )

    def request_tree_delete(self, path):
        title = self.TREE_DELETE_TITLES[len(path) - 1]

        self.click_tree_action(
            path,
            (By.XPATH, f"./div/button[@title='{title}']"),
        )

        def outcome(driver):
            try:
                if self.loading_visible(driver):
                    return False

                if self.popup_visible():
                    return {
                        "popup": True,
                        "message": self.get_delete_message(),
                        "cancel": self.popup_has_cancel(),
                    }

                if self.find_tree_node(path) is None:
                    return {
                        "popup": False,
                        "message": "",
                        "cancel": False,
                    }

                return False

            except self.RETRY_ERRORS:
                return False

        return self.wait.until(
            outcome,
            message=f"No deletion response for: {path}",
        )

    def confirm_tree_delete(self, path):
        self.click(self.DELETE_CONFIRM)

        def deleted(driver):
            try:
                if self.loading_visible(driver):
                    return False

                if self.find_tree_node(path) is not None:
                    return False

                # Wait for the confirmation dialog to transition.
                return not self.popup_has_cancel()

            except self.RETRY_ERRORS:
                return False

        self.wait.until(
            deleted,
            message=f"Tree node was not deleted: {path}",
        )

        if self.popup_visible():
            self.acknowledge_popup()

    def check_parent_delete_response(self, path):
        response = self.request_tree_delete(path)

        if not response["popup"]:
            return response["message"]

        message = response["message"]

        # The application may block deletion immediately.
        if message == self.RELATED_RECORDS_MESSAGE:
            self.acknowledge_popup()
            return message

        # Some versions check dependencies after confirmation.
        if response["cancel"]:
            initial_message = message
            self.click(self.DELETE_CONFIRM)

            def dependency_response(driver):
                try:
                    if self.loading_visible(driver):
                        return False

                    if not self.popup_visible():
                        return False

                    current_message = self.get_delete_message()

                    if current_message != initial_message:
                        return {"message": current_message}

                    return False

                except self.RETRY_ERRORS:
                    return False

            result = self.wait.until(
                dependency_response,
                message=(
                    "No dependency response after confirming "
                    f"parent deletion: {path}"
                ),
            )
            message = result["message"]

        if self.popup_visible():
            self.acknowledge_popup()

        return message