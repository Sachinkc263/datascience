"""
Dynamic Multi-Subreddit Reddit Scraper
======================================
Scrape any number of subreddits into a single pandas DataFrame.
Uses PullPush API (Pushshift successor) — no Reddit API creds needed.
Works in Google Colab / Jupyter out of the box.

Usage:
    1. Edit SUBREDDITS list below
    2. Run the cell
    3. DataFrame `df` is ready + CSV saved per subreddit and combined
"""

import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

# ── CONFIG (edit these) ─────────────────────────────────────────
SUBREDDITS = [
    "programming",
    "learnpython",
    "datascience",
    "MachineLearning",
    "artificial",
    "cscareerquestions"
    # add as many as you want...
]

MAX_PAGES_PER_SUB = 5   # 100 posts/page → 5 pages ≈ 500 posts per sub
OUTPUT_DIR = "scraped_data"
SAVE_INDIVIDUAL = True   # save per-subreddit CSVs alongside combined
# ────────────────────────────────────────────────────────────────

BASE_URL = "https://api.pullpush.io/reddit/search/submission/"
HEADERS = {"User-Agent": "MultiSubScraper/2.0"}
PAGE_SIZE = 100
RATE_LIMIT_DELAY = 1.0


def fetch_page(subreddit: str, before: int | None = None) -> list[dict]:
    """Fetch a single page of posts from PullPush API."""
    params = {
        "subreddit": subreddit,
        "size": PAGE_SIZE,
        "sort": "desc",
        "sort_type": "created_utc",
    }
    if before is not None:
        params["before"] = before

    resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json().get("data", [])


def scrape_subreddit(subreddit: str, max_pages: int = MAX_PAGES_PER_SUB) -> list[dict]:
    """
    Paginate through a single subreddit using created_utc cursor.
    Returns deduplicated list of raw post dicts.
    """
    all_posts: list[dict] = []
    before: int | None = None

    print(f"\n{'─'*50}")
    print(f"  Scraping r/{subreddit} ({max_pages} pages max)")
    print(f"{'─'*50}")

    for page in range(max_pages):
        try:
            posts = fetch_page(subreddit, before=before)
        except requests.exceptions.RequestException as e:
            print(f"  [page {page}] request failed: {e} — stopping.")
            break

        if not posts:
            print(f"  [page {page}] empty response — stopping.")
            break

        all_posts.extend(posts)
        before = posts[-1].get("created_utc", 0)
        oldest = datetime.fromtimestamp(before, tz=timezone.utc).strftime("%Y-%m-%d")
        print(f"  [page {page}] +{len(posts):>3} posts | total: {len(all_posts):>4} | oldest: {oldest}")

        if len(posts) < PAGE_SIZE:
            break
        time.sleep(RATE_LIMIT_DELAY)

    # deduplicate
    seen: set[str] = set()
    unique = [p for p in all_posts if p.get("id", "") not in seen and not seen.add(p.get("id", ""))]
    print(f"  ✓ {len(unique)} unique posts")
    return unique


def posts_to_dataframe(posts: list[dict], subreddit: str) -> pd.DataFrame:
    """Transform raw API response into a clean DataFrame."""
    records = []
    for p in posts:
        created = datetime.fromtimestamp(p.get("created_utc", 0), tz=timezone.utc)
        selftext = (p.get("selftext") or "").strip()
        if selftext in ("[removed]", "[deleted]"):
            selftext = ""

        records.append({
            "subreddit": subreddit,
            "id": p.get("id", ""),
            "title": p.get("title", ""),
            "author": p.get("author", "[deleted]"),
            "selftext": selftext,
            "score": p.get("score", 0),
            "upvote_ratio": p.get("upvote_ratio", 0.0),
            "num_comments": p.get("num_comments", 0),
            "created_utc": created,
            "permalink": f"https://reddit.com{p.get('permalink', '')}",
            "link_flair_text": p.get("link_flair_text") or "",
            "is_self": p.get("is_self", True),
            "domain": p.get("domain", ""),
        })

    df = pd.DataFrame(records)
    if not df.empty:
        df.sort_values("created_utc", ascending=False, inplace=True)
        df.reset_index(drop=True, inplace=True)
    return df


def scrape_multiple(
    subreddits: list[str],
    max_pages: int = MAX_PAGES_PER_SUB,
) -> pd.DataFrame:
    """
    Scrape multiple subreddits and return a combined DataFrame.
    Each row tagged with its source subreddit.
    """
    frames: list[pd.DataFrame] = []
    output_dir = Path(OUTPUT_DIR)
    output_dir.mkdir(exist_ok=True)

    for sub in subreddits:
        raw = scrape_subreddit(sub, max_pages=max_pages)
        sub_df = posts_to_dataframe(raw, subreddit=sub)

        if sub_df.empty:
            print(f"  ⚠ No data for r/{sub}, skipping.")
            continue

        frames.append(sub_df)

        if SAVE_INDIVIDUAL:
            path = output_dir / f"{sub.lower()}.csv"
            sub_df.to_csv(path, index=False)
            print(f"  💾 Saved {path} ({len(sub_df)} rows)")

    if not frames:
        print("\n⚠ No data scraped from any subreddit.")
        return pd.DataFrame()

    combined = pd.concat(frames, ignore_index=True)
    combined.sort_values("created_utc", ascending=False, inplace=True)
    combined.reset_index(drop=True, inplace=True)

    combined_path = output_dir / "all_subreddits.csv"
    combined.to_csv(combined_path, index=False)
    print(f"\n💾 Combined CSV saved: {combined_path} ({len(combined)} rows)")

    return combined


def print_summary(df: pd.DataFrame) -> None:
    """Print a quick overview of the scraped data."""
    if df.empty:
        return

    print(f"\n{'='*60}")
    print(f"  SCRAPE SUMMARY")
    print(f"{'='*60}")
    print(f"  Total posts   : {len(df)}")
    print(f"  Subreddits    : {df['subreddit'].nunique()}")
    print(f"  Date range    : {df['created_utc'].min()} → {df['created_utc'].max()}")
    print(f"  With body text: {(df['selftext'].str.len() > 0).sum()}")

    print(f"\n  Posts per subreddit:")
    for sub, count in df["subreddit"].value_counts().items():
        date_min = df.loc[df["subreddit"] == sub, "created_utc"].min().strftime("%Y-%m-%d")
        date_max = df.loc[df["subreddit"] == sub, "created_utc"].max().strftime("%Y-%m-%d")
        print(f"    r/{sub:<20s} {count:>5} posts  ({date_min} → {date_max})")

    print(f"\n  Top 10 posts by score (all subs):")
    cols = ["subreddit", "title", "score", "num_comments", "created_utc"]
    print(df.nlargest(10, "score")[cols].to_string(index=False))
    print(f"{'='*60}")


# ── RUN ─────────────────────────────────────────────────────────
df = scrape_multiple(SUBREDDITS)
print_summary(df)
df.head(10)
