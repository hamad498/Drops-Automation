from pathlib import Path

from selenium.common.exceptions import (
    ElementClickInterceptedException,
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from pages.standard_type_page import StandardTypePage


class RigItemsLocationsPage(StandardTypePage):
    MENU = (
        By.CSS_SELECTOR,
        "a[ng-click='RigItemsLocations()']",
    )
    ADD_ZONE = (
        By.CSS_SELECTOR,
        "button[ng-click='OpenInspectionZoneDailog(null)']",
    )
    PAGE_SAVE = (
        By.CSS_SELECTOR,
        "button[ng-click='SaveRigitemslocation()']",
    )
    ZONES = (
        By.CSS_SELECTOR,
        "li[ng-repeat='zone in SiteControls.InspectionZones']",
    )

    POPUP = (
        By.CSS_SELECTOR,
        ".sweet-alert.visible",
    )
    POPUP_CONFIRM = (
        By.CSS_SELECTOR,
        ".sweet-alert.visible button.confirm",
    )
    POPUP_CANCEL = (
        By.CSS_SELECTOR,
        ".sweet-alert.visible button.cancel",
    )

    BLOCKED_MESSAGE = (
        "You can't delete this record. because related records are exists"
    )
    SUCCESS_MESSAGE = "record deleted successfully..!"

    RETRY_ERRORS = (
        ElementClickInterceptedException,
        NoSuchElementException,
        StaleElementReferenceException,
    )

    FORMS = {
        "zone": {
            "name": (By.ID, "txtZoneName"),
            "order": (By.ID, "txtZoneOrder"),
        },
        "area": {
            "name": (By.ID, "txtAreaName"),
            "order": (By.ID, "txtAreaOrder"),
        },
        "level": {
            "name": (By.ID, "txtLevelName"),
        },
    }

    SAVE_SELECTORS = {
        "zone": (
            "button[type='submit']"
            "[ng-disabled='InspectionZoneForm.$invalid']"
        ),
        "area": (
            "button[type='submit']"
            "[ng-disabled='InspectionAreaForm.$invalid']"
        ),
        "level": (
            "button[type='submit']"
            "[ng-disabled='InspectionLevelForm.$invalid']"
        ),
    }

    def open(self):
        self.wait_idle()

        if not any(
            element.is_displayed()
            for element in self.driver.find_elements(*self.MENU)
        ):
            self.click(self.SETTINGS)

        self.click(self.MENU)

        self.wait.until(
            lambda driver: any(
                element.is_displayed()
                for element in driver.find_elements(*self.ADD_ZONE)
            ),
            message="Rig Items Locations page did not open.",
        )

        self.wait_idle()

    @staticmethod
    def normalize(value):
        return " ".join(value.split())

    def direct_name(self, element):
        value = self.driver.execute_script(
            """
            return Array.from(arguments[0].childNodes)
                .filter(node => node.nodeType === Node.TEXT_NODE)
                .map(node => node.textContent)
                .join(" ");
            """,
            element,
        )
        return self.normalize(value)

    def find_node(self, path):
        if not 1 <= len(path) <= 3:
            raise ValueError(
                "Path must contain Zone, Area and/or Level."
            )

        matches = [
            node
            for node in self.driver.find_elements(*self.ZONES)
            if node.is_displayed()
            and self.direct_name(node) == path[0]
        ]

        if len(matches) > 1:
            raise AssertionError(
                f"Duplicate Zone name: {path[0]}"
            )

        if not matches:
            return None

        node = matches[0]

        child_paths = (
            "./ul/li[@ng-repeat='area in zone.Inspection_Areas']",
            "./ul/li[@ng-repeat='level in area.Inspection_Levels']",
        )

        for name, child_xpath in zip(path[1:], child_paths):
            matches = [
                child
                for child in node.find_elements(
                    By.XPATH,
                    child_xpath,
                )
                if child.is_displayed()
                and self.direct_name(child) == name
            ]

            if len(matches) > 1:
                raise AssertionError(
                    f"Duplicate hierarchy name: {path}"
                )

            if not matches:
                return None

            node = matches[0]

        return node

    def exists(self, path):
        return self.find_node(path) is not None

    def wait_for_node(self, path):
        def attempt(driver):
            try:
                return self.find_node(path) or False
            except StaleElementReferenceException:
                return False

        try:
            return self.wait.until(
                attempt,
                message=f"Hierarchy record not found: {path}",
            )

        except TimeoutException as exc:
            visible_zones = []

            for node in self.driver.find_elements(*self.ZONES):
                try:
                    if node.is_displayed():
                        visible_zones.append(
                            {
                                "direct_name": self.direct_name(node),
                                "text": node.text[:500],
                            }
                        )
                except StaleElementReferenceException:
                    continue

            screenshot = (
                Path("screenshots")
                / "rig_location_record_missing.png"
            ).resolve()

            screenshot.parent.mkdir(
                parents=True,
                exist_ok=True,
            )
            self.driver.save_screenshot(str(screenshot))

            raise AssertionError(
                "Hierarchy record not found after Save.\n"
                f"Expected path: {path!r}\n"
                f"Visible Zones: {visible_zones!r}\n"
                f"Popup: {self.popup_details_now()!r}\n"
                f"Screenshot: {screenshot}"
            ) from exc

    def wait_for_absence(self, path):
        def attempt(driver):
            try:
                return not self.exists(path)
            except StaleElementReferenceException:
                return False

        self.wait.until(
            attempt,
            message=f"Deleted record still appears: {path}",
        )

    def node_action(self, path, xpath):
        self.wait_idle()

        def attempt(driver):
            try:
                node = self.find_node(path)

                if node is None:
                    return False

                button = node.find_element(
                    By.XPATH,
                    xpath,
                )

                if (
                    not button.is_displayed()
                    or not button.is_enabled()
                ):
                    return False

                driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center'});",
                    button,
                )

                button.click()
                return True

            except self.RETRY_ERRORS:
                return False

        self.wait.until(
            attempt,
            message=f"Could not perform hierarchy action: {path}",
        )

    def visible_field(self, locator):
        for field in self.driver.find_elements(*locator):
            if field.is_displayed():
                return field

        raise NoSuchElementException(
            f"No visible hierarchy field: {locator}"
        )

    def modal(self, kind):
        field = self.visible_field(
            self.FORMS[kind]["name"]
        )

        return field.find_element(
            By.XPATH,
            "./ancestor::div["
            "contains(concat(' ', normalize-space(@class), ' '), "
            "' modal ')"
            "][1]",
        )

    def wait_for_form(self, kind):
        def attempt(driver):
            try:
                return self.visible_field(
                    self.FORMS[kind]["name"]
                )
            except self.RETRY_ERRORS:
                return False

        self.wait.until(
            attempt,
            message=f"{kind.title()} form did not open.",
        )

        self.wait_idle()

    def open_add(self, kind, parent=None):
        if kind == "zone":
            self.click(self.ADD_ZONE)

        elif kind == "area":
            self.node_action(
                parent,
                "./span[@title='Create New Area']",
            )

        elif kind == "level":
            self.node_action(
                parent,
                "./span[@title='Create New level']",
            )

        else:
            raise ValueError(
                f"Unsupported hierarchy type: {kind}"
            )

        self.wait_for_form(kind)

    def edit_node(self, kind, path):
        titles = {
            "zone": "Edit Zone",
            "area": "Edit Area",
            "level": "Edit level",
        }

        self.node_action(
            path,
            f"./div/button[@title='{titles[kind]}']",
        )

        self.wait_for_form(kind)

    def fill_field(self, kind, key, value, verify=True):
        locator = self.FORMS[kind][key]
        value = str(value)
        self.wait_idle()
        last_actual = None

        def attempt(driver):
            nonlocal last_actual

            try:
                field = self.visible_field(locator)

                if not field.is_enabled():
                    return False

                driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center'});",
                    field,
                )

                field.send_keys(Keys.CONTROL, "a")
                field.send_keys(Keys.BACKSPACE)

                if value:
                    field.send_keys(value)

                field.send_keys(Keys.TAB)

                last_actual = self.visible_field(
                    locator
                ).get_property("value")

                if verify:
                    return last_actual == value

                return True

            except self.RETRY_ERRORS:
                return False

        try:
            self.wait.until(
                attempt,
                message=f"Could not fill {kind} / {key}.",
            )

        except TimeoutException as exc:
            raise AssertionError(
                f"Could not fill {kind} / {key}.\n"
                f"Expected: {value!r}\n"
                f"Actual: {last_actual!r}"
            ) from exc

        return last_actual

    def form_details(self, kind):
        return {
            key: self.visible_field(
                locator
            ).get_property("value")
            for key, locator in self.FORMS[kind].items()
        }

    def form_save_enabled(self, kind):
        buttons = self.modal(kind).find_elements(
            By.CSS_SELECTOR,
            self.SAVE_SELECTORS[kind],
        )

        visible_buttons = [
            button
            for button in buttons
            if button.is_displayed()
        ]

        if len(visible_buttons) != 1:
            raise AssertionError(
                f"Expected one visible {kind} Save button; "
                f"found {len(visible_buttons)}."
            )

        return visible_buttons[0].is_enabled()

    def form_button(self, kind, selector):
        last_issue = ""

        def attempt(driver):
            nonlocal last_issue

            try:
                buttons = self.modal(kind).find_elements(
                    By.CSS_SELECTOR,
                    selector,
                )

                button = next(
                    (
                        element
                        for element in buttons
                        if element.is_displayed()
                        and element.is_enabled()
                    ),
                    None,
                )

                if button is None:
                    last_issue = "No visible enabled matching button."
                    return False

                driver.execute_script(
                    """
                    arguments[0].scrollIntoView({
                        block: "center",
                        inline: "nearest"
                    });
                    """,
                    button,
                )

                button.click()
                return True

            except self.RETRY_ERRORS as exc:
                last_issue = (
                    f"{type(exc).__name__}: {exc}"
                )
                return False

        try:
            self.wait.until(
                attempt,
                message=f"Could not click {kind} button: {selector}",
            )

        except TimeoutException as exc:
            raise AssertionError(
                f"Could not click {kind} button: {selector}\n"
                f"Last issue: {last_issue}"
            ) from exc

    def wait_form_closed(self, kind):
        self.wait.until(
            lambda driver: not any(
                field.is_displayed()
                for field in driver.find_elements(
                    *self.FORMS[kind]["name"]
                )
            ),
            message=f"{kind.title()} form remained open.",
        )

        self.wait_idle()

    def save_page(self):
        self.click(self.PAGE_SAVE)
        self.wait_idle()

        details = self.popup_details_now()

        if details:
            if details["confirmation"]:
                raise AssertionError(
                    "Unexpected confirmation after main Save: "
                    f"{details!r}"
                )

            self.dismiss_popup()

            if details["title"].strip().lower() == "error":
                raise AssertionError(
                    "Rig Items Locations Save failed: "
                    f"{details['message']}"
                )

        self.open()

    def save_form(self, kind):
        self.wait_idle()

        details = self.form_details(kind)
        print(f"Saving {kind}: {details!r}")

        self.form_button(
            kind,
            self.SAVE_SELECTORS[kind],
        )
        self.wait_form_closed(kind)

        # Persist the complete hierarchy, then reopen.
        self.save_page()

    def close_form(self, kind):
        self.form_button(
            kind,
            "button.close",
        )
        self.wait_form_closed(kind)

    def request_node_delete(self, kind, path):
        titles = {
            "zone": "Delete zone",
            "area": "Delete Area",
            "level": "Delete level",
        }

        self.node_action(
            path,
            f"./div/button[@title='{titles[kind]}']",
        )

        return self.read_popup()

    def popup_details_now(self):
        try:
            for popup in self.driver.find_elements(*self.POPUP):
                if not popup.is_displayed():
                    continue

                message = popup.find_element(
                    By.TAG_NAME,
                    "p",
                ).text.strip()

                if not message:
                    return False

                return {
                    "title": popup.find_element(
                        By.TAG_NAME,
                        "h2",
                    ).text.strip(),
                    "message": message,
                    "confirmation": any(
                        button.is_displayed()
                        for button in popup.find_elements(
                            By.CSS_SELECTOR,
                            "button.cancel",
                        )
                    ),
                }

            return False

        except (
            NoSuchElementException,
            StaleElementReferenceException,
        ):
            return False

    def read_popup(self):
        return self.wait.until(
            lambda driver: self.popup_details_now(),
            message="Expected hierarchy popup did not appear.",
        )

    def dismiss_popup(self, cancel=False):
        self.click(
            self.POPUP_CANCEL
            if cancel
            else self.POPUP_CONFIRM
        )

        self.wait.until(
            lambda driver: not any(
                popup.is_displayed()
                for popup in driver.find_elements(*self.POPUP)
            ),
            message="Hierarchy popup remained open.",
        )

        self.wait_idle()

    def confirm_node_delete(self):
        self.click(self.POPUP_CONFIRM)

        def response(driver):
            details = self.popup_details_now()

            if not details or details["confirmation"]:
                return False

            return details

        details = self.wait.until(
            response,
            message="Delete result popup did not appear.",
        )

        message = details["message"]
        self.dismiss_popup()

        # Persist successful deletions before reopening the page.
        if self.normalize(message) == self.normalize(
            self.SUCCESS_MESSAGE
        ):
            self.save_page()

        return message

    def parent_delete_response(self, kind, path):
        details = self.request_node_delete(kind, path)

        if details["confirmation"]:
            return self.confirm_node_delete()

        message = details["message"]
        self.dismiss_popup()
        return message