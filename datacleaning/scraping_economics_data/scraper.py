import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import time

url = "https://tradingeconomics.com/commodities"

options = uc.ChromeOptions()
options.headless = False          # Set True later when it works
# options.add_argument("--start-maximized")

driver = uc.Chrome(options=options, version_main=None)  # auto-detects your Chrome version

try:
    driver.get(url)
    time.sleep(5)                    # Wait for AWS WAF challenge to solve itself
    
    # Optional: wait until real content loads
    driver.implicitly_wait(10)
    
    print("Page title:", driver.title)
    print("Current URL:", driver.current_url)
    
    # Save the real page
    html = driver.page_source
    with open("real_commodities.html", "w", encoding="utf-8") as f:
        f.write(html)
    
    print("✅ Success! Real page saved to real_commodities.html")
    
except Exception as e:
    print("Error:", e)
finally:
    time.sleep(3)   # keep browser open a bit so you can see
    # driver.quit()   # uncomment when you're done