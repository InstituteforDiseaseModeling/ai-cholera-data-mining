#!/usr/bin/env python3
"""
Cross-country source harvesting.

Agents collect sources one country at a time, but many of those sources are
multi-country documents: ECDC Communicable Disease Threats Reports, WHO
multi-country cholera situation reports and epidemiological updates, the Weekly
Epidemiological Record (WER), WHO AFRO outbreak bulletins, Africa CDC weekly
reports, UNICEF and OCHA regional updates. A document found for country A
routinely carries figures for countries B and C that never cited it. A
2026-10-07 content study of 49 such documents found 389 MOSAIC-country cholera
figures, of which 58 (15%) had been used by the country they describe.

This tool finds those documents across all 40 countries' metadata, fetches each
once, extracts the figures they give for MOSAIC countries, screens every figure
against what the target country already has, and writes the ones that add
information through py/add_observation.py. Methodology, the agent extraction
protocol and the guardrails are in
.claude/skills/cross-country-source-harvesting/SKILL.md (with reference.md).

Run every subcommand with `python3 -I`: several read downloaded (untrusted)
documents, and -I keeps them from influencing the interpreter.

    python3 -I py/xref_harvest.py registry               # global sweep
    python3 -I py/xref_harvest.py fetch [--workers 6]    # global sweep
    python3 -I py/xref_harvest.py fetch --url URL --name NAME   # one document (Agent 5 push)
    python3 -I py/xref_harvest.py excerpt                # global sweep
    python3 -I py/xref_harvest.py parse                  # global sweep (ECDC, AFRO bulletins)
    python3 -I py/xref_harvest.py verify FILE            # agent self-check, read-only
    python3 -I py/xref_harvest.py screen                 # global sweep
    python3 -I py/xref_harvest.py apply --run RUN (--iso ISO | --all) [--dry-run]
    python3 -I py/xref_harvest.py rollback --run RUN (--iso ISO | --all) --reason TEXT
    python3 -I py/xref_harvest.py queue ISO              # read-only

Shared files are written under an internal lock (reference/.xref_tool.lock), so
do not wrap these commands in py/with_lock.py.

Files
  reference/xref/source_registry.csv     one row per multi-country document
  reference/xref/candidates/*.csv        extracted figures (auto_*.csv from `parse`;
                                         agent_<ISO>_a<N>_<YYYYMMDD>.csv from agents)
  reference/xref/candidates_screened.csv every candidate with flags and a decision
  reference/xref/harvest_log.csv         every row `apply` wrote (audit, rollback)
  cache/sources/<hash>/                  fetched documents (gitignored; untrusted)
  cache/xref_excerpts/<hash>.txt         cholera excerpts for agents (gitignored)
"""

import argparse
import csv
import fcntl
import hashlib
import html
import json
import re
import subprocess
import sys
import threading
import time
import zipfile
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import quote as urlquote, unquote, urljoin, urlparse

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
REF = ROOT / "reference"
XREF = REF / "xref"
CAND_DIR = XREF / "candidates"
REGISTRY = XREF / "source_registry.csv"
SCREENED = XREF / "candidates_screened.csv"
HARVEST_LOG = XREF / "harvest_log.csv"
ALIASES = XREF / "aliases.csv"
TOOL_LOCK = REF / ".xref_tool.lock"
CACHE = ROOT / "cache" / "sources"
EXCERPTS = ROOT / "cache" / "xref_excerpts"
TODAY = date.today()
UA = "Mozilla/5.0 (compatible; MOSAIC-cholera-research/1.0)"
csv.field_size_limit(sys.maxsize)

MOSAIC = sorted(k for k, v in json.load(open(REF / "country_mapping.json"))["countries"].items()
                if v.get("mosaic_framework"))

# ------------------------------------------------------------------ series --
# key: (reliability level, confidence weight for harvested rows, priority when
# two series give the same figure, display label). Classification is by host
# first (see classify): keywords in an agent-written Source name or Description
# mislabelled US State Department reports and IFRC appeals as WER.
SERIES = {
    "WER": (1, 0.90, 1, "WHO Weekly Epidemiological Record"),
    "WHO_MC": (1, 0.90, 2, "WHO multi-country cholera situation report / epidemiological update"),
    "AFRO_OEW": (1, 0.90, 3, "WHO AFRO Weekly Bulletin on Outbreaks and Other Emergencies"),
    "AFRICA_CDC": (2, 0.80, 4, "Africa CDC weekly epidemic intelligence report"),
    "ECDC": (2, 0.75, 5, "ECDC Communicable Disease Threats Report"),
    "UNICEF_REG": (2, 0.75, 6, "UNICEF regional cholera update"),
    "OCHA_REG": (2, 0.70, 7, "OCHA regional cholera update"),
}
CFR_CAP_WEIGHT = 0.60             # CFR 15-20%: kept, down-weighted
CFR_REVIEW_WEIGHT = 0.70          # CFR 10-15%: CLAUDE.md flags outside 0.5-10% for review
WHO_HOSTS = ("who.int", "iris.who.int", "apps.who.int", "afro.who.int", "cdn.who.int", "emro.who.int")

# --------------------------------------------------------------- countries --
# Most specific first; each match consumes its span. X codes are blockers:
# non-MOSAIC countries, and sub-national or false-friend names that contain a
# country name (Niger State, Zaire Province, Bas-Congo, Guinea worm, Benin City,
# Zanzibar, Somaliland, Cabinda). Long names match case-insensitively (WER and
# bulletins print "MALAWI"); short acronyms are case-sensitive.
_CI = lambda p: f"(?i:{p})"
COUNTRY_PATTERNS = [
    ("XZP", _CI(r"Zaire\s+Province|Prov[íi]ncia\s+do\s+Zaire|Zaire\s+province")),
    ("XBC", _CI(r"Bas[- ]Congo|Kongo[- ]Central")),
    ("XCB", _CI(r"Cabinda")),
    ("COD", _CI(r"Democratic\s+Republic\s+of\s+(?:the\s+)?Congo|Dem(?:ocratic|\.)\s*Rep(?:ublic|\.)?\s+(?:of\s+)?"
                r"(?:the\s+)?Congo|D\.?\s?R\.?\s+(?:of\s+(?:the\s+)?)?Congo\b|DR\s?Congo\b|R\.?\s?D\.?\s+(?:du\s+)?Congo\b|"
                r"RDCongo\b|Congo\s*,?\s*(?:the\s+)?Dem(?:ocratic|\.)?\s*Rep(?:ublic|\.)?(?:\s+of(?:\s+the)?)?|"
                r"Congo\s+D\.?\s?R\.?(?![a-z])|Congo\s*\(\s*(?:the\s+)?Dem[^)]{0,30}\)|Congo\s*\(\s*Kinshasa\s*\)|"
                r"Congo\s*\(\s*R\.?\s?D\.?\s*\)|Congo\s+R\.?\s?D\.?(?![a-z])|"
                r"Congo[- ]Kinshasa|R[ée]publique\s+d[ée]mocratique\s+du\s+Congo|R[ée]p\.?\s*d[ée]m\.?\s*du\s+Congo|"
                r"Rep[úu]blica\s+Democr[áa]tica\s+do\s+Congo|\bZa[iï]re\b") + r"|\bDRC\b|\bRDC\b"),
    ("SSD", _CI(r"South\s+Sudan|Soudan\s+du\s+Sud|Sud[ãa]o\s+do\s+Sul")),
    ("XSD", _CI(r"\bSudan\b|\bSoudan\b|\bSud[ãa]o\b")),
    ("CAF", _CI(r"Central\s+African\s+Rep(?:ublic|\.)?|R[ée]publique\s+centrafricaine|Rep[úu]blica\s+Centro-?Africana")
            + r"|\bCAR\b"),
    ("GNQ", _CI(r"Equatorial\s+Guinea|Guin[ée]e\s+[ée]quatoriale|Guin[ée]\s+Equatorial")),
    ("GNB", _CI(r"Guinea\s?[- ]\s?Bissau|Guin[ée]e?\s?[- ]\s?Bissau|Guinea\s+Bissau|Guin[ée]e?\s+Bissau")),
    ("XPG", _CI(r"Papua\s+New\s+Guinea|Nouvelle-Guin[ée]e")),
    ("XGW", _CI(r"Guinea[- ]worm|ver\s+de\s+Guin[ée]e")),
    ("GIN", _CI(r"\bGuinea\b|\bGuin[ée]e\b|\bGuin[ée]\b")),
    ("NGA", _CI(r"\bNigeria\b|\bNig[ée]ria\b")),
    ("XNS", _CI(r"Niger\s+State|Niger\s+Delta|River\s+Niger|Niger\s+River|fleuve\s+Niger")),
    ("NER", _CI(r"\bNiger\b|\bN[íi]ger\b")),
    ("COG", _CI(r"Republic\s+of\s+(?:the\s+)?Congo|Congo\s*,?\s*Rep(?:ublic|\.)?(?:\s+of)?(?![a-z])|"
                r"Congo[- ]Brazzaville|Congo\s*\(\s*Brazzaville\s*\)|R[ée]publique\s+du\s+Congo|"
                r"Rep[úu]blica\s+do\s+Congo|\bCongo\b")),
    ("CIV", _CI(r"C[ôo]te\s+d['’ʼ`´]?\s?Ivoire|Ivory\s+Coast|Costa\s+do\s+Marfim")),
    ("XZN", _CI(r"Zanzibar")),
    ("TZA", _CI(r"Tanzania|Tanzanie|Tanz[âa]nia")),
    ("SWZ", _CI(r"Eswatini|Swaziland|Essuat[íi]ni|Suazil[âa]ndia")),
    ("ZAF", _CI(r"South\s+Africa|Afrique\s+du\s+Sud|[ÁA]frica\s+do\s+Sul")),
    ("BFA", _CI(r"Burkina\s+Faso|Upper\s+Volta|Haute-Volta")),
    ("XBN", _CI(r"Benin\s+City")),
    ("BEN", _CI(r"\bBenin\b|\bB[ée]nin\b|\bDahomey\b")),
    ("ZWE", _CI(r"Zimbabwe|Zimbabu[ée]|Southern\s+Rhodesia|\bRhodesia\b")),
    ("NAM", _CI(r"Namibia|Namibie|Nam[íi]bia|South\s+West\s+Africa")),
    ("CMR", _CI(r"Cameroon|Cameroun|Camar[õo]es")),
    ("TCD", _CI(r"\bChad\b|\bTchad\b")),
    ("MRT", _CI(r"Mauritania|Mauritanie|Maurit[âa]nia")),
    ("SEN", _CI(r"Senegal|S[ée]n[ée]gal")),
    ("SLE", _CI(r"Sierra\s+Leone|Serra\s+Leoa")),
    ("GMB", _CI(r"\bGambia\b|\bGambie\b|\bG[âa]mbia\b")),
    ("ETH", _CI(r"Ethiopia|[ÉE]thiopie|Eti[óo]pia")),
    ("ERI", _CI(r"Eritrea|[ÉE]rythr[ée]e|Eritreia")),
    ("XSL", _CI(r"Somaliland|Puntland")),
    ("SOM", _CI(r"Somalia|Somalie|Som[áa]lia")),
    ("AGO", _CI(r"Angola")),
    ("BDI", _CI(r"Burundi")),
    ("BWA", _CI(r"Botswana")),
    ("GAB", _CI(r"\bGabon\b|\bGab[ãa]o\b")),
    ("GHA", _CI(r"\bGhana\b")),
    ("KEN", _CI(r"\bKenya\b|\bQu[ée]nia\b")),
    ("LBR", _CI(r"\bLiberia\b|\bLib[ée]ria\b")),
    ("MLI", _CI(r"\bMali\b")),
    ("MOZ", _CI(r"Mozambique|Mo[çc]ambique")),
    ("MWI", _CI(r"Malawi|Mal[áa]wi")),
    ("RWA", _CI(r"Rwanda|Ruanda")),
    ("TGO", _CI(r"\bTogo\b")),
    ("UGA", _CI(r"Uganda|Ouganda")),
    ("ZMB", _CI(r"Zambia|Zambie|Z[âa]mbia")),
    ("XOT", _CI(r"\b(?:Yemen|Y[ée]men|Afghanistan|Haiti|Ha[iï]ti|Comoros|Comores|Mayotte|Madagascar|Djibouti|"
                r"Lesotho|Mauritius|Maurice|Cabo\s+Verde|Cape\s+Verde|Sao\s+Tome|S[ãa]o\s+Tom[ée]|Egypt|Libya|"
                r"Tunisia|Algeria|Morocco|Syria|Lebanon|Iraq|Iran|Pakistan|India|Bangladesh|Nepal|Myanmar|"
                r"Burma|Philippines|Dominican\s+Republic|Sri\s+Lanka|China|Indonesia|Ecuador|Peru|Mexico|"
                r"Taiwan|Viet\s?Nam|Thailand|Malaysia|Cambodia|Saudi\s+Arabia|Oman|Kuwait|Bahrain|Qatar)\b")),
]
COUNTRY_RX = [(iso, re.compile(p)) for iso, p in COUNTRY_PATTERNS]
assert {iso for iso, _ in COUNTRY_PATTERNS if not iso.startswith("X")} == set(MOSAIC)


def find_countries(text):
    """Non-overlapping [(iso, start, end)] in text order, specific names first."""
    taken, out = [], []
    for iso, rx in COUNTRY_RX:
        for m in rx.finditer(text):
            s, e = m.span()
            if any(s < te and e > ts for ts, te in taken):
                continue
            taken.append((s, e))
            out.append((iso, s, e))
    return sorted(out, key=lambda x: x[1])


# ------------------------------------------------------------------- utils --
MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
MONTHS.update({"fév": 2, "fev": 2, "avr": 4, "mai": 5, "jui": 6, "aoû": 8, "aou": 8, "déc": 12,
               "janv": 1, "févr": 2, "juin": 6, "juil": 7, "sept": 9})
NUMBER_WORDS = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
                "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
                "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
                "nineteen": 19, "twenty": 20}


def d(s):
    try:
        y, m, dd = map(int, (s or "").strip()[:10].split("-"))
        return date(y, m, dd)
    except Exception:
        return None


def parse_text_date(s):
    """'12 July 2026', '09 August 2026', '1-Jan-21', '5-Aug-2021', '31 Dec 2025'."""
    s = (s or "").strip().replace(" ", " ")
    m = re.match(r"(\d{1,2})[\s-]+([A-Za-zéû]{3,})\.?[\s,-]+(\d{2,4})$", s)
    if not m:
        return None
    day, mon, yr = int(m.group(1)), m.group(2).lower(), int(m.group(3))
    mon = mon[:4] if mon[:4] in MONTHS else mon[:3]
    if mon not in MONTHS:
        return None
    if yr < 100:                       # 2-digit years: never in the future
        yr += 2000 if yr <= TODAY.year % 100 else 1900
    try:
        return date(yr, MONTHS[mon], day)
    except ValueError:
        return None


def to_int(tok):
    if tok is None:
        return None
    t = str(tok).strip().lower()
    if t in ("no", "zero"):
        return 0
    if t in NUMBER_WORDS:
        return NUMBER_WORDS[t]
    t = re.sub(r"[\s,  ']", "", t)
    return int(t) if t.isdigit() else None


def norm_text(t):
    """Whitespace/quote/dash-normalised text for verbatim quote checks."""
    t = t.replace("­", "").replace(" ", " ").replace(" ", " ").replace("﻿", "")
    t = re.sub(r"[’‘ʼ`´]", "'", t)
    t = re.sub(r"[“”]", '"', t)
    t = re.sub(r"[–—−]", "-", t)
    t = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1-\2", t)
    return re.sub(r"\s+", " ", t).strip()


def num_pattern(n):
    """Regex for integer n as printed (12345, 12 345, 12,345, 12.345), as a whole
    token: not preceded by a digit or digit+[,.], not followed by a digit or
    [,.]+digit, so a quote cut at '19' cannot stand for a printed 191."""
    s = str(n)
    if len(s) <= 3:
        core = s
    else:
        k = len(s) % 3 or 3
        core = s[:k] + "".join(rf"(?:,\s?|[ .\u00a0\u202f'])?{s[i:i + 3]}" for i in range(k, len(s), 3))  # incl. "8, 435"
    return rf"(?<!\d)(?<!\d[,.]){core}(?!\d)(?![,.]\d)"


_UNIT = r"(?:new\s+)?(?:suspected\s+|confirmed\s+)?(?:cholera\s+)?(?:cases?|deaths?|cas|d[ée]c[èe]s|casos|[óo]bitos)"


def value_in(v, text):
    """Is count v stated in text? Number words count only before a case/death noun."""
    if v is None:
        return True
    if re.search(num_pattern(v), text):
        return True
    for word, val in NUMBER_WORDS.items():
        if val == v and re.search(rf"\b{word}\s+{_UNIT}\b", text, re.I):
            return True
    # "no deaths were reported" is a zero; "no deaths data available" is not
    if v == 0 and re.search(rf"\bno\s+{_UNIT}\b(?!\s+(?:data|information|figures?|available|updates?|yet|"
                            rf"reports?\b|breakdown))", text, re.I):
        return True
    return False


def canon_url(url):
    u = unquote((url or "").strip())
    u = re.sub(r"^https?://(web\.)?archive\.org/web/\d+[a-z_]*/", "", u)
    u = re.sub(r"^https?://", "", u)
    u = re.sub(r"^www\.", "", u).split("#")[0].rstrip("/")
    u = re.sub(r"[?&](utm_[^&]+|ind=\d+|wpdmdl=\d+|sequence=\d+|isallowed=\w+)", "", u, flags=re.I)
    return u.lower()


def host_of(url):
    """Host of the document itself - a Wayback copy reports the archived host."""
    u = re.sub(r"^https?://(web\.)?archive\.org/web/\d+[a-z_]*/", "", (url or "").strip())
    h = urlparse(u if "://" in u else "https://" + u).netloc.lower()
    return h[4:] if h.startswith("www.") else h


def key_hash(k):
    return hashlib.sha1(k.encode()).hexdigest()[:16]


def read_csv(path):
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    tmp.replace(path)


@contextmanager
def tool_lock():
    """Serialise writers of shared reference/xref files across processes."""
    TOOL_LOCK.parent.mkdir(parents=True, exist_ok=True)
    with open(TOOL_LOCK, "w") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


# ---------------------------------------------------------------- identity --
PSEUDO_SOURCE = re.compile(r"\b(bundle|corpus|sweep|closure|compilation|systematic|volumes?\s+\d+\s*[-–]\s*\d+|"
                           r"vols?\.\s*\d+\s*[-–]|series\s*\(weeks|weeks?\s+\d+\s*[-–]\s*\d+)\b", re.I)


SIGNATURES = {   # post-fetch: the document must carry its series' own header
    "WER": r"weekly\s+epidemiological\s+record|relev[ée]\s+[ée]pid[ée]miologique\s+hebdomadaire|wkly\s+epidem",
    "AFRO_OEW": r"weekly\s+bulletin\s+on\s+outbreaks|outbreaks\s+and\s+other\s+emergencies|this\s+weekly\s+"
                r"bulletin\s+focuses|all\s+events\s+currently\s+being\s+monitored",
    "WHO_MC": r"multi-country\s+(?:outbreak\s+of\s+)?cholera|external\s+situation\s+report",
    "ECDC": r"communicable\s+disease\s+threats\s+report",
    "AFRICA_CDC": r"africa\s+cdc|africa\s+centres\s+for\s+disease",
    "UNICEF_REG": r"unicef|plateforme\s+chol[ée]ra|cholera\s+platform",
    "OCHA_REG": r"\bocha\b|coordination\s+of\s+humanitarian\s+affairs",
}
REGIONAL = (r"esaro|wcaro|\bwca\b|eastern\s+and\s+southern\s+africa|east\s+and\s+southern\s+africa|"
            r"west\s+and\s+central\s+africa|central\s+and\s+west\s+africa|southern\s+africa|east(?:ern)?\s+africa|"
            r"sahel|horn\s+of\s+africa|great\s+lakes|regional|platform|plateforme|rosea|rowca")


def classify(url, title):
    """Candidate series from the document's URL (host, path, file name) and its
    own title - never an agent-written Description - so keyword-rich notes cannot
    turn a State Department report into WER. Wayback copies are classified by the
    archived URL. `validate_series` then checks the fetched text carries the
    series' own header before anything is extracted from it."""
    c, h, t = canon_url(url), host_of(url), (title or "")
    ct = c + " " + t
    if PSEUDO_SOURCE.search(t):
        return None
    if h.endswith("ecdc.europa.eu"):
        if "cholera-monthly" in c or "/all-topics" in c:
            return None                      # live overview page: content replaced monthly
        if re.search(r"communicable-disease-threats-report|/documents/.*\.pdf", c) and \
                re.search(r"threats? report|cdtr|wcp-", ct, re.I):
            return "ECDC"
        return None
    who = h.endswith("who.int")
    rw = h.endswith("reliefweb.int")
    arch = h == "archive.org"
    if who or rw or arch:
        if re.search(r"/docstore/wer/|/wer\d{4}\.pdf|\bwer\d{4}|weekly-epidemiological-record", c) or \
                ((who or arch) and re.search(r"weekly\s+epidemiological\s+record|relev[ée]\s+[ée]pid[ée]miologique", t, re.I)):
            return "WER"
        if re.search(r"/oew\d|\boew\d{1,2}[-_]|weekly-bulletin-outbreaks", c) or \
                ((who or rw) and re.search(r"outbreaks\s+and\s+other\s+emergencies|\bOEW\s?\d", t, re.I)):
            return "AFRO_OEW"
        if re.search(r"cholera", ct, re.I) and \
                re.search(r"multi-country|external[- ]situation[- ]report|epidemiological[- ]update", ct, re.I) and (who or rw):
            return "WHO_MC"
    if h.endswith("africacdc.org") and re.search(r"weekly|epidemic-intelligence|event-based", ct, re.I):
        return "AFRICA_CDC"
    if h.endswith("plateformecholera.info") or ((h.endswith("unicef.org") or rw) and re.search(r"unicef", ct, re.I)
                                               and re.search(REGIONAL, t, re.I) and re.search(r"cholera|chol[ée]ra", ct, re.I)):
        return "UNICEF_REG"
    if (h.endswith("unocha.org") or rw) and re.search(r"\bocha\b|rosea|rowca", ct, re.I) and re.search(REGIONAL, t, re.I):
        return "OCHA_REG"
    return None


def validate_series(series, text):
    """The fetched document must carry its series' own header; regional
    UNICEF/OCHA documents must also discuss cholera in two or more MOSAIC
    countries. Returns a reason string when invalid, else ''."""
    head = text[:20000]
    if not re.search(SIGNATURES[series], head if series in ("ECDC", "WER") else text, re.I):
        return f"no {series} header in the document"
    if series in ("UNICEF_REG", "OCHA_REG", "AFRICA_CDC", "WHO_MC"):
        if not re.search(r"chol[eé]ra", text, re.I):
            return "no cholera content"
        if len({c for c, s, e in find_countries(text) if not c.startswith("X")}) < 2:
            return "fewer than two MOSAIC countries mentioned"
    return ""


def doc_key(url, name=""):
    """Stable identity for a document cited under different URLs/names. Depends
    only on URL and title - never on fetch results - so cache paths, candidate
    files and harvest_log entries keep their meaning across sweeps."""
    c, n, h = canon_url(url), name or "", host_of(url)
    who = h.endswith("who.int")
    # WER: docstore file name, or a single-issue WHO-hosted title
    m = re.search(r"/wer(\d{2})(\d{2})\.pdf", c)
    if m:
        return f"wer:{int(m.group(1))}:{int(m.group(2))}"
    if who and re.search(r"weekly\s+epidemiological\s+record|\bwer\b", n, re.I):
        issues = re.findall(r"\b(\d{2,3})\s*\(\s*(\d{1,2})\s*\)", n)
        vol_no = re.findall(r"vol(?:ume)?\.?\s*(\d{2,3})[,;]?\s*(?:no\.?|n°|issue)\s*(\d{1,2})\b", n, re.I)
        found = issues + vol_no
        if len(set(found)) == 1 and 45 <= int(found[0][0]) <= 110:
            return f"wer:{int(found[0][0])}:{int(found[0][1])}"
    # ECDC CDTR: year + week from URL, else title
    if h.endswith("ecdc.europa.eu"):
        wk = re.search(r"week[- ]?(\d{1,2})\b", c) or re.search(r"week\s*(\d{1,2})\b", n, re.I)
        yr = re.search(r"(20[12]\d)", c) or re.search(r"\b(20[12]\d)\b", n)
        if wk and yr:
            return f"ecdc:{yr.group(1)}:{int(wk.group(1))}"
    # WHO AFRO bulletins: OEW<week>-<dd><dd><mm><yyyy>.pdf -> year = last 4 digits
    m = re.search(r"oew0?(\d{1,2})[-_]?\d{0,8}?(20[12]\d)\.pdf", c)
    if m and 1 <= int(m.group(1)) <= 53:
        return f"oew:{m.group(2)}:{int(m.group(1))}"
    if who and re.search(r"outbreaks\s+and\s+other\s+emergencies", n, re.I):
        wk, yr = re.search(r"week\s*(\d{1,2})\b", n, re.I), re.findall(r"\b(20[12]\d)\b", n)
        if wk and len(set(yr)) == 1:
            return f"oew:{yr[0]}:{int(wk.group(1))}"
    # WHO multi-country situation reports / epidemiological updates
    if re.search(r"multi-country", c + " " + n, re.I):
        m = re.search(r"(external[- ]situation[- ]report|epidemiological[- ]update|sitrep)[^0-9]{0,8}(\d{1,3})(?!\d)",
                      c + " " + n, re.I)
        if m:
            kind = "esr" if "situation" in m.group(1).lower() or "sitrep" in m.group(1).lower() else "epi"
            return f"whomc:{kind}:{int(m.group(2))}"
    # Africa CDC: issue date from the file name, else the title
    if h.endswith("africacdc.org"):
        m = re.search(r"(\d{1,2})[_-]?([a-z]{3,9})[_-]?(20\d{2}|\d{2})(?:-\d)?\.pdf", c)
        if m and m.group(2)[:3] in MONTHS:
            y = int(m.group(3)) if len(m.group(3)) == 4 else 2000 + int(m.group(3))
            return f"africacdc:{y}-{MONTHS[m.group(2)[:3]]:02d}-{int(m.group(1)):02d}"
        m = re.search(r"(\d{1,2})\s+([A-Za-z]{3,})\s+(20\d\d)", n)
        if m and m.group(2)[:3].lower() in MONTHS:
            return f"africacdc:{m.group(3)}-{MONTHS[m.group(2)[:3].lower()]:02d}-{int(m.group(1)):02d}"
    m = re.search(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", c)
    if m:
        return "iris:" + m.group(0)
    m = re.search(r"10665/(\d{4,7})", c)
    if m:
        return "irish:" + m.group(1)
    return "url:" + c.split("?")[0]


def doc_date(k, meta=None):
    """Approximate publication date of a document, or None (undated)."""
    m = re.match(r"(?:ecdc|oew):(\d{4}):(\d{1,2})$", k)
    if m:
        try:
            dd = date.fromisocalendar(int(m.group(1)), int(m.group(2)), 7)
            return dd + timedelta(days=7) if k.startswith("oew") else dd
        except ValueError:
            return None
    m = re.match(r"wer:(\d+):(\d+)$", k)
    if m:
        return date(int(m.group(1)) + 1925, 1, 1) + timedelta(days=7 * int(m.group(2)))
    m = re.match(r"africacdc:(\d{4}-\d{2}-\d{2})$", k)
    if m:
        return d(m.group(1))
    if meta and meta.get("doc_date"):
        return d(meta["doc_date"])
    return None


def wer_kind(title, text=None):
    """WER content type. Weekly notification tables print several columns side by
    side, so a text line mixes countries and diseases and a verbatim quote can
    pair numbers with the wrong country. They are not harvested (a page-image
    pass is future work); annual cholera reports, provisional summaries and the
    multi-country updates are."""
    t = (title or "").lower()
    if text is not None:
        has_notif = re.search(r"notifications?\s+(?:of\s+diseases\s+)?re[cç]eived|notifications\s+(?:de\s+maladies\s+)?re[çc]ues|"
                              r"diseases\s+subject\s+to\s+the\s+"
                              r"regulations|maladies\s+soumises|infected\s+areas\s+as\s+on|zones\s+infect[ée]es", text, re.I)
        has_annual = re.search(r"cholera\s+in\s+(19|20)\d\d|cholera,\s+(19|20)\d\d|le\s+chol[ée]ra\s+en\s+(19|20)\d\d|"
                               r"chol[ée]ra,\s+(19|20)\d\d|multi-country\s+outbreak\s+of\s+cholera", text, re.I)
        if has_notif and not has_annual:
            return "notifications"
        if has_annual:
            return "annual"
    if re.search(r"diseases subject|maladies soumises|notifications? received|infected areas|ihr notification|"
                 r"cholera notification|notifications", t):
        return "notifications"
    if re.search(r"multi-country|monthly (cholera )?update", t):
        return "mc_update"
    if re.search(r"cholera[, ]+(in )?(19|20)\d\d|le chol[ée]ra en|annual cholera|global cholera|cholera situation|"
                 r"first (four|six|nine) months", t):
        return "annual"
    return "other"


# ---------------------------------------------------------------- coverage --
EPOCH = date(1960, 1, 1)
NDAYS = (TODAY - EPOCH).days + 800


# WHO region prefixes in Location codes: JHU codes Somalia EMR::SOM (WHO EMRO),
# and an AFR-only filter hid all 736 of its rows from screening.
REGION_PREFIXES = ("AFR", "EMR")


def is_national(loc, iso):
    return (loc or "").strip() in {f"{p_}::{iso}" for p_ in REGION_PREFIXES}


def is_subnational(loc, iso):
    return any((loc or "").strip().startswith(f"{p_}::{iso}::") for p_ in REGION_PREFIXES)


def national_rows(iso):
    """National rows with a case count, all layers:
    [(tl, tr, sch, layer, index, evidence)]. JHU 'Phantom: True' rows (derived,
    not reported) are left out: a 6-case phantom over 2017-2019 turned BDI's
    reported 2019 figures into conflicts."""
    out = []
    for layer in ("ai", "jhu", "who"):
        for r in read_csv(DATA / iso / f"cholera_data_{layer}.csv"):
            if not is_national(r.get("Location"), iso):
                continue
            if "Phantom: True" in (r.get("processing_notes") or ""):
                continue
            raw = (r.get("sCh") or "").strip()
            if raw == "":
                continue
            try:
                s = float(raw)
            except ValueError:
                continue
            tl, tr = d(r.get("TL")), d(r.get("TR"))
            if tl and tr and tl <= tr:
                notes = r.get("processing_notes") or ""
                ev = ("documented" if "Documented_Absence" in notes else
                      "inferred" if "Inferred_Absence" in notes else "")
                out.append((tl, tr, s, layer.upper(), r.get("Index", ""), ev))
    return out


def subnational_rows(iso):
    """Sub-national rows with a case count, all layers: [(tl, tr, sch, layer, index, location)]."""
    out = []
    for layer in ("ai", "jhu", "who"):
        for r in read_csv(DATA / iso / f"cholera_data_{layer}.csv"):
            loc = (r.get("Location") or "").strip()
            if not is_subnational(loc, iso):
                continue
            try:
                s = float((r.get("sCh") or "").strip())
            except ValueError:
                continue
            tl, tr = d(r.get("TL")), d(r.get("TR"))
            if tl and tr and tl <= tr:
                out.append((tl, tr, s, layer.upper(), r.get("Index", ""), loc))
    return out


class Coverage:
    """Per-day finest span of national rows (positive, and zero separately)."""

    def __init__(self, iso, rows=None):
        import numpy as np
        self.np = np
        self.rows = rows if rows is not None else national_rows(iso)
        self.finest = np.full(NDAYS, 10 ** 9, dtype=np.int64)
        self.zero_finest = np.full(NDAYS, 10 ** 9, dtype=np.int64)
        for tl, tr, s, layer, idx, ev in self.rows:
            a, b = max(0, (tl - EPOCH).days), min(NDAYS - 1, (tr - EPOCH).days)
            if b < a:
                continue
            arr = self.zero_finest if s == 0 else self.finest
            seg = arr[a:b + 1]
            np.minimum(seg, (tr - tl).days + 1, out=seg)

    def _frac(self, tl, tr, arr, max_span):
        a, b = max(0, (tl - EPOCH).days), min(NDAYS - 1, (tr - EPOCH).days)
        if b < a:
            return 0.0
        seg = arr[a:b + 1]
        return float((seg <= max_span).sum()) / len(seg)

    def equal_or_finer(self, tl, tr):
        """Share of the period's days covered by a positive OR zero row no coarser
        than max(7 days, the period) - the union, at week resolution."""
        span = max(7, (tr - tl).days + 1)
        return self._frac(tl, tr, self.np.minimum(self.finest, self.zero_finest), span)

    def zero_cover(self, tl, tr):
        return self._frac(tl, tr, self.zero_finest, 10 ** 8)


def cover_fraction(rows, tl, tr):
    """Share of [tl, tr]'s days covered by rows (positive or zero) no coarser than
    max(7 days, the period) - Coverage.equal_or_finer for an explicit row list."""
    span = max(7, (tr - tl).days + 1)
    covered = set()
    for etl, etr, s, *_rest in rows:
        if (etr - etl).days + 1 > span or etr < tl or etl > tr:
            continue
        a, b = max(etl, tl), min(etr, tr)
        covered.update(range(a.toordinal(), b.toordinal() + 1))
    return len(covered) / ((tr - tl).days + 1)


def load_gaps():
    g = defaultdict(list)
    for r in read_csv(REF / "effective_surveillance_gaps_detailed.csv"):
        a, b = d(r["gap_start"]), d(r["gap_end"])
        if a and b:
            g[r["iso_code"]].append((a, b))
    return g


# ---------------------------------------------------------------- registry --
def metadata_docs():
    """Yield (iso, metadata row, series, doc_key) for every harvestable entry."""
    for iso in MOSAIC:
        for m in read_csv(DATA / iso / "metadata_ai.csv"):
            url = (m.get("URL") or "").strip()
            if not url.lower().startswith(("http://", "https://")):
                continue
            series = classify(url, m.get("Source", ""))
            if series:
                yield iso, m, series, doc_key(url, m.get("Source", ""))


def build_registry(quiet=False):
    docs = {}
    for iso, m, series, k in metadata_docs():
        idx = (m.get("Index") or "").strip()
        e = docs.setdefault(k, {"series": Counter(), "names": Counter(), "urls": Counter(),
                                "citing": defaultdict(list), "periods": set(), "date_ranges": set()})
        e["series"][series] += 1
        e["names"][m.get("Source", "").strip()] += 1
        e["urls"][m["URL"].strip()] += 1
        e["citing"][iso].append(idx)
        ds = re.findall(r"(\d{4}-\d{2}-\d{2})", m.get("Date_Range", "") or "")
        if len(ds) >= 2 and d(ds[0]) and d(ds[-1]) and d(ds[0]) <= d(ds[-1]):
            e["date_ranges"].add((d(ds[0]), d(ds[-1])))
    idx_periods = defaultdict(list)
    for iso in MOSAIC:
        for r in read_csv(DATA / iso / "cholera_data_ai.csv"):
            tl, tr = d(r.get("TL")), d(r.get("TR"))
            if tl and tr:
                idx_periods[(iso, (r.get("source_index") or "").strip())].append((tl, tr))
    cov = {iso: Coverage(iso) for iso in MOSAIC}
    out = []
    for k, e in docs.items():
        for iso, idxs in e["citing"].items():
            for idx in idxs:
                e["periods"].update(idx_periods.get((iso, idx), []))
        series = e["series"].most_common(1)[0][0]
        periods = sorted(e["periods"]) or sorted(e["date_ranges"])
        if len(periods) > 60:
            periods = periods[:: max(1, len(periods) // 60)]
        bene = [iso for iso in MOSAIC if iso not in e["citing"] and
                (not periods or any(cov[iso].equal_or_finer(a, b) < 0.5 for a, b in periods))]
        level, weight = SERIES[series][0], SERIES[series][1]
        best = sorted(e["urls"], key=lambda u: (not re.search(r"\.pdf($|\?)|/content$|/bitstreams?/", u, re.I),
                                                 "web.archive.org" in u, -e["urls"][u]))[0]
        title = e["names"].most_common(1)[0][0][:240]
        dd_ = doc_date(k)
        out.append({
            "doc_key": k, "series": series, "reliability_level": level, "weight": weight,
            "title": title, "best_url": best, "n_urls": len(e["urls"]), "urls": " | ".join(list(e["urls"])[:8]),
            "n_citing": len(e["citing"]), "citing": " ".join(sorted(e["citing"])),
            "citing_indices": " ".join(f"{i}:{','.join(v)}" for i, v in sorted(e["citing"].items())),
            "n_periods": len(e["periods"]) or len(e["date_ranges"]),
            "period_min": str(min(p[0] for p in periods)) if periods else "",
            "period_max": str(max(p[1] for p in periods)) if periods else "",
            "doc_date": str(dd_) if dd_ else "",
            "n_beneficiaries": len(bene), "beneficiaries": " ".join(bene),
            "wer_kind": wer_kind(" | ".join(e["names"])) if series == "WER" else "",
        })
    out.sort(key=lambda r: (r["series"], r["doc_key"]))
    with tool_lock():
        write_csv(REGISTRY, out, list(out[0].keys()))
    if not quiet:
        sc = Counter(r["series"] for r in out)
        print(f"{len(out)} multi-country documents -> {REGISTRY.relative_to(ROOT)}")
        for s, n in sc.most_common():
            rs = [r for r in out if r["series"] == s]
            print(f"  {s:11s} docs={n:5d}  cited-by-1={sum(1 for r in rs if r['n_citing'] == 1):5d}"
                  f"  with-beneficiaries={sum(1 for r in rs if r['n_beneficiaries'] > 0):5d}")
    return out


def cmd_registry(a):
    build_registry()
    return 0


def doc_info(k, reg=None):
    """Registry row for a doc_key, falling back to the cache (single-doc fetches)."""
    reg = reg if reg is not None else {r["doc_key"]: r for r in read_csv(REGISTRY)}
    if k in reg:
        return reg[k]
    mf = CACHE / key_hash(k) / "meta.json"
    if mf.exists():
        m = json.loads(mf.read_text())
        s = m.get("series", "")
        if s in SERIES:
            return {"doc_key": k, "series": s, "reliability_level": SERIES[s][0], "weight": SERIES[s][1],
                    "title": m.get("title", ""), "best_url": m.get("url_used", ""), "urls": m.get("url_used", ""),
                    "citing": m.get("citing", ""), "doc_date": m.get("doc_date", ""), "wer_kind": ""}
    return None


# ------------------------------------------------------------------- fetch --
_THROTTLE = {"iris.who.int": 1.5, "apps.who.int": 1.5}   # min seconds between requests, per host
_last_hit, _throttle_lock = {}, threading.Lock()


def _throttle(url):
    """IRIS blocks clients that hit it hard (2026-10-07: a 6-worker sweep was
    cut off for hours), so requests to it are spaced out across all threads."""
    h = host_of(url)
    gap = next((g for k, g in _THROTTLE.items() if h.endswith(k)), 0)
    if not gap:
        return
    with _throttle_lock:
        wait = _last_hit.get(h, 0) + gap - time.time()
        if wait > 0:
            time.sleep(wait)
        _last_hit[h] = time.time()


def curl(url, dest, timeout=90):
    if not url.lower().startswith(("http://", "https://")):
        return 0, url, ""
    _throttle(url)
    r = subprocess.run(["curl", "-sSL", "--proto", "=http,https", "--max-time", str(timeout), "--retry", "2",
                        "--retry-delay", "3", "-A", UA, "-o", str(dest), "-w",
                        "%{http_code}\t%{url_effective}\t%{content_type}", url],
                       capture_output=True, text=True)
    parts = (r.stdout or "").split("\t")
    code = int(parts[0]) if parts and parts[0].isdigit() else 0
    return code, (parts[1] if len(parts) > 1 else url), (parts[2] if len(parts) > 2 else "")


def get_json(url, work):
    f = work / ("j_" + key_hash(url) + ".json")
    code, _, _ = curl(url, f, 60)
    try:
        if code != 200 or not f.exists():
            return None
        return json.loads(f.read_text(errors="replace"))
    except ValueError:
        return None
    finally:
        f.unlink(missing_ok=True)


def iris_item(url, work):
    c = canon_url(url)
    uu = re.search(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", c)
    api = "https://iris.who.int/server/api"
    if uu and "/bitstreams/" in c:
        b = get_json(f"{api}/core/bitstreams/{uu.group(0)}/bundle", work)
        href = (((b or {}).get("_links") or {}).get("item") or {}).get("href")
        return get_json(href, work) if href else None
    if uu and "/items/" in c:
        return get_json(f"{api}/core/items/{uu.group(0)}", work)
    h = re.search(r"10665/(\d{4,7})", c)
    if h:
        return get_json(f"{api}/pid/find?id=10665/{h.group(1)}", work)
    return None


def pdftotext(pdf):
    out = pdf.with_suffix(".txt")
    subprocess.run(["pdftotext", "-layout", str(pdf), str(out)], capture_output=True)
    return out.read_text(errors="replace") if out.exists() else ""


def iris_download(item, work, prefer_pdf):
    """An IRIS item's text: its PDF through pdftotext -layout (keeps table rows
    together), or IRIS's TEXT bundle, which scrambles tables, as a fallback."""
    bundles = get_json(item["_links"]["bundles"]["href"], work) or {}
    by = {b["name"]: b for b in (bundles.get("_embedded") or {}).get("bundles", [])}

    def bits(name):
        if name not in by:
            return []
        j = get_json(by[name]["_links"]["bitstreams"]["href"], work) or {}
        return (j.get("_embedded") or {}).get("bitstreams", [])
    for b in sorted([b for b in bits("ORIGINAL") if b.get("name", "").lower().endswith(".pdf")],
                    key=lambda b: -(b.get("sizeBytes") or 0))[:1]:
        f = work / "source.pdf"
        code, _, _ = curl(b["_links"]["content"]["href"], f, 180)
        if code == 200 and f.exists() and f.read_bytes()[:5] == b"%PDF-":
            text = pdftotext(f)
            if len(norm_text(text)) > 300 or prefer_pdf:
                return text, "iris_pdf"
    txts = [b for b in bits("TEXT") if b.get("name", "").lower().endswith(".txt")]
    parts = []
    for b in txts[:3]:
        f = work / "iris_text.txt"
        code, _, _ = curl(b["_links"]["content"]["href"], f)
        if code == 200 and f.exists():
            parts.append(f.read_text(errors="replace"))
    if sum(len(p) for p in parts) > 300:
        return "\n\n".join(parts), "iris_text"
    return None, "iris_no_file"


def html_to_text(h):
    h = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", h)
    h = re.sub(r"(?i)<br\s*/?>|</p>|</tr>|</li>|</h\d>|</div>", "\n", h)
    h = re.sub(r"(?i)</t[dh]>", "    ", h)
    h = re.sub(r"<[^>]+>", " ", h)
    return html.unescape(h)


def identity_tokens(k):
    """Tokens a linked PDF's file name must contain to be this document."""
    m = re.match(r"ecdc:(\d{4}):(\d+)$", k)
    if m:
        return [rf"week[-_ ]?0?{int(m.group(2))}\b", m.group(1)]
    m = re.match(r"whomc:\w+:(\d+)$", k)
    if m:
        return [rf"(?<!\d)0?{m.group(1)}(?!\d)"]
    m = re.match(r"oew:(\d{4}):(\d+)$", k)
    if m:
        return [rf"oew0?{int(m.group(2))}\b", m.group(1)]
    m = re.match(r"wer:(\d+):(\d+)$", k)
    if m:
        return [rf"wer0?{m.group(1)}0?{m.group(2)}(?!\d)"]
    return None


def zip_member_date_ok(name, k):
    m = re.match(r"africacdc:(\d{4})-(\d{2})-(\d{2})$", k)
    if not m:
        return True
    y, mo, dd = int(m.group(1)), int(m.group(2)), int(m.group(3))
    mon = [n for n, i in MONTHS.items() if i == mo and len(n) == 3]
    pats = [rf"(?<!\d)0?{dd}[_ -]*(?:{'|'.join(mon)})[a-z]*[_ -]*(?:{y}|{y % 100})"]
    return any(re.search(p, name, re.I) for p in pats)


def fetch_url(url, work, series, k):
    """Return (text, method, final_url, iris_item). Never executes fetched content."""
    c = canon_url(url)
    wayback_copy = bool(re.match(r"https?://(web\.)?archive\.org/web/", url))
    if ("iris.who.int" in c or "apps.who.int/iris" in c) and not wayback_copy:
        item = iris_item(url, work)
        if item:
            text, method = iris_download(item, work, prefer_pdf=series in ("AFRO_OEW", "WER", "WHO_MC"))
            if text:
                return text, method, url, item
    m_ia = re.match(r"(?:https?://)?(?:www\.)?archive\.org/details/([^/?#]+)", url)
    if m_ia:
        meta = get_json(f"https://archive.org/metadata/{m_ia.group(1)}", work) or {}
        txt = [f["name"] for f in meta.get("files", []) if f.get("name", "").endswith("_djvu.txt")]
        if txt:
            f = work / "ia_djvu.txt"
            code, final, _ = curl(f"https://archive.org/download/{m_ia.group(1)}/{urlquote(txt[0])}", f, 180)
            if code == 200 and f.exists():
                return f.read_text(errors="replace"), "archive_org_ocr", final, None
        return None, "archive_org_no_text", url, None
    raw = work / "download.bin"
    code, final, ctype = curl(url, raw)
    if code != 200 or not raw.exists() or raw.stat().st_size < 200:
        return None, f"http_{code}", final, None
    head = raw.read_bytes()[:5]
    if head == b"%PDF-":
        pdf = work / "source.pdf"
        raw.replace(pdf)
        return pdftotext(pdf), "pdf", final, None
    if head[:4] == b"PK\x03\x04":
        # Download managers (Africa CDC) serve multi-report packages as ZIPs. One
        # document per member: keep only the member dated like this doc_key.
        # Read members in memory (never extract paths: zip-slip) and cap sizes.
        texts = []
        try:
            with zipfile.ZipFile(raw) as z:
                for info in z.infolist()[:20]:
                    if not info.filename.lower().endswith(".pdf") or info.file_size > 60_000_000:
                        continue
                    if not zip_member_date_ok(Path(info.filename).name, k):
                        continue
                    pdf = work / f"member_{len(texts)}.pdf"
                    pdf.write_bytes(z.read(info))
                    if pdf.read_bytes()[:5] == b"%PDF-":
                        texts.append(pdftotext(pdf))
        except zipfile.BadZipFile:
            return None, "zip_bad", final, None
        raw.unlink(missing_ok=True)
        if len(texts) == 1:
            return texts[0], "zip_member", final, None
        return None, ("zip_ambiguous" if texts else "zip_no_matching_member"), final, None
    h = raw.read_text(errors="replace")
    if h.count("�") > 0.01 * max(len(h), 1) or "\x00" in h[:2000]:
        return None, "binary_unknown", final, None
    if "<html" in h[:3000].lower() or "html" in ctype:
        toks = identity_tokens(k)
        base_host = host_of(final)
        for mm in re.finditer(r"""href=["']([^"']+?\.pdf(?:\?[^"']*)?)["']""", h, re.I):
            link = urljoin(final, html.unescape(mm.group(1)))
            if not link.lower().startswith(("http://", "https://")) or \
                    host_of(link).split(".")[-2:] != base_host.split(".")[-2:]:
                continue
            fname = unquote(urlparse(link).path.rsplit("/", 1)[-1])
            sole_attachment = (base_host.endswith("reliefweb.int") and "/attachments/" in link and
                               len({m2.group(1) for m2 in re.finditer(r"""href=["']([^"']*/attachments/[^"']+?\.pdf)""", h, re.I)}) == 1)
            if (toks and all(re.search(t, fname, re.I) for t in toks)) or sole_attachment:
                pdf = work / "source.pdf"
                code2, final2, _ = curl(link, pdf, 180)
                if code2 == 200 and pdf.exists() and pdf.read_bytes()[:5] == b"%PDF-":
                    return pdftotext(pdf), "html_pdf", final2, None
        return html_to_text(h), "html", final, None
    return h, "text", final, None


def wayback(url, work, when):
    ts = (when or TODAY).strftime("%Y%m%d")
    j = get_json(f"https://archive.org/wayback/available?url={urlquote(canon_url(url), safe='')}&timestamp={ts}", work)
    snap = (((j or {}).get("archived_snapshots") or {}).get("closest") or {})
    if snap.get("available") and snap.get("url"):
        return re.sub(r"/web/(\d+)/", r"/web/\1id_/", snap["url"])
    return None


def fetch_doc(row):
    k = row["doc_key"]
    dest = CACHE / key_hash(k)
    if (dest / "text.txt").exists():
        return k, "cached"
    dest.mkdir(parents=True, exist_ok=True)
    work = dest / "work"
    work.mkdir(exist_ok=True)
    urls = [row["best_url"]] + [u.strip() for u in row["urls"].split("|") if u.strip() and u.strip() != row["best_url"]]
    when = d(row.get("period_max")) or doc_date(k)
    text, method, used, item, snap = None, "none", "", None, ""
    for u in urls[:4]:
        text, method, used, item = fetch_url(u, work, row["series"], k)
        if text and len(norm_text(text)) > 300:
            used = u
            break
        wb = wayback(u, work, when)
        if wb:
            text, method, _, item = fetch_url(wb, work, row["series"], k)
            if text and len(norm_text(text)) > 300:
                used, snap, method = u, wb, "wayback_" + method
                break
        time.sleep(0.5)
    meta = {"doc_key": k, "series": row["series"], "title": row.get("title", ""), "url_used": used,
            "wayback_snapshot": snap, "method": method, "citing": row.get("citing", ""),
            "doc_date": row.get("doc_date", ""), "fetched_at": datetime.now().isoformat(timespec="seconds")}
    if item:
        meta["iris_item"] = item.get("uuid")
        meta["iris_name"] = item.get("name")
    for f in work.glob("*"):
        if f.name == "source.pdf":
            f.replace(dest / "source.pdf")
        else:
            f.unlink(missing_ok=True)
    try:
        work.rmdir()
    except OSError:
        pass
    invalid = validate_series(row["series"], text) if text and len(norm_text(text)) > 300 else ""
    if invalid:
        meta["invalid_reason"] = invalid
        text = None
    if text and len(norm_text(text)) > 300:
        (dest / "text.txt").write_text(text)
        meta.update(sha256=hashlib.sha256(text.encode()).hexdigest(), chars=len(text), status="ok")
        if row["series"] == "WER":
            meta["wer_kind"] = wer_kind(row.get("title", "") + " " + (meta.get("iris_name") or ""), text)
    else:
        meta["status"] = "invalid_series" if invalid else "failed"
    (dest / "meta.json").write_text(json.dumps(meta, indent=1))
    return k, meta["status"]


def cmd_fetch(a):
    if a.url:
        series = classify(a.url, a.name)
        if not series:
            print(f"not a harvestable multi-country document (series unknown): {a.url}")
            return 1
        k = doc_key(a.url, a.name)
        dd_ = doc_date(k)
        row = {"doc_key": k, "series": series, "title": a.name, "best_url": a.url, "urls": a.url,
               "citing": a.citing, "doc_date": str(dd_) if dd_ else "", "period_max": ""}
        print(f"{k} [{series}]: {fetch_doc(row)[1]} -> {(CACHE / key_hash(k)).relative_to(ROOT)}")
        return 0
    reg = read_csv(REGISTRY)
    todo = [r for r in reg if r["series"] in SERIES and (a.all or int(r["n_beneficiaries"]) > 0)
            and not (r.get("wer_kind") == "notifications" and not a.include_notifications)]
    if a.series:
        todo = [r for r in todo if r["series"] in a.series.split(",")]
    todo = [r for r in todo if not (CACHE / key_hash(r["doc_key"]) / "text.txt").exists()
            and not (a.skip_failed and (CACHE / key_hash(r["doc_key"]) / "meta.json").exists())]
    if a.exclude_host:
        todo = [r for r in todo if not any(h in canon_url(r["best_url"]) for h in a.exclude_host.split(","))]
    if a.only_host:
        todo = [r for r in todo if any(h in canon_url(r["best_url"]) for h in a.only_host.split(","))]
    if a.limit:
        todo = todo[: a.limit]
    print(f"fetching {len(todo)} documents into {CACHE.relative_to(ROOT)}/ ({a.workers} workers)", flush=True)
    stats = Counter()
    with ThreadPoolExecutor(a.workers) as ex:
        for i, (k, st) in enumerate(ex.map(fetch_doc, todo), 1):
            stats[st] += 1
            if i % 50 == 0:
                print(f"  {i}/{len(todo)} {dict(stats)}", flush=True)
    print("done:", dict(stats))
    return 0


def cmd_aliases(a):
    """Map ReliefWeb report pages to their PDF attachments (one document, two
    URLs), so a country citing the page counts as citing the attachment."""
    reg = read_csv(REGISTRY)
    known = {(r["doc_key"], r["alias_key"]) for r in read_csv(ALIASES)}
    work = CACHE.parent / "alias_work"
    work.mkdir(parents=True, exist_ok=True)
    pages = [r for r in reg if "reliefweb.int/report/" in canon_url(r["best_url"])]
    out, n = list(read_csv(ALIASES)), 0
    for r in pages:
        f = work / "page.html"
        code, final, ctype = curl(r["best_url"], f, 60)
        if code != 200 or not f.exists():
            continue
        h = f.read_text(errors="replace")
        for uuid_ in sorted(set(re.findall(r"/attachments/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/", h))):
            pair = (r["doc_key"], "iris:" + uuid_)        # attachment doc_keys carry the UUID
            if pair not in known:
                known.add(pair)
                out.append({"doc_key": pair[0], "alias_key": pair[1], "how": "reliefweb attachment"})
                n += 1
        time.sleep(0.3)
    f.unlink(missing_ok=True)
    with tool_lock():
        write_csv(ALIASES, out, ["doc_key", "alias_key", "how"])
    print(f"{len(pages)} ReliefWeb report pages checked; +{n} aliases ({len(out)} total) -> {ALIASES.relative_to(ROOT)}")
    return 0


# ----------------------------------------------------------------- excerpt --
STOP_HDR = re.compile(r"\n[ \t]*(PLAGUE|PESTE|YELLOW FEVER|FI[ÈE]VRE JAUNE|SMALLPOX|VARIOLE|Poliomyelitis|Poliovirus|"
                      r"Ebola|Mpox|Monkeypox|Measles|Dengue|Influenza|Diphtheria|Meningitis|Anthrax|Lassa|Marburg|"
                      r"Rift Valley|Chikungunya|COVID)\b", re.I)


def cholera_spans(text):
    spans = []
    for m in re.finditer(r"chol[eé]ra", text, re.I):
        stop = STOP_HDR.search(text, m.end(), min(len(text), m.end() + 8000))
        spans.append((max(0, m.start() - 400), stop.start() if stop else min(len(text), m.end() + 4000)))
    spans.sort()
    merged = []
    for s, e in spans:
        if merged and s <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
        else:
            merged.append((s, e))
    return merged


def make_excerpt(text, focus, cap=16000):
    keep = set()
    # split on "\n" only: splitlines() also breaks on pdftotext's form feeds,
    # so its line numbers drift from what an editor or grep shows for full_text
    lines = text.split("\n")
    offsets, pos = [], 0
    for ln in lines:
        offsets.append(pos)
        pos += len(ln) + 1
    spans = cholera_spans(text)

    def in_span(off):
        return any(s <= off < e for s, e in spans)
    scored = []
    for i, ln in enumerate(lines):
        if not in_span(offsets[i]) or not re.search(r"\d", ln):
            continue
        isos = {x[0] for x in find_countries(ln) if not x[0].startswith("X")}
        if isos:
            scored.append((2 if isos & focus else 1, i))
    header_rx = re.compile(r"\b(Table|Country|Pays|Cases|Cas|Deaths|D[ée]c[èe]s|Cumulative|since|as of|CHOLERA|"
                           r"CHOL[ÉE]RA)\b", re.I)
    for score, i in sorted(scored, reverse=True):
        for j in range(max(0, i - 2), min(len(lines), i + 3)):
            keep.add(j)
        if sum(len(lines[j]) for j in keep) > cap:
            break
    for i, ln in enumerate(lines):
        if in_span(offsets[i]) and header_rx.search(ln) and any(abs(i - j) <= 6 for j in keep):
            keep.add(i)
    out, last = [], -2
    for i in sorted(keep):
        if i != last + 1:
            out.append("   [...]")
        out.append(f"{i + 1:6d}| {lines[i].rstrip()}")
        last = i
    return "\n".join(out)


def cmd_excerpt(a):
    reg = {r["doc_key"]: r for r in read_csv(REGISTRY)}
    EXCERPTS.mkdir(parents=True, exist_ok=True)
    manifest, skipped = [], Counter()
    for mf in sorted(CACHE.glob("*/meta.json")):
        m = json.loads(mf.read_text())
        if m.get("status") != "ok":
            continue
        r = reg.get(m["doc_key"]) or doc_info(m["doc_key"], reg)
        if not r:
            skipped["not in registry"] += 1
            continue
        if r["series"] in ("ECDC", "AFRO_OEW"):
            skipped["parsed automatically"] += 1
            continue
        text = (mf.parent / "text.txt").read_text(errors="replace")
        if r["series"] == "WER":
            kind = m.get("wer_kind") or wer_kind(r.get("title", ""), text)
            if kind == "notifications":
                skipped["WER notification tables"] += 1
                continue
        focus = set((r.get("beneficiaries") or "").split())
        ex = make_excerpt(text, focus)
        if not ex.strip():
            skipped["no cholera country lines"] += 1
            continue
        path = EXCERPTS / f"{key_hash(r['doc_key'])}.txt"
        hdr = (f"doc_key: {r['doc_key']}\nseries: {r['series']}\ntitle: {r.get('title', '')}\n"
               f"url: {m.get('url_used') or r.get('best_url', '')}\npublished (approx.): {r.get('doc_date') or 'unknown'}\n"
               f"cited_by: {r.get('citing', '')}\n"
               f"beneficiaries (no equal/finer national data for this document's periods): {r.get('beneficiaries', '')}\n"
               f"full_text: {(mf.parent / 'text.txt').relative_to(ROOT)}\n"
               f"line numbers below refer to full_text; copy quotes from full_text\n{'=' * 78}\n")
        path.write_text(hdr + ex + "\n")
        mentioned = sorted({x[0] for x in find_countries(ex) if not x[0].startswith("X")})
        manifest.append({"doc_key": r["doc_key"], "series": r["series"], "excerpt": str(path.relative_to(ROOT)),
                         "chars": len(ex), "countries": " ".join(mentioned),
                         "beneficiaries_mentioned": " ".join(sorted(set(mentioned) & focus))})
    write_csv(EXCERPTS / "manifest.csv", manifest,
              ["doc_key", "series", "excerpt", "chars", "countries", "beneficiaries_mentioned"])
    print(f"{len(manifest)} excerpts -> {EXCERPTS.relative_to(ROOT)}/ "
          f"({sum(1 for x in manifest if x['beneficiaries_mentioned'])} mention a beneficiary); skipped {dict(skipped)}")
    return 0


# ------------------------------------------------------------------- parse --
CAND_FIELDS = ["doc_key", "target_iso", "location", "tl", "tr", "period_type", "sch", "cch", "deaths",
               "quote", "extractor", "notes"]
WRITE_TYPES = {"weekly", "period", "ytd", "prior_year_ytd", "annual", "outbreak_cumulative"}
PERIOD_TYPES = WRITE_TYPES | {"reporting_window"}


def parse_ecdc(text, doc):
    """ECDC monthly cholera update: per-country paragraphs.

    'Angola: Since 12 July 2026 and as of 9 August 2026, 524 new cases, including
    four new deaths, have been reported. Since 1 January 2026 and as of 9 August
    2026, 5 903 cases, including 120 deaths, have been reported. In comparison,
    in 2025 and as of 4 August 2025, 27 666 cases, including 773 deaths, were
    reported.'

    Quotes are the matched sentence; `screen` attributes them to the country
    through the paragraph heading ("Angola:") immediately before them.
    """
    flat = norm_text(text)
    out = []
    num = r"(\d{1,3}(?: \d{3})+|\d+|[a-z]+)"
    dt = r"(\d{1,2} [A-Z][a-z]+ \d{4})"
    rx_window = re.compile(rf"Since {dt} and as of {dt}, {num} new cases?(?:, including {num} new deaths?)?,? ha(?:ve|s) been reported")
    rx_ytd = re.compile(rf"Since 1 January (\d{{4}}) and as of {dt}, {num} cases?(?:, including {num} deaths?)?,? ha(?:ve|s) been reported")
    rx_prior = re.compile(rf"In comparison, (?:since 0?1 January|in) (\d{{4}}) and as of {dt}, {num} cases?(?:, including {num} deaths?)?,? (?:were|was) reported")
    heads = list(re.finditer(r"(?<![A-Za-z])([A-Z][A-Za-z' ’,.()-]{2,60}?):\s+(?=Since )", flat))
    for i, m in enumerate(heads):
        head = m.group(1)
        isos = [x[0] for x in find_countries(head)]
        if len(isos) != 1 or isos[0].startswith("X"):
            continue
        iso = isos[0]
        end = heads[i + 1].start() if i + 1 < len(heads) else m.end() + 900
        body = flat[m.end(): min(end, m.end() + 900)]
        stop = re.search(r"Since \d{1,2} [A-Z][a-z]+ \d{4}, no updates", body)
        if stop:
            body = body[: stop.start()]
        for rx, ptype in ((rx_window, "reporting_window"), (rx_ytd, "ytd"), (rx_prior, "prior_year_ytd")):
            g = rx.search(body)
            if not g:
                continue
            if ptype == "reporting_window":
                tl, tr, sch, de = parse_text_date(g.group(1)), parse_text_date(g.group(2)), g.group(3), g.group(4)
            else:
                tl, tr, sch, de = date(int(g.group(1)), 1, 1), parse_text_date(g.group(2)), g.group(3), g.group(4)
            out.append(dict(doc_key=doc, target_iso=iso, location=f"AFR::{iso}", tl=tl, tr=tr, period_type=ptype,
                            sch=to_int(sch), cch="", deaths=to_int(de), quote=g.group(0), extractor="auto_ecdc",
                            notes=f"ECDC monthly cholera update, paragraph '{head}:'"))
    return out


OEW_DATE = r"\d{1,2}-[A-Za-z]{3}-\d{2,4}"
NAME_TOKENS = re.compile(r"^(?:Democratic|Republic|of|the|Congo|Central|African|United|Tanzania|Equatorial|Guinea|"
                         r"Bissau|South|Sudan|Côte|Cote|d'Ivoire|d’Ivoire|Sierra|Leone|Burkina|Faso|Rep\.?|Dem\.?)$", re.I)
SUSPECT_DEF = re.compile(r"unknown\s+origin|gastro-?enteritis|shigell", re.I)


def _oew_numbers(cells):
    """Total cases, confirmed, deaths, CFR from the numeric cells; CFR must agree."""
    vals = []
    for c in cells:
        c = c.strip()
        if c in ("-", "–", ""):
            vals.append(None)
        elif re.fullmatch(r"\d{1,3}(?:[ ,]\d{3})*|\d+", c):
            vals.append(int(re.sub(r"[ ,]", "", c)))
        elif re.fullmatch(r"\d+(?:\.\d+)?%", c):
            vals.append(float(c[:-1]))
        else:
            return None
    if len(vals) < 4 or not isinstance(vals[3], float) or vals[0] is None:
        return None
    total, conf, deaths, cfr = vals[:4]
    if deaths is None or total <= 0 or deaths > total or (conf is not None and conf > total):
        return None
    if abs(100.0 * deaths / total - cfr) > max(0.15, 0.06 * cfr):
        return None
    return total, conf, deaths, cfr


_ADM1 = {}
DISTRICT_ADM1 = {"MWI", "UGA"}      # reference/country_profiles.json uses districts as their ADM1
GENERIC_ADM1 = {"North", "South", "East", "West", "Centre", "Center", "Central", "Littoral", "Far North", "Northwest",
                "Southwest", "North West", "South West", "Upper East", "Upper West", "Western", "Eastern", "Northern",
                "Southern", "Coast", "Lake", "Lakes", "Nord", "Sud", "Est", "Ouest", "Plateau", "Plateaux", "Savanes",
                "Maritime", "Kara", "Centrale"}


def fold(s):
    import unicodedata
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()


def adm1_named(iso, text):
    """Provinces (ADM1, current and legacy names in reference/country_profiles.json)
    named in text. Directional names count only before a unit word, so
    'Bujumbura North' is not North Province."""
    if not _ADM1:
        prof = json.loads((REF / "country_profiles.json").read_text())["countries"]
        for k, c in prof.items():
            names = set(c.get("adm1") or [])
            for v in (c.get("adm1_legacy") or {}).values():
                names |= set(v)
            _ADM1[k] = {fold(n) for n in names if n}
    t_ = fold(text)
    found = set()
    for n in _ADM1.get(iso, ()):
        tail = r"\s+(?i:provinces?|regions?|states?|count(?:y|ies)|departments?|prefectures?)\b" if n in GENERIC_ADM1 else ""
        if re.search(r"(?<![A-Za-z])" + re.escape(n) + r"(?![A-Za-z])" + tail, t_):
            found.add(n)
    return found


def parse_oew(text, doc):
    """WHO AFRO bulletin 'All events currently being monitored' cholera rows.

    Country | Event | Grade | Date notified | Start of reporting period |
    End of reporting period | Total cases | Cases confirmed | Deaths | CFR

    Cells are separated by runs of 2+ spaces in pdftotext -layout output. A
    country name wrapped onto the lines above/below is joined only from the
    country column and only from name tokens (narrative fragments glued into
    names turned DRC rows into Congo). Rows naming a sub-national qualifier, a
    country with more than one cholera event in the bulletin, or a narrative
    describing an unconfirmed outbreak (gastroenteritis, shigellosis, AWD) are
    marked so `screen` logs instead of writing them.
    """
    out = []
    lines = text.splitlines()
    rows = []
    for i, ln in enumerate(lines):
        if not re.search(r"\bCholera\b", ln):
            continue
        cells = re.split(r"\s{2,}", ln.strip())
        try:
            ev = next(j for j, c in enumerate(cells) if c.lower() == "cholera")
        except StopIteration:
            continue
        dates = [j for j, c in enumerate(cells) if re.fullmatch(OEW_DATE, c)]
        if len(dates) < 3 or dates[0] <= ev:
            continue
        nums = _oew_numbers(cells[dates[2] + 1: dates[2] + 5])
        if not nums:
            continue
        name = " ".join(cells[:ev]).strip()
        col = len(ln) - len(ln.lstrip())
        parts = [name] if name else []
        for k_ in (-1, 1):
            j = i + k_
            if not (0 <= j < len(lines)) or not lines[j].strip():
                continue
            frag_ln = lines[j]
            frag_col = len(frag_ln) - len(frag_ln.lstrip())
            frag = re.split(r"\s{2,}", frag_ln.strip())[0]
            if abs(frag_col - col) <= 4 and frag and all(NAME_TOKENS.match(w) for w in frag.split()):
                parts = ([frag] + parts) if k_ < 0 else (parts + [frag])
        full = " ".join(parts)
        found = find_countries(full)
        isos = {x[0] for x in found if not x[0].startswith("X")}
        blocked = any(x[0].startswith("X") for x in found) or "(" in full
        if len(isos) != 1:
            continue
        iso = isos.pop()
        d1, d2, d3 = (parse_text_date(cells[j]) for j in dates[:3])
        if not (d1 and d2 and d3):
            continue
        # Start of the cumulative: a 1 January start after notification is a
        # reporting-period reset (Kenya: notified 6-Mar-17, reporting from
        # 1-Jan-18, 5,756 = 2018); otherwise the earlier date (outbreaks start
        # before notification; Cameroon 2021 has the two columns swapped).
        tl = d2 if (d2 > d1 and d2.month == 1 and d2.day == 1) else min(d1, d2)
        # The row's own narrative block: the text trailing its CFR cell, then the
        # following lines up to the next table row (a line with two bulletin
        # dates). A fixed 12-line window read the next item (BDI 2019 wk44 turned
        # national on the malaria item's "46 districts"), and starting on the
        # next line missed text printed on the row line itself (wk31 vs wk30).
        block = [" ".join(cells[dates[2] + 5:])]
        for ln2 in lines[i + 1: i + 15]:
            if len(re.findall(OEW_DATE, ln2)) >= 2:
                break
            block.append(ln2)
        narrative = " ".join(" ".join(block).split())
        # Share clauses ("41% (28) of cases reported from Bujumbura Centre health
        # district") describe part of an event, not where the event is.
        # (a share needs "of ... cases" after it: "CFR 3.4%) were reported from Kariba
        # district" is not one)
        located = re.sub(r"\b\d+(?:[.,]\d+)?\s*%\s*(?:\(\s*\d[\d\s,]*\)\s*)?of\s+(?:the\s+)?(?:\w+\s+){0,2}?"
                         r"cases?\b[^.;]*", " ", narrative)
        units = r"(?i:(?:health\s+)?(?:district|region|province|county|state|sub-county|municipality|zone))"
        named = {m.group(1) for m in re.finditer(r"\b(?:in|from)\s+(?:the\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+"
                                                 + units + r"\b", located)}
        provinces = adm1_named(iso, located)
        num = (r"(?:\d+|both|all|several|multiple|other|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
               r"thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty)"
               r"(?:-(?:one|two|three|four|five|six|seven|eight|nine))?")
        adm1_units = "provinces|regions|states|counties" + ("|districts" if iso in DISTRICT_ADM1 else "")
        wide_adm1 = re.search(r"countrywide|nationwide|national\s+(?:total|level)|across\s+the\s+country|\b" + num +
                              r"\s+(?:of\s+the\s+\d+\s+)?(?:affected\s+)?(?:health\s+)?(?:" + adm1_units + r")\b",
                              narrative, re.I)
        wide_sub = re.search(r"\b" + num + r"\s+(?:of\s+the\s+\d+\s+)?(?:affected\s+)?(?:health\s+)?"
                             r"(?:districts|zones|LGAs|sub-counties|wards)\b", narrative, re.I)
        # ... or attributes the total to the country ("Malawi has reported a total of 63")
        national = name and re.search(re.escape(name) + r"\s+(?:has|have)\s+(?:now\s+)?(?:reported|recorded|registered|"
                                      r"notified)\b|\b(?:in\s+the\s+country|nationally)\b", narrative)
        # Sub-national: an event confined to one province (however many districts in
        # it), or - when no province is named - to one named district, and never
        # called national or multi-province. Even the country's only event.
        local = not national and not wide_adm1 and \
            (len(provinces) == 1 or (not provinces and len(named) == 1 and not wide_sub))
        rows.append(dict(i=i, iso=iso, blocked=blocked or bool(local), tl=tl, tr=d3, nums=nums, quote=ln.strip(),
                         suspect=bool(SUSPECT_DEF.search(narrative)),
                         imported=bool(re.search(r"\bimport", narrative, re.I))))
    per_country = Counter(r["iso"] for r in rows)
    for r in rows:
        total, conf, deaths, cfr = r["nums"]
        flags = []
        if r["blocked"] or per_country[r["iso"]] > 1:
            flags.append("SUBNATIONAL_EVENT")
        if r["suspect"]:
            flags.append("SUSPECT_DEFINITION")
        if r["imported"]:
            flags.append("IMPORTED")
        loc = f"AFR::{r['iso']}" + ("::UNSPECIFIED" if "SUBNATIONAL_EVENT" in flags else "")
        out.append(dict(doc_key=doc, target_iso=r["iso"], location=loc, tl=r["tl"], tr=r["tr"],
                        period_type="outbreak_cumulative", sch=total, cch=conf if conf is not None else "",
                        deaths=deaths, quote=r["quote"], extractor="auto_oew",
                        notes=(" ".join(flags) + " | " if flags else "") +
                        f"AFRO bulletin event row (line {r['i'] + 1}); CFR {cfr}% matches deaths/cases; "
                        f"start = 1 January reset, else earlier of notification and reporting-period start"))
    return out


def cmd_parse(a):
    CAND_DIR.mkdir(parents=True, exist_ok=True)
    reg = {r["doc_key"]: r for r in read_csv(REGISTRY)}
    rows = {"ECDC": [], "AFRO_OEW": []}
    for mf in sorted(CACHE.glob("*/meta.json")):
        m = json.loads(mf.read_text())
        info = reg.get(m["doc_key"])
        series = info["series"] if info else m.get("series")
        if m.get("status") != "ok" or series not in rows:
            continue
        text = (mf.parent / "text.txt").read_text(errors="replace")
        rows[series].extend((parse_ecdc if series == "ECDC" else parse_oew)(text, m["doc_key"]))
    with tool_lock():
        for s, rs in rows.items():
            for r in rs:
                for k in ("tl", "tr"):
                    r[k] = str(r[k]) if r[k] else ""
                for k in ("sch", "deaths", "cch"):
                    r[k] = "" if r.get(k) in (None, "") else str(r[k])
            write_csv(CAND_DIR / f"auto_{s.lower()}.csv", rs, CAND_FIELDS)
            print(f"auto_{s.lower()}.csv: {len(rs)} candidates")
    return 0


# ------------------------------------------------------------------ assess --
WINDOW_RX = re.compile(
    r"\bnew\s+(?:suspected\s+|confirmed\s+)?cases?\b.{0,140}\b(?:since|as of)\b|\b(?:since|as of)\b.{0,140}\bnew\s+"
    r"(?:suspected\s+|confirmed\s+)?cases?\b|since\s+(?:the\s+)?(?:last|previous)\s+(?:update|report|bulletin)|"
    r"(?:last|past|previous)\s+(?:28|seven|7|14|fourteen|21)\s+days|(?:in\s+the\s+)?(?:past|last)\s+(?:week|month|"
    r"two\s+weeks|four\s+weeks)|this\s+reporting\s+period|depuis\s+(?:la\s+)?derni[eè]re|au\s+cours\s+des\s+"
    r"(?:28|sept)\s+derniers\s+jours|nouveaux\s+cas", re.I)
APPROX_RX = (r"(?:over|more\s+than|almost|nearly|about|approximately|approx\.?|around|some|at\s+least|close\s+to|"
             r"estimated|est\.|upwards\s+of|in\s+excess\s+of|~|>|≈|plus\s+de|pr[èe]s\s+de|environ|quelques?|presque|"
             r"mais\s+de|cerca\s+de|quase|aproximadamente)\s*")
ZERO_BAD = re.compile(r"no\s+updates?|not\s+(?:been\s+)?reported|did\s+not\s+report|no\s+report|no\s+data|"
                      r"not\s+available|non\s+disponible|\.\.\.|…|pending|awaited", re.I)
AS_OF_INFERRED = re.compile(r"as-of\s*(?:date\s*)?(?:=|is|set\s+to|taken\s+from)\s*(?:the\s+)?(?:bulletin|report|publication|"
                            r"issue|page)|(?:bulletin|report(?:'s)?|publication|issue)\s+date\s+(?:used|as|=)|"
                            r"TR\s*(?:=|is|set\s+to)\s*(?:the\s+)?(?:bulletin|report|publication)", re.I)


def awd_footnote(iso, text):
    """Does the document footnote this country's figures as including AWD
    ("** Namibia - Includes cholera and AWD")?"""
    # ('** Namibia: Includes cholera cases and Acute Watery Diarrhoea AWD cases')
    for m in re.finditer(r"includ\w*\s+(?:both\s+)?cholera(?:\s+cases)?\s+and\s+(?:AWD|acute\s+watery\s+diarrh\w*)|"
                         r"cholera\s*/\s*AWD\s+cases?\s+(?:for|in)", text, re.I):
        window = text[max(0, m.start() - 90): m.end() + 30]
        if iso in {c for c, s, e in find_countries(window)}:
            return True
    return False


IMPORTED_RX = re.compile(r"\bimport(?:ed|é|és|ée|ées|ado|ados|ation)?\b", re.I)


def locate_quote(q, text):
    """Start offset of a token-bounded occurrence of q in text, else None."""
    if not q:
        return None
    for m in re.finditer(re.escape(q), text):
        s, e = m.span()
        if (s == 0 or not (text[s - 1].isalnum() and q[0].isalnum())) and \
                (e == len(text) or not (text[e].isalnum() and q[-1].isalnum())):
            return s
    return None


def attribute(iso, q, text, pos, counts):
    """Is every count attributable to iso? Returns (ok, reason, subnational)."""
    lead = max(0, pos - 90)
    ctx = text[lead: pos + len(q)]
    off = pos - lead
    ms = find_countries(ctx)
    inside = [(c, s - off, e - off) for c, s, e in ms if s >= off]
    spans_into = [c for c, s, e in ms if s < off < e]
    if spans_into and iso not in spans_into:
        return False, f"quote starts inside the name {spans_into[0]}", False
    mine = [(s, e) for c, s, e in inside if c == iso]
    if mine:
        s0, e0 = mine[0]
        if any(c.startswith("X") and c not in ("XOT", "XSD") and abs(s - e0) <= 25 for c, s, e in inside if s >= e0) or \
                re.match(r"\s*\((?:[A-Z][a-z]+(?:\s|$|\))){1,3}", q[e0:]):
            return True, "", True                # "Tanzania (Zanzibar)", "Angola (Cabinda)"
        others = sorted(s for c, s, e in inside if c != iso)
        prev_end = max([e for c, s, e in inside if c != iso and e <= s0] or [0])
        nxt = min([s for s in others if s >= e0] or [len(q)])
        zone = q[prev_end:nxt]
        if all(value_in(v, zone) for v in counts if v is not None):
            return True, "", False
        return False, "count not in the target's part of the quote", False
    # paragraph heading: "Angola: Since ..." with no other country in between
    before = text[max(0, pos - 700): pos]
    # a heading starts a sentence ("... last paragraph. Kenya: ..."), so the
    # previous sentence ("...Democratic Republic of the Congo.") is not read into it
    heads = list(re.finditer(r"(?:^|(?<=[.;!?:]\s)|(?<=\]\s))([A-Z][A-Za-z' ,()-]{2,60}?):\s", before))
    if heads and not inside:
        h = heads[-1]
        hc = [c for c, s, e in find_countries(h.group(1))]
        between = before[h.end():]
        if hc == [iso] and not find_countries(between):
            if all(value_in(v, q) for v in counts if v is not None):
                return True, "", False
    return False, "target country not named in the quote or its paragraph heading", False


def assess(r, info, text, rows, cov, gaps, subrows=None):
    """One candidate -> (decision, reason, extras). Shared by screen, verify, apply."""
    iso = (r.get("target_iso") or "").strip().upper()
    ex = {}
    if iso not in MOSAIC:
        return "REJECT_SCOPE", "target not a MOSAIC country", ex
    if not info:
        return "REJECT_DOC", "doc_key not in registry or cache", ex
    if info.get("series") == "WER" and info.get("wer_kind_text") == "notifications":
        return "REJECT_SOURCE_TYPE", "WER weekly notification table (not harvestable from text)", ex
    ptype = r.get("period_type")
    if ptype not in PERIOD_TYPES:
        return "REJECT_FORMAT", f"period_type {ptype!r}", ex
    tl, tr = d(r.get("tl")), d(r.get("tr"))
    sch, deaths, cch = to_int(r.get("sch")), to_int(r.get("deaths")), to_int(r.get("cch"))
    if not tl or not tr or tl > tr or tr > TODAY:
        return "REJECT_DATES", "missing, reversed or future dates", ex
    pub = d(info.get("doc_date")) if info.get("doc_date") else None
    if pub and tr > pub + timedelta(days=14):
        return "REJECT_DATES", f"period ends after the document's publication (~{pub})", ex
    if AS_OF_INFERRED.search(r.get("notes") or ""):
        return "REJECT_DATES", "end date taken from the bulletin/report/publication date, not printed for the figure", ex
    if text is None:
        return "REJECT_UNVERIFIED", "document text not cached", ex
    q = norm_text(r.get("quote") or "")
    pos = locate_quote(q, text)
    ex["quote_verified"] = pos is not None
    if pos is None:
        return "REJECT_UNVERIFIED", "quote not found verbatim (token-bounded) in the cached document", ex
    if not all(value_in(v, q) for v in (sch, deaths, cch) if v is not None):
        return "REJECT_NUMBERS", "a count is not in the quote as a whole number", ex
    ok, why, subnational = attribute(iso, q, text, pos, (sch, deaths, cch))
    if not ok:
        return "REJECT_COUNTRY", why, ex
    if iso == "COG" and re.search(r"democratic\s+republic\s+of", q, re.I):
        return "REJECT_COUNTRY", "quote contains a wrapped 'Democratic Republic of (the) Congo' name", ex
    for v in (sch, deaths):
        if v is not None and re.search(APPROX_RX + num_pattern(v), q, re.I):
            return "REJECT_APPROX", "approximate figure", ex
    if IMPORTED_RX.search(q) or "IMPORTED" in (r.get("notes") or ""):
        return "REJECT_IMPORTED", "imported cases", ex
    if ptype == "reporting_window" or WINDOW_RX.search(q):
        return "LOG_WINDOW", "reporting window ('new since ...', 'last 28 days'), not an epidemiological period", ex
    # note flags (set by `parse`, or by an agent) can only withhold a figure, never admit one
    if subnational or "SUBNATIONAL_EVENT" in (r.get("notes") or "") or \
            not is_national(r.get("location"), iso):
        return "LOG_SUBNATIONAL", "sub-national or one of several events; harvest writes national rows only", ex
    if sch is None:
        return "LOG_NOCOUNT", "no case count", ex
    if sch == 0:
        if ZERO_BAD.search(q):
            return "REJECT_ZERO_SEMANTICS", "zero claim from a non-report ('no updates', 'not reported', '...')", ex
        return "LOG_ZERO", "unverified zero claim; never auto-written - lead for Agent 3", ex
    if (deaths is not None and deaths > sch) or (cch is not None and cch > sch):
        return "REJECT_ARITH", "deaths or cCh exceed sCh", ex
    span = (tr - tl).days + 1
    if span < 6 or (ptype in ("outbreak_cumulative", "ytd", "prior_year_ytd") and span <= 8):
        # a cumulative of a week or less becomes an "observed" week in the builder,
        # and later snapshots of the same series are then not decumulated against it
        return "LOG_SHORT", "period of a week or less (cumulatives this short read as observed weeks)", ex
    if ptype == "weekly" and not 6 <= span <= 8:
        return "REJECT_PERIOD", "weekly row whose span is not one week", ex
    if ptype == "annual" and not (tl.month == 1 and tl.day <= 4 and tr.month == 12 and tr.day >= 28
                                  and tl.year == tr.year):
        return "REJECT_PERIOD", "annual row that is not a calendar year", ex
    if ptype in ("ytd", "prior_year_ytd") and not (tl.month == 1 and tl.day == 1 and tl.year == tr.year):
        return "REJECT_PERIOD", "year-to-date row that does not start on 1 January of its year", ex
    if ptype == "prior_year_ytd" and pub and tr.year >= pub.year:
        return "REJECT_PERIOD", "prior-year figure not in a year before the document", ex
    if ptype == "outbreak_cumulative" and span > 400:
        return "LOG_AMBIGUOUS", "protracted event: cumulative start date unreliable", ex
    if ptype != "annual" and span > 731:
        return "LOG_AGGREGATE", "multi-year aggregate (> 2 years): too coarse to harvest", ex
    if "SUSPECT_DEFINITION" in (r.get("notes") or ""):
        return "LOG_DEFINITION", "bulletin narrative: unconfirmed outbreak (gastroenteritis/shigellosis)", ex
    # AWD: judged from the figure's own words and the document's footnotes for this
    # country - not from an agent's notes or a table title (SOM, ETH: AWD/cholera
    # is the national case definition)
    if iso not in ("SOM", "ETH") and (re.search(r"\bAWD\b|acute\s+watery\s+diarrh|diarrh[ée]e\s+aqueuse", q, re.I)
                                      or awd_footnote(iso, text)):
        return "LOG_DEFINITION", "count includes or is acute watery diarrhoea (not a cholera count)", ex
    # the series fixes the weight; the registry's copy can be stale
    w = SERIES[info["series"]][1] if info.get("series") in SERIES else float(info.get("weight") or 0.7)
    if deaths is not None and sch >= 20:
        cfr = 100.0 * deaths / sch
        if cfr > 20:
            return "LOG_CFR_OUTLIER", f"CFR {cfr:.1f}% > 20%", ex
        if cfr > 15:
            w = min(w, CFR_CAP_WEIGHT)
        elif cfr > 10:
            w = min(w, CFR_REVIEW_WEIGHT)
    ex["weight"] = f"{w:.2f}"
    ex["in_effective_gap"] = any(a0 <= tr and b0 >= tl for a0, b0 in gaps.get(iso, []))
    # the target's own agents already read this document (under any URL variant):
    # their coding - often sub-national, or deliberately not recorded - stands
    if iso in (info.get("identity_citing") or "").split():
        return "LOG_TARGET_CITES", "the target already cites this document; its own extraction takes precedence", ex
    # a national copy of a figure the target holds as a sub-national row
    for (stl, str_, ss, slayer, sidx, sloc) in (subrows or []):
        sov = (min(str_, tr) - max(stl, tl)).days + 1
        if ss > 0 and sov > 0 and abs(ss - sch) <= max(1, 0.02 * max(ss, sch)) and \
                (sov / span >= 0.5 or sov / ((str_ - stl).days + 1) >= 0.5):
            return "DUPLICATE_SUBNATIONAL", f"same count as sub-national row {slayer}[{sidx}] {sloc} {stl}..{str_}", ex
    # -- consistency with every overlapping national row, any layer, any span --
    cumulative = ptype in ("ytd", "prior_year_ytd", "outbreak_cumulative", "annual")
    issues, agree = [], []
    weeks = {}
    for (etl, etr, s, layer, idx, ev) in rows:
        if s <= 0:
            continue
        tag = f"{layer}[{idx}]={s:g} {etl}..{etr}"
        if (etr - etl).days <= 7 and etl >= tl - timedelta(days=1) and etr <= tr + timedelta(days=1):
            wk = etl.isocalendar()[:2]
            weeks[wk] = max(weeks.get(wk, 0), s)
        ov = (min(etr, tr) - max(etl, tl)).days + 1
        same_start = abs((etl - tl).days) <= 3
        if ov <= 0 and not same_start:
            continue
        espan = (etr - etl).days + 1
        same_val = abs(s - sch) <= max(1, 0.02 * max(s, sch))
        if same_val and ov > 0 and (ov / span >= 0.5 or ov / espan >= 0.5):
            agree.append(f"restated {tag}")
            continue
        if same_start and cumulative and etr != tr:
            # successive snapshots of one cumulative series: they must rise
            if etr > tr and s < sch * 0.98:
                issues.append(f"exceeds a later cumulative from the same start: {tag}")
            elif etr < tr and s > sch * 1.02:
                issues.append(f"below an earlier cumulative from the same start: {tag}")
            continue
        if abs((etl - tl).days) <= 7 and abs((etr - tr).days) <= 7:
            issues.append(f"same period, different count: {tag}")
            continue
        if etl <= tl + timedelta(days=3) and etr >= tr - timedelta(days=3):
            if sch > s * 1.10 + 1:
                issues.append(f"exceeds the enclosing row {tag}")
            continue
        if tl <= etl + timedelta(days=3) and tr >= etr - timedelta(days=3):
            if s > sch * 1.10 + 1:
                issues.append(f"below the contained row {tag}")
            continue
        if ov / span >= 0.5 and ov / espan >= 0.5:
            issues.append(f"overlapping row with a different count: {tag}")
    if weeks and sum(weeks.values()) > sch * 1.10 + 1:
        issues.append(f"{len(weeks)} contained weeks sum to {sum(weeks.values()):g}")
    # A total equal to the rows it contains only restates them. Weeks count by
    # their midpoint (WHO week 1 starts in the previous December), also through
    # the week STARTING on the as-of date (ECDC dates are WHO-week Mondays); then
    # any non-overlapping contained rows (MWI: 682 = 370 + 117 + 195).
    def wk_sum(end):
        ws = {}
        for (etl, etr, s, layer, idx, ev) in rows:
            mid = etl + (etr - etl) / 2
            if s > 0 and (etr - etl).days <= 7 and tl <= mid <= end:
                ws[etl.isocalendar()[:2]] = max(ws.get(etl.isocalendar()[:2], 0), s)
        return ws
    tiles, last_end = [], None
    for (etl, etr, s, layer, idx, ev) in sorted(rows, key=lambda x: (x[0], -(x[1] - x[0]).days)):
        if s > 0 and etl >= tl - timedelta(days=3) and etr <= tr + timedelta(days=3) and \
                (etr - etl).days + 1 < span and (last_end is None or etl > last_end):
            tiles.append(s)
            last_end = etr
    for label, vals in (("contained weeks", list(wk_sum(tr).values())),
                        ("contained weeks to the week after the as-of date", list(wk_sum(tr + timedelta(days=7)).values())),
                        ("contained rows", tiles)):
        if vals and abs(sum(vals) - sch) <= max(1, 0.02 * sch):
            agree.append(f"equals the sum of {len(vals)} {label} ({sum(vals):g})")
            break
    ex["consistency"] = "; ".join((issues + agree)[:4])
    if issues:
        return "CONFLICT", issues[0], ex
    if agree:
        return "CORROBORATES", agree[0], ex
    zc = cov.zero_cover(tl, tr)
    ex["zero_cover"] = f"{zc:.2f}"
    # Positive figure vs recorded zeros: a conflict when fewer than 7 of its days
    # fall outside zero rows (no room for its cases) and no positive row at least
    # as fine as the candidate already records cases inside it. A coarser row (an
    # annual total) does not count: it cannot place cases inside the zeros.
    finer_pos = any(s > 0 and etl <= tr and etr >= tl and (etr - etl).days + 1 <= span
                    for (etl, etr, s, *_rest) in rows)
    if span * (1 - zc) < 7 and not finer_pos:
        return "CONFLICT_ZERO", "positive figure over a period the target records as zero", ex
    if cumulative:
        # earlier snapshots of the same cumulative series (positive, same start,
        # longer than a week, ending before TR) are not finer data about the
        # later period; weekly rows and zeros that happen to start on TL are.
        # Snapshots of one chain share their start date exactly: MWI's calendar
        # March row (1-31 Mar) is not a snapshot of an event that began 3 Mar.
        indep = [x for x in rows if not (x[2] > 0 and x[0] == tl
                                         and (x[1] - x[0]).days + 1 > 8 and x[1] < tr)]
        eq = cover_fraction(indep, tl, tr)
    else:
        eq = cov.equal_or_finer(tl, tr)
    ex["equal_or_finer_cover"] = f"{eq:.2f}"
    if eq >= 0.5:
        return "SKIP_COVERED", "target already has equal-or-finer national data (week resolution)", ex
    return "ADD", "adds national data at a resolution the target lacks", ex


def load_doc_infos(reg):
    infos, texts = {}, {}
    for mf in CACHE.glob("*/meta.json"):
        m = json.loads(mf.read_text())
        k = m["doc_key"]
        info = dict(reg.get(k) or doc_info(k, reg) or {})
        if not info:
            continue
        if m.get("status") == "ok":
            raw = (mf.parent / "text.txt").read_text(errors="replace")
            texts[k] = norm_text(raw)
            if info.get("series") == "WER":
                info["wer_kind_text"] = m.get("wer_kind") or wer_kind(info.get("title", ""), raw)
        if not info.get("doc_date") and m.get("status") == "ok":
            ao = title_as_of(page_title(k))
            if ao:
                info["doc_date"] = str(ao)
        info["sha256"] = m.get("sha256", "")
        info["url_used"] = m.get("url_used", "")
        info["wayback_snapshot"] = m.get("wayback_snapshot", "")
        info["iris_name"] = m.get("iris_name", "")
        infos[k] = info
    for k, r in reg.items():
        infos.setdefault(k, dict(r))
    # One document, several identities: identical cached text, or a ReliefWeb
    # report page and its PDF attachment (reference/xref/aliases.csv, from the
    # `aliases` subcommand). Citing countries are pooled across them.
    groups = defaultdict(set)
    for k, info in infos.items():
        if info.get("sha256"):
            groups["sha:" + info["sha256"]].add(k)
    for a_ in read_csv(ALIASES):
        groups["alias:" + a_["alias_key"]] |= {a_["doc_key"], a_["alias_key"]}
    member = defaultdict(set)
    for g, ks in groups.items():
        for k in ks:
            member[k] |= ks
    for k, info in infos.items():
        citing = set((info.get("citing") or "").split())
        for alias in member.get(k, {k}):
            if alias in infos:
                citing |= set((infos[alias].get("citing") or "").split())
            elif alias in reg:
                citing |= set((reg[alias].get("citing") or "").split())
        info["identity_citing"] = " ".join(sorted(citing))
    return infos, texts


# ------------------------------------------------------------------ screen --
SCREEN_FIELDS = CAND_FIELDS + ["series", "candidate_id", "decision", "reason", "quote_verified", "target_cites_doc",
                               "consistency", "equal_or_finer_cover", "zero_cover", "in_effective_gap", "weight",
                               "doc_date", "doc_title", "doc_url", "doc_citing", "source_file"]


def candidate_id(r):
    return key_hash("|".join((r.get(f) or "").strip() for f in
                             ("doc_key", "target_iso", "location", "tl", "tr", "sch", "deaths", "period_type")))


PEER_DECISIONS = {"ADD", "CORROBORATES", "CONFLICT", "SKIP_COVERED", "DUPLICATE", "CHAIN_SUPERSEDED",
                  "CONFLICT_HARVEST", "LOG_TARGET_CITES", "LOG_SHORT", "LOG_UNCORROBORATED"}


def date_rank(info):
    dd_ = d(info.get("doc_date")) if info and info.get("doc_date") else None
    return (1, dd_.toordinal()) if dd_ else (0, 0)          # undated sorts last


def cmd_screen(a):
    reg = {r["doc_key"]: r for r in read_csv(REGISTRY)}
    infos, texts = load_doc_infos(reg)
    gaps = load_gaps()
    cov, rows_by, subs_by = {}, {}, {}
    cands = []
    for f in sorted(CAND_DIR.glob("*.csv")):
        for r in read_csv(f):
            r["source_file"] = f.name
            r["target_iso"] = (r.get("target_iso") or "").strip().upper()
            cands.append(r)
    out = []
    for r in cands:
        k, iso = (r.get("doc_key") or "").strip(), r["target_iso"]
        info = infos.get(k)
        if iso in MOSAIC and iso not in cov:
            rows_by[iso] = national_rows(iso)
            subs_by[iso] = subnational_rows(iso)
            cov[iso] = Coverage(iso, rows_by[iso])
        if iso in MOSAIC:
            dec, why, ex = assess(r, info, texts.get(k), rows_by[iso], cov[iso], gaps, subs_by[iso])
        else:
            dec, why, ex = "REJECT_SCOPE", "target not a MOSAIC country", {}
        r.update(ex)
        r.update(decision=dec, reason=why, candidate_id=candidate_id(r), series=(info or {}).get("series", ""),
                 doc_date=(info or {}).get("doc_date", ""), doc_title=(info or {}).get("title", ""),
                 doc_url=(info or {}).get("url_used") or (info or {}).get("best_url", ""),
                 doc_citing=(info or {}).get("citing", ""),
                 target_cites_doc=iso in ((info or {}).get("identity_citing", "")).split())
        out.append(r)

    # 1. one ADD per (target, period +-3 days): official series first, then the
    #    later document (a revision), undated last; the rest are DUPLICATE or
    #    CONFLICT_HARVEST
    adds = sorted([r for r in out if r["decision"] == "ADD"], key=lambda r: (r["target_iso"], r["tl"], r["tr"]))
    clusters = []
    for r in adds:
        for cl in clusters:
            b = cl[0]
            if b["target_iso"] == r["target_iso"] and abs((d(b["tl"]) - d(r["tl"])).days) <= 3 \
                    and abs((d(b["tr"]) - d(r["tr"])).days) <= 3:
                cl.append(r)
                break
        else:
            clusters.append([r])
    for cl in clusters:
        cl.sort(key=lambda r: (SERIES[r["series"]][2], tuple(-x for x in date_rank(infos.get(r["doc_key"]))),
                               -float(r["weight"])))
        best = cl[0]
        for r in cl[1:]:
            same = abs(to_int(r["sch"]) - to_int(best["sch"])) <= max(1, 0.02 * to_int(best["sch"]))
            r["decision"] = "DUPLICATE" if same else "CONFLICT_HARVEST"
            r["reason"] = f"same target/period as candidate {best['candidate_id']}" + ("" if same else " with a different count")

    # National figures with a usable decision may revise or supersede another
    # candidate; sub-national, window, zero and definition-flagged ones may not
    # (ZWE's national 11,735 was superseded by a Manicaland 6,064).
    def chain_peer(x):
        return x.get("quote_verified") in (True, "TRUE") and is_national(x.get("location"), x["target_iso"]) \
            and x["decision"] in PEER_DECISIONS and to_int(x.get("sch"))

    # 2. cumulative chains (target, start +-3 days, any series/type) must be
    #    non-decreasing together with the target's existing AI rows, or the
    #    weekly builder cannot decumulate them (a later lower total becomes a
    #    negative residual and inferred-zero weeks). Later documents are revisions.
    for iso in {r["target_iso"] for r in out if r["decision"] == "ADD"}:
        cand = [r for r in out if r["decision"] == "ADD" and r["target_iso"] == iso]
        verified = [r for r in out if r["target_iso"] == iso and chain_peer(r)
                    and r["period_type"] in ("ytd", "prior_year_ytd", "outbreak_cumulative")]
        fixed = [(tl, tr, s) for (tl, tr, s, layer, idx, ev) in rows_by.get(iso, []) if layer == "AI" and s > 0]
        for r in sorted(cand, key=lambda r: (d(r["tr"]), date_rank(infos.get(r["doc_key"]))), reverse=True):
            tl, tr, v = d(r["tl"]), d(r["tr"]), to_int(r["sch"])
            peers_later = [to_int(x["sch"]) for x in verified if x is not r
                           and abs((d(x["tl"]) - tl).days) <= 3 and d(x["tr"]) > tr]
            fixed_later = [s for (ftl, ftr, s) in fixed if abs((ftl - tl).days) <= 3 and ftr > tr]
            fixed_earlier = [s for (ftl, ftr, s) in fixed if abs((ftl - tl).days) <= 3 and ftr < tr]
            if fixed_later and v > min(fixed_later) * 1.02:
                r["decision"], r["reason"] = "CONFLICT", f"exceeds a later existing cumulative ({min(fixed_later):g})"
            elif fixed_earlier and v < max(fixed_earlier) * 0.98:
                r["decision"], r["reason"] = "CONFLICT", f"below an earlier existing cumulative ({max(fixed_earlier):g})"
            elif peers_later and v > min(peers_later):
                r["decision"], r["reason"] = "CHAIN_SUPERSEDED", \
                    f"exceeds a later revised total ({min(peers_later)}) in the same cumulative chain"

    # 2b. a cumulative revised by a later document of the same series: that
    #     document gives a total to a later date AND the count for exactly the
    #     interval in between, and the two disagree with this total (JCISA
    #     bulletin 12: Angola 211 to 26 Feb with week 8 = 11, so weeks 1-7 = 200,
    #     not bulletin 10's preliminary 168 to 19 Feb). Final beats preliminary.
    usable = chain_peer
    # Undated documents (JCISA bulletins on ReliefWeb) are ordered by the latest
    # as-of date among their own figures.
    data_end = defaultdict(lambda: date.min)
    for x in out:
        if usable(x) and d(x["tr"]):
            data_end[x["doc_key"]] = max(data_end[x["doc_key"]], d(x["tr"]))

    def later(kb, kr):
        rb, rr = date_rank(infos.get(kb)), date_rank(infos.get(kr))
        return rb > rr if rb[0] and rr[0] else data_end[kb] > data_end[kr]
    for r in [x for x in out if x["decision"] == "ADD" and x["period_type"] in ("ytd", "outbreak_cumulative")]:
        tl, tr, v = d(r["tl"]), d(r["tr"]), to_int(r["sch"])
        for b in out:
            if b is r or not usable(b) or b["target_iso"] != r["target_iso"] or b["series"] != r["series"] \
                    or b["doc_key"] == r["doc_key"] or d(b["tl"]) != tl or d(b["tr"]) <= tr \
                    or not later(b["doc_key"], r["doc_key"]):
                continue
            for w in out:
                if w is b or w is r or not usable(w) or w["doc_key"] != b["doc_key"] \
                        or w["target_iso"] != r["target_iso"] \
                        or abs((d(w["tl"]) - (tr + timedelta(days=1))).days) > 1 \
                        or abs((d(w["tr"]) - d(b["tr"])).days) > 1:
                    continue
                implied = to_int(b["sch"]) - to_int(w["sch"])
                if abs(implied - v) > max(2, 0.05 * v):
                    r["decision"], r["reason"] = "CHAIN_SUPERSEDED", (
                        f"revised by {b['doc_key']}: {b['sch']} to {b['tr']} less its {w['sch']} for "
                        f"{w['tl']}..{w['tr']} leaves {implied} for this period, not {v}")
                    break
            if r["decision"] != "ADD":
                break

    # 3. CLAUDE.md: outbreaks > 1000 cases need two independent sources
    for r in out:
        if r["decision"] != "ADD" or to_int(r["sch"]) <= 1000:
            continue
        tl, tr, v = d(r["tl"]), d(r["tr"]), to_int(r["sch"])
        span = (tr - tl).days + 1
        corroborated = False
        for x in out:
            if x is r or x["target_iso"] != r["target_iso"] or x["series"] == r["series"] or \
                    x["decision"] not in ("ADD", "CORROBORATES", "DUPLICATE", "SKIP_COVERED"):
                continue
            xtl, xtr = d(x["tl"]), d(x["tr"])
            ov = (min(xtr, tr) - max(xtl, tl)).days + 1
            xv = to_int(x["sch"])
            if ov > 0 and ov / span >= 0.5 and ov / ((xtr - xtl).days + 1) >= 0.5 and xv and 1 / 1.5 <= xv / v <= 1.5:
                corroborated = True
                break
        if not corroborated:
            r["decision"], r["reason"] = "LOG_UNCORROBORATED", ">1000 cases from a single source (CLAUDE.md 2-source rule)"

    for r in out:
        for b in ("quote_verified", "target_cites_doc", "in_effective_gap"):
            if b in r:
                r[b] = "TRUE" if r[b] in (True, "TRUE") else "FALSE"
    with tool_lock():
        write_csv(SCREENED, out, SCREEN_FIELDS)
    dc = Counter(r["decision"] for r in out)
    print(f"{len(out)} candidates screened -> {SCREENED.relative_to(ROOT)}")
    for k_, n in dc.most_common():
        print(f"  {k_:20s} {n}")
    return 0


def cmd_verify(a):
    """Read-only self-check for an agent's candidate file (verification and
    gating only - consistency with existing data is `screen`'s job)."""
    reg = {r["doc_key"]: r for r in read_csv(REGISTRY)}
    infos, texts = load_doc_infos(reg)
    empty = Coverage("AGO", [])
    bad, n = Counter(), 0
    for r in read_csv(Path(a.file)):
        n += 1
        k = (r.get("doc_key") or "").strip()
        r["target_iso"] = (r.get("target_iso") or "").strip().upper()
        dec, why, _ = assess(r, infos.get(k), texts.get(k), [], empty, {})
        if dec.startswith("REJECT"):
            bad[dec] += 1
            print(f"  line {n + 1} ({r['target_iso']} {r.get('tl')}..{r.get('tr')} sCh={r.get('sch')}): {dec} - {why}")
    print(f"{n} rows checked; rejected: {dict(bad) or 'none'}")
    return 1 if bad else 0


# ------------------------------------------------------------------- apply --
LOG_FIELDS = ["run", "applied_at", "tool_sha", "candidate_id", "target_iso", "data_index", "meta_index", "meta_action",
              "doc_key", "series", "doc_url", "sha256", "tl", "tr", "period_type", "sch", "cch", "deaths", "weight",
              "status", "message"]


class BuilderGate:
    """Simulate py/build_weekly_timeseries.py for one country before and after a
    candidate row, so a harvested row can never lower a year's total (the 50%
    coverage rule dropped a 5,426-case increment when four correct weekly rows
    were added to ZMB 2018), add more cases than it carries, or turn documented
    zero weeks into estimates. Templates use JHU/WHO rows only, so they are
    computed once."""

    def __init__(self):
        import importlib.util, shutil
        self.shutil = shutil
        spec = importlib.util.spec_from_file_location("bwt", ROOT / "py" / "build_weekly_timeseries.py")
        self.bwt = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.bwt)
        self.templates = self.bwt.build_all_templates(self.bwt.load_country_map())
        self.tmp = CACHE.parent / "xref_gate"          # under the gitignored cache/
        self.tmp.mkdir(parents=True, exist_ok=True)
        self.real = self.bwt.DATA_DIR

    def series(self, iso, extra_row=None):
        if iso not in self.templates:
            return None
        if extra_row is None:
            self.bwt.DATA_DIR = self.real
        else:
            d = self.tmp / iso
            d.mkdir(parents=True, exist_ok=True)
            for f in ("cholera_data_ai.csv", "cholera_data_jhu.csv", "cholera_data_who.csv"):
                (d / f).unlink(missing_ok=True)       # baseline CSVs are mode 444
                if (DATA / iso / f).exists():
                    self.shutil.copyfile(DATA / iso / f, d / f)
            ai = d / "cholera_data_ai.csv"
            if ai.exists() and ai.stat().st_size and not ai.read_bytes().endswith(b"\n"):
                with open(ai, "a", encoding="utf-8") as fh:
                    fh.write("\n")
            with open(ai, "a", newline="", encoding="utf-8") as fh:
                csv.writer(fh).writerow([extra_row.get(c, "") for c in
                                         ["Index", "Location", "TL", "TR", "deaths", "sCh", "cCh", "CFR",
                                          "reporting_date", "source_index", "source", "confidence_weight",
                                          "processing_notes", "source_database"]])
            self.bwt.DATA_DIR = self.tmp
        try:
            return self.bwt.process_country(iso, self.templates[iso], {})
        finally:
            self.bwt.DATA_DIR = self.real

    @staticmethod
    def context(rows):
        """Zero windows (non-documented zero rows longer than a week: documented
        zero weeks are protected separately) and official annual totals (median
        of the JHU/WHO national calendar-year rows) from national_rows()."""
        zeros = [(a, b) for (a, b, s, layer, idx, ev) in rows if s == 0 and ev != "documented" and (b - a).days > 7]
        ann = defaultdict(list)
        for (a, b, s, layer, idx, ev) in rows:
            if s > 0 and layer in ("JHU", "WHO") and a.year == b.year and a.month == 1 and a.day <= 4 \
                    and b.month == 12 and b.day >= 28:
                ann[a.year].append(s)
        return zeros, {y: sorted(v)[len(v) // 2] for y, v in ann.items()}

    @staticmethod
    def window(series, a, b):
        """Cases the weekly series puts in [a, b], partial weeks pro rata."""
        tot = 0.0
        for e in series.values():
            ov = (min(e["sunday"], b) - max(e["monday"], a)).days + 1
            if ov > 0:
                tot += e["sch"] * min(ov, 7) / 7.0
        return tot

    @staticmethod
    def check(before, after, sch, tl, tr, zeros=(), annuals=None):
        """Why the builder would mishandle the row, or "". A correct row is held
        when it would (a) lower a year by more than max(2, 1%), unless the new
        total is closer to that year's official annual; (b) raise a year it does
        not cover by more than max(2, 1%, a quarter of the row); (c) add more
        cases than it carries; (d) turn documented-zero
        weeks into estimates; (e) leave its own period further from its count
        than it was (BDI 2020: 67.6 -> 82.6 cases against a row of 70); or
        (f) move cases into recorded-zero periods beyond what it repairs in its
        own period (ZMB 2017's year-to-date rows moved a builder surplus out of
        Jan-May, where the row's counts forbid it, into an inferred-zero window:
        allowed, since the counts are the stronger evidence)."""
        annuals = annuals or {}
        yb, ya = defaultdict(float), defaultdict(float)
        for k, e in before.items():
            yb[k[0]] += e["sch"]
        for k, e in after.items():
            ya[k[0]] += e["sch"]
        own_years = {k[0] for k, e in after.items() if e["monday"] <= tr and e["sunday"] >= tl}
        for y in sorted(set(yb) | set(ya)):
            tol = max(2.0, 0.01 * yb[y])
            if ya[y] < yb[y] - tol:
                off = annuals.get(y)
                if off is None or abs(ya[y] - off) >= abs(yb[y] - off):
                    return f"weekly builder would lower {y} from {yb[y]:,.0f} to {ya[y]:,.0f}"
            # residual shifts within an aggregate that spans the year are tolerated up to a
            # quarter of the row (AGO 2017 weeks: +3 into Dec 2016); ZMB's 197-case Jan 2018
            # week pushed 294 cases into 2017
            if y not in own_years and ya[y] > yb[y] + max(tol, 0.25 * sch):
                return f"weekly builder would move cases into {y} ({yb[y]:,.0f} -> {ya[y]:,.0f})"
        gain = sum(ya.values()) - sum(yb.values())
        if gain > sch * 1.02 + 2:
            return f"weekly builder would add {gain:,.0f} cases for a row of {sch}"
        lost_zero = [k for k, e in before.items() if e["method"] == "documented_zero"
                     and k in after and after[k]["method"] != "documented_zero"]
        if lost_zero:
            return f"weekly builder would turn {len(lost_zero)} documented-zero week(s) into estimates"
        wb, wa = BuilderGate.window(before, tl, tr), BuilderGate.window(after, tl, tr)
        vb, va = abs(wb - sch), abs(wa - sch)
        if va > max(2.0, 0.05 * sch) and va > vb + 0.5:
            return f"weekly builder would put {wa:,.0f} cases in the row's own period (was {wb:,.0f}), not {sch}"

        def zsum(series):
            tot = 0.0
            for e in series.values():
                best = max([(min(e["sunday"], b) - max(e["monday"], a)).days + 1 for a, b in zeros] or [0])
                if best > 0:
                    tot += e["sch"] * min(best, 7) / 7.0
            return tot
        if zeros:
            dz = zsum(after) - zsum(before)
            if dz > max(2.0, 0.02 * sch) + max(0.0, vb - va):
                return f"weekly builder would move {dz:,.0f} cases into recorded-zero periods"
        return ""


def run_tool(script, args):
    r = subprocess.run([sys.executable, "-I", "-B", str(ROOT / "py" / script)] + args,
                       capture_output=True, text=True, cwd=ROOT)
    return r.returncode, (r.stdout + r.stderr).strip()


def migrate_log():
    """Rewrite harvest_log.csv under the current LOG_FIELDS header. Rows are
    mapped by their own width (old header or current), so a log begun by an
    earlier version of the tool stays readable by field name."""
    if not HARVEST_LOG.exists():
        return
    with open(HARVEST_LOG, newline="", encoding="utf-8") as fh:
        raw = list(csv.reader(fh))
    if not raw or raw[0] == LOG_FIELDS:
        return
    old = raw[0]
    out = []
    for row in raw[1:]:
        if len(row) == len(LOG_FIELDS):
            out.append(dict(zip(LOG_FIELDS, row)))
        elif len(row) == len(old):
            out.append(dict(zip(old, row)))
        else:
            sys.exit(f"harvest_log.csv: row of width {len(row)} matches neither header; fix by hand")
    write_csv(HARVEST_LOG, out, LOG_FIELDS)


def append_log(entry):
    migrate_log()
    new = not HARVEST_LOG.exists()
    HARVEST_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(HARVEST_LOG, "a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=LOG_FIELDS, extrasaction="ignore")
        if new:
            w.writeheader()
        w.writerow(entry)


def display_title(k, info):
    """Neutral source name from the document itself, never another country's label."""
    if info.get("iris_name"):
        return re.sub(r"\s+", " ", info["iris_name"])[:200]
    m = re.match(r"ecdc:(\d{4}):(\d+)$", k)
    if m:
        return f"ECDC Communicable Disease Threats Report, week {int(m.group(2))} {m.group(1)}"
    m = re.match(r"oew:(\d{4}):(\d+)$", k)
    if m:
        return f"WHO AFRO Weekly Bulletin on Outbreaks and Other Emergencies, week {int(m.group(2))} {m.group(1)}"
    m = re.match(r"wer:(\d+):(\d+)$", k)
    if m:
        return f"WHO Weekly Epidemiological Record, vol. {m.group(1)} ({int(m.group(1)) + 1925}), no. {m.group(2)}"
    m = re.match(r"whomc:(\w+):(\d+)$", k)
    if m:
        kind = "External Situation Report" if m.group(1) == "esr" else "Epidemiological Update"
        return f"WHO Multi-country outbreak of cholera, {kind} #{m.group(2)}"
    m = re.match(r"africacdc:(\d{4}-\d{2}-\d{2})$", k)
    if m:
        return f"Africa CDC Epidemic Intelligence Weekly Report, {m.group(1)}"
    tail = unquote(urlparse(info.get("url_used") or info.get("best_url") or "").path.rstrip("/").rsplit("/", 1)[-1])
    return f"{SERIES[info['series']][3]}: {tail[:120]}"


NAV_RX = re.compile(r"^(skip to (main )?content|main navigation|log ?in|sign ?in|help|menu|search\b|"
                    r"content search|what are you looking for|cookies?\b|accept\b|share\b|print\b)", re.I)


def page_title(k):
    """An HTML page's own <title> line as cached (ReliefWeb: '<report title> -
    <primary country> | ReliefWeb'), without the site name and ReliefWeb's
    primary-country tag, which labels the page, not the document's subject."""
    f = CACHE / key_hash(k) / "text.txt"
    if not f.exists():
        return ""
    lines = [" ".join(ln.split()) for ln in f.read_text(errors="replace").split("\n")[:40]]
    for s in [s for s in lines if s][:3]:
        m = re.match(r"(.+?)\s*\|\s*ReliefWeb$", s)
        if m:
            head, _, tag = m.group(1).rpartition(" - ")
            return head if head and not re.search(r"\d", tag) else m.group(1)
    return ""


def title_as_of(title):
    """'(as of 22 August 2017)' or a trailing ', 08 Dec 2008' in a bulletin's own
    title: its data or issue date, a lower bound for publication."""
    m = re.search(r"\bas\s+of\s+(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)\s+(\d{4})", title or "", re.I) or \
        re.search(r",\s*(\d{1,2})\s+([A-Za-z]{3,})\.?\s+(\d{4})\s*$", title or "")   # OCHA: '..., 08 Dec 2008'
    if m:
        try:
            return datetime.strptime(f"{m.group(1)} {m.group(2)[:3]} {m.group(3)}", "%d %b %Y").date()
        except ValueError:
            return None
    return None


def doc_heading(k):
    """The document's own title: an HTML page's title line, else the first
    substantial line of the cached text that is not site navigation."""
    pt = page_title(k)
    if pt:
        return pt[:200]
    f = CACHE / key_hash(k) / "text.txt"
    if not f.exists():
        return ""
    for ln in f.read_text(errors="replace").split("\n")[:60]:
        s = " ".join(ln.split())
        if 4 <= len(s.split()) <= 18 and len(s) <= 140 and re.search(r"[A-Za-z]{4}", s) \
                and not NAV_RX.search(s) \
                and not re.search(r"page\s*\d|www\.|https?:|©|copyright", s, re.I):
            return s
    return ""


def target_meta_index(iso, k, info, run, r, span=None, data_end=None):
    """Reuse the target's entry only for the same URL that was verified, Active
    and at least as reliable as the series; otherwise register a neutral entry."""
    url = info.get("url_used") or info.get("best_url")
    level = int(info.get("reliability_level") or 2)
    for m in read_csv(DATA / iso / "metadata_ai.csv"):
        lv = re.search(r"Level\s*([1-4])\b", m.get("Reliability_Level") or "")
        if canon_url(m.get("URL", "")) == canon_url(url) and lv and int(lv.group(1)) == level and \
                (m.get("Status") or "Active").strip() not in ("Superseded", "Retracted", "Inactive"):
            return m["Index"], "reused", level
    title = display_title(k, info)
    if title.startswith(SERIES[info["series"]][3] + ":"):
        head = doc_heading(k)                 # file-name titles are opaque: use the document's own title line
        if head:
            # a heading that names its own publisher stands alone (JCISA is WHO/UNICEF/OCHA/Oxfam)
            title = head if re.search(r"JCISA|Joint Cholera Initiative|UNICEF|OCHA|WHO|ECDC|Africa CDC", head) \
                else f"{SERIES[info['series']][3]}: {head}"
    when = info.get("doc_date") or (f"data to {data_end}" if data_end and data_end > date.min else "") \
        or k.split(":", 1)[-1][:40]
    name = f"{title} ({when}) [multi-country; cross-country harvest]"
    desc = (f"Multi-country document ({SERIES[info['series']][3]}; doc_key {k}) first collected for "
            f"{info.get('citing') or 'another country'}. Text sha256 {info.get('sha256', '')[:16]}"
            f"{'; read from Wayback snapshot ' + info['wayback_snapshot'] if info.get('wayback_snapshot') else ''}. "
            f"Registered for {iso} by cross-country source harvesting ({run}).")
    args = ["register-source", iso, "--name", name, "--url", url, "--reliability", str(level),
            "--description", desc, "--date-range", f"{span[0]} to {span[1]}" if span else f"{r['tl']} to {r['tr']}",
            "--discovery", f"cross-country source harvest {run}: doc_key {k}",
            "--cross-references", info.get("citing", "")]
    rc, msg = run_tool("add_observation.py", args)
    m = re.search(r"(?:REGISTERED|EXISTS) index=(\d+)", msg)
    if not m and "already uses the Source name" in msg:
        args[args.index("--name") + 1] = name[:-1] + f" {key_hash(k)[:6]}]"
        rc, msg = run_tool("add_observation.py", args)
        m = re.search(r"(?:REGISTERED|EXISTS) index=(\d+)", msg)
    if m:
        return m.group(1), ("registered" if "REGISTERED" in msg else "exists"), level
    return None, msg, level


PTXT = {"ytd": "year-to-date total (1 January to the as-of date)",
        "prior_year_ytd": "previous year's year-to-date total, quoted as a comparison",
        "annual": "calendar-year total", "weekly": "weekly count", "period": "count for the stated period",
        "outbreak_cumulative": "event cumulative from the start of the reporting period"}


def cmd_apply(a):
    if not (a.iso or a.all):
        print("apply needs --iso ISO[,ISO] or --all")
        return 2
    reg = {r["doc_key"]: r for r in read_csv(REGISTRY)}
    infos, texts = load_doc_infos(reg)
    gaps = load_gaps()
    tool_sha = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:12]
    gate = None if a.no_gate else BuilderGate()
    with tool_lock():
        done = {r["candidate_id"] for r in read_csv(HARVEST_LOG) if r["status"] == "added"}
        todo = [r for r in read_csv(SCREENED) if r["decision"] == "ADD" and r["candidate_id"] not in done]
        if a.iso:
            todo = [r for r in todo if r["target_iso"] in a.iso.upper().split(",")]
        print(f"{len(todo)} ADD candidates{' (dry run)' if a.dry_run else ''}", flush=True)
        stats = Counter()
        by_iso = defaultdict(list)
        for r in todo:
            by_iso[r["target_iso"]].append(r)
        # latest as-of date among each document's own figures (dates undated documents)
        data_end = defaultdict(lambda: date.min)
        for x in read_csv(SCREENED):
            if x.get("quote_verified") == "TRUE" and not x["decision"].startswith("REJECT") and d(x.get("tr")):
                data_end[x["doc_key"]] = max(data_end[x["doc_key"]], d(x["tr"]))
        for iso, rs in sorted(by_iso.items()):
            rows = national_rows(iso)
            subs = subnational_rows(iso)
            cov = Coverage(iso, rows)
            zeros, annuals = BuilderGate.context(rows)
            before = gate.series(iso) if gate else None
            spans = defaultdict(list)              # metadata Date_Range covers all of a document's rows
            for x in rs:
                spans[x["doc_key"]] += [x["tl"], x["tr"]]
            # finest periods first, so coarser totals are re-assessed against them
            for r in sorted(rs, key=lambda r: ((d(r["tr"]) - d(r["tl"])).days, r["tl"])):
                k = r["doc_key"]
                info = infos.get(k) or {}
                dec, why, ex = assess(r, info, texts.get(k), rows, cov, gaps, subs)
                if dec == "ADD" and gate and before is not None:
                    trial = {"Index": "0", "Location": f"AFR::{iso}", "TL": r["tl"], "TR": r["tr"],
                             "sCh": str(to_int(r["sch"])), "deaths": r.get("deaths", ""), "cCh": r.get("cch", ""),
                             "confidence_weight": ex["weight"], "processing_notes": "trial", "source_database": "AI"}
                    after = gate.series(iso, trial)
                    why_gate = BuilderGate.check(before, after or {}, to_int(r["sch"]), d(r["tl"]), d(r["tr"]),
                                                 zeros, annuals)
                    if why_gate:
                        dec, why = "CONFLICT_BUILDER", why_gate
                entry = {f: r.get(f, "") for f in LOG_FIELDS}
                entry.update(tool_sha=tool_sha, run=a.run, applied_at=datetime.now().isoformat(timespec="seconds"),
                             doc_url=info.get("url_used") or info.get("best_url", ""), sha256=info.get("sha256", "")[:16])
                print(f"  {iso} {r['tl']}..{r['tr']} {r['period_type']:19s} sCh={r['sch'] or '-':>6} "
                      f"d={r.get('deaths') or '-':>4} {dec if dec != 'ADD' else 'ADD'}"
                      f"{': ' + why if dec != 'ADD' else ''}  [{k}]", flush=True)
                if dec != "ADD":
                    stats["rescreened_" + dec] += 1
                    if not a.dry_run:
                        entry.update(status="skipped_rescreen", message=f"{dec}: {why}")
                        append_log(entry)
                    continue
                if a.dry_run:
                    stats["would_add"] += 1
                    continue
                midx, action, level = target_meta_index(iso, k, info, a.run, r,
                                                        (min(spans[k]), max(spans[k])), data_end.get(k))
                if not midx:
                    entry.update(status="meta_failed", message=str(action)[-300:])
                    append_log(entry)
                    stats["meta_failed"] += 1
                    continue
                weight = min(float(ex["weight"]), 1.0 if level == 1 else 0.9)
                pub = d(info.get("doc_date")) if info.get("doc_date") else None
                if not pub and data_end.get(k, date.min) > date.min:
                    pub = data_end[k]                 # undated: the latest date the document reports
                rep = pub if pub and pub >= d(r["tr"]) else d(r["tr"])
                national = ("Only cholera event listed for this country in the bulletin; treated as the national "
                            "count." if r["period_type"] == "outbreak_cumulative" else "National total.")
                note = (f"[XREF-HARVEST {a.run}] Cross-country source harvest: figure for {iso} from a multi-country "
                        f"document ({SERIES[info['series']][3]}, doc_key {k}) first collected for "
                        f"{info.get('citing') or 'another country'}. Period type: {PTXT[r['period_type']]}. "
                        f"Fetched from {info.get('url_used') or info.get('best_url')} (text sha256 "
                        f"{info.get('sha256', '')[:16]}); quote verified verbatim; screened against existing rows "
                        f"(equal-or-finer coverage {ex.get('equal_or_finer_cover', '')}). {national} "
                        f"Do not sum with sub-national rows.")
                args = ["add", iso, "--source-index", midx, "--location", f"AFR::{iso}", "--tl", r["tl"],
                        "--tr", r["tr"], "--confidence", f"{weight:.2f}", "--quote", r["quote"], "--note", note,
                        "--reporting-date", str(rep)]
                for f, flag in (("sch", "--sch"), ("cch", "--cch"), ("deaths", "--deaths")):
                    if (r.get(f) or "").strip() != "":
                        args += [flag, str(to_int(r[f]))]
                rc, msg = run_tool("add_observation.py", args)
                m = re.search(r"ADDED row Index=(\d+)", msg)
                entry.update(meta_index=midx, meta_action=action, weight=f"{weight:.2f}",
                             data_index=m.group(1) if m else "", status="added" if m else "rejected",
                             message="" if m else msg[-300:])
                append_log(entry)
                stats[entry["status"]] += 1
                if m:      # later candidates for this country see the new row
                    rows = national_rows(iso)
                    cov = Coverage(iso, rows)
                    zeros, annuals = BuilderGate.context(rows)
                    before = gate.series(iso) if gate else None
    print(dict(stats))
    return 0


def cmd_rollback(a):
    if not (a.iso or a.all):
        print("rollback needs --iso ISO[,ISO] or --all")
        return 2
    n = skipped = 0
    with tool_lock():
        log = read_csv(HARVEST_LOG)
        for e in log:
            if e["run"] != a.run or e["status"] != "added":
                continue
            if a.iso and e["target_iso"] not in a.iso.upper().split(","):
                continue
            row = next((r for r in read_csv(DATA / e["target_iso"] / "cholera_data_ai.csv")
                        if r["Index"] == e["data_index"]), None)
            if not row or f"[XREF-HARVEST {a.run}]" not in (row.get("processing_notes") or "") or \
                    row["TL"] != e["tl"] or row["TR"] != e["tr"] or to_int(row["sCh"]) != to_int(e["sch"]):
                print(f"  skip {e['target_iso']} Index {e['data_index']}: row missing or changed since the harvest")
                skipped += 1
                continue
            rc, msg = run_tool("revise_observation.py", [e["target_iso"], "--index", e["data_index"], "--delete",
                                                         "--agent", "7", "--reason",
                                                         f"cross-country harvest rollback ({a.run}): {a.reason}"])
            if rc == 0:
                e["status"] = "rolled_back"
                n += 1
            else:
                print(f"  rollback failed {e['target_iso']} {e['data_index']}: {msg[-200:]}")
        write_csv(HARVEST_LOG, log, LOG_FIELDS)
    print(f"rolled back {n} rows of run {a.run}; skipped {skipped}")
    return 0


def cmd_queue(a):
    rows = [r for r in read_csv(SCREENED) if r["target_iso"] == a.iso.upper()]
    done = {r["candidate_id"] for r in read_csv(HARVEST_LOG) if r["status"] == "added"}
    show = [r for r in rows if r["candidate_id"] not in done and
            (r["decision"] in ("ADD", "CORROBORATES", "CONFLICT", "CONFLICT_ZERO", "CONFLICT_HARVEST",
                               "DUPLICATE_SUBNATIONAL", "CONFLICT_BUILDER")
             or r["decision"].startswith("LOG_"))]
    print(f"{a.iso.upper()}: {len(show)} open candidates from {len({r['doc_key'] for r in show})} documents")
    for r in sorted(show, key=lambda r: (r["decision"], r["tl"])):
        print(f"  {r['decision']:20s} {r['tl']}..{r['tr']} sCh={r['sch']} d={r['deaths']} "
              f"[{r['period_type']}] {r['doc_key']}  {r['reason']}")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("registry").set_defaults(func=cmd_registry)
    f = sub.add_parser("fetch")
    f.add_argument("--limit", type=int, default=0)
    f.add_argument("--workers", type=int, default=4)
    f.add_argument("--series", default="")
    f.add_argument("--all", action="store_true", help="also documents with no beneficiaries")
    f.add_argument("--skip-failed", action="store_true", help="do not retry earlier failures")
    f.add_argument("--include-notifications", action="store_true",
                   help="also WER weekly notification issues (not harvestable from text; see wer_kind)")
    f.add_argument("--exclude-host", default="", help="comma list of hosts to defer (e.g. iris.who.int when it throttles)")
    f.add_argument("--only-host", default="", help="comma list of hosts to fetch")
    f.add_argument("--url", default="", help="fetch one document (Agent 5 push)")
    f.add_argument("--name", default="", help="its Source name, with --url")
    f.add_argument("--citing", default="", help="ISO that registered it, with --url")
    f.set_defaults(func=cmd_fetch)
    sub.add_parser("excerpt").set_defaults(func=cmd_excerpt)
    sub.add_parser("aliases", help="map ReliefWeb report pages to their PDF attachments").set_defaults(func=cmd_aliases)
    sub.add_parser("parse").set_defaults(func=cmd_parse)
    sub.add_parser("screen").set_defaults(func=cmd_screen)
    p = sub.add_parser("verify", help="read-only self-check of an agent candidate file")
    p.add_argument("file")
    p.set_defaults(func=cmd_verify)
    p = sub.add_parser("apply")
    p.add_argument("--run", required=True)
    p.add_argument("--iso", default="")
    p.add_argument("--all", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--no-gate", action="store_true", help="skip the weekly-builder simulation gate (not recommended)")
    p.set_defaults(func=cmd_apply)
    p = sub.add_parser("rollback")
    p.add_argument("--run", required=True)
    p.add_argument("--iso", default="")
    p.add_argument("--all", action="store_true")
    p.add_argument("--reason", required=True)
    p.set_defaults(func=cmd_rollback)
    p = sub.add_parser("queue")
    p.add_argument("iso")
    p.set_defaults(func=cmd_queue)
    a = ap.parse_args()
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())
