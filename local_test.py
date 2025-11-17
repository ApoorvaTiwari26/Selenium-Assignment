from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service

import time
import requests
from collections import Counter
import re
import os

from dotenv import load_dotenv

# Load environment variables from the .env file 
load_dotenv()

# RapidAPI translation setup
url = "https://rapid-translate-multi-traduction.p.rapidapi.com/t"
headers = {
    "x-rapidapi-key": os.getenv("RAPID_API_KEY"),
    "x-rapidapi-host": "rapid-translate-multi-traduction.p.rapidapi.com",
    "Content-Type": "application/json"
}


def create_driver():
    """Create and return a WebDriver instance"""
    options = ChromeOptions()
    
    try:
        #Launching Chrome browser with options
        driver = webdriver.Chrome(options=options)
        return driver
    except Exception as e:
        print(f"Failed to create Chrome driver: {e}")
        raise e


def download_image(url, save_folder='images'):  #Grabs image from the web and save it locally
    try:
        response = requests.get(url)
        if response.status_code == 200:
            if not os.path.exists(save_folder):   ## Makes folder in the case it doesn’t exist
                os.makedirs(save_folder)
            image_name = os.path.join(save_folder, url.split('/')[-1].split('?')[0])  #Creating file name from URL
            with open(image_name, 'wb') as f:
                f.write(response.content)
            print(f"Image saved as {image_name}")
        else:
            print(f"Failed to retrieve image from {url}")
    except Exception as e:
        print(f"Error downloading image: {e}")


def get_best_image_url(src):  #Selects best quality image from the srcset attribute
    image_sources = src.split(',')
    sorted_sources = sorted(image_sources, key=lambda x: int(x.split()[-1][:-1]), reverse=True)  # Sort by width descending
    return sorted_sources[0].split()[0]


def translate_text(text, from_lang="es", to_lang="en"):  #Translates text using RapidAPI translation 
    payload = {"from": from_lang, "to": to_lang, "q": text}
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        translation = response.json()  #Extract translated text
        return translation[0]
    else:
        print(f"Translation API error: {response.status_code}")
        return None


def clean_and_tokenize(text):  #Cleans and tokenizes text
    text = text.lower()
    text = re.sub(r'[^a-z\s]', '', text)
    return text.split()


def test_elpais_scraping_local(driver):  #Main test function for scraping El Pais' opinion section
    wait = WebDriverWait(driver, 10)

    try:
        driver.maximize_window()
        driver.get("https://elpais.com/")
        time.sleep(5)

        lang_attr = driver.find_element(By.TAG_NAME, 'html').get_attribute('lang')   #Checks page language
        print(f"Page language detected: {lang_attr}")

        try:
            accept_btn = wait.until(EC.element_to_be_clickable((By.ID, 'didomi-notice-agree-button')))  #Accept cookies banner
            accept_btn.click()
        except:
            print("No accept banner")

        opinion_btn = wait.until(   #Navigate to opinion section
            EC.element_to_be_clickable((By.XPATH, '//a[@data-mrf-link="https://elpais.com/opinion/"]'))
        )
        opinion_btn.click()

        time.sleep(5)

        opinion_section = wait.until(   
            EC.visibility_of_element_located((By.XPATH, '//section[@data-dtm-region="portada_apertura"]'))
        )
        articles = opinion_section.find_elements(By.TAG_NAME, 'article')[:5]

        tc_dict = {}  #Title-content dictionary
        img_scr_list = []  #Image source list

        for article in articles:
            title = article.find_element(By.XPATH, './/h2').text
            content = article.find_element(By.XPATH, './/p').text
            tc_dict[title] = content

            try:
                img_srcset = article.find_element(By.TAG_NAME, 'img').get_attribute('srcset')  #Get image srcset
                if img_srcset:
                    img_scr_list.append(get_best_image_url(img_srcset))
            except:
                print(f"No image found for: {title}")

        print(tc_dict)
        print(f"Images found: {len(img_scr_list)} → {img_scr_list}")

        translated_titles = []  #Translates article titles
        for title in tc_dict.keys():
            t = translate_text(title)
            if t:
                translated_titles.append(t)

        print("Translated titles:", translated_titles)

        all_words = [] 
        for title in translated_titles:
            all_words.extend(clean_and_tokenize(title))

        word_counts = Counter(all_words)  #Counts repeated words
        repeated_words = {w: c for w, c in word_counts.items() if c >= 2}  

        print("Repeated words (>2):")
        for w, c in repeated_words.items():   
            print(f"{w}: {c}")

        for img_url in img_scr_list:  #Downloads images 
            download_image(img_url)

        print("Scraping test completed")

    except Exception as e:
        print(f"Test failed: {e}")
        raise e



if __name__ == "__main__":  #Run the test
    driver = create_driver()
    try:
        test_elpais_scraping_local(driver)
    finally:
        driver.quit()
