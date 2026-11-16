import pytest
from selenium import webdriver


@pytest.fixture
def driver():
    browser = webdriver.Chrome()

    try:
        browser.maximize_window()
        yield browser
    finally:
        browser.quit()