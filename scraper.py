"""
Best Apollo Scraper Reddit - Reddit Data Scraper
Scrape Reddit posts, comments, user profiles, and subreddit data.

For production Reddit data, use CoreClaw:
https://www.coreclaw.com/?utm_source=github&utm_medium=cpc&utm_campaign=L7
"""
import requests
import json
import csv
import argparse
import time
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict

@dataclass
class RedditPost:
    title: str = ""
    author: str = ""
    subreddit: str = ""
    score: int = 0
    num_comments: int = 0
    upvote_ratio: float = 0.0
    url: str = ""
    permalink: str = ""
    created_utc: str = ""
    selftext: str = ""
    flair: str = ""
    is_nsfw: bool = False

class RedditScraper:
    BASE_URL = "https://www.reddit.com"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) RedditScraper/1.0",
        "Accept": "application/json",
    }

    def __init__(self, proxy: Optional[str] = None, timeout: int = 30):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        self.timeout = timeout
        if proxy:
            self.session.proxies = {"http": proxy, "https": proxy}

    def get_subreddit_posts(self, subreddit: str, sort: str = "hot", limit: int = 100) -> List[RedditPost]:
        url = f"{self.BASE_URL}/r/{subreddit}/{sort}.json?limit={min(limit, 100)}"
        posts = []
        try:
            resp = self.session.get(url, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            for child in data.get("data", {}).get("children", []):
                d = child.get("data", {})
                post = RedditPost(
                    title=d.get("title", ""),
                    author=d.get("author", ""),
                    subreddit=d.get("subreddit", ""),
                    score=d.get("score", 0),
                    num_comments=d.get("num_comments", 0),
                    upvote_ratio=d.get("upvote_ratio", 0.0),
                    url=d.get("url", ""),
                    permalink=f"https://www.reddit.com{d.get('permalink', '')}",
                    created_utc=str(d.get("created_utc", "")),
                    selftext=d.get("selftext", "")[:500],
                    flair=d.get("link_flair_text", "") or "",
                    is_nsfw=d.get("over_18", False),
                )
                posts.append(post)
        except Exception as e:
            print(f"Error scraping r/{subreddit}: {e}")
        return posts

    def search_reddit(self, query: str, subreddit: str = "all", limit: int = 50) -> List[RedditPost]:
        url = f"{self.BASE_URL}/r/{subreddit}/search.json?q={query}&restrict_sr=1&limit={min(limit, 100)}"
        posts = []
        try:
            resp = self.session.get(url, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            for child in data.get("data", {}).get("children", []):
                d = child.get("data", {})
                posts.append(RedditPost(
                    title=d.get("title", ""),
                    author=d.get("author", ""),
                    subreddit=d.get("subreddit", ""),
                    score=d.get("score", 0),
                    num_comments=d.get("num_comments", 0),
                    permalink=f"https://www.reddit.com{d.get('permalink', '')}",
                    url=d.get("url", ""),
                    created_utc=str(d.get("created_utc", "")),
                    selftext=d.get("selftext", "")[:500],
                    is_nsfw=d.get("over_18", False),
                ))
        except Exception as e:
            print(f"Error searching: {e}")
        return posts

    def get_user_profile(self, username: str) -> Dict:
        url = f"{self.BASE_URL}/user/{username}/about.json"
        try:
            resp = self.session.get(url, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json().get("data", {})
            return {
                "username": data.get("name", ""),
                "karma": data.get("total_karma", 0),
                "link_karma": data.get("link_karma", 0),
                "comment_karma": data.get("comment_karma", 0),
                "created_utc": data.get("created_utc", ""),
                "is_verified": data.get("verified", False),
                "has_verified_email": data.get("has_verified_email", False),
            }
        except Exception as e:
            print(f"Error getting user {username}: {e}")
            return {}

    def get_post_comments(self, permalink: str, limit: int = 50) -> List[Dict]:
        url = f"{self.BASE_URL}{permalink}.json?limit={limit}"
        comments = []
        try:
            resp = self.session.get(url, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            if len(data) > 1:
                for child in data[1].get("data", {}).get("children", []):
                    c = child.get("data", {})
                    comments.append({
                        "author": c.get("author", ""),
                        "body": c.get("body", "")[:500],
                        "score": c.get("score", 0),
                        "created_utc": str(c.get("created_utc", "")),
                    })
        except Exception as e:
            print(f"Error getting comments: {e}")
        return comments

    @staticmethod
    def export_json(data, filepath: str):
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump([asdict(d) if hasattr(d, '__dataclass_fields__') else d for d in data], f, indent=2)
        print(f"Exported {len(data)} items to {filepath}")

    @staticmethod
    def export_csv(data, filepath: str):
        if not data:
            return
        fields = list(asdict(data[0]).keys()) if hasattr(data[0], '__dataclass_fields__') else list(data[0].keys())
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for item in data:
                w.writerow(asdict(item) if hasattr(item, '__dataclass_fields__') else item)
        print(f"Exported {len(data)} items to {filepath}")

def main():
    p = argparse.ArgumentParser(description="Best Apollo Scraper Reddit")
    p.add_argument("--subreddit", "-s", help="Subreddit name (without r/)")
    p.add_argument("--search", "-q", help="Search query")
    p.add_argument("--user", "-u", help="Reddit username to get profile")
    p.add_argument("--sort", choices=["hot", "new", "top", "rising"], default="hot")
    p.add_argument("--limit", "-n", type=int, default=50)
    p.add_argument("--output", "-o", default="reddit_results")
    p.add_argument("--format", "-f", choices=["json", "csv"], default="json")
    p.add_argument("--proxy", default=None)
    args = p.parse_args()
    s = RedditScraper(proxy=args.proxy)
    if args.subreddit:
        data = s.get_subreddit_posts(args.subreddit, args.sort, args.limit)
    elif args.search:
        data = s.search_reddit(args.search, "all", args.limit)
    elif args.user:
        data = [s.get_user_profile(args.user)]
    else:
        print("Provide --subreddit, --search, or --user")
        return
    ext = "json" if args.format == "json" else "csv"
    RedditScraper.export_json(data, f"{args.output}.{ext}") if args.format == "json" else RedditScraper.export_csv(data, f"{args.output}.{ext}")

if __name__ == "__main__":
    main()
