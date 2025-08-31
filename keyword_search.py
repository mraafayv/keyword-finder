import re
from playwright.sync_api import sync_playwright
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

def add_lang_param(url, lang="en_US"):
    """Append or replace ?setlang=... in a URL"""
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    qs["setlang"] = [lang]   # overwrite or add
    new_query = urlencode(qs, doseq=True)
    return urlunparse(parsed._replace(query=new_query))

def run():
    start_url = "https://www.amazon.jobs/content/de/teams/fulfillment-and-operations/germany#:Resj6H1:"
    keywords = ["16.15"]

    matched_links = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # open the start page
        page.goto(start_url, wait_until="domcontentloaded")
        print(f"Opened: {start_url}")

        # collect only links that start with https://hvr
        links = page.query_selector_all('a[href^="https://hvr"]')
        hrefs = [a.get_attribute("href") for a in links if a.get_attribute("href")]

        print(f"Found {len(hrefs)} useful links to visit.")

        # compile keywords (case-insensitive)
        keyword_patterns = [re.compile(re.escape(k), re.IGNORECASE) for k in keywords]

        # check each link with setlang=en_US
        for href in hrefs:
            try:
                url_with_lang = add_lang_param(href, "en_US")
                page.goto(url_with_lang, wait_until="domcontentloaded", timeout=60000)
                text = page.locator("body").inner_text()

                if any(p.search(text) for p in keyword_patterns):
                    matched_links.append(url_with_lang)
            except Exception as e:
                print(f"Failed to visit {href}: {e}")

        browser.close()

    print("\nMatched Links:")
    for link in matched_links:
        print(link)

    return matched_links

if __name__ == "__main__":
    run()