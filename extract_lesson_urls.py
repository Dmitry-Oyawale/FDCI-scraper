import re
import csv
import argparse
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError



UNIT_TEXT_RE = re.compile(r"^\s*Unit\b", re.IGNORECASE)
LESSON_TEXT_RE = re.compile(r"\bLesson\s*\d+\b", re.IGNORECASE)



def normalize_url(base: str, href: str) -> str:
    if not href:
        return ""
    return urljoin(base, href)


def unique_keep_order(items):
    seen = set()
    out = []
    for x in items:
        if x and x not in seen:
            seen.add(x)
            out.append(x)
    return out


def safe_goto(page, url: str, timeout=60000):
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=timeout)
    except PlaywrightTimeoutError:
        page.goto(url, timeout=timeout)


def auto_scroll(page, step=900, max_scrolls=30):
    for _ in range(max_scrolls):
        page.mouse.wheel(0, step)
        page.wait_for_timeout(200)



def extract_unit_links_from_grade(page) -> list[str]:
    page.wait_for_load_state("domcontentloaded")

    locators = [
        page.locator("main a[href*='/collection/']"),
        page.locator("a[href*='/collection/']"),
    ]

    base = page.url
    unit_links = []

    for anchors in locators:
        for i in range(anchors.count()):
            a = anchors.nth(i)
            text = (a.inner_text() or "").strip()
            if not UNIT_TEXT_RE.match(text):
                continue
            href = a.get_attribute("href")
            unit_links.append(normalize_url(base, href))

        unit_links = unique_keep_order(unit_links)
        if unit_links:
            break

    return unit_links


def extract_lesson_items_from_unit(page) -> list[str]:
    
    page.wait_for_load_state("domcontentloaded")
    page.wait_for_timeout(500)
    auto_scroll(page)

    base = page.url
    lesson_links = []

    lesson_nodes = page.locator("text=/\\bLesson\\s*\\d+\\b/i")
    count = lesson_nodes.count()

    for i in range(count):
        node = lesson_nodes.nth(i)

        link = node.locator("xpath=ancestor-or-self::a[@href][1]")
        if link.count() == 0:
            continue

        href = link.first.get_attribute("href")
        if not href:
            continue

        full = normalize_url(base, href)

        if "/collection/" in full or "/activity/" in full:
            lesson_links.append(full)

    return unique_keep_order(lesson_links)


def extract_activity_links_from_lesson_collection(page) -> list[str]:
    page.wait_for_load_state("domcontentloaded")
    page.wait_for_timeout(500)
    auto_scroll(page)

    base = page.url
    activity_links = []

    anchors = page.locator("a[href*='/activity/']")
    for i in range(anchors.count()):
        a = anchors.nth(i)
        href = a.get_attribute("href")
        activity_links.append(normalize_url(base, href))

    return unique_keep_order(activity_links)



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("grade_url")
    parser.add_argument("--out", default="lesson_links.csv")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--profile", default="amplify_profile")
    parser.add_argument("--pause-for-login", action="store_true")
    args = parser.parse_args()

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=args.profile,
            headless=not args.headed,
        )
        page = context.new_page()

        print(f"Opening grade page:\n  {args.grade_url}")
        safe_goto(page, args.grade_url)

        unit_links = extract_unit_links_from_grade(page)

        if not unit_links:
            print("\nUnits found: 0")
            print("Likely not logged in yet.")
            if args.pause_for_login:
                print("\nLog in in the opened browser.")
                input("Press ENTER after logging in...")
                unit_links = extract_unit_links_from_grade(page)

        print(f"\nUnits found: {len(unit_links)}")
        for i, u in enumerate(unit_links, 1):
            print(f"  [{i}] {u}")

        all_activity_links = []

        for unit_idx, unit_url in enumerate(unit_links, 1):
            print(f"\n[Unit {unit_idx}/{len(unit_links)}] Visiting unit page...")
            safe_goto(page, unit_url)

            lesson_items = extract_lesson_items_from_unit(page)
            print(f"  Lesson items found: {len(lesson_items)}")

            for lesson_idx, lesson_url in enumerate(lesson_items, 1):
                print(f"    [Lesson {lesson_idx}] {lesson_url}")

                if "/activity/" in lesson_url:
                    all_activity_links.append(lesson_url)
                    continue

                safe_goto(page, lesson_url)
                activities = extract_activity_links_from_lesson_collection(page)
                print(f"      Activity links found: {len(activities)}")
                all_activity_links.extend(activities)

        all_activity_links = unique_keep_order(all_activity_links)

        print(f"\nTOTAL lesson activity links: {len(all_activity_links)}")
        print(f"Saving to: {args.out}")

        with open(args.out, "w", encoding="utf-8") as f:
            f.write("LESSON_URLS = [\n")
            for link in all_activity_links:
                f.write(f'    "{link}",\n')
            f.write("]\n")


        context.close()


if __name__ == "__main__":
    main()
