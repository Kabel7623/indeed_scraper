import pandas as pd
import time
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup

def scrape_with_selenium_and_bs4(job_title, location, num_pages):
    """
    Scrapes job listings by controlling an already running Chrome browser
    (started with --remote-debugging-port=9222) and parsing the HTML with BeautifulSoup.
    """

    # Attach to running Chrome
    options = webdriver.ChromeOptions()
    options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")  

    try:
        driver = webdriver.Chrome(options=options)
    except Exception as e:
        print("\n❌ Error attaching to running Chrome. Make sure you started Chrome with:")
        print("   chrome.exe --remote-debugging-port=9222 --user-data-dir=C:\\selenium\\chrome-profile")
        print(f"Error details: {e}")
        return pd.DataFrame()

    all_jobs_data = []
    
    print(f"\n🚀 Starting scrape for '{job_title}' in '{location}' for {num_pages} page(s)...")

    # Construct the initial URL
    search_url = f"https://in.indeed.com/jobs?q={job_title.replace(' ', '+')}&l={location.replace(' ', '+')}"
    driver.get(search_url)

    for page in range(num_pages):
        print(f"\n📄 Scraping page {page + 1}...")
        
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.ID, "mosaic-provider-jobcards"))
            )
            job_cards = driver.find_elements(By.CLASS_NAME, "job_seen_beacon")
            
            if not job_cards:
                print("No job cards found on this page.")
                break

            for card in job_cards:
                try:
                    driver.execute_script("arguments[0].scrollIntoView(true);", card)
                    time.sleep(random.uniform(0.5, 1.5))
                    card.click()
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.ID, "jobsearch-ViewjobPaneWrapper"))
                    )
                except Exception as e:
                    print(f"   - Warning: Could not click job card or pane did not load. Skipping. Details: {e}")
                    continue
                
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                
                job_pane = soup.find('div', id='jobsearch-ViewjobPaneWrapper')
                if not job_pane:
                    print("   - Warning: Could not find job pane in parsed HTML. Skipping.")
                    continue

                job_data = {}
                
                title_tag = job_pane.find('h2', class_=lambda x: x and 'jobsearch-JobInfoHeader-title' in x)
                company_tag = job_pane.find('div', {'data-testid': 'inlineHeader-companyName'})
                location_tag = job_pane.find('div', {'data-testid': 'inlineHeader-companyLocation'})
                description_tag = job_pane.find('div', id='jobDescriptionText')
                salary_tag = job_pane.find('div', id='salaryInfoAndJobType')
                
                # --- Robust date finder ---
                date_posted_text = "N/A"
                date_posted_tag = job_pane.find('span', {'data-testid': 'job-age'})
                if date_posted_tag:
                    date_posted_text = date_posted_tag.get_text(strip=True)
                else:
                    footer = soup.find('div', class_='jobsearch-JobMetadataFooter')
                    if footer:
                        date_div = footer.find('div', string=lambda text: text and any(keyword in text for keyword in ['ago', 'Posted', 'Just posted']))
                        if date_div:
                            date_posted_text = date_div.get_text(strip=True)

                job_data['title'] = title_tag.get_text(strip=True).replace('- job post', '') if title_tag else "N/A"
                job_data['company'] = company_tag.get_text(strip=True) if company_tag else "N/A"
                job_data['location'] = location_tag.get_text(strip=True) if location_tag else "N/A"
                job_data['date_posted'] = date_posted_text
                job_data['description'] = description_tag.get_text(separator='\n', strip=True) if description_tag else "N/A"
                job_data['salary'] = salary_tag.get_text(strip=True) if salary_tag else "Not specified"
                job_data['url'] = driver.current_url

                all_jobs_data.append(job_data)
                print(f"  ✅ Scraped: {job_data['title']} at {job_data['company']}")

            if page < num_pages - 1:
                try:
                    next_button = driver.find_element(By.CSS_SELECTOR, "[data-testid='pagination-page-next']")
                    next_button.click()
                except NoSuchElementException:
                    print("No 'Next' button found. Reached the last page.")
                    break

        except TimeoutException:
            print(f"Timed out waiting for job cards on page {page + 1}.")
            break
        except Exception as e:
            print(f"An unexpected error occurred on page {page + 1}: {e}")
            break

    driver.quit()
    print("\n🏁 Scraping finished.")
    
    if not all_jobs_data:
        print("No data was scraped.")
        return pd.DataFrame()
        
    return pd.DataFrame(all_jobs_data)

if __name__ == "__main__":
    print("--- Indeed Job Scraper ---")
    job_title_input = input("▶ Enter the job title to search for (e.g., Data Analyst): ")
    location_input = input("▶ Enter the location (e.g., Bengaluru, Remote): ")
    
    while True:
        try:
            pages_input = int(input("▶ Enter the number of pages to scrape: "))
            if pages_input > 0:
                break
            else:
                print("Please enter a number greater than 0.")
        except ValueError:
            print("Invalid input. Please enter a whole number.")

    job_df = scrape_with_selenium_and_bs4(job_title_input, location_input, pages_input)

    if not job_df.empty:
        filename_base = f"{job_title_input.replace(' ', '')}{location_input.replace(' ', '_')}"
        
        print("\n💾 Saving data to files...")
        
        csv_file = f"{filename_base}.csv"
        job_df.to_csv(csv_file, index=False, encoding='utf-8')
        print(f"   -> Data successfully saved to {csv_file}")
        
        json_file = f"{filename_base}.json"
        job_df.to_json(json_file, orient='records', indent=4, force_ascii=False)
        print(f"   -> Data successfully saved to {json_file}")
        
        excel_file = f"{filename_base}.xlsx"
        job_df.to_excel(excel_file, index=False)
        print(f"   -> Data successfully saved to {excel_file}")

# how to run
# step 1: in cmd go to the file path location ,here indeed scraper == (cd indeed-scraper)
# step 2: setup the vitual environment - (python -m venv venv)
# step 3: run the virtual environment - (venv\Scripts\activate)
# step 4 : open the chrome location to run - ("C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\selenium\chrome-profile"
# )
# step 5 : python  scraper.py