from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import os
import re

GRADE_OVERVIEW_URL = "https://classroom.amplify.com/collection/6802a76e907aef8d98d039a8?checkAmplifyLogin=true&collections=68067ea4e80416cdbb08bf03"
STORAGE_STATE = "amplify_storage_state.json"
OUT_PY = "lesson_urls_grade4.py"

ACTIVITY_RE = re.compile(r"^https://classroom\.amplify\.com/activity/[0-9a-f]{24}\b", re.I)

UNIT_MARKER_RE = re.compile(r"\bUnit\s+(Zero|\d+)\b", re.I)
COLLECTION_RE = re.compile(r"^https://classroom\.amplify\.com/collection/[0-9a-f]{24}\b", re.I)


def normalize_url(url: str) -> str:
    return (url or "").split("#", 1)[0].strip()


def write_python_list(path: str, urls: list[str]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write("LESSON_URLS = [\n")
        for u in urls:
            f.write(f'    "{u}",\n')
        f.write("]\n")


def dedupe_preserve_order(items: list[str]) -> list[str]:
    seen = set()
    out = []
    for x in items:
        if x and x not in seen:
            seen.add(x)
            out.append(x)
    return out


def scroll_to_load(page, rounds: int = 12, step: int = 1200, wait_ms: int = 200) -> None:
    for _ in range(rounds):
        page.mouse.wheel(0, step)
        page.wait_for_timeout(wait_ms)


def get_unit_links_from_grade_page(page) -> list[str]:

    selector = "main a[href]" if page.locator("main").count() else "a[href]"

    links = page.eval_on_selector_all(
        selector,
        """
        (els) => els.map(a => ({
          href: a.href,
          text: (a.innerText || "").trim()
        }))
        """
    )

    unit_urls = []
    for item in links:
        href = normalize_url(item.get("href", ""))
        text = item.get("text", "") or ""
        if not href or not text:
            continue
        if COLLECTION_RE.match(href) and UNIT_MARKER_RE.search(text):
            unit_urls.append(href)

    return dedupe_preserve_order(unit_urls)


def get_lesson_links_from_unit_page(page) -> list[str]:

    selector = "main" if page.locator("main").count() else "body"

    items = page.eval_on_selector_all(
        f"{selector} *",
        r"""
        (els) => {
          const isLessonLabel = (el) => {
            const t = (el.innerText || "").trim();
            return /\bLesson\s+\d+\s*:/i.test(t);
          };

          const results = [];
          const seen = new Set();

          for (const el of els) {
            if (!isLessonLabel(el)) continue;

            let container = el;
            for (let i = 0; i < 10; i++) {
              if (!container || !container.parentElement) break;
              container = container.parentElement;

              const a = container.querySelector('a[href*="/activity/"]');
              if (a) break;
            }

            const a = container && container.querySelector('a[href*="/activity/"]');
            if (!a) continue;

            const href = a.href || "";
            if (!href) continue;

            if (!seen.has(href)) {
              seen.add(href);
              results.push(href);
            }
          }
          return results;
        }
        """
    )

    lesson_urls = []
    for href in items:
        href = normalize_url(href)
        if ACTIVITY_RE.match(href):
            lesson_urls.append(href)

    return dedupe_preserve_order(lesson_urls)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)

        if os.path.exists(STORAGE_STATE):
            context = browser.new_context(storage_state=STORAGE_STATE)
        else:
            context = browser.new_context()

        page = context.new_page()

        if not os.path.exists(STORAGE_STATE):
            page.goto("https://classroom.amplify.com", wait_until="domcontentloaded", timeout=120000)
            input("Log in in the opened browser, then press ENTER here to save login state...")
            context.storage_state(path=STORAGE_STATE)
            print(f"Saved login state to: {STORAGE_STATE}")

        print("Opening grade page...")
        page.goto(GRADE_OVERVIEW_URL, wait_until="domcontentloaded", timeout=120000)
        page.wait_for_timeout(1500)
        scroll_to_load(page, rounds=8)

        unit_urls = get_unit_links_from_grade_page(page)
        print(f"Found {len(unit_urls)} unit links.")

        all_lessons = []

        for i, unit_url in enumerate(unit_urls, start=1):
            print(f"[Unit {i}/{len(unit_urls)}] {unit_url}")
            try:
                page.goto(unit_url, wait_until="domcontentloaded", timeout=120000)
                page.wait_for_timeout(1500)

                scroll_to_load(page, rounds=14)

                lessons = get_lesson_links_from_unit_page(page)
                print(f"  Lessons found: {len(lessons)}")
                all_lessons.extend(lessons)

            except PlaywrightTimeoutError:
                print("  TIMEOUT loading unit (skipping).")
                continue

        all_lessons = dedupe_preserve_order(all_lessons)

        write_python_list(OUT_PY, all_lessons)
        print(f"\nTotal lessons found: {len(all_lessons)}")
        print(f"Wrote: {OUT_PY}")

        context.close()
        browser.close()


if __name__ == "__main__":
    main()
