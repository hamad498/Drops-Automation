from selenium.webdriver.common.by import By

from pages.base_page import BasePage


class AdminDashboardPage(BasePage):
    HEADING = (By.XPATH, "//h1[normalize-space()='Admin Dashboard']")

    def get_heading_text(self):
        heading = self.wait_for_visible(self.HEADING)
        return heading.text