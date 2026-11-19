import csv
import json

from pathlib import Path
from uuid import uuid4

import pytest

from pages.item_type_page import ItemTypePage
from tests import test_item_types
from tests import test_rigs


class CompleteFlowChecks(test_item_types.ItemTypeChecks):
    def __init__(self, driver):
        self.driver = driver
        self.rows = []
        self.saved = False

        self.folder = (
            Path("reports")
            / f"complete_flow_{uuid4().hex[:12]}"
        )
        self.folder.mkdir(parents=True, exist_ok=True)

    def save_report(self):
        json_path = self.folder / "field_results.json"
        csv_path = self.folder / "field_results.csv"

        json_path.write_text(
            json.dumps(self.rows, indent=2, default=str),
            encoding="utf-8",
        )

        with csv_path.open(
            "w",
            newline="",
            encoding="utf-8-sig",
        ) as stream:
            writer = csv.DictWriter(
                stream,
                fieldnames=[
                    "check",
                    "expected",
                    "actual",
                    "result",
                    "error",
                    "screenshot",
                ],
            )

            writer.writeheader()
            writer.writerows(self.rows)

        self.saved = True

    def finish(self):
        # Individual modules call finish().
        # Save their results and continue to the next module.
        self.save_report()

    def final_result(self):
        self.save_report()

        failures = [
            row
            for row in self.rows
            if row["result"] == "FAIL"
        ]
        passed_count = len(self.rows) - len(failures)

        print("\nComplete flow reached its final step.")
        print(
            f"Collected checks: {passed_count} passed; "
            f"{len(failures)} failed."
        )
        print(
            "Detailed results: "
            f"{(self.folder / 'field_results.csv').resolve()}"
        )

        if failures:
            summary = "\n".join(
                f"- {row['check']}: "
                f"expected={row['expected']!r}; "
                f"actual={row['actual']!r}"
                for row in failures
            )

            pytest.fail(
                f"Complete flow verification failures:\n{summary}",
                pytrace=False,
            )


@pytest.fixture
def complete_checks(driver):
    checks = CompleteFlowChecks(driver)

    try:
        yield checks

    finally:
        # Preserve evidence if a blocking step interrupts the flow.
        if not checks.saved:
            checks.save_report()

        print(f"\nComplete flow report folder: {checks.folder.resolve()}")


def test_complete_flow(
    driver,
    complete_checks,
    monkeypatch,
):
    checks = complete_checks

    print("\nStarting complete DROPS automation flow.")

    # This existing flow performs the only login.
    # It retains the Client, Rig, Inspector, Certificate and Job.
    print(
        "\nSTAGE 1: Login, Client, Rig hierarchy, "
        "Inspector, Certificate and Job"
    )

    test_rigs.test_client_to_rig_flow(
        driver,
        checks,
    )

    def open_item_types_in_current_session(current_driver):
        assert current_driver is driver, (
            "Complete flow must use the same browser session."
        )

        page = ItemTypePage(current_driver)
        page.open()
        return page

    # Reuse the existing Item Type tests while skipping their login helper.
    # The replacement applies only inside this context.
    with monkeypatch.context() as patch:
        patch.setattr(
            test_item_types,
            "login_to_item_types",
            open_item_types_in_current_session,
        )

        print(
            "\nSTAGE 2: Item Type, Checklist, Standard Reference "
            "and disposable record deletion"
        )

        test_item_types.test_item_type_lifecycle(
            driver,
            checks,
        )

        print("\nSTAGE 3: Same-name Item Type submission")

        test_item_types.test_same_item_type_name_updates_prompts(
            driver,
            checks,
        )

    # Raise collected verification failures only after all stages finish.
    checks.final_result()