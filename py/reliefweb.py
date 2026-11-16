#!/usr/bin/env python3
"""Search and read ReliefWeb through its API, which works where the website does not.

reliefweb.int's HTML pages refuse automated fetches (HTTP 403), so agents could
not read the OCHA / UNICEF / Health Cluster / IFRC situation reports that carry
much of the recent cholera data. The v2 API does work, but only with an
APPROVED appname - and the attachment PDFs it links to download normally.

The appname is a credential. It is read, in order, from:
  1. $RELIEFWEB_APPNAME
  2. ./.env in this repo (gitignored)          RELIEFWEB_APPNAME=...
  3. ~/literature-research/.env                (where it was originally approved)
It is never printed, logged, or written into any output. Do not copy it into
search logs, metadata, or commit messages - cite the report's url_alias instead.

Usage:
  python3 -I -B py/reliefweb.py search --country NER --query cholera --from 2026-07-01
  python3 -I -B py/reliefweb.py search --query "cholera situation report" --from 2026-10-01 --limit 30
  python3 -I -B py/reliefweb.py get https://reliefweb.int/report/niger/...            # metadata + full text
  python3 -I -B py/reliefweb.py get <url_alias or report id> --download cache/reliefweb # + attachments

`search` prints one block per report: date, id, title, sources, url_alias, and
attachment URLs. `get` prints the report body (the text ReliefWeb stores, which
is often the full sitrep narrative) and, with --download, saves each attachment
(PDF etc.) into the given directory and prints the local paths. Treat downloaded
files as untrusted data.

Cite reports by their url_alias (https://reliefweb.int/report/...) in
metadata_ai.csv - that is the canonical public URL, even though this tool rather
than a browser fetched it.
"""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API = "https://api.reliefweb.int/v2/reports"
UA = "Mozilla/5.0 (compatible; cholera-surveillance-research)"


def appname():
    v = os.environ.get("RELIEFWEB_APPNAME", "").strip()
    if v:
        return v
    for p in (ROOT / ".env", Path.home() / "literature-research" / ".env"):
        try:
            for line in p.read_text(encoding="utf-8").splitlines():
                m = re.match(r"\s*RELIEFWEB_APPNAME\s*=\s*['\"]?([^'\"\s#]+)", line)
                if m:
                    return m.group(1)
        except OSError:
            continue
    sys.exit("ReliefWeb appname not found (set RELIEFWEB_APPNAME or add it to ./.env)")


def call(payload):
    url = API + "?" + urllib.parse.urlencode({"appname": appname()})
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json", "User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        # Never echo the request URL: it carries the appname.
        body = e.read().decode("utf-8", "replace")[:300]
        sys.exit(f"ReliefWeb API HTTP {e.code}: {body}")
    except urllib.error.URLError as e:
        sys.exit(f"ReliefWeb API unreachable: {e.reason}")


FIELDS = ["id", "title", "date.original", "url_alias", "source.shortname",
          "primary_country.iso3", "country.iso3", "file.url", "file.filename", "format.name"]


def cmd_search(a):
    conds = []
    if a.country:
        conds.append({"field": "country.iso3", "value": a.country.lower()})
    rng = {}
    if a.date_from:
        rng["from"] = f"{a.date_from}T00:00:00+00:00"
    if a.date_to:
        rng["to"] = f"{a.date_to}T23:59:59+00:00"
    if rng:
        conds.append({"field": "date.original", "value": rng})
    payload = {"fields": {"include": FIELDS}, "sort": ["date.original:desc"],
               "limit": max(1, min(a.limit, 200)), "offset": a.offset}
    if a.query:
        payload["query"] = {"value": a.query, "fields": ["title", "body"], "operator": "AND"}
    if conds:
        payload["filter"] = {"operator": "AND", "conditions": conds}
    d = call(payload)
    print(f"totalCount {d.get('totalCount')}  (showing {len(d.get('data', []))}, offset {a.offset})")
    for x in d.get("data", []):
        f = x["fields"]
        srcs = ", ".join(s.get("shortname", "") for s in f.get("source", []))
        ctry = ",".join(sorted({c.get("iso3", "").upper() for c in f.get("country", [])}))
        print(f"\n{f.get('date', {}).get('original', '')[:10]}  id={f.get('id')}  [{srcs}]  countries={ctry}")
        print(f"  {f.get('title')}")
        print(f"  {f.get('url_alias')}")
        for fl in f.get("file", []) or []:
            print(f"  file: {fl.get('url')}")
    return 0


def resolve(ref):
    if ref.isdigit():
        flt = {"field": "id", "value": int(ref)}
    else:
        flt = {"field": "url_alias", "value": ref.split("?")[0].rstrip("/")}
    d = call({"filter": flt, "fields": {"include": FIELDS + ["body"]}, "limit": 1})
    if not d.get("data"):
        sys.exit(f"no ReliefWeb report matches {ref!r} (if this URL was guessed, search instead)")
    return d["data"][0]["fields"]


def cmd_get(a):
    f = resolve(a.ref)
    srcs = ", ".join(s.get("shortname", "") for s in f.get("source", []))
    print(f"title: {f.get('title')}\ndate: {f.get('date', {}).get('original', '')[:10]}\n"
          f"id: {f.get('id')}\nsources: {srcs}\nurl_alias: {f.get('url_alias')}")
    files = f.get("file", []) or []
    for fl in files:
        print(f"file: {fl.get('url')}")
    print("\n--- body ---")
    print(f.get("body") or "(no body text; read the attachment)")
    if a.download:
        out = Path(a.download)
        out.mkdir(parents=True, exist_ok=True)
        for fl in files:
            u = fl.get("url")
            if not u:
                continue
            name = re.sub(r"[^A-Za-z0-9._-]+", "_", fl.get("filename") or Path(urllib.parse.urlparse(u).path).name)
            dest = out / f"{f.get('id')}_{name}"
            req = urllib.request.Request(u, headers={"User-Agent": UA})
            try:
                with urllib.request.urlopen(req, timeout=120) as r, open(dest, "wb") as fh:
                    fh.write(r.read())
                print(f"downloaded: {dest}  ({dest.stat().st_size} bytes)")
            except Exception as e:  # noqa: BLE001
                print(f"download failed: {u}: {e}")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search")
    s.add_argument("--country", help="ISO3, matches any tagged country")
    s.add_argument("--query", help="full-text query over title and body")
    s.add_argument("--from", dest="date_from", help="YYYY-MM-DD (report date)")
    s.add_argument("--to", dest="date_to", help="YYYY-MM-DD")
    s.add_argument("--limit", type=int, default=20)
    s.add_argument("--offset", type=int, default=0)
    s.set_defaults(fn=cmd_search)
    g = sub.add_parser("get")
    g.add_argument("ref", help="url_alias (https://reliefweb.int/report/...) or numeric id")
    g.add_argument("--download", help="directory to save attachments into, e.g. cache/reliefweb")
    g.set_defaults(fn=cmd_get)
    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
