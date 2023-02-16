import re
import time
import pickle
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.wait import WebDriverWait

# Selenium Config
opts = Options()
agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 ' \
        'Safari/537.36'
opts.add_argument(f"user-agent={agent}")
opts.add_argument('log-level=3')

driver = webdriver.Chrome(options=opts, service=Service(ChromeDriverManager().install()))
driver.maximize_window()
kinopoisk_url = 'https://www.kinopoisk.ru/special/birthday19/'


driver.get(kinopoisk_url)
xpath_expr = "//button[contains(text(),'Играть') or contains(text(),'Новый эпизод')]"
elements = WebDriverWait(driver, timeout=800, poll_frequency=1).until(lambda d: d.find_elements(By.XPATH, xpath_expr))

pickle.dump(driver.get_cookies(), open("cookies.pkl", "wb"))

driver.quit()
