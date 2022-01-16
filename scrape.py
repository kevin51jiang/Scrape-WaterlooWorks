#!/usr/bin/python3

from bs4 import BeautifulSoup
import getpass
import re
from pick import pick
import os
import time
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException

def main():
    # Get user login information
    username = input("Username: ")
    password = getpass.getpass("Password: ")
    headless = input("Headless? (Y/N): ").rstrip().lstrip()
    yes = ["Yes", "Y", "YES", "y", "yes"]

    # monk user input
    # username = ''
    # password = ''

    # default co-op url
    posting_url = "http://waterlooworks.uwaterloo.ca/myAccount/co-op/coop-postings.htm"
    dashboard_url = "https://waterlooworks.uwaterloo.ca/myAccount/dashboard.htm"
    login_url = 'https://waterlooworks.uwaterloo.ca/'
    output_name = 'output.csv'

    # start selenium in chromium 
    chrome_options = webdriver.chrome.options.Options()
    if (headless in yes):
        print("Headless")
        chrome_options.add_argument("--headless") 

    if os.path.exists("./chromedriver"):
        browser = webdriver.Chrome(executable_path="./chromedriver", chrome_options=chrome_options)
    else:
        browser = webdriver.Chrome(options=chrome_options)

    main_page_html = login(username, password, login_url, dashboard_url, posting_url, browser)
    if (not main_page_html):
        print("ERROR: Duo 2FA timed out")
        return 10

    # get quick search options from main page content
    quick_search_options = get_quick_search_options(main_page_html)

    # If the options list is empty, either the login did not work or there are no available jobs to scrape
    if (not quick_search_options):
        print("ERROR: login unsuccessful (NO JOBS FOUND)")
        return 10

    choice = prompt_quick_search(quick_search_options)

    # mock user promt
    # choice = 'For My Program'
    

    # peek the first page of the quick search page, get the token and page count and save all data to the output
    data = get_job_lists(choice, browser, output_name)

    print("Done!")


def login(username, password, login_url, dashboard_url, posting_url, browser):
    # go to login page
    browser.get(login_url)
    browser.find_element_by_class_name("btn--landing").click()

    # get username and password fields
    user_field = browser.find_element_by_id("userNameInput") #username form field
    pass_field = browser.find_element_by_id("passwordInput") #password form field

    # log in
    user_field.send_keys(username + "@uwaterloo.ca")
    browser.find_element_by_id("nextButton").click()
    pass_field.send_keys(password)
    browser.find_element_by_id("submitButton").click()

    # wait for 2FA to finish
    print("Please authenticate using Duo 2FA")
    try:
        WebDriverWait(browser, 120).until(
                lambda browser: browser.current_url == dashboard_url)
    except TimeoutException:
        return None

    browser.get(posting_url) #navigate to coop posting page
    # wait for javascript to run then grab page contents
    time.sleep(3)
    return repr(browser.execute_script("return document.body.innerHTML")) #returns the inner HTML

def get_quick_search_options(main_page_html):

        print("Getting options...")

        # Only get the options that has jobs, exclude those that have 0 job.
        # pattern = r'<td class="full"><a href=".+?:\\\'(.+?)\\\'.+?">(.+?)<\/a><\/td>'     # THIS PATTERN IS WRONG
        pattern = r'<td class="full"><a href=".+?:.+?" onclick=(.+?)>(.+?)<\/a><\/td>'
        
        results = re.findall(pattern, main_page_html)

        quick_search_options = {}
        for result in results:
            key = "".join(re.findall(r'(?<!\\)(?:\w|\s)', result[1])).lstrip().rstrip()
            quick_search_options[key] = result[0]

        return quick_search_options

def prompt_quick_search(quick_search_options):
    message = "Which quick search do you want to crawl? "
    choices = list(quick_search_options)
    choice, index = pick(choices, message)
    return choice

def get_job_lists(choice, browser, output_name):
    
    print("Getting job lists ...")

    # Navigate to the job listings page then wait for the javascript to load
    browser.find_element_by_link_text(choice).click()

    # Get the HTML of the page and check if this is the last page (next_page_buttons)
    page_html = browser.execute_script("return document.body.innerHTML")
    pattern = r'<a href=".+?" onclick="loadPostingTable(.+?)">\s*»\s*<\/a>'
    next_page_buttons = []
    next_page_buttons = re.findall(pattern, page_html)

    # dots for loading screen
    dots = ""

    # Scrape the tables and save it to output_name as a CSV

    with open(output_name, 'w') as f:
        while (next_page_buttons):
            
            # loading screen stuff
            print("Working" + dots)
            # update dots
            if (dots == "..."):
                dots = ""
            else:
                dots += "."

            # wait for JavaScript to load then download the page info
            time.sleep(2)
            soup = BeautifulSoup(page_html, "html.parser")

            for tr in soup.find_all('tr')[2:]:
                tds = tr.find_all('td')
                for x in tds[2:]:
                    f.write( ' '.join(x.text.split()).replace(',', ' ') + ","),
                f.write("\n")

            # navigate to the next page and get the HTML, next page buttons
            browser.find_element_by_link_text("»").click()

            page_html = browser.execute_script("return document.body.innerHTML")
            next_page_buttons = re.findall(pattern, page_html)


if __name__ == "__main__":
    main()

