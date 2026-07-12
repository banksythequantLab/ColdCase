"""Full-frame 1920x1080 HTML slides for the demo video - big, readable text.
Rendered to PNG via headless Chrome, then paired with the cloned narration.
"""
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&family=JetBrains+Mono:wght@600&display=swap');
*{margin:0;box-sizing:border-box}
html,body{width:1920px;height:1080px;overflow:hidden}
body{background:radial-gradient(ellipse at 30% 20%,#132033 0%,#0d1117 65%);
color:#e9edf2;font-family:'Inter',sans-serif;display:flex;flex-direction:column;
justify-content:center;padding:110px 130px;letter-spacing:-.02em}
.kick{color:#f0b429;font-weight:800;font-size:34px;letter-spacing:.18em;
text-transform:uppercase;margin-bottom:28px}
h1{font-size:120px;font-weight:900;line-height:.98;letter-spacing:-.04em}
h2{font-size:66px;font-weight:800;line-height:1.08}
p{font-size:46px;font-weight:400;color:#c9d1d9;line-height:1.4;margin-top:34px;max-width:1500px}
.gold{color:#f0b429}.grn{color:#3fb950}.blu{color:#58a6ff}
.row{display:flex;gap:40px;margin-top:50px}
.stat{background:#161b22;border:1px solid #2a3038;border-radius:20px;padding:44px 54px;flex:1}
.stat .n{font-size:110px;font-weight:900;letter-spacing:-.04em;line-height:1;font-variant-numeric:tabular-nums}
.stat .l{font-size:30px;color:#8b949e;margin-top:16px;text-transform:uppercase;letter-spacing:.06em;font-weight:600}
.board div{display:flex;align-items:center;gap:34px;font-size:52px;font-weight:700;margin:20px 0}
.board .sc{color:#f0b429;font-weight:900;font-variant-numeric:tabular-nums;width:150px}
.board .poi{color:#3fb950;font-size:34px;font-weight:800;background:#12301c;padding:6px 20px;border-radius:30px}
.mono{font-family:'JetBrains Mono',monospace}
.big{font-size:150px;font-weight:900;letter-spacing:-.04em;line-height:1}
</style>
"""


def wrap(inner):
    return f"<!doctype html><html><head><meta charset=utf-8>{CSS}</head><body>{inner}</body></html>"


SLIDES = [
    # 0 - title
    wrap("""<div class=kick>CockroachDB &times; AWS &middot; Agentic Memory</div>
    <h1>Cold&nbsp;Case</h1>
    <p style="font-size:52px;font-style:italic;color:#f0b429;font-weight:600;
    margin-top:24px">&ldquo;Metadata is not documentation. It is evidence.&rdquo;</p>
    <p style="margin-top:28px">We gave an AI agent
    <span class=gold>517,401 real Enron emails</span>, hid the list of who was
    convicted, and asked it to solve the case &mdash; from scratch.</p>"""),
    # 1 - architecture / memory
    wrap("""<div class=kick>The memory is the product</div>
    <h2>CockroachDB is the agent's <span class=blu>brain state</span></h2>
    <p>Every email becomes a vector in a distributed index, joined to a
    communication graph and a transactional record of every hypothesis,
    finding, and piece of evidence.</p>
    <div class=row>
      <div class=stat><div class=n>956K</div><div class=l>vector memories</div></div>
      <div class=stat><div class=n>363K</div><div class=l>graph edges</div></div>
      <div class=stat><div class=n>49</div><div class=l>sessions remembered</div></div>
    </div>
    <p style="font-size:38px;color:#8b949e">It stores the <b class=gold>investigation itself</b>, not just the documents.</p>"""),
    # 2 - blind result board
    wrap("""<div class=kick>Investigating blind &middot; 100% precision@3</div>
    <h2>Its top suspects are all <span class=grn>real convictions</span></h2>
    <div class=board style="margin-top:40px">
      <div><span class=sc>0.99</span> SKILLING JEFFREY K <span class=poi>REAL POI</span></div>
      <div><span class=sc>0.99</span> LAY KENNETH L <span class=poi>REAL POI</span></div>
      <div><span class=sc>0.99</span> HIRKO JOSEPH <span class=poi>REAL POI</span></div>
      <div><span class=sc>0.99</span> KOPPER MICHAEL J <span class=poi>REAL POI</span></div>
    </div>
    <p style="font-size:38px">Found using <b class=gold>nothing but raw email</b> &mdash; no answer key.</p>"""),
    # 3 - ablation money shot
    wrap("""<div class=kick>The proof: same agent, run twice</div>
    <h2>Persistent memory is what makes it work</h2>
    <div class=row style="margin-top:60px">
      <div class=stat><div class="n" style="color:#ef4444">0/18</div><div class=l>POIs &mdash; WITHOUT memory</div></div>
      <div class=stat><div class="n grn">4/18</div><div class=l>POIs &mdash; WITH CockroachDB</div></div>
      <div class=stat><div class="n gold">100%</div><div class=l>precision@3</div></div>
    </div>
    <p style="font-size:40px">Same model. Different memory. <b class=gold>Different outcome.</b></p>"""),
    # 4 - kill / resume
    wrap("""<div class=kick>Durable across crashes</div>
    <h2>Kill it mid-investigation. Restart it.</h2>
    <p>It resumes from <span class=gold>exactly</span> where it left off &mdash;
    without reprocessing a single document.</p>
    <p class="mono" style="font-size:52px;color:#3fb950;margin-top:60px">&gt; resuming case&hellip; &#10003;</p>
    <p style="font-size:40px">The memory was never in the process. It was always in
    <b class=blu>CockroachDB</b>.</p>"""),
    # 5 - close: speed + attorney-hours + tagline
    wrap("""<div class=kick>517,401 documents &middot; no answer key</div>
    <h2>In under <span class=gold>9 hours</span> of compute, it did the work of
    <span class=grn>thousands of attorney-hours</span></h2>
    <div class=row style="margin-top:56px">
      <div class=stat><div class="n gold">~8 hrs</div><div class=l>agent compute, 44 sessions</div></div>
      <div class=stat><div class="n grn">8,600+</div><div class=l>equivalent attorney-hours</div></div>
      <div class=stat><div class="n blu">1000&times;</div><div class=l>faster first-pass review</div></div>
    </div>
    <p style="font-size:52px;margin-top:56px"><b class=gold>CockroachDB turns a
    database into an e-discovery tool.</b></p>
    <p style="font-size:34px;color:#8b949e">github.com/banksythequantLab/ColdCase &middot; coldcase.savagealgo.com</p>"""),
]
