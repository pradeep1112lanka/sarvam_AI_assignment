import os
import zipfile
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from PIL import Image
import pytesseract
import time
import shutil

# Path to Tesseract executable
pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"  # Update as needed for your Linux installation

BASE_URL = "https://data.telangana.gov.in/search/"

# Set up Selenium WebDriver
def setup_selenium(download_dir):
    options = Options()
    options.add_argument("--headless")  # Run in headless mode
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-extensions")

    # Set custom download directory
    prefs = {"download.default_directory": download_dir}
    options.add_experimental_option("prefs", prefs)

    driver = webdriver.Chrome(options=options)
    return driver

# Extract dataset links from a single page
def extract_dataset_links(driver, page_number):
    page_url = f"{BASE_URL}?page={page_number}"
    driver.get(page_url)
    time.sleep(2)

    dataset_links = []
    dataset_elements = driver.find_elements(By.CSS_SELECTOR, ".dc-search-list-item h2 a")
    for item in dataset_elements:
        link = item.get_attribute("href")
        if link:
            dataset_links.append(link)
    
    return dataset_links

# Extract metadata and click the specific "Download" button
def extract_metadata_and_download(driver, dataset_link, output_dir, download_dir):
    driver.get(dataset_link)
    time.sleep(2)

    try:
        # Extract dataset name
        dataset_name = driver.find_element(By.TAG_NAME, 'h1').text.strip()
        dataset_folder = os.path.join(output_dir, dataset_name.replace(" ", "_").replace("/", "_"))
        os.makedirs(dataset_folder, exist_ok=True)

        # Extract metadata
        metadata_content = driver.find_element(By.CSS_SELECTOR, ".col-md-9.col-sm-12").text.strip()
        metadata_file_path = os.path.join(dataset_folder, f"{dataset_name}_metadata.txt")
        with open(metadata_file_path, "w", encoding="utf-8") as f:
            f.write(metadata_content)

        print(f"Metadata saved for {dataset_name}")

        # Find and click the "Download" button
        download_button = driver.find_element(By.XPATH, "//a[contains(text(),'Download')]")
        download_button.click()
        handle_download(driver, dataset_folder, download_dir)

        return dataset_folder
    except Exception as e:
        print(f"Error processing dataset: {e}")
        return None

# Solve CAPTCHA using OCR
def solve_captcha(captcha_image_path):
    image = Image.open(captcha_image_path)
    captcha_text = pytesseract.image_to_string(image).strip()
    return captcha_text

# Handle the download process after clicking "Download"
def handle_download(driver, dataset_folder, download_dir):
    try:
        # Wait for form to appear
        WebDriverWait(driver, 1).until(
            EC.presence_of_element_located((By.NAME, "Name"))
        )

        # Fill form fields automatically
        driver.find_element(By.NAME, "Name").send_keys("Pradeep")
        driver.find_element(By.NAME, "Email").send_keys("ee22b074@smail.iitm.ac.in")
        driver.find_element(By.NAME, "Purpose").send_keys("Research")

        # Select usage type (Non-commercial)
        usage_type = driver.find_elements(By.NAME, "type")
        for radio_button in usage_type:
            if radio_button.get_attribute('value') == 'non-commercial':
                radio_button.click()
                break

        # Solve CAPTCHA
        captcha_image = driver.find_element(By.CSS_SELECTOR, "img.captcha")
        captcha_path = os.path.join(dataset_folder, "captcha.png")
        captcha_image.screenshot(captcha_path)
        captcha_text = solve_captcha(captcha_path)

        driver.find_element(By.NAME, "captcha").send_keys(captcha_text)

        # Submit form
        driver.find_element(By.XPATH, "//button[contains(text(),'Download')]").click()
        time.sleep(10)  # Wait for download to complete

        print(f"Download initiated for {dataset_folder}")

        # Move the downloaded file to the dataset folder
        move_downloaded_files(download_dir, dataset_folder)
    except Exception as e:
        print(f"Error handling download: {e}")

# Move downloaded file to dataset folder
def move_downloaded_files(download_dir, dataset_folder):
    for file_name in os.listdir(download_dir):
        file_path = os.path.join(download_dir, file_name)
        if os.path.isfile(file_path):
            shutil.move(file_path, dataset_folder)
            print(f"Moved {file_name} to {dataset_folder}")

# Zip the entire dataset directory
def zip_dataset_folder(output_dir):
    zip_filename = f"{output_dir}.zip"
    with zipfile.ZipFile(zip_filename, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(output_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, output_dir)
                zipf.write(file_path, arcname)
    print(f"Zipped datasets into {zip_filename}")

# Process datasets and download them
def process_datasets(driver, dataset_links, output_dir, download_dir):
    for dataset_link in dataset_links:
        print(f"Processing dataset: {dataset_link}")
        dataset_folder = extract_metadata_and_download(driver, dataset_link, output_dir, download_dir)
        if not dataset_folder:
            print(f"Skipping dataset: {dataset_link}")

# Main function
def main():
    output_dir = "telanganadatasets"
    os.makedirs(output_dir, exist_ok=True)

    # Temporary download directory
    download_dir = os.path.join(output_dir, "temp_downloads")
    os.makedirs(download_dir, exist_ok=True)

    driver = setup_selenium(download_dir)
    all_dataset_links = []
    page_number = 1

    while page_number < 31:  # Adjust this to scrape multiple pages
        print(f"Processing page {page_number}")
        dataset_links = extract_dataset_links(driver, page_number)
        # if not dataset_links:
        #     break
        all_dataset_links.extend(dataset_links)
        page_number += 1
        if page_number==31:
            break
    # Process each dataset
    process_datasets(driver, all_dataset_links, output_dir, download_dir)

    driver.quit()

    # Clean up temporary download directory
    shutil.rmtree(download_dir)

    # Zip the dataset folder
    zip_dataset_folder(output_dir)

if __name__ == "__main__":
    main()
