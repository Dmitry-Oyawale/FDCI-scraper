from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import csv
import re
import time
import os

LESSON_URLS = [

]

OUTFILE = "amplify_teacher_presentation_cards.csv"
STORAGE_STATE = "amplify_storage_state.json"


def clean(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def safe_inner_text(locator, timeout=1500) -> str:
    try:
        return locator.inner_text(timeout=timeout)
    except Exception:
        return ""


def try_click_preview(page) -> None:
    try:
        btn = page.get_by_role("button", name="Preview")
        if btn.count() > 0:
            btn.first.click(timeout=5000)
            page.wait_for_timeout(800)
    except Exception:
        pass


def wait_for_lesson_shell(page, timeout=120000) -> None:
    page.wait_for_selector(".teacher-page-content", timeout=timeout, state="attached")


def wait_for_miniscreens(page, timeout=120000) -> None:
    page.wait_for_selector(".alp-preview-miniscreen, .k5-note .ProseMirror", timeout=timeout, state="attached")


def has_miniscreens_quick(page, timeout=10000) -> bool:
    try:
        page.wait_for_selector(".alp-preview-miniscreen, .k5-note .ProseMirror", timeout=timeout, state="attached")
        return True
    except PlaywrightTimeoutError:
        return False


with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)

    if os.path.exists(STORAGE_STATE):
        context = browser.new_context(storage_state=STORAGE_STATE)
    else:
        context = browser.new_context()

    page = context.new_page()

    if not os.path.exists(STORAGE_STATE):
        print("\nA browser window opened.")
        print("1) In THAT window, log into Amplify (SSO/etc).")
        print("2) Once you can open a lesson normally in that same window, come back here.")
        input("Then press ENTER here to save login + start scraping...")
        context.storage_state(path=STORAGE_STATE)
        print(f"Saved login state to: {STORAGE_STATE}")

    with open(OUTFILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "lesson_url",
            "lesson_title",
            "card_step",
            "section",
            "card_text",
            "translated_text"
        ])


        for idx, lesson_url in enumerate(LESSON_URLS, start=1):
            print(f"\n[{idx}/{len(LESSON_URLS)}] Scraping: {lesson_url}")

            try:
                page.goto(lesson_url, wait_until="domcontentloaded", timeout=120000)
                page.wait_for_timeout(1500)

                wait_for_lesson_shell(page, timeout=120000)

                try_click_preview(page)

                if not has_miniscreens_quick(page, timeout=10000):
                    print("No teacher presentation miniscreens found (skipping).")
                    continue

            except PlaywrightTimeoutError:
                ts = int(time.time())
                debug_path = f"debug_timeout_{ts}.png"
                try:
                    page.screenshot(path=debug_path, full_page=True)
                    print(f"TIMEOUT. Saved screenshot: {debug_path}")
                except Exception:
                    print("TIMEOUT. (Also failed to save screenshot.)")

                print("Final URL:", page.url)
                continue

            lesson_title = safe_inner_text(page.locator(".activity-title h1")) \
                or safe_inner_text(page.locator("h1")) \
                or ""

            miniscreens = page.locator(".alp-preview-miniscreen")
            count = miniscreens.count()
            print("Miniscreens found:", count)

            for i in range(count):
                ms = miniscreens.nth(i)

                step = safe_inner_text(ms.locator(".step-index span"))
                section = safe_inner_text(ms.locator(".section-name-text span"))
                text = safe_inner_text(ms.locator(".k5-note .ProseMirror"))

                writer.writerow([
                    lesson_url,
                    clean(lesson_title),
                    clean(step),
                    clean(section),
                    clean(text),
                    ""  # empty column to be filled later by translator
                ])

    context.close()
    browser.close()

print(f"\nDone. Wrote {OUTFILE}")

