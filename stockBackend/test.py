import json
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common import NoSuchElementException, ElementNotInteractableException
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By

def get_stock_data(symbol):
    start_time = time.time()  # Record the start time
    url = f'https://finance.yahoo.com/quote/{symbol}'
    response = requests.get(url)
    end_time = time.time()  # Record the end time

    soup = BeautifulSoup(response.text, 'html.parser')
    # Example: Extracting the current stock price

    stock_price_after_hour = soup.find(attrs={'data-symbol': symbol, 'data-field': 'postMarketPrice'})
    stock_price_regular = soup.find(attrs={'data-symbol': symbol, 'data-field': 'regularMarketPrice'})
    if stock_price_after_hour is not None:
        stock_price = stock_price_after_hour.text
    else:
        stock_price = stock_price_regular.text
    return stock_price


def get_news_text_from_url(url, driver: WebDriver):
    # Load the page
    driver.get(url)
    button_xpath = '//*[@id="consent-page"]/div/div/div/form/div[2]/div[2]/button[2]'
    try:
        time.sleep(1)
        button_element = driver.find_element(By.CLASS_NAME, 'reject-all')
        # Click the button
        button_element.click()
    except NoSuchElementException:
        pass

    try:
        while True:
            button_element = driver.find_element(By.CLASS_NAME, 'collapse-button')
            button_element.click()

    except (NoSuchElementException, ElementNotInteractableException):
        pass

    # Locate the time element using its XPath
    time_element = driver.find_element(By.CSS_SELECTOR, 'time[datetime]')
    datetime_str = time_element.get_attribute('datetime')
    python_datetime = datetime.strptime(datetime_str, '%Y-%m-%dT%H:%M:%S.%fZ')

    article_element = driver.find_element(By.CLASS_NAME, 'caas-body')

    data = article_element.text

    # Close the browser
    return data, python_datetime


def scrape_stock_news(symbol, url):
    options = webdriver.ChromeOptions()
    #options.add_argument('--headless')
    options.add_argument('--ignore-ssl-errors=yes')
    options.add_argument('--ignore-certificate-errors')

    driver = webdriver.Remote(
        command_executor=f'http://{url}:4444/wd/hub',
        options=options
    )
    # Replace 'AAPL' with the desired stock symbol
    url = f'https://finance.yahoo.com/quote/{symbol}'

    html = BeautifulSoup(requests.get(url).text, 'html.parser')

    result = []
    for e in html.select(' div:has(>h3>a)'):
        try:
            a_tag = e.select_one('h3 > a')
            if a_tag:
                href = a_tag.get('href')
                news = get_news_text_from_url(f'https://finance.yahoo.com/{href}', driver)
                result.append({'title': e.h3.text, 'href': href, 'article': news[0], 'time': news[1]})
        except Exception as e:
            print(e)

    driver.quit()
    return result


#print(json.dumps(scrape_stock_news('SMCI'), default=str))
# print(get_news_text_from_url('https://finance.yahoo.com/video/tech-meta-truly-patek-philippe-130036883.html'))
