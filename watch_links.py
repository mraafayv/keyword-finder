import os
import re
from dotenv import load_dotenv
from telegram_sender import send_message
from playwright.sync_api import sync_playwright
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

load_dotenv()

TOKEN = os.environ["TG_BOT_TOKEN"]   # raises KeyError if missing (good fail)
CHAT_ID = os.environ["TG_CHANNEL_ID"]
START_URL = os.environ["START_URL"]

def add_lang_param(url, lang="en_US"):
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    qs["setlang"] = [lang]
    return urlunparse(parsed._replace(query=urlencode(qs, doseq=True)))

def build_amount_regex(values):
    # Build a pattern that matches e.g. 2000, 2,000, 2.000, €2000, 2000 €, EUR 2000
    # alts = []
    # for n in values:
    #     if len(n) > 3:
    #         head, tail = n[:-3], n[-3:]
    #         with_sep = fr"{head}[.,\s]?{tail}"
    #     else:
    #         with_sep = n
    #     alts.append(fr"(?:€\s*)?(?:{n}|{with_sep})\s*(?:€|eur)?")
    # return re.compile(fr"\b(?:{'|'.join(alts)})\b", re.IGNORECASE)

    alts = []
    for n in values:
        if len(n) > 3:
            head, tail = n[:-3], n[-3:]
            with_sep = fr"{head}[.,\s]?{tail}"  # 2,000 / 2.000 / 2 000
            body = fr"(?:{n}|{with_sep})"
        else:
            body = n
        # Allow € or EUR as prefix OR suffix; spaces optional
        alts.append(fr"(?:(?:€|eur)\s*)?{body}(?:\s*(?:€|eur))?")
    # Guard so we don't match inside 12000 or 20005
    pattern = fr"(?<!\d)(?:{'|'.join(alts)})(?!\d)"
    return re.compile(pattern, re.IGNORECASE)

def run():
    start_url = START_URL

    # --- keyword logic ---
    bonus_phrase_re = re.compile(r"\b(?:signing bonus|sign[-\s]?on bonus)\b", re.IGNORECASE)
    amount_re = build_amount_regex(["1000", "1500", "2000", "2500", "3000"])
    bonus_word_re = re.compile(r"\bbonus\b", re.IGNORECASE)  # to pair with amounts

    matched_links = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            extra_http_headers={"Accept-Language": "en-US,en;q=0.9"}
        )

        # Block heavy resources to speed up
        context.route("**/*", lambda route: route.abort()
                      if route.request.resource_type in {"image","stylesheet","font","media","other"}
                      else route.continue_())

        page = context.new_page()

        # open the start page
        page.goto(start_url, wait_until="domcontentloaded")
        print(f"Opened: {start_url}")

        # collect only links that start with https://hvr
        links = page.query_selector_all('a[href^="https://hvr"]')
        hrefs = [a.get_attribute("href") for a in links if a.get_attribute("href")]

        # dedupe while preserving order
        seen, hrefs_unique = set(), []
        for h in hrefs:
            if h not in seen:
                seen.add(h)
                hrefs_unique.append(h)

        # scan each link (force English)
        for href in hrefs_unique:
            try:
                url_with_lang = add_lang_param(href, "en_US")
                page.goto(url_with_lang, wait_until="domcontentloaded", timeout=15000)

                # IMPORTANT: visible text only to avoid hidden numbers
                text = page.locator("body").inner_text() or ""

                # Match logic:
                # 1) direct bonus phrase (signing/sign-on)
                # OR
                # 2) 'bonus' appears AND one of the target amounts appears
                has_direct_bonus_phrase = bool(bonus_phrase_re.search(text))
                has_bonus_amount_combo = bool(bonus_word_re.search(text) and amount_re.search(text))

                if has_direct_bonus_phrase or has_bonus_amount_combo:
                    matched_links.append(url_with_lang)

            except Exception as e:
                print(f"Failed to visit {href}: {e}")

        browser.close()


    if matched_links:
    
        try:
            send_message(TOKEN, CHAT_ID, matched_links)  
        except Exception as e:
            print(f"Failed to send Telegram message: {e}")

    # print("\nMatched Links:")

    # for link in matched_links:
    #     print(link)

    return matched_links

    

if __name__ == "__main__":
    run()

