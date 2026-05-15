#!/usr/bin/env python3
"""
URL integrity checker for all metadata_ai.csv files across 40 MOSAIC countries.
Checks every URL for accessibility and generates a structured report.
"""

import csv
import os
import sys
import time
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "reference"

# HTTP session with retries and timeout
def make_session():
    session = requests.Session()
    retry = Retry(total=2, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (compatible; MOSAIC-URL-Checker/1.0; +https://mosaiccholeramodel.org)"
    })
    return session

def check_url(args):
    iso, source_index, source_name, url, session = args
    result = {
        "iso": iso,
        "source_index": source_index,
        "source": source_name,
        "url": url,
        "status_code": None,
        "status_category": None,
        "redirect_url": None,
        "response_time_s": None,
        "error": None,
    }

    if not url or url.strip() == "" or url.strip().lower() in ("n/a", "na", "none", "-"):
        result["status_category"] = "NO_URL"
        return result

    try:
        t0 = time.time()
        # Try HEAD first (faster), fall back to GET if HEAD not allowed
        resp = session.head(url, timeout=15, allow_redirects=True)
        if resp.status_code == 405:  # Method not allowed
            resp = session.get(url, timeout=15, allow_redirects=True, stream=True)
            resp.close()
        elapsed = round(time.time() - t0, 2)

        result["status_code"] = resp.status_code
        result["response_time_s"] = elapsed

        # Track final URL after redirects
        if resp.url != url:
            result["redirect_url"] = resp.url

        # Categorize
        code = resp.status_code
        if 200 <= code < 300:
            result["status_category"] = "OK"
        elif 300 <= code < 400:
            result["status_category"] = "REDIRECT"
        elif code == 401:
            result["status_category"] = "AUTH_REQUIRED"
        elif code == 403:
            result["status_category"] = "FORBIDDEN"
        elif code == 404:
            result["status_category"] = "NOT_FOUND"
        elif code == 410:
            result["status_category"] = "GONE"
        elif 400 <= code < 500:
            result["status_category"] = "CLIENT_ERROR"
        elif 500 <= code < 600:
            result["status_category"] = "SERVER_ERROR"
        else:
            result["status_category"] = f"HTTP_{code}"

    except requests.exceptions.Timeout:
        result["status_category"] = "TIMEOUT"
        result["error"] = "Request timed out after 15s"
    except requests.exceptions.SSLError as e:
        result["status_category"] = "SSL_ERROR"
        result["error"] = str(e)[:120]
    except requests.exceptions.ConnectionError as e:
        result["status_category"] = "CONNECTION_ERROR"
        result["error"] = str(e)[:120]
    except Exception as e:
        result["status_category"] = "ERROR"
        result["error"] = str(e)[:120]

    return result


def load_all_urls():
    """Collect all URLs from every metadata_ai.csv across all country directories."""
    all_entries = []
    missing_files = []

    for country_dir in sorted(DATA_DIR.iterdir()):
        if not country_dir.is_dir():
            continue
        iso = country_dir.name
        meta_file = country_dir / "metadata_ai.csv"
        if not meta_file.exists():
            missing_files.append(iso)
            continue

        try:
            with open(meta_file, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                if not rows:
                    continue
                if "URL" not in reader.fieldnames:
                    print(f"  WARNING: {iso}/metadata_ai.csv has no URL column")
                    continue
                for row in rows:
                    url = row.get("URL", "").strip()
                    all_entries.append((
                        iso,
                        row.get("Index", ""),
                        row.get("Source", ""),
                        url,
                    ))
        except Exception as e:
            print(f"  ERROR reading {meta_file}: {e}")

    return all_entries, missing_files


def run_checks(entries, max_workers=10):
    """Run URL checks concurrently."""
    session = make_session()
    tasks = [(iso, idx, src, url, session) for iso, idx, src, url in entries]

    results = []
    total = len(tasks)
    done = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(check_url, t): t for t in tasks}
        for future in as_completed(futures):
            done += 1
            result = future.result()
            results.append(result)
            if done % 25 == 0 or done == total:
                ok = sum(1 for r in results if r["status_category"] == "OK")
                broken = sum(1 for r in results if r["status_category"] in
                             ("NOT_FOUND", "GONE", "CONNECTION_ERROR", "TIMEOUT", "SSL_ERROR", "ERROR", "SERVER_ERROR"))
                print(f"  Progress: {done}/{total} checked | OK: {ok} | Broken: {broken}", end="\r")

    print()  # newline after progress
    return results


def write_report(results, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Full detailed CSV
    detail_path = output_dir / "url_check_results.csv"
    fieldnames = ["iso", "source_index", "source", "url", "status_code",
                  "status_category", "redirect_url", "response_time_s", "error"]
    with open(detail_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(sorted(results, key=lambda r: (r["iso"], r["source_index"])))

    # Broken-only CSV (actionable list)
    broken_categories = {"NOT_FOUND", "GONE", "CONNECTION_ERROR", "TIMEOUT",
                         "SSL_ERROR", "ERROR", "SERVER_ERROR", "CLIENT_ERROR"}
    broken = [r for r in results if r["status_category"] in broken_categories]
    broken_path = output_dir / "url_check_broken.csv"
    with open(broken_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(sorted(broken, key=lambda r: (r["iso"], r["source_index"])))

    # Summary by country and category
    from collections import defaultdict, Counter
    by_country = defaultdict(list)
    for r in results:
        by_country[r["iso"]].append(r["status_category"])

    summary_path = output_dir / "url_check_summary.txt"
    category_totals = Counter(r["status_category"] for r in results)

    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("=" * 60 + "\n")
        f.write("MOSAIC CHOLERA DATA — URL INTEGRITY REPORT\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 60 + "\n\n")

        f.write("OVERALL SUMMARY\n")
        f.write("-" * 40 + "\n")
        total = len(results)
        no_url = category_totals.get("NO_URL", 0)
        checked = total - no_url
        ok_count = category_totals.get("OK", 0)
        redirect_count = category_totals.get("REDIRECT", 0)
        forbidden_count = category_totals.get("FORBIDDEN", 0) + category_totals.get("AUTH_REQUIRED", 0)
        broken_count = sum(category_totals.get(c, 0) for c in broken_categories)

        f.write(f"Total URL entries:    {total}\n")
        f.write(f"Skipped (no URL):     {no_url}\n")
        f.write(f"Checked:              {checked}\n")
        f.write(f"  OK (2xx):           {ok_count}  ({100*ok_count/checked:.1f}%)\n")
        f.write(f"  Redirect (3xx):     {redirect_count}\n")
        f.write(f"  Forbidden/Auth:     {forbidden_count}  (paywall/access-restricted)\n")
        f.write(f"  BROKEN:             {broken_count}  ({100*broken_count/checked:.1f}%)\n")
        f.write("\nBroken breakdown:\n")
        for cat in sorted(broken_categories):
            n = category_totals.get(cat, 0)
            if n:
                f.write(f"  {cat:<20} {n}\n")

        f.write("\n" + "=" * 60 + "\n")
        f.write("BROKEN URLs BY COUNTRY\n")
        f.write("=" * 60 + "\n")
        if not broken:
            f.write("No broken URLs found.\n")
        else:
            by_iso = defaultdict(list)
            for r in broken:
                by_iso[r["iso"]].append(r)
            for iso in sorted(by_iso):
                f.write(f"\n{iso} ({len(by_iso[iso])} broken):\n")
                for r in by_iso[iso]:
                    f.write(f"  [{r['source_index']}] {r['status_category']} — {r['url'][:90]}\n")
                    f.write(f"       Source: {r['source'][:80]}\n")
                    if r["error"]:
                        f.write(f"       Error:  {r['error'][:80]}\n")

        f.write("\n" + "=" * 60 + "\n")
        f.write("PER-COUNTRY STATUS SUMMARY\n")
        f.write("=" * 60 + "\n")
        for iso in sorted(by_country):
            counts = Counter(by_country[iso])
            total_iso = len(by_country[iso])
            ok_iso = counts.get("OK", 0)
            broken_iso = sum(counts.get(c, 0) for c in broken_categories)
            forbidden_iso = counts.get("FORBIDDEN", 0) + counts.get("AUTH_REQUIRED", 0)
            flag = " ⚠" if broken_iso else ""
            f.write(f"  {iso}: {total_iso} URLs | OK={ok_iso} | Forbidden={forbidden_iso} | Broken={broken_iso}{flag}\n")

    return detail_path, broken_path, summary_path, broken_count, len(results)


def main():
    print(f"\nMOSAIC URL Integrity Checker")
    print(f"Data directory: {DATA_DIR}")
    print(f"Loading URLs from metadata_ai.csv files...")

    entries, missing = load_all_urls()

    if missing:
        print(f"  Countries with no metadata_ai.csv: {', '.join(missing)}")

    # Deduplicate URLs but keep all entries for the report
    unique_urls = set(url for _, _, _, url in entries if url)
    print(f"  Found {len(entries)} URL entries across {len(set(iso for iso,_,_,_ in entries))} countries")
    print(f"  Unique URLs to check: {len(unique_urls)}")
    print(f"\nChecking URLs (10 concurrent workers, 15s timeout each)...")
    print(f"This may take several minutes...\n")

    t_start = time.time()
    results = run_checks(entries, max_workers=10)
    elapsed = round(time.time() - t_start, 1)

    print(f"\nChecks complete in {elapsed}s. Writing report...")

    detail_path, broken_path, summary_path, n_broken, n_total = write_report(results, OUTPUT_DIR)

    print(f"\nResults written to:")
    print(f"  Summary:  {summary_path}")
    print(f"  Broken:   {broken_path}")
    print(f"  Full:     {detail_path}")

    # Print summary to stdout
    print("\n" + "=" * 60)
    with open(summary_path) as f:
        # Print just the overall summary section
        lines = f.readlines()
        for i, line in enumerate(lines):
            if "PER-COUNTRY STATUS" in line:
                break
        print("".join(lines[:i]))

    return 0 if n_broken == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
