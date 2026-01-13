from playwright.sync_api import sync_playwright
import csv
import re

LESSON_URLS = [
    "https://classroom.amplify.com/activity/688d29ffa0fa82bb4881972d?checkAmplifyLogin=true&collections=68067ea4e80416cdbb08bf03%2C6802a6f4907aef8d98bac94b%2C688d29ffa0fa82bb4881970e",
    "https://classroom.amplify.com/activity/688d28b6a0fa82bb487b8567?checkAmplifyLogin=true&collections=68067ea4e80416cdbb08bf03%2C6802a6f4907aef8d98bac94b%2C688d29ffa0fa82bb4881970e",
    "https://classroom.amplify.com/activity/688d29ffa0fa82bb48819783?checkAmplifyLogin=true&collections=68067ea4e80416cdbb08bf03%2C6802a6f4907aef8d98bac94b%2C688d29ffa0fa82bb4881970e",
    "https://classroom.amplify.com/activity/688d29ffa0fa82bb48819825?checkAmplifyLogin=true&collections=68067ea4e80416cdbb08bf03%2C6802a6f4907aef8d98bac94b%2C688d29ffa0fa82bb4881970e", 
    "https://classroom.amplify.com/activity/688d29ffa0fa82bb48819892?checkAmplifyLogin=true&collections=68067ea4e80416cdbb08bf03%2C6802a6f4907aef8d98bac94b%2C688d29ffa0fa82bb4881970e",
    "https://classroom.amplify.com/activity/688d2a00a0fa82bb488198eb?checkAmplifyLogin=true&collections=68067ea4e80416cdbb08bf03%2C6802a6f4907aef8d98bac94b%2C688d29ffa0fa82bb4881970e"
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
            page.goto(lesson_url, wait_until="networkidle")

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

