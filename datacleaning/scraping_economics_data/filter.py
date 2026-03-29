from bs4 import BeautifulSoup
import csv
import os

# ====================== CONFIG ======================
html_file = "real_commodities.html"          # ← your scraped file
output_folder = "commodities_tables"         # folder where CSVs will be saved

# Create folder if it doesn't exist
os.makedirs(output_folder, exist_ok=True)

# ====================== READ HTML ======================
with open(html_file, "r", encoding="utf-8") as f:
    soup = BeautifulSoup(f, "html.parser")

tables = soup.find_all("table")

print(f"Found {len(tables)} table(s) on the page.\n")

# ====================== PROCESS EACH TABLE ======================
for idx, table in enumerate(tables, 1):
    print(f"Processing Table {idx}...")

    # --- 1. Get Headers (from <thead> or first <tr>) ---
    headers = []
    
    thead = table.find("thead")
    if thead:
        headers = [th.get_text(strip=True) for th in thead.find_all(["th", "td"])]
    else:
        # Try first row as header
        first_row = table.find("tr")
        if first_row:
            headers = [cell.get_text(strip=True) for cell in first_row.find_all(["th", "td"])]

    # --- 2. Get Data Rows ---
    rows = []
    tbody = table.find("tbody")
    
    if tbody:
        row_tags = tbody.find_all("tr")
    else:
        # If no <tbody>, take all rows except the first one (header)
        all_rows = table.find_all("tr")
        row_tags = all_rows[1:] if headers else all_rows

    for row in row_tags:
        cells = [cell.get_text(strip=True).replace("\n", " ").replace("\r", "") 
                 for cell in row.find_all(["td", "th"])]
        if cells and any(cell.strip() for cell in cells):  # skip completely empty rows
            rows.append(cells)

    # --- 3. Create nice filename ---
    # Try to get a meaningful name from nearby heading or table class/id
    table_name = f"table_{idx}"
    
    # Optional: look for previous h2/h3 or table caption
    caption = table.find("caption")
    if caption:
        table_name = caption.get_text(strip=True)[:50]
    else:
        heading = table.find_previous(["h1", "h2", "h3"])
        if heading:
            table_name = heading.get_text(strip=True)[:50]
    
    # Clean filename
    table_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in table_name)
    filename = os.path.join(output_folder, f"{table_name or f'table_{idx}'}.csv")

    # --- 4. Write to CSV ---
    with open(filename, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        
        if headers:
            writer.writerow(headers)
        writer.writerows(rows)

    print(f"   → Saved: {filename}")
    print(f"      Columns : {len(headers)}")
    print(f"      Rows    : {len(rows)}\n")

print("✅ All tables have been extracted and saved!")
print(f"📁 Check the folder: {os.path.abspath(output_folder)}")