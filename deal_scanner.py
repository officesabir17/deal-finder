"""
deal_scanner.py

Scans Amazon India "Today's Deals" and Flipkart "Offers Zone" pages for
products that are either:
  - priced under RS_UNDER (default 100), OR
  - discounted by DISCOUNT_PCT or more (default 80%)

Sends a push notification (via ntfy.sh, free, no signup) for every match found.
Keeps a local seen-items cache (seen.json) so you don't get repeat notifications
for the same deal every run.

Run manually:  python deal_scanner.py
Run on schedule: see .github/workflows/scan.yml (GitHub Actions, free)
"""

import json
import os
import re
import time
from pathlib import Path

import requests
from playwright.sync_api import sync_playwright

# ---------- CONFIG ----------
RS_UNDER = 100            # alert if price is below this (in INR)
DISCOUNT_PCT = 80         # alert if discount % is this or higher
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "change-me-to-a-unique-topic")
SEEN_FILE = Path(__file__).parent / "seen.json"

AMAZON_DEALS_URL = "https://www.amazon.in/gp/goldbox"
FLIPKART_DEALS_URL = "https://www.flipkart.com/offers-store"

HEADERS_NOTE = (
    "Sites frequently change their HTML structure and add anti-bot checks. "
    "If a run finds 0 deals for both platforms repeatedly, the selectors "
    "below likely need to be updated — inspect the live page and adjust."
)


def load_seen():
    if SEEN_FILE.exists():
        return set(json.loads(SEEN_FILE.read_text()))
    return set()


def save_seen(seen):
    SEEN_FILE.write_text(json.dumps(list(seen)))


def notify(title, message, url=None):
    """Send a push notification via ntfy.sh (free, no account needed)."""
    headers = {"Title": title}
    if url:
        headers["Click"] = url
    try:
        requests.post(f"https://ntfy.sh/{NTFY_TOPIC}", data=message.encode("utf-8"), headers=headers, timeout=10)
    except Exception as e:
        print(f"Notification failed: {e}")


def parse_price(text):
    """Extract a plain integer price from a string like '₹1,499' or 'Rs. 99'."""
    if not text:
        return None
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else None


def scan_amazon(page, seen):
    matches = []
    print("Scanning Amazon deals...")
    try:
        page.goto(AMAZON_DEALS_URL, timeout=30000)
        page.wait_for_timeout(3000)
    except Exception as e:
        print(f"Amazon page load failed: {e}")
        return matches

    # Amazon deal cards — selector may need adjusting; this targets the
    # goldbox deal grid item containers.
    cards = page.query_selector_all("div[data-testid='product-card'], div.a-section.a-spacing-none.dealTile")
    if not cards:
        # Fallback: broader deal card class used on some Amazon deal layouts
        cards = page.query_selector_all("div.DealCard-module__dealCard")

    for card in cards:
        try:
            title_el = card.query_selector("span, a")
            title = title_el.inner_text().strip() if title_el else "Unknown product"

            price_el = card.query_selector("span.a-price .a-offscreen, span[class*='price']")
            price_text = price_el.inner_text() if price_el else None
            price = parse_price(price_text)

            discount_el = card.query_selector("span[class*='discount'], span[class*='badge']")
            discount_text = discount_el.inner_text() if discount_el else ""
            discount_match = re.search(r"(\d+)%", discount_text)
            discount = int(discount_match.group(1)) if discount_match else None

            link_el = card.query_selector("a")
            link = link_el.get_attribute("href") if link_el else ""
            if link and link.startswith("/"):
                link = "https://www.amazon.in" + link

            uid = f"amazon:{title}:{price}"
            if uid in seen:
                continue

            if (price is not None and price < RS_UNDER) or (discount is not None and discount >= DISCOUNT_PCT):
                matches.append({"platform": "Amazon", "title": title, "price": price, "discount": discount, "url": link})
                seen.add(uid)
        except Exception:
            continue

    return matches


def scan_flipkart(page, seen):
    matches = []
    print("Scanning Flipkart deals...")
    try:
        page.goto(FLIPKART_DEALS_URL, timeout=30000)
        page.wait_for_timeout(3000)
    except Exception as e:
        print(f"Flipkart page load failed: {e}")
        return matches

    # Flipkart deal card selectors — commonly used classes for product tiles.
    cards = page.query_selector_all("div._1AtVbE, div._4ddWXP, a.s1Q9rs")
    if not cards:
        cards = page.query_selector_all("div[class*='col']")

    for card in cards:
        try:
            title_el = card.query_selector("a.IRpwTa, div._4rR01T, a.s1Q9rs")
            title = title_el.inner_text().strip() if title_el else None
            if not title:
                continue

            price_el = card.query_selector("div._30jeq3")
            price = parse_price(price_el.inner_text() if price_el else None)

            discount_el = card.query_selector("div._3Ay6Sb span, div.UkUFwK span")
            discount_text = discount_el.inner_text() if discount_el else ""
            discount_match = re.search(r"(\d+)%", discount_text)
            discount = int(discount_match.group(1)) if discount_match else None

            link_el = card.query_selector("a")
            link = link_el.get_attribute("href") if link_el else ""
            if link and link.startswith("/"):
                link = "https://www.flipkart.com" + link

            uid = f"flipkart:{title}:{price}"
            if uid in seen:
                continue

            if (price is not None and price < RS_UNDER) or (discount is not None and discount >= DISCOUNT_PCT):
                matches.append({"platform": "Flipkart", "title": title, "price": price, "discount": discount, "url": link})
                seen.add(uid)
        except Exception:
            continue

    return matches


def main():
    seen = load_seen()
    all_matches = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        ))

        all_matches += scan_amazon(page, seen)
        time.sleep(2)
        all_matches += scan_flipkart(page, seen)

        browser.close()

    save_seen(seen)

    print(f"Found {len(all_matches)} matching deal(s).")
    for m in all_matches:
        title = m["title"][:80]
        price_str = f"₹{m['price']}" if m["price"] else "?"
        discount_str = f"{m['discount']}% off" if m["discount"] else ""
        msg = f"{price_str} {discount_str}\n{title}"
        notify(f"🔥 Deal on {m['platform']}", msg, url=m.get("url"))
        print(f"[{m['platform']}] {title} — {price_str} {discount_str}")

    if not all_matches:
        print(HEADERS_NOTE)


if __name__ == "__main__":
    main()
