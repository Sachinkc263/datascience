import csv, time
from time import sleep
import undetected_chromedriver as uc
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

url = input("Enter the url of post to scrape:")

def get_full_text_with_emojis(driver, element):
    """Extracts full text including emojis from <img alt="😂"> tags inside the element"""
    return driver.execute_script("""
        function getTextWithEmojis(el) {
            let result = '';
            for (let node of el.childNodes) {
                if (node.nodeType === 3) {
                    // Text node
                    result += node.textContent;
                } else if (node.nodeType === 1) {
                    // Element node
                    if (node.tagName === 'IMG' && node.getAttribute('alt')) {
                        result += node.getAttribute('alt');
                    } else {
                        // Recurse into spans, divs, etc.
                        result += getTextWithEmojis(node);
                    }
                }
            }
            return result.trim();
        }
        return getTextWithEmojis(arguments[0]);
    """, element)
    
# Driver setup
options = uc.ChromeOptions()
version = 146

driver = uc.Chrome(options=options, version_main=version,use_subprocess=True)
driver.maximize_window()
wait = WebDriverWait(driver, 15)


driver.get(url)

# Get title
title = wait.until(
    EC.presence_of_element_located(
        (By.CSS_SELECTOR, '[style="text-align: start;"]')
    )
).text

print("Title:", title)

# open comment order menu
menu_button = wait.until(
    EC.element_to_be_clickable(
        (By.CSS_SELECTOR, '[aria-haspopup="menu"]')
    )
)

driver.execute_script(
    "arguments[0].scrollIntoView({block:'center'});",
    menu_button
)
menu_button.click()

all_comments = wait.until(
    EC.element_to_be_clickable(
        (By.XPATH, '//span[contains(text(),"All comments")]')
    )
)
all_comments.click()

sleep(2)

def scroll_comments_to_end(driver, waiit):

    dialog = wait.until(
        EC.presence_of_element_located(
            (By.XPATH, '(//div[@role="dialog"])[last()]')
        )
    )

    # find scroll container automatically
    scroll_box = driver.execute_script("""
        const dialog = arguments[0];
        const all = dialog.querySelectorAll("div");

        for (const el of all) {
            if (el.scrollHeight > el.clientHeight + 100) {
                return el;
            }
        }
        return null;
    """, dialog)

    if not scroll_box:
        raise Exception("Scroll container not found")

    print("Loading all comments + replies...")

    last_count = 0
    stable_rounds = 0

    while True:

        # -----------------------------
        # Expand replies + more comments
        # -----------------------------
        expand_buttons = driver.find_elements(
            By.XPATH,
            '''
            //div[@role="button"][.//span[contains(text(),"reply")]]
            |
            //div[@role="button"][.//span[contains(text(),"View")]]
            |
            //span[contains(text(),"View")]/ancestor::div[@role="button"]
            '''
        )

        for btn in expand_buttons:
            try:
                driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center'});",
                    btn
                )
                driver.execute_script("arguments[0].click();", btn)
                time.sleep(0.4)
            except:
                pass

        # -----------------------------
        # 2. FAST scroll (instant)
        # -----------------------------
        driver.execute_script(
            "arguments[0].scrollTop = arguments[0].scrollHeight",
            scroll_box
        )

        time.sleep(1.2)  # small adaptive wait

        # -----------------------------
        # 3. detect new comments
        # -----------------------------
        comments = driver.find_elements(
            By.XPATH,
            '//div[@role="article"]//div[@dir="auto"]'
        )

        current_count = len(comments)

        if current_count == last_count:
            stable_rounds += 1
        else:
            stable_rounds = 0

        if stable_rounds >= 5:
            print("All comments + replies loaded")
            break

        last_count = current_count

scroll_comments_to_end(driver, wait)

# ---------------------------
# EXTRACT COMMENTS
# ---------------------------
print("Extracting comments...")
comments_elements = driver.find_elements(By.CSS_SELECTOR, '[class="x78zum5 xdt5ytf"]')
comments_list = []
for i, element in enumerate(comments_elements):
    if i ==0:
        continue
    
    # Find text containers inside each comment block
    comment_text_elements = element.find_elements(By.CSS_SELECTOR, '[style="text-align: start;"]')
    
    if comment_text_elements:
        full_comment_parts = []
        for part in comment_text_elements:
            text = get_full_text_with_emojis(driver, part)
            if text:
                full_comment_parts.append(text)
        
        # Join all parts of the same comment with newline (preserves paragraph breaks)
        full_comment = "\n".join(full_comment_parts)
        
        if full_comment.strip():
            comments_list.append(full_comment)

print("Total comments collected:", len(comments_list))

# ---------------------------
# SAVE TO CSV (UTF‑8 + EMOJI SAFE)
# ---------------------------
filename = "comments.csv"

with open(filename, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    # Header
    writer.writerow(["Title", "Comment"])
    # Data rows
    for comment in comments_list:
        writer.writerow([title, comment])

print(f"✅ Comments saved to {filename}")
    
driver.quit()