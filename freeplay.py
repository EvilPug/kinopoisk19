import os

import time
import pickle
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

import config as c


driver = webdriver.Chrome(options=c.opts,
                          service=Service(ChromeDriverManager().install()))
driver.maximize_window()
driver.get(c.kp_url)

cookies = pickle.load(open('cookies/juliana.pkl', "rb"))
for cookie in cookies:
    driver.add_cookie(cookie)

driver.get(c.kp_url)

time.sleep(1000000)

