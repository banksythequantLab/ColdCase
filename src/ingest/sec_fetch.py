"""Fetch Enron's SEC EDGAR filings (public) - the documents that name Fastow,
the LJM partnerships, and the related-party transactions the emails don't cover.
Saves stripped text to data/sec/.
"""
import os
import re
import time
import html
import json
import requests

CIK = "0001024401"
HDR = {"User-Agent": "ColdCase Research dj@soltis.info"}
OUT = os.path.join(os.path.dirname(__file__), "..", "..", "data", "sec")
os.makedirs(OUT, exist_ok=True)
# forms most likely to carry POI / related-party / restatement content
WANT = {"10-K", "10-K405", "10-K/A", "10-K405/A", "DEF 14A", "10-Q/A",
        "8-K", "8-K/A"}


def strip(txt):
    txt = re.sub(r"(?is)<script.*?</script>|<style.*?</style>", " ", txt)
    txt = re.sub(r"(?s)<[^>]+>", " ", txt)
    txt = html.unescape(txt)
    txt = re.sub(r"[ \t\xa0]+", " ", txt)
    txt = re.sub(r"\n\s*\n\s*\n+", "\n\n", txt)
    return txt.strip()


def main():
    sub = requests.get(
        f"https://data.sec.gov/submissions/CIK{CIK}.json",
        headers=HDR, timeout=30).json()
    r = sub["filings"]["recent"]
    rows = list(zip(r["form"], r["filingDate"], r["accessionNumber"],
                    r["primaryDocument"]))
    # keep wanted forms; prioritise 2000-2002 (the fraud window)
    picked, seen_forms = [], {}
    for form, date, acc, doc in rows:
        if form not in WANT or not doc:
            continue
        yr = date[:4]
        if form.startswith("8-K") and yr not in ("2001", "2002"):
            continue
        key = form
        seen_forms[key] = seen_forms.get(key, 0) + 1
        if form.startswith("8-K") and seen_forms[key] > 20:
            continue
        picked.append((form, date, acc, doc))
    print(f"downloading {len(picked)} filings...", flush=True)
    n = 0
    for form, date, acc, doc in picked:
        accnd = acc.replace("-", "")
        url = (f"https://www.sec.gov/Archives/edgar/data/{int(CIK)}/"
               f"{accnd}/{doc}")
        try:
            body = requests.get(url, headers=HDR, timeout=40).text
        except Exception as e:
            print("  skip", url, str(e)[:60]); continue
        text = strip(body)
        if len(text) < 400:
            continue
        safe = f"{date}_{form.replace('/','-').replace(' ','')}_{accnd}.txt"
        with open(os.path.join(OUT, safe), "w", encoding="utf-8") as f:
            f.write(f"SEC FILING | {form} | filed {date} | Enron Corp\n\n"
                    + text[:600000])
        n += 1
        if n % 10 == 0:
            print(f"  {n} saved", flush=True)
        time.sleep(0.15)   # be polite to EDGAR
    print(f"DONE: {n} filings -> {OUT}")


if __name__ == "__main__":
    main()
