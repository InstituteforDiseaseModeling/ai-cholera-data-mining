#!/usr/bin/env python3
"""
URL-check the health_domains in reference/country_profiles.json.

country_profiles.json ships with `health_domains_verified: false` because the
domains were authored from model knowledge. An audit found roughly one in three
either does not resolve at all or resolves but fails over HTTPS - and agents
fetch over HTTPS, so a broken certificate is as good as a dead host. During an
unattended 40-country run each of those is a silently wasted query.

This script resolves every domain, records what actually happened, and writes
reference/country_profiles_domain_status.json. With --update it also flips the
`health_domains_verified` flag and stamps per-domain status into the profile so
agents can skip known-dead hosts.

Usage:
    python py/verify_country_profiles.py                # check, write status file
    python py/verify_country_profiles.py --update       # also annotate the profile
    python py/verify_country_profiles.py --timeout 15   # slower networks
"""

import argparse
import json
import ssl
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent
PROFILES = ROOT / "reference" / "country_profiles.json"
OUT = ROOT / "reference" / "country_profiles_domain_status.json"

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0 Safari/537.36")


def probe(domain, timeout):
    """Return a status dict for one domain. Never raises.

    Tries the bare host and, if that fails to resolve, the www. variant. Many
    government sites publish an A record only for www, so probing the bare host
    alone reports a live ministry as dead - it wrongly condemned COD's
    sante.gouv.cd and ZMB's znphi.co.zm, both of which serve fine on www.
    """
    result = {"domain": domain, "https": None, "http": None,
              "final_url": None, "status": None, "note": "",
              "resolved_as": domain}

    hosts = [domain]
    if not domain.startswith("www.") and "/" not in domain:
        hosts.append("www." + domain)

    for host in hosts:
        r = _probe_host(host, timeout)
        if r["status"] == "ok":
            r["domain"] = domain
            r["resolved_as"] = host
            return r
        result = r
        result["domain"] = domain
        result["resolved_as"] = host
    return result


def _probe_host(domain, timeout):
    result = {"domain": domain, "https": None, "http": None,
              "final_url": None, "status": None, "note": ""}

    for scheme in ("https", "http"):
        url = f"{scheme}://{domain}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA},
                                         method="GET")
            ctx = ssl.create_default_context()
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
                result[scheme] = r.status
                if scheme == "https" or result["https"] is None:
                    result["final_url"] = r.url
                if 200 <= r.status < 400:
                    break
        except urllib.error.HTTPError as e:
            # A 403/503 still proves the host exists and terminates TLS.
            result[scheme] = e.code
            result["note"] = f"HTTP {e.code}"
        except ssl.SSLCertVerificationError as e:
            result[scheme] = "tls_error"
            result["note"] = f"TLS: {str(e)[:90]}"
        except urllib.error.URLError as e:
            result[scheme] = "unreachable"
            reason = str(getattr(e, "reason", e))
            result["note"] = reason[:90]
            if "Name or service not known" in reason or "nodename nor servname" in reason:
                result[scheme] = "nxdomain"
        except Exception as e:  # noqa: BLE001
            result[scheme] = "error"
            result["note"] = f"{type(e).__name__}: {str(e)[:70]}"

    https_ok = isinstance(result["https"], int) and 200 <= result["https"] < 400
    http_ok = isinstance(result["http"], int) and 200 <= result["http"] < 400

    if https_ok:
        result["status"] = "ok"
    elif result["https"] in ("nxdomain",) and result["http"] in ("nxdomain", None):
        result["status"] = "dead"
    elif http_ok:
        # Agents fetch over HTTPS; HTTP-only is effectively unusable to them.
        result["status"] = "http_only"
    elif isinstance(result["https"], int):
        result["status"] = "blocked"   # exists, refuses us (403/503/etc.)
    else:
        result["status"] = "unreachable"
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--timeout", type=float, default=12.0)
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--update", action="store_true",
                    help="write status back into country_profiles.json")
    args = ap.parse_args()

    payload = json.loads(PROFILES.read_text())
    countries = payload["countries"]

    jobs = [(iso, d) for iso, p in countries.items() for d in p.get("health_domains", [])]
    print(f"Checking {len(jobs)} domains across {len(countries)} countries "
          f"(timeout {args.timeout}s)...\n")

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        results = list(ex.map(lambda j: (j[0], probe(j[1], args.timeout)), jobs))

    by_iso = {}
    counts = {}
    for iso, r in results:
        by_iso.setdefault(iso, []).append(r)
        counts[r["status"]] = counts.get(r["status"], 0) + 1

    icon = {"ok": "OK  ", "http_only": "HTTP", "blocked": "BLOK",
            "unreachable": "DEAD", "dead": "NXDM"}
    for iso in sorted(by_iso):
        for r in by_iso[iso]:
            if r["status"] != "ok":
                print(f"  {icon.get(r['status'],'????')}  {iso}  {r['domain']:34s} "
                      f"{r['note'][:60]}")

    total = len(results)
    ok = counts.get("ok", 0)
    print(f"\n  reachable over HTTPS : {ok}/{total} ({ok/total*100:.0f}%)")
    for k in ("http_only", "blocked", "unreachable", "dead"):
        if counts.get(k):
            print(f"  {k:20s} : {counts[k]}")

    OUT.write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "timeout_seconds": args.timeout,
        "summary": counts,
        "countries": {iso: rs for iso, rs in sorted(by_iso.items())},
    }, indent=2) + "\n")
    print(f"\nWrote {OUT.relative_to(ROOT)}")

    if args.update:
        for iso, rs in by_iso.items():
            countries[iso]["health_domains_status"] = {
                r["domain"]: r["status"] for r in rs
            }
        payload["metadata"]["health_domains_verified"] = True
        payload["metadata"]["health_domains_verified_at"] = \
            datetime.now(timezone.utc).isoformat()
        PROFILES.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
        print(f"Annotated {PROFILES.relative_to(ROOT)} "
              f"(health_domains_verified: true)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
