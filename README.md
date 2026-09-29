# Deal Finder — Amazon + Flipkart (₹100 under OR 80%+ off)

Automatically scans Amazon's "Today's Deals" and Flipkart's "Offers Zone" every
15 minutes, and sends a free push notification to your phone whenever a
product is priced under ₹100 OR discounted 80% or more.

Runs entirely on GitHub's free servers — your laptop/phone don't need to stay on.

## One-time setup (~10 minutes)

### 1. Get a notification channel (ntfy.sh — free, no signup)
1. Install the **ntfy** app: [Android](https://play.google.com/store/apps/details?id=io.heckel.ntfy) / [iOS](https://apps.apple.com/us/app/ntfy/id1625396347)
2. Pick a unique topic name — something random, e.g. `mehboob-deals-8823` (anyone who knows the exact name could subscribe too, so keep it non-obvious).
3. In the ntfy app, tap **+** → Subscribe to topic → enter your topic name.

### 2. Put this code on GitHub
1. Create a free GitHub account if you don't have one: https://github.com/signup
2. Create a new repository (e.g. `deal-finder`), and upload all the files from this folder to it (drag-and-drop works on github.com, or use `git push` if you're comfortable with git).

### 3. Add your topic name as a secret
1. In your new GitHub repo, go to **Settings → Secrets and variables → Actions**
2. Click **New repository secret**
3. Name: `NTFY_TOPIC`, Value: the topic name you picked in step 1 (e.g. `mehboob-deals-8823`)

### 4. Turn it on
1. Go to the **Actions** tab in your repo
2. You'll see "Deal Scanner" — click it, then click **Enable workflow** if prompted
3. To test immediately: click **Run workflow** (top right) instead of waiting 15 minutes

That's it — from now on it runs automatically every 15 minutes, and you'll get
a notification on your phone the moment a matching deal is found.

## Changing the thresholds

Open `deal_scanner.py` and edit these two lines near the top:
```python
RS_UNDER = 100            # alert if price is below this (in INR)
DISCOUNT_PCT = 80         # alert if discount % is this or higher
```

## Important limitations (please read)

- **Selectors will likely need adjusting.** Amazon and Flipkart change their
  page structure often, and I built this without being able to test live
  against their actual current deals pages. If you run it and get 0 results
  repeatedly, the CSS selectors in `deal_scanner.py` (the `query_selector_all`
  lines) need to be updated to match the current page — right-click a deal
  on the live site → Inspect, and adjust the selector accordingly. Happy to
  help fix these once you share what the page structure looks like when it fails.
- **Only scans the "Deals" pages**, not the entire site (scanning all of
  Amazon/Flipkart isn't technically feasible and would get blocked instantly).
  This means it will catch deals that are already listed in their official
  deals sections — not hidden/individual product price changes elsewhere.
- **GitHub Actions free tier** gives 2,000 minutes/month for private repos
  (unlimited for public repos) — a 15-min schedule uses well within this.
- **Anti-bot blocking is possible.** Both sites may detect and block
  automated browsing over time. If that happens, the scan will silently
  return 0 results — check the Actions tab logs for errors.
- This scans public deal listing pages only; no login or personal account
  access is involved.
