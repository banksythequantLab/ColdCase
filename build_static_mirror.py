"""
Build a STATIC, always-on read-only mirror of the Cold Case dashboard for
Cloudflare Pages. Because the corpus/DB is frozen, a snapshot is faithful.

It hits the live dashboard on 127.0.0.1:8060 once, saves every read endpoint to
a static JSON file, snapshots the two HTML pages, and injects a small fetch-shim
so the *identical* UI runs with no live DB (api/x -> api/x.json,
api/casefile?name=Y -> api/casefile_<slug>.json). Output: web_static/ -> deploy
to Cloudflare Pages (`wrangler pages deploy web_static`).
"""
import os, json, re, urllib.request

BASE = "http://127.0.0.1:8060"
OUT = r"B:\ColdCase\web_static"
os.makedirs(os.path.join(OUT, "api"), exist_ok=True)

SHIM = """<script>
// static-mirror fetch shim: repoint live API calls to snapshot JSON files
(function(){const _f=window.fetch;window.fetch=function(u,o){try{
 if(typeof u==='string'&&/(^|\\/)api\\//.test(u)){
   var m=u.match(/api\\/casefile\\?name=(.+)$/);
   if(m){u='api/casefile_'+decodeURIComponent(m[1]).replace(/[^a-z0-9]+/gi,'_').replace(/^_|_$/g,'').toLowerCase()+'.json';}
   else{u=u.replace(/^\\/?api\\/([a-z_]+).*$/,'api/$1.json');}
 }}catch(e){}return _f(u,o);};})();
</script>"""

def get(path):
    with urllib.request.urlopen(BASE + path, timeout=30) as r:
        return r.read().decode("utf-8", "replace")

def slug(name):
    # must match the JS shim: /[^a-z0-9]+/gi -> "_", trim, lowercase
    return re.sub(r"[^a-z0-9]+", "_", str(name), flags=re.I).strip("_").lower()

# 1. no-param API endpoints -> api/<name>.json
endpoints = ["stats", "progress", "leads", "suspects", "graph", "timeline", "filings", "replay"]
data = {}
for e in endpoints:
    try:
        txt = get("/api/" + e)
        json.loads(txt)  # validate
        open(os.path.join(OUT, "api", e + ".json"), "w", encoding="utf-8").write(txt)
        data[e] = json.loads(txt); print("  api/%s.json" % e)
    except Exception as ex:
        print("  !! /api/%s failed: %s" % (e, ex))

# 2. casefiles for every named person in suspects + leads
names = set()
for key in ("suspects", "leads"):
    d = data.get(key)
    rows = d if isinstance(d, list) else (d.get("rows") or d.get("items") or d.get(key) or []) if isinstance(d, dict) else []
    for row in rows:
        if isinstance(row, dict):
            for k in ("name", "nm", "full_name", "real_name", "person"):
                if row.get(k): names.add(row[k]); break
# the Unified case file chips call /api/casefile?name=<short> (CFPEOPLE in the UI)
names.update(["Skilling", "Fastow", "Lay", "Causey", "Kopper"])
for nm in sorted(names):
    try:
        txt = get("/api/casefile?name=" + urllib.request.quote(nm))
        open(os.path.join(OUT, "api", "casefile_%s.json" % slug(nm)), "w", encoding="utf-8").write(txt)
    except Exception as ex:
        print("  !! casefile %s failed: %s" % (nm, ex))
print("  casefiles snapshotted:", len(names))

# 3. HTML pages with the shim injected right after <head>
for page, fn in [("/", "index.html"), ("/replay", "replay.html")]:
    html = get(page)
    html = re.sub(r"(<head[^>]*>)", r'\1<meta charset="utf-8">' + SHIM, html, count=1, flags=re.I)
    # make links relative so /replay works as replay.html on Pages
    html = html.replace('href="/replay"', 'href="replay.html"').replace("href='/replay'", "href='replay.html'")
    html = html.replace('"/replay"', '"replay.html"')
    # static mirror: auto-load the stat cards (no RU cost against a snapshot)
    autoload = ("<script>addEventListener('DOMContentLoaded',function(){setTimeout(function(){"
                "document.querySelectorAll('button').forEach(function(b){"
                "if(/refresh db stats/i.test(b.textContent))b.click();});},500);});</script>")
    html = html.replace("</body>", autoload + "</body>")
    open(os.path.join(OUT, fn), "w", encoding="utf-8").write(html)
    print("  %s (%d KB)" % (fn, len(html) // 1024))

# 4. a tiny banner note + Pages config
open(os.path.join(OUT, "_headers"), "w").write("/*\n  X-Robots-Tag: noindex\n")
print("\nDONE -> web_static/  (deploy: wrangler pages deploy web_static --project-name coldcase)")
