from selenium.common.exceptions import (
    ElementClickInterceptedException,
    NoSuchElementException,
    StaleElementReferenceException,
)
from selenium.webdriver.common.keys import Keys
from pathlib import Path

from selenium.common.exceptions import (
    ElementClickInterceptedException,
    NoSuchElementException,
    StaleElementReferenceException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select

from pages.base_page import BasePage


class JobPage(BasePage):
    MENU = (By.CSS_SELECTOR, "a[ng-click='LoadJobGrid()']")
    ADD = (By.CSS_SELECTOR, "button[ng-click='LoadJobAdminView()']")
    SAVE = (
        By.CSS_SELECTOR,
        "button[type='submit'][ng-disabled='JobForm.$invalid']",
    )

    NUMBER = (By.CSS_SELECTOR, "input[ng-model='JobControls.JobNumber']")
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
    REPORT_SEARCH = (By.CSS_SELECTOR, "input[ng-model='SFilter']")
    REPORT_ROWS = (
        By.XPATH,
        "//tr[td//span[@ng-bind='J.SectionName']]",
    )
    

    CONTRACT_UPLOAD = (By.ID, "PdfInp")
    CONTRACT_LINK = (By.CSS_SELECTOR, "a#Pdftextbox")

    SEARCH = (By.CSS_SELECTOR, "input[ng-model='SearchWord']")
    SEARCH_BUTTON = (
        By.CSS_SELECTOR,
        "button[ng-click='GetJobSearch()']",
    )
    ROWS = (By.CSS_SELECTOR, "tr[ng-repeat='J in JobData']")

    POPUP_MESSAGE = (By.CSS_SELECTOR, ".sweet-alert.visible > p")
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

    def click(self, locator):
        def attempt(driver):
            try:
                element = driver.find_element(*locator)

                if not element.is_displayed() or not element.is_enabled():
                    return False

                driver.execute_script(
                    """
                    arguments[0].scrollIntoView({
                        block: 'center',
                        inline: 'nearest',
                        behavior: 'instant'
                    });
                    """,
                    element,
                )

                element.click()
                return True

            except self.RETRY_ERRORS:
                return False

        self.wait.until(
            attempt,
            message=f"Could not click: {locator}",
        )

    def set_text(self, locator, value):
        from selenium.common.exceptions import TimeoutException

        value = str(value)
        last_issue = {"detail": "Field was not ready."}

        def attempt(driver):
            try:
                fields = driver.find_elements(*locator)
                visible_fields = [
                    field for field in fields
                    if field.is_displayed()
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

                driver.execute_script(
                    """
                    arguments[0].scrollIntoView({
                        block: 'center',
                        inline: 'nearest',
                        behavior: 'instant'
                    });
                    """,
                    field,
                )

                field.click()
                field.send_keys(Keys.CONTROL, "a")
                field.send_keys(Keys.BACKSPACE)

                if value:
                    field.send_keys(value)

                field.send_keys(Keys.TAB)

                actual = field.get_property("value")
                last_issue["detail"] = f"Actual field value: {actual!r}"
                return actual == value

            except self.RETRY_ERRORS as error:
                last_issue["detail"] = (
                    f"{type(error).__name__}: {str(error).split('Stacktrace:')[0]}"
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

                assert len(matching) == 1, (
                    f"Multiple dropdown options found: {text}"
                )

                dropdown.select_by_visible_text(text)
                return dropdown.first_selected_option.text.strip() == text
            except self.RETRY_ERRORS:
                return False

        self.wait.until(
            attempt,
            message=f"Dropdown option unavailable: {text} in {locator}",
        )

    def set_checkbox(self, locator, checked):
        def attempt(driver):
            try:
                checkbox = driver.find_element(*locator)
                if not checkbox.is_displayed() or not checkbox.is_enabled():
                    return False

                if checkbox.is_selected() != checked:
                    checkbox.click()

                return checkbox.is_selected() == checked
            except self.RETRY_ERRORS:
                return False

        self.wait.until(attempt, message=f"Could not set checkbox: {locator}")

    def open(self):
        from selenium.common.exceptions import TimeoutException

        try:
            self.click(self.MENU)
        except TimeoutException as error:
            screenshot = Path("screenshots/jobs_menu_blocked.png")
            screenshot.parent.mkdir(parents=True, exist_ok=True)
            self.driver.save_screenshot(str(screenshot))

            details = self.driver.execute_script(
                """
                const links = Array.from(document.querySelectorAll(
                    "a[ng-click='LoadJobGrid()']"
                ));

                return links.map(link => {
                    const rect = link.getBoundingClientRect();
                    const x = Math.max(
                        0, Math.min(innerWidth - 1, rect.x + rect.width / 2)
                    );
                    const y = Math.max(
                        0, Math.min(innerHeight - 1, rect.y + rect.height / 2)
                    );
                    const top = document.elementFromPoint(x, y);

                    return {
                        text: link.innerText,
                        width: rect.width,
                        height: rect.height,
                        coveringElement: top ? top.outerHTML.slice(0, 600) : null
                    };
                });
                """
            )

            messages = [
                element.text.strip()
                for element in self.driver.find_elements(
                    *self.POPUP_MESSAGE
                )
                if element.is_displayed()
            ]

            raise AssertionError(
                f"Jobs List navigation failed after Update.\n"
                f"Menu details: {details}\n"
                f"Visible popup messages: {messages}\n"
                f"Screenshot: {screenshot.resolve()}"
            ) from error

        self.visible(self.ADD)
        self.visible(self.SEARCH)

    def open_add_form(self):
        self.click(self.ADD)
        self.wait.until(
            lambda driver: self.visible(self.NUMBER).get_property("value") == ""
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

    def save_and_assign(self):
        self.click(self.SAVE)

        def saved_form_ready(driver):
            try:
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
            message="Job did not reach the Update / Inspector assignment form.",
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
                    if row.is_displayed():
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
            fields = driver.find_elements(*locator)

            # File input hidden ho sakta hai; uska upload button visible ho.
            active_fields = [
                field
                for field in fields
                if field.is_enabled()
                and field.find_element(By.XPATH, "..").is_displayed()
            ]

            if len(active_fields) == 1:
                return active_fields[0]

            if len(active_fields) > 1:
                raise AssertionError(
                    f"Multiple active upload inputs found: {locator}"
                )

            return False

        field = self.wait.until(
            find_upload_input,
            message=f"No active upload input found: {locator}",
        )

        field.send_keys(str(path))

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

        print(f"Upload input: {locator}")
        print(f"Selected files: {selected_files}")

        # Kuch upload handlers processing ke baad input reset kar dete hain.
        # Is liye actual success ko report row/link se verify karte hain.
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

        # Clear any report filter before looking for the uploaded row.
        self.set_text(self.REPORT_SEARCH, "")

        self.upload_file(self.REPORT_UPLOAD, file_path)

        from selenium.common.exceptions import TimeoutException

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
                f"Uploaded report could not be verified.\n"
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
                    if cells and cells[0].text.strip() == section_name:
                        matches.append(row)

                if not matches:
                    return False

                assert len(matches) == 1, (
                    f"Multiple reports found: {section_name}"
                )

                row = matches[0]
                link = row.find_element(
                    By.CSS_SELECTOR, "a[ng-click='AddInspFileView(J)']"
                )
                order_field = row.find_element(
                    By.CSS_SELECTOR, "input[ng-model='J.FileOrder']"
                )

                if not link.is_displayed():
                    return False

                actual_order = order_field.get_property("value")
                if order is not None and actual_order != str(order):
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
            message=f"Report missing or values did not match: {section_name}",
        )

    def upload_contract(self, file_path):
        self.upload_file(self.CONTRACT_UPLOAD, file_path)

        def read_attachment_name(driver):
            try:
                for link in driver.find_elements(*self.CONTRACT_LINK):
                    if link.is_displayed():
                        text = link.text.strip()
                        if text:
                            return text

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

    def wait_for_job_details(self, expected):
        def read_details(driver):
            try:
                rows = self.matching_rows(expected["number"])
                if not rows:
                    return False

                assert len(rows) == 1, (
                    f"Multiple Jobs found: {expected['number']}"
                )

                cells = rows[0].find_elements(By.TAG_NAME, "td")
                if len(cells) < 6:
                    return False

                actual = {
                    "number": cells[0].text.strip(),
                    "description": cells[1].text.strip(),
                    "inspectors": [
                        name.strip()
                        for name in cells[2].text.split(",")
                        if name.strip()
                    ],
                    "inspection_date": cells[3].text.strip(),
                    "client": cells[4].text.strip(),
                    "rig": cells[5].text.strip(),
                }

                if actual == expected:
                    return actual
                return False
            except StaleElementReferenceException:
                return False

        return self.wait.until(
            read_details,
            message=f"Saved Job grid values did not match: {expected}",
        )

    def edit(self, job_number):
        def attempt(driver):
            try:
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

                if not action.is_displayed() or not action.is_enabled():
                    return False

                driver.execute_script(
                    """
                    arguments[0].scrollIntoView({
                        block: 'center',
                        inline: 'nearest',
                        behavior: 'instant'
                    });
                    """,
                    action,
                )

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

    def get_form_details(self):
        return {
            "number": self.visible(self.NUMBER).get_property("value"),
            "description": self.visible(self.DESCRIPTION).get_property("value"),
            "inspection_date": (
                self.visible(self.INSPECTION_DATE).get_property("value")
            ),
            "next_inspection": (
                self.visible(self.NEXT_INSPECTION).get_property("value")
            ),
            "status": Select(
                self.visible(self.STATUS)
            ).first_selected_option.text.strip(),
            "stage": Select(
                self.visible(self.STAGE)
            ).first_selected_option.text.strip(),
            "client": Select(
                self.visible(self.CLIENT)
            ).first_selected_option.text.strip(),
            "rig": Select(
                self.visible(self.RIG)
            ).first_selected_option.text.strip(),
            "ongoing_access": self.visible(self.ONGOING_ACCESS).is_selected(),
            "auto_reference": self.visible(self.AUTO_REFERENCE).is_selected(),
        }

    def wait_for_form_details(self, expected):
        def read_details(driver):
            try:
                actual = self.get_form_details()
                return actual if actual == expected else False
            except self.RETRY_ERRORS:
                return False

        return self.wait.until(
            read_details,
            message=f"Reopened Job form values did not match: {expected}",
        )