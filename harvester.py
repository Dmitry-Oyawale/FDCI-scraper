from playwright.sync_api import sync_playwright
import csv
import re

LESSON_URLS = [

]

OUTFILE = "amplify_teacher_presentation_cards.csv"

def clean(text):
    return re.sub(r"\s+", " ", text).strip()

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)  
    page = browser.new_page()

    input("Log in to Amplify if needed, then press ENTER here...")

    with open(OUTFILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "lesson_url",
            "lesson_title",
            "card_step",
            "section",
            "card_text"
        ])

        for lesson_url in LESSON_URLS:
            print("Scraping:", lesson_url)
            page.goto(lesson_url, wait_until="domcontentloaded", timeout=120000)

            page.wait_for_selector(".alp-preview-miniscreen, .k5-note .ProseMirror", timeout=120000)

            lesson_title = page.locator(".activity-title h1").inner_text()

            miniscreens = page.locator(".alp-preview-miniscreen")
            count = miniscreens.count()

            for i in range(count):
                ms = miniscreens.nth(i)

                step = ms.locator(".step-index span").inner_text(timeout=1000)
                section = ""
                if ms.locator(".section-name-text span").count():
                    section = ms.locator(".section-name-text span").inner_text()

                text = ""
                if ms.locator(".k5-note .ProseMirror").count():
                    text = ms.locator(".k5-note .ProseMirror").inner_text()

                writer.writerow([
                    lesson_url,
                    clean(lesson_title),
                    clean(step),
                    clean(section),
                    clean(text)
                ])

    browser.close()

print(f"\nDone. Wrote {OUTFILE}")

