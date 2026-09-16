"""Collect AMS JobBarometer occupation statistics (Tier-1, official, longitudinal).

jobbarometer.ams.at publishes, per AMS occupation (Berufsuntergruppe) and per
Bundesland (NUTS-2), the yearly number of online job advertisements 2020-2025
("Inserate aus dem Internet"), a 3-year trend rating, the share of all ads,
a comparison with similar occupations, the Bundesland distribution and the
most demanded competencies (Austria-wide). Pages are server-rendered HTML.

URL: https://jobbarometer.ams.at/berufe/{group_id}/{beruf_id}/{bl}
     bl in AT11..AT34 (NUTS-2) or omitted for all of Austria.
Politeness: 2s delay (the site timed out once during a fast probe).
"""
from __future__ import annotations

import html
import json
import re
import sys
import time
from pathlib import Path

from common import RawWriter, Session

BASE = "https://jobbarometer.ams.at"
GROUP_IDS = list(range(270, 335))
BL = ["AT11", "AT12", "AT13", "AT21", "AT22", "AT31", "AT32", "AT33", "AT34"]
RELEVANT_GROUPS = {295: "Datenbanken", 301: "IT-Analyse und -Organisation", 286: "Marketing, Werbung, Public Relations",
                   291: "Wirtschaftsberatung, Unternehmensdienstleistungen", 285: "Management, Organisation",
                   290: "Wirtschaft und Technik", 303: "Softwaretechnik, Programmierung", 282: "Bank-, Finanz- und Versicherungswesen"}
RELEVANT_NAME_RE = re.compile(r"data|daten|statist|informatik|markt|marketing|analy|business|controll|mathemat|wirtschaftswissen|sozialwissen|forschung|künstliche|ki[- ]|machine|software|projekt|e-?commerce|online|digital|web", re.I)


def vis(t: str) -> str:
    t = re.sub(r"<script.*?</script>", " ", t, flags=re.S)
    t = re.sub(r"<[^>]+>", "\n", t)
    t = html.unescape(t)
    t = re.sub(r"[ \t\r]+", " ", t)
    t = re.sub(r"\n\s*\n+", "\n", t)
    return t


def pairs(block: str, stop: str) -> list[tuple[str, str]]:
    """Parse alternating 'label\\nvalue' lines until `stop` marker."""
    out = []
    lines = [l.strip() for l in block.split("\n") if l.strip()]
    i = 0
    while i + 1 < len(lines):
        if lines[i].startswith(stop):
            break
        lab, val = lines[i], lines[i + 1]
        if re.match(r"^[<>]?\s*[\d.,+\-]+\s*%?$", val):
            out.append((lab, val))
            i += 2
        else:
            i += 1
    return out


def num(s: str):
    s = s.strip().replace(".", "").replace("%", "").replace("+", "").replace(",", ".")
    if s.startswith("<"):
        return {"lt": float(s[1:].strip())}
    try:
        return float(s)
    except ValueError:
        return None


def parse_detail(t: str) -> dict:
    v = vis(t)
    d = {}
    m = re.search(r"Trends, Daten und Fakten zum Beruf \"(.+?)\"\s*(?:\((.+?)\))?", v)
    d["beruf_name"] = m.group(1) if m else None
    d["region_name"] = (m.group(2) if m and m.group(2) else "Österreich")
    m = re.search(r"3-Jahres Trend \((\d{4})-(\d{4})\)\n(\w+)", v)
    d["trend_window"] = f"{m.group(1)}-{m.group(2)}" if m else None
    d["trend_3y"] = m.group(3) if m else None
    m = re.search(r"Anteil an allen Inseraten \((\d{4})\)\n([^\n]+)", v)
    d["share_year"] = int(m.group(1)) if m else None
    d["share_label"] = m.group(2).strip() if m else None
    m = re.search(r"Zahl der Inserate \((\d{4})\)\n([\d.<>]+)", v)
    d["count_year"] = int(m.group(1)) if m else None
    d["count_latest"] = num(m.group(2)) if m else None
    i = v.find("Entwicklung der vergangenen Jahre")
    j = v.find("Vergleich mit", i)
    d["yearly_counts"] = {int(y): num(c) for y, c in re.findall(r"\n(20\d\d)\n([\d.<>]+)(?=\n)", v[i:j])} if i > 0 else {}
    i = v.find("Vergleich mit ähnlichen Berufen"); j = v.find("Bundesländervergleich", i)
    d["similar_occupations"] = [(a, num(b)) for a, b in pairs(v[i:j], "Bundesländervergleich")[1:]] if i > 0 else []
    i = v.find("Bundesländervergleich"); j = v.find("Kartenansicht", i)
    d["bundesland_counts"] = [(a, num(b)) for a, b in pairs(v[i:j], "Kartenansicht")[1:]] if i > 0 else []
    i = v.find("Am häufigsten nachgefragte Kompetenzen"); j = v.find("Entwicklung der nachgefragten Kompetenzen", i)
    d["top_competencies_pct"] = [(a, num(b)) for a, b in pairs(v[i:j], "Entwicklung der")[1:]] if i > 0 else []
    i = v.find("Entwicklung der nachgefragten Kompetenzen"); j = v.find("Datenquelle:", i)
    d["growing_competencies_pp"] = [(a, num(b)) for a, b in pairs(v[i:j], "Datenquelle")[1:]] if i > 0 else []
    m = re.search(r"Berufsbeschreibung\n(.+?)\nTrend\n", v, re.S)
    d["description"] = m.group(1).strip() if m else None
    return d


def catalogue(s: Session, w: RawWriter) -> dict:
    cat = {}
    for gid in GROUP_IDS:
        r = s.get(f"{BASE}/berufe/{gid}")
        if r is None or r.status_code != 200:
            continue
        t = r.text
        m = re.search(r"<title>AMS JobBarometer - Details zu (.+?) in Österreich</title>", t)
        gname = html.unescape(m.group(1)) if m else None
        berufe = {b: html.unescape(n) for b, n in re.findall(r'data-beruf-id="(\d+)"\s*title="([^"]+)"', t)}
        m2 = re.search(r"Elektrotechnik.*?|Büro.*?", t)
        cat[gid] = {"group_name": gname, "berufe": berufe}
        w.write("catalogue", {"group_id": gid, "group_name": gname, "berufe": berufe})
        print(f"[jb] group {gid} {gname}: {len(berufe)} berufe", flush=True)
    return cat


def main():
    w = RawWriter("jobbarometer")
    s = Session(delay=2.0)
    cat_path = w.dir / "catalogue.jsonl"
    if cat_path.exists():
        cat = {}
        for line in open(cat_path, encoding="utf-8"):
            e = json.loads(line)["record"]; cat[e["group_id"]] = e
    else:
        cat = catalogue(s, w)
    targets = []
    for gid, g in cat.items():
        gid = int(gid)
        for bid, name in (g.get("berufe") or {}).items():
            if gid in RELEVANT_GROUPS or RELEVANT_NAME_RE.search(name):
                targets.append((gid, bid, name))
    print(f"{len(targets)} target occupations")
    done = w.existing_ids("details", lambda e: (e["record"]["group_id"], e["record"]["beruf_id"], e["record"]["bl"]))
    for gid, bid, name in targets:
        for bl in [None] + BL:
            key = (gid, bid, bl or "AT")
            if key in done:
                continue
            url = f"{BASE}/berufe/{gid}/{bid}" + (f"/{bl}" if bl else "")
            r = s.get(url)
            if r is None or r.status_code != 200:
                w.log_query(url=url, status=(r.status_code if r else None), error=True)
                continue
            d = parse_detail(r.text)
            d.update({"group_id": gid, "beruf_id": bid, "beruf_name_catalogue": name, "bl": bl or "AT", "url": url, "html": r.text})
            w.write("details", d)
        print(f"[jb] done {name} ({gid}/{bid})", flush=True)
    w.close()


if __name__ == "__main__":
    main()
