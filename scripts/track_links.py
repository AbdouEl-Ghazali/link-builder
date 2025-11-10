#!/usr/bin/env python3
"""
Backlink tracking script for link-building workflow.

Reads prospects.json and checks which sites now contain backlinks
to build-a-dress.com. Uses standard library only for minimal dependencies.
"""

import json
import urllib.request
import urllib.parse
import urllib.error
import re
from datetime import datetime
from pathlib import Path

# Configuration
PROSPECTS_FILE = Path(__file__).parent.parent / "data" / "prospects.json"
TARGET_DOMAIN = "build-a-dress.com"
OUTPUT_FILE = Path(__file__).parent.parent / "data" / "backlink_check.json"


def fetch_page_content(url):
    """Fetch HTML content from a URL."""
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; LinkBuilder/1.0; +https://build-a-dress.com)"
            }
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.read().decode("utf-8", errors="ignore")
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
        print(f"Error fetching {url}: {e}")
        return None


def check_backlink(html_content, target_domain):
    """Check if HTML content contains a link to the target domain."""
    if not html_content:
        return False
    
    # Look for links to the target domain
    patterns = [
        rf'href=["\']https?://{re.escape(target_domain)}',
        rf'href=["\']https?://www\.{re.escape(target_domain)}',
        rf'href=["\']/{re.escape(target_domain)}',
    ]
    
    for pattern in patterns:
        if re.search(pattern, html_content, re.IGNORECASE):
            return True
    
    return False


def main():
    """Main tracking function."""
    print(f"Reading prospects from {PROSPECTS_FILE}")
    
    if not PROSPECTS_FILE.exists():
        print(f"Error: {PROSPECTS_FILE} not found")
        return
    
    with open(PROSPECTS_FILE, "r") as f:
        prospects = json.load(f)
    
    if not prospects:
        print("No prospects found in prospects.json")
        return
    
    print(f"Checking {len(prospects)} prospects for backlinks...")
    
    results = []
    for prospect in prospects:
        site_name = prospect.get("site_name", "Unknown")
        homepage_url = prospect.get("homepage_url", "")
        
        if not homepage_url:
            print(f"Skipping {site_name}: no homepage URL")
            continue
        
        print(f"Checking {site_name} ({homepage_url})...")
        html_content = fetch_page_content(homepage_url)
        has_backlink = check_backlink(html_content, TARGET_DOMAIN)
        
        result = {
            "site_name": site_name,
            "homepage_url": homepage_url,
            "has_backlink": has_backlink,
            "checked_at": datetime.now().isoformat(),
        }
        results.append(result)
        
        status = "✓ Found backlink" if has_backlink else "✗ No backlink"
        print(f"  {status}")
    
    # Save results
    output_data = {
        "target_domain": TARGET_DOMAIN,
        "checked_at": datetime.now().isoformat(),
        "results": results,
        "summary": {
            "total_checked": len(results),
            "backlinks_found": sum(1 for r in results if r["has_backlink"]),
        }
    }
    
    with open(OUTPUT_FILE, "w") as f:
        json.dump(output_data, f, indent=2)
    
    print(f"\nResults saved to {OUTPUT_FILE}")
    print(f"Summary: {output_data['summary']['backlinks_found']}/{output_data['summary']['total_checked']} backlinks found")


if __name__ == "__main__":
    main()

