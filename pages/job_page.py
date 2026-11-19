from pathlib import Path
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select

from pages.base_page import BasePage


class JobPage(BasePage):
    MENU = (
        By.CSS_SELECTOR,
        "a[ng-click='LoadJobGrid()']",
    )
    ADD = (
        By.CSS_SELECTOR,
        "button[ng-click='LoadJobAdminView()']",
    )
    SAVE = (
        By.CSS_SELECTOR,
        "button[type='submit'][ng-disabled='JobForm.$invalid']",
    )

    NUMBER = (
        By.CSS_SELECTOR,
        "input[ng-model='JobControls.JobNumber']",
    )
    DESCRIPTION = (
        By.CSS_SELECTOR,
        "input[ng-model='JobControls.JobDescription']",
    )
    INSPECTION_DATE = (By.ID, "txtInspectionDate")
    NEXT_INSPECTION = (By.ID, "txtNextInpsection")

    STATUS = (
        By.CSS_SELECTOR,
        "select[ng-model='JobControls.JobStauts']",
    )
    STAGE = (
        By.CSS_SELECTOR,
        "select[ng-model='JobControls.CurrentStage']",
    )
    CLIENT = (
        By.CSS_SELECTOR,
        "select[ng-model='JobControls.ClientId']",
    )
    RIG = (
        By.CSS_SELECTOR,
        "select[ng-model='JobControls.RigID']",
    )

    ONGOING_ACCESS = (By.ID, "IsOngoingAccess")
    AUTO_REFERENCE = (By.ID, "ckcheckbox")
    OVERLAY = (By.CSS_SELECTOR, ".splash-loading")

    OPTIONAL_TEXT_FIELDS = {
        "po_number": (
            By.CSS_SELECTOR,
            "input[ng-model='JobControls.PONumber']",
        ),
        "report_issue_date": (
            By.CSS_SELECTOR,
            "input[ng-model='JobControls.ReportIssueDate']",
        ),
        "report_number": (
            By.CSS_SELECTOR,
            "input[ng-model='JobControls.RefReportNo']",
        ),
        "inspection_reference": (
            By.CSS_SELECTOR,
            "input[ng-model='JobControls.InspReference']",
        ),
    }

    OPTIONAL_SELECT_FIELDS = {
        "paid_status": (
            By.CSS_SELECTOR,
            "select[ng-model='JobControls.PaidStatus']",
        ),
        "reporting_office": (
            By.CSS_SELECTOR,
            "select[ng-model='JobControls.ReportingOfficeId']",
        ),
        "technical_manager": (
            By.CSS_SELECTOR,
            "select[ng-model='JobControls.ReportManagerId']",
        ),
    }

    INSPECTOR = (
        By.CSS_SELECTOR,
        "select[ng-model='JobInspectorControl.InspectorId']",
    )
    ASSIGN = (
        By.CSS_SELECTOR,
        "button[ng-disabled='JobInspector.$invalid']",
    )
    INSPECTOR_ROWS = (
        By.CSS_SELECTOR,
        "tr[ng-repeat='J in Jobinspector']",
    )

    SECTION_NAME = (By.ID, "txtSecName")
    REPORT_UPLOAD = (By.ID, "PdfAddInspFInp")
    REPORT_SEARCH = (
        By.CSS_SELECTOR,
        "input[ng-model='SFilter']",
    )
    REPORT_ROWS = (
        By.XPATH,
        "//tr[td//span[@ng-bind='J.SectionName']]",
    )

    CONTRACT_UPLOAD = (By.ID, "PdfInp")
    CONTRACT_LINK = (By.CSS_SELECTOR, "a#Pdftextbox")

    SEARCH = (
        By.CSS_SELECTOR,
        "input[ng-model='SearchWord']",
    )
    SEARCH_BUTTON = (
        By.CSS_SELECTOR,
        "button[ng-click='GetJobSearch()']",
    )
    ROWS = (
        By.CSS_SELECTOR,
        "tr[ng-repeat='J in JobData']",
    )

    POPUP_MESSAGE = (
        By.CSS_SELECTOR,
        ".sweet-alert.visible > p",
    )
    POPUP_OK = (
        By.CSS_SELECTOR,
        ".sweet-alert.visible button.confirm",
    )

    RETRY_ERRORS = (
        ElementClickInterceptedException,
        NoSuchElementException,
        StaleElementReferenceException,
    )

    def visible(self, locator):
        return self.wait_for_visible(locator)

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

    def loading_visible(self, driver):
        return any(
            element.is_displayed()
            for element in driver.find_elements(*self.OVERLAY)
        )

    def close_datepicker(self):
        # Send Escape as a keyboard action.
        # Do not call send_keys on the active file input.
        ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()

    def click(self, locator):
        self.close_datepicker()

        def attempt(driver):
            try:
                if self.loading_visible(driver):
                    return False

                elements = [
                    element
                    for element in driver.find_elements(*locator)
                    if element.is_displayed() and element.is_enabled()
                ]

                if len(elements) != 1:
                    return False

                element = elements[0]
                self.scroll_to(element)
                element.click()
                return True

            except self.RETRY_ERRORS:
                return False

        self.wait.until(
            attempt,
            message=f"Could not click: {locator}",
        )

    def set_text(self, locator, value):
        value = str(value)
        last_issue = {"detail": "Field was not ready."}

        self.close_datepicker()

        def attempt(driver):
            try:
                if self.loading_visible(driver):
                    last_issue["detail"] = "Loading overlay is visible."
                    return False

                fields = driver.find_elements(*locator)
                visible_fields = [
                    field for field in fields if field.is_displayed()
                ]

                if len(visible_fields) != 1:
                    last_issue["detail"] = (
                        f"Matching fields: {len(fields)}; "
                        f"visible fields: {len(visible_fields)}"
                    )
                    return False

                field = visible_fields[0]

                if not field.is_enabled():
                    last_issue["detail"] = "Field is disabled."
                    return False

                if field.get_property("readOnly"):
                    last_issue["detail"] = "Field is read-only."
                    return False

                self.scroll_to(field)

                # send_keys focuses the input without a mouse click.
                # A calendar overlapping the input cannot intercept that click.
                field.send_keys(Keys.ESCAPE)
                field.send_keys(Keys.CONTROL, "a")
                field.send_keys(Keys.BACKSPACE)

                if value:
                    field.send_keys(value)

                # Close the current calendar and trigger the field's blur event.
                field.send_keys(Keys.ESCAPE)
                field.send_keys(Keys.TAB)

                # Tab may focus another date input and open its calendar.
                self.close_datepicker()

                # Re-find after Angular updates.
                actual = driver.find_element(
                    *locator
                ).get_property("value")

                last_issue["detail"] = f"Actual field value: {actual!r}"
                return actual == value

            except self.RETRY_ERRORS as error:
                last_issue["detail"] = (
                    f"{type(error).__name__}: "
                    f"{str(error).split('Stacktrace:')[0]}"
                )
                return False

        try:
            self.wait.until(
                attempt,
                message=f"Could not enter text: {locator}",
            )

        except TimeoutException as error:
            screenshot = Path("screenshots/job_text_entry_failed.png")
            screenshot.parent.mkdir(parents=True, exist_ok=True)
            self.driver.save_screenshot(str(screenshot))

            raise AssertionError(
                f"Could not fill {locator}.\n"
                f"Last issue: {last_issue['detail']}\n"
                f"Screenshot: {screenshot.resolve()}"
            ) from error

    def select_text(self, locator, text):
        self.close_datepicker()

        def attempt(driver):
            try:
                if self.loading_visible(driver):
                    return False

                elements = [
                    element
                    for element in driver.find_elements(*locator)
                    if element.is_displayed() and element.is_enabled()
                ]

                if len(elements) != 1:
                    return False

                element = elements[0]
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
                    f"Multiple dropdown options found: {text}"
                )

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

    def set_checkbox(self, locator, checked):
        checked = bool(checked)
        last_issue = {"detail": "Checkbox was not ready."}

        self.close_datepicker()

        def attempt(driver):
            try:
                if self.loading_visible(driver):
                    last_issue["detail"] = "Loading overlay is visible."
                    return False

                matches = driver.find_elements(*locator)
                visible = [
                    element
                    for element in matches
                    if element.is_displayed()
                ]

                if len(visible) != 1:
                    last_issue["detail"] = (
                        f"Matching checkboxes: {len(matches)}; "
                        f"visible: {len(visible)}"
                    )
                    return False

                checkbox = visible[0]

                if not checkbox.is_enabled():
                    last_issue["detail"] = "Checkbox is disabled."
                    return False

                if checkbox.is_selected() == checked:
                    return True

                self.scroll_to(checkbox)
                self.close_datepicker()

                try:
                    checkbox.click()

                except ElementClickInterceptedException as error:
                    last_issue["detail"] = (
                        "Mouse click intercepted: "
                        f"{str(error).split('Stacktrace:')[0]}"
                    )

                    # Space toggles a checkbox through normal keyboard input.
                    checkbox.send_keys(Keys.SPACE)

                # Re-find after Angular updates.
                current = [
                    element
                    for element in driver.find_elements(*locator)
                    if element.is_displayed()
                ]

                if len(current) != 1:
                    last_issue["detail"] = (
                        "Checkbox changed during the update."
                    )
                    return False

                actual = current[0].is_selected()

                last_issue["detail"] = (
                    f"Expected selected={checked}; actual={actual}"
                )
                return actual == checked

            except self.RETRY_ERRORS as error:
                last_issue["detail"] = (
                    f"{type(error).__name__}: "
                    f"{str(error).split('Stacktrace:')[0]}"
                )
                return False

        try:
            self.wait.until(
                attempt,
                message=f"Could not set checkbox: {locator}",
            )

        except TimeoutException as error:
            screenshot = Path(
                "screenshots/job_checkbox_failed.png"
            )
            screenshot.parent.mkdir(parents=True, exist_ok=True)
            self.driver.save_screenshot(str(screenshot))

            raise AssertionError(
                f"Could not set checkbox: {locator}\n"
                f"Expected selected: {checked}\n"
                f"Last issue: {last_issue['detail']}\n"
                f"Screenshot: {screenshot.resolve()}"
            ) from error

    def open(self):
        try:
            self.click(self.MENU)

        except TimeoutException as error:
            screenshot = Path("screenshots/jobs_menu_blocked.png")
            screenshot.parent.mkdir(parents=True, exist_ok=True)
            self.driver.save_screenshot(str(screenshot))

            messages = [
                element.text.strip()
                for element in self.driver.find_elements(
                    *self.POPUP_MESSAGE
                )
                if element.is_displayed()
            ]

            raise AssertionError(
                "Jobs List navigation failed.\n"
                f"Visible popup messages: {messages}\n"
                f"Screenshot: {screenshot.resolve()}"
            ) from error

        self.visible(self.ADD)
        self.visible(self.SEARCH)

    def open_add_form(self):
        self.click(self.ADD)

        def empty_form(driver):
            try:
                field = driver.find_element(*self.NUMBER)
                return (
                    field.is_displayed()
                    and field.get_property("value") == ""
                )
            except self.RETRY_ERRORS:
                return False

        self.wait.until(
            empty_form,
            message="Empty Add Job form did not open.",
        )

    def fill_form(
        self,
        number,
        description,
        inspection_date,
        next_inspection,
        client_name,
        rig_name,
        status="Current",
        stage="Job Created",
    ):
        self.set_text(self.NUMBER, number)
        self.set_text(self.DESCRIPTION, description)
        self.set_text(self.INSPECTION_DATE, inspection_date)
        self.set_text(self.NEXT_INSPECTION, next_inspection)

        self.select_text(self.STATUS, status)
        self.select_text(self.STAGE, stage)

        # Selecting Client loads its associated Rigs.
        self.select_text(self.CLIENT, client_name)
        self.select_text(self.RIG, rig_name)

    def fill_additional_fields(self, values):
        for key, locator in self.OPTIONAL_TEXT_FIELDS.items():
            self.set_text(locator, values[key])

        for key, locator in self.OPTIONAL_SELECT_FIELDS.items():
            self.select_text(locator, values[key])

    def save_and_assign(self):
        self.click(self.SAVE)

        def saved_form_ready(driver):
            try:
                if self.loading_visible(driver):
                    return False

                button = driver.find_element(*self.SAVE)
                inspector = driver.find_element(*self.INSPECTOR)

                return (
                    button.is_displayed()
                    and button.text.strip() == "Update"
                    and inspector.is_displayed()
                )

            except self.RETRY_ERRORS:
                return False

        self.wait.until(
            saved_form_ready,
            message=(
                "Job did not reach the Update / "
                "Inspector assignment form."
            ),
        )

    def update(self):
        assert self.visible(self.SAVE).text.strip() == "Update"
        self.click(self.SAVE)

    def assign_inspector(self, inspector_name):
        self.select_text(self.INSPECTOR, inspector_name)
        self.click(self.ASSIGN)
        self.wait_for_inspector(inspector_name)

    def wait_for_inspector(self, inspector_name):
        def assigned(driver):
            try:
                names = []

                for row in driver.find_elements(*self.INSPECTOR_ROWS):
                    if not row.is_displayed():
                        continue

                    cells = row.find_elements(By.TAG_NAME, "td")

                    if cells:
                        names.append(cells[0].text.strip())

                count = names.count(inspector_name)

                assert count <= 1, (
                    f"Inspector assigned more than once: {inspector_name}"
                )
                return count == 1

            except StaleElementReferenceException:
                return False

        self.wait.until(
            assigned,
            message=f"Assigned Inspector missing: {inspector_name}",
        )

    def upload_file(self, locator, file_path):
        path = Path(file_path).resolve()

        assert path.is_file(), f"Test PDF missing: {path}"
        assert path.stat().st_size > 0, f"Test PDF is empty: {path}"

        def find_upload_input(driver):
            try:
                if self.loading_visible(driver):
                    return False

                active_fields = [
                    field
                    for field in driver.find_elements(*locator)
                    if field.is_enabled()
                    and field.find_element(By.XPATH, "..").is_displayed()
                ]

                assert len(active_fields) <= 1, (
                    f"Multiple active upload inputs found: {locator}"
                )

                return active_fields[0] if active_fields else False

            except self.RETRY_ERRORS:
                return False

        field = self.wait.until(
            find_upload_input,
            message=f"No active upload input found: {locator}",
        )

        field.send_keys(str(path))

        try:
            selected_files = self.driver.execute_script(
                """
                return Array.from(arguments[0].files || []).map(
                    file => ({
                        name: file.name,
                        size: file.size,
                        type: file.type
                    })
                );
                """,
                field,
            )
        except StaleElementReferenceException:
            # The upload handler may replace its input immediately.
            selected_files = []

        print(f"Upload input: {locator}")
        print(f"Selected files: {selected_files}")

        # The report row or contract link verifies the upload result.
        if selected_files:
            assert len(selected_files) == 1
            assert selected_files[0]["name"] == path.name
            assert selected_files[0]["size"] == path.stat().st_size

    def upload_report(self, section_name, file_path):
        self.set_text(self.SECTION_NAME, section_name)

        actual_name = self.visible(
            self.SECTION_NAME
        ).get_property("value")

        assert actual_name == section_name, (
            f"Section Name was not entered correctly: {actual_name!r}"
        )

        self.set_text(self.REPORT_SEARCH, "")
        self.upload_file(self.REPORT_UPLOAD, file_path)

        try:
            return self.wait_for_report(section_name)

        except TimeoutException as error:
            screenshot = Path("screenshots/job_report_upload_failed.png")
            screenshot.parent.mkdir(parents=True, exist_ok=True)
            self.driver.save_screenshot(str(screenshot))

            popup_messages = [
                element.text.strip()
                for element in self.driver.find_elements(
                    *self.POPUP_MESSAGE
                )
                if element.is_displayed()
            ]
            report_rows = [
                row.text.strip()
                for row in self.driver.find_elements(*self.REPORT_ROWS)
                if row.is_displayed()
            ]

            raise AssertionError(
                "Uploaded report could not be verified.\n"
                f"Expected Section: {section_name!r}\n"
                f"Visible popup messages: {popup_messages!r}\n"
                f"Visible report rows: {report_rows!r}\n"
                f"Screenshot: {screenshot.resolve()}"
            ) from error

    def wait_for_report(self, section_name, order=None):
        def read_report(driver):
            try:
                matches = []

                for row in driver.find_elements(*self.REPORT_ROWS):
                    if not row.is_displayed():
                        continue

                    cells = row.find_elements(By.TAG_NAME, "td")

                    if (
                        cells
                        and cells[0].text.strip() == section_name
                    ):
                        matches.append(row)

                if not matches:
                    return False

                assert len(matches) == 1, (
                    f"Multiple reports found: {section_name}"
                )

                row = matches[0]
                link = row.find_element(
                    By.CSS_SELECTOR,
                    "a[ng-click='AddInspFileView(J)']",
                )
                order_field = row.find_element(
                    By.CSS_SELECTOR,
                    "input[ng-model='J.FileOrder']",
                )

                if not link.is_displayed():
                    return False

                actual_order = order_field.get_property("value")

                if (
                    order is not None
                    and actual_order != str(order)
                ):
                    return False

                return {
                    "section": section_name,
                    "link_text": link.text.strip(),
                    "order": actual_order,
                }

            except self.RETRY_ERRORS:
                return False

        return self.wait.until(
            read_report,
            message=(
                "Report missing or values did not match: "
                f"{section_name}"
            ),
        )

    def upload_contract(self, file_path):
        self.upload_file(self.CONTRACT_UPLOAD, file_path)

        def read_attachment_name(driver):
            try:
                for link in driver.find_elements(*self.CONTRACT_LINK):
                    if link.is_displayed() and link.text.strip():
                        return link.text.strip()

                return False

            except StaleElementReferenceException:
                return False

        return self.wait.until(
            read_attachment_name,
            message=(
                "Contract PDF was selected, but its attachment "
                "link did not show a filename."
            ),
        )

    def search(self, job_number):
        self.set_text(self.SEARCH, job_number)
        self.click(self.SEARCH_BUTTON)

    def matching_rows(self, job_number):
        matches = []

        for row in self.driver.find_elements(*self.ROWS):
            if not row.is_displayed():
                continue

            cells = row.find_elements(By.TAG_NAME, "td")

            if cells and cells[0].text.strip() == job_number:
                matches.append(row)

        return matches

    def get_job_grid_details(self, job_number):
        def read(driver):
            try:
                if self.loading_visible(driver):
                    return False

                rows = self.matching_rows(job_number)

                if not rows:
                    return False

                assert len(rows) == 1, (
                    f"Multiple Jobs found: {job_number}"
                )

                row = rows[0]
                cells = row.find_elements(By.TAG_NAME, "td")

                if len(cells) < 6:
                    return False

                paid_status_cells = row.find_elements(
                    By.CSS_SELECTOR,
                    "span[ng-bind='J.PaidStatus']",
                )

                # Keep blank values blank so the test reports the mismatch.
                paid_status = (
                    paid_status_cells[0].text.strip()
                    if paid_status_cells
                    else "<Paid Status column missing>"
                )

                return {
                    "number": cells[0].text.strip(),
                    "description": cells[1].text.strip(),
                    "inspectors": sorted(
                        name.strip()
                        for name in cells[2].text.split(",")
                        if name.strip()
                    ),
                    "inspection_date": cells[3].text.strip(),
                    "client": cells[4].text.strip(),
                    "rig": cells[5].text.strip(),
                    "paid_status": paid_status,
                }

            except self.RETRY_ERRORS:
                return False

        return self.wait.until(
            read,
            message=f"Job row unavailable: {job_number}",
        )

    def wait_for_job_details(self, expected):
        def matches(driver):
            actual = self.get_job_grid_details(expected["number"])

            if all(
                actual.get(key) == value
                for key, value in expected.items()
            ):
                return {
                    key: actual[key]
                    for key in expected
                }

            return False

        return self.wait.until(
            matches,
            message=(
                f"Saved Job grid values did not match: {expected}"
            ),
        )

    def edit(self, job_number):
        self.close_datepicker()

        def attempt(driver):
            try:
                if self.loading_visible(driver):
                    return False

                rows = self.matching_rows(job_number)

                if not rows:
                    return False

                assert len(rows) == 1, (
                    f"Multiple Jobs found: {job_number}"
                )

                action = rows[0].find_element(
                    By.CSS_SELECTOR,
                    "span[title='Edit Record']",
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
            message=f"Could not edit Job: {job_number}",
        )

        def correct_form_open(driver):
            try:
                field = driver.find_element(*self.NUMBER)
                return (
                    field.is_displayed()
                    and field.get_property("value") == job_number
                )
            except self.RETRY_ERRORS:
                return False

        self.wait.until(
            correct_form_open,
            message=f"Edit form did not open for Job: {job_number}",
        )

    def read_field(self, key):
        text_fields = {
            "number": self.NUMBER,
            "description": self.DESCRIPTION,
            "inspection_date": self.INSPECTION_DATE,
            "next_inspection": self.NEXT_INSPECTION,
            **self.OPTIONAL_TEXT_FIELDS,
        }
        select_fields = {
            "status": self.STATUS,
            "stage": self.STAGE,
            "client": self.CLIENT,
            "rig": self.RIG,
            **self.OPTIONAL_SELECT_FIELDS,
        }
        checkboxes = {
            "ongoing_access": self.ONGOING_ACCESS,
            "auto_reference": self.AUTO_REFERENCE,
        }

        if key in text_fields:
            return self.visible(
                text_fields[key]
            ).get_property("value")

        if key in select_fields:
            return Select(
                self.visible(select_fields[key])
            ).first_selected_option.text.strip()

        if key in checkboxes:
            return self.visible(checkboxes[key]).is_selected()

        raise KeyError(f"Unknown Job field: {key}")

    def get_form_details(self):
        keys = (
            "number",
            "description",
            "inspection_date",
            "next_inspection",
            "status",
            "stage",
            "client",
            "rig",
            "ongoing_access",
            "auto_reference",
        )

        return {
            key: self.read_field(key)
            for key in keys
        }

    def wait_for_form_details(self, expected):
        def read_details(driver):
            try:
                actual = {
                    key: self.read_field(key)
                    for key in expected
                }
                return actual if actual == expected else False

            except self.RETRY_ERRORS:
                return False

        return self.wait.until(
            read_details,
            message=(
                f"Reopened Job form values did not match: {expected}"
            ),
        )