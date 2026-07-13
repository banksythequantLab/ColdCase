"""Suite demo video v2 -- built to the 4-judge consensus script.
Open on Fastow -> suite -> ablations -> Hold Firewall (200 vs 0) -> fusion ->
enterprise depth (RLS + multi-region) -> Managed MCP -> close bookend on Fastow.
Cloned voice (johnson:8300), ffmpeg assembly. <3 minutes.
"""
import os, subprocess, requests

HERE = os.path.dirname(os.path.abspath(__file__))
REF = r"B:\freeclone-backend\derek-voice.wav"
CLONE_URL = "http://johnson:8300/api/clone"
CHROME = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"

CSS = """<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&family=JetBrains+Mono:wght@600;700&display=swap');
*{margin:0;box-sizing:border-box}
html,body{width:1920px;height:1080px;overflow:hidden}
body{background:radial-gradient(ellipse at 30% 20%,#132033 0%,#0d1117 65%);
color:#e9edf2;font-family:'Inter',sans-serif;display:flex;flex-direction:column;
justify-content:center;padding:110px 130px;letter-spacing:-.02em}
.kick{color:#f0b429;font-weight:800;font-size:34px;letter-spacing:.16em;
text-transform:uppercase;margin-bottom:26px}
h1{font-size:120px;font-weight:900;line-height:.96;letter-spacing:-.04em}
h2{font-size:64px;font-weight:800;line-height:1.08}
p{font-size:44px;font-weight:400;color:#c9d1d9;line-height:1.4;margin-top:30px;max-width:1580px}
.gold{color:#f0b429}.grn{color:#3fb950}.blu{color:#58a6ff}.red{color:#f85149}.pur{color:#bc8cff}
.board div{display:flex;align-items:center;gap:28px;font-size:44px;font-weight:700;margin:16px 0}
.board .ag{width:320px;font-weight:800}
.row{display:flex;gap:36px;margin-top:44px}
.stat{background:#161b22;border:1px solid #2a3038;border-radius:18px;padding:38px 46px;flex:1}
.stat .n{font-size:96px;font-weight:900;letter-spacing:-.04em;line-height:1;font-variant-numeric:tabular-nums}
.stat .l{font-size:27px;color:#8b949e;margin-top:14px;text-transform:uppercase;letter-spacing:.05em;font-weight:600}
.mono{font-family:'JetBrains Mono',monospace}
</style>"""

def wrap(inner):
    return f"<!doctype html><html><head><meta charset=utf-8>{CSS}</head><body>{inner}</body></html>"

# (kind, content, narration)  kind: 'html' slide or 'img' existing PNG
SCENES = [
 ("html", wrap("""<div class=kick>One SQL statement &middot; five agents &middot; one CockroachDB</div>
   <h2>Cold Case named four ringleaders. <span class=grn>Only the suite caught Fastow.</span></h2>
   <div class=board style="margin-top:42px">
     <div><span class="ag">Cold Case</span>Skilling &middot; Lay &middot; Kopper &middot; Hirko &mdash; 4/18</div>
     <div><span class="ag">Witness</span>2 sworn contradictions</div>
     <div><span class="ag">Chronicle</span>LJM2 self-dealing timeline</div>
     <div><span class="ag">Gap Hunter</span>3 withheld documents</div>
     <div><span class="ag">Hold Firewall</span>hold on 200 docs, ACID</div>
   </div>
   <p style="font-size:40px">Fastow was near-invisible in email &mdash; no single agent could catch him. <b class=gold>The entwined memory did.</b></p>"""),
  "Cold Case independently names four convicted ringleaders: Skilling, Lay, Kopper, "
  "and Hirko. But Fastow, the architect, was near-invisible in email. Yet one SQL "
  "query over the shared CockroachDB memory assembles his whole case file. No single "
  "agent could solve it; the entwined memory did."),

 ("img", r"B:\ediscovery-suite\docs\hero.png",
  "This is Not A Lawyer: five specialized e-discovery agents feeding one "
  "transactional memory, which produces a single unified case file. Not chat "
  "history, not a vector cache. With memory off, every agent's result "
  "collapses. Persistence is the whole product."),

 ("img", r"B:\Chronicle\docs\suite_ablations.png",
  "Every agent ships an objective ablation: same model, same data, memory on "
  "versus off. Cold Case finds four of the real convicts versus zero. Chronicle's "
  "theory converges on the truth instead of oscillating to the wrong answer. "
  "Witness keeps twelve of twelve contradictions versus three. Persistent memory "
  "doesn't just add speed. It changes the outcome."),

 ("img", r"B:\HoldFirewall\docs\spoliation.png",
  "This is a transactional engine, not a vector store. Rogue deletion scripts "
  "race an agent placing legal holds. Under READ COMMITTED, every one of two "
  "hundred held documents is destroyed. Under CockroachDB SERIALIZABLE: zero. "
  "Same cluster, same contention. The only variable is the isolation level."),
]

SCENES += [
 ("html", wrap("""<div class=kick>Vector + graph fusion &middot; one SQL statement</div>
   <h2>The graph finds who the <span class=blu>vector misses</span></h2>
   <div class=board style="margin-top:40px;font-family:'JetBrains Mono',monospace;font-size:38px">
     <div><span style="width:520px;font-weight:700">KITCHEN, LOUISE</span><span class=grn>graph-only &mdash; vector ranked 0</span></div>
     <div><span style="width:520px;font-weight:700">LAVORATO, JOHN</span><span class=grn>graph-only &mdash; vector ranked 0</span></div>
     <div><span style="width:520px;font-weight:700">SHACKLETON &middot; SAGER</span><span class=grn>LJM in-house counsel</span></div>
   </div>
   <p>C-SPANN vectors fused with a 363,000-edge communication graph, in one
   statement. <b class=gold>Vectors, graph joins, and ACID &mdash; one engine.</b></p>"""),
  "Our retriever fuses vector search with a three hundred sixty three thousand "
  "edge communication graph, in one SQL statement. It surfaces fraud-network "
  "figures, including the LJM in-house lawyers, that pure vector search ranks "
  "nowhere. Vectors, graph joins, and A-C-I-D, in one engine. That is why CockroachDB."),

 ("html", wrap("""<div class=kick>The database enforces what the law demands</div>
   <h2>Ethical walls &amp; <span class=blu>proven resilience</span></h2>
   <div class=row style="margin-top:40px">
     <div class=stat><div class="n" style="font-size:56px;color:#3fb950">RLS</div>
       <div class=l style="text-transform:none;font-size:29px;margin-top:18px">Row-level security: a reviewer
       <b>physically cannot</b> read another matter or a privileged document &mdash; zero rows, not filtered in code.</div></div>
     <div class=stat><div class="n" style="font-size:40px">EU region <span style="color:#f85149">OFFLINE</span> &rarr; <span style="color:#3fb950">0 lost</span></div>
       <div class=l style="text-transform:none;font-size:29px;margin-top:18px">Take the entire <b>europe-west1</b> region down &mdash;
       all <b>6 legal holds survive</b>, including the 2 GDPR-pinned EU rows. SURVIVE REGION FAILURE, proven.</div></div>
   </div>"""),
  "The database enforces what the law demands. Row-level security walls off "
  "privileged and cross-matter data -- a reviewer physically cannot read it. And "
  "when we take the entire European region offline, every legal hold survives: "
  "zero lost, even the GDPR-pinned EU rows. Data residency and resilience, proven."),

 ("html", wrap("""<div class=kick>Managed MCP Server &middot; audit in plain English</div>
   <h2>Interrogate the whole case memory, live</h2>
   <p class=mono style="font-size:42px;color:#58a6ff;margin-top:44px">&ldquo;Who was involved in LJM2, and what did they hide?&rdquo;</p>
   <p style="font-size:38px">&rarr; the MCP server queries live, consistent, transactional state
   and returns the people, the timeline, and the withheld documents &mdash; with sources.</p>"""),
  "Attorneys and judges audit the entire case memory in plain English through the "
  "Managed MCP server: live queries against consistent, transactional state, "
  "returning the people, the timeline, and the documents, with their sources."),

 ("html", wrap("""<div class=kick>github.com/banksythequantLab/ediscovery-suite</div>
   <h2>No single agent solved this case.<br><span class=grn>Persistent, transactional memory did.</span></h2>
   <p style="font-size:48px;margin-top:44px">Five legal agents. One CockroachDB memory. Entwined.</p>
   <p style="font-size:40px;color:#f0b429;font-weight:600">Metadata isn't documentation &mdash; it's legally defensible evidence.</p>"""),
  "No single agent solved this case. Persistent, transactional, shared memory did. "
  "Five legal agents, one CockroachDB memory. Metadata isn't documentation. "
  "It is legally defensible evidence."),
]

# --- live Memory Replay scene (real UI screen recording), inserted after the hero at assembly ---
CLIP_SRC = r"C:\Users\solti\Videos\Screen Recordings\Screen Recording 2026-07-13 003013.mp4"
CAP_HTML = """<!doctype html><html><head><meta charset=utf-8>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
*{margin:0;box-sizing:border-box}
html,body{width:1920px;height:1080px;overflow:hidden;
 background:radial-gradient(ellipse at 24% 16%,#131c2b 0%,#0d1117 62%,#0a0e13 100%);
 font-family:Inter,sans-serif;color:#e9edf2}
.frame{position:absolute;left:96px;top:52px;width:836px;height:956px;
 border:2px solid #2f3743;border-radius:22px;background:#0b0f14}
.cap{position:absolute;left:988px;top:150px;width:852px}
.kick{color:#f0b429;font-weight:800;font-size:29px;letter-spacing:.14em;text-transform:uppercase}
h2{font-size:58px;font-weight:900;line-height:1.06;margin-top:22px;letter-spacing:-.02em}
.gold{color:#f0b429}
ul{margin-top:46px;list-style:none}
li{font-size:32px;color:#c9d1d9;font-weight:500;margin:28px 0;padding-left:40px;position:relative;line-height:1.32}
li:before{content:'';position:absolute;left:0;top:13px;width:16px;height:16px;border-radius:4px;background:#f0b429}
li.g:before{background:#3fb950}
</style></head><body>
<div class=frame></div>
<div class=cap>
  <div class=kick>Live &#183; Memory Replay</div>
  <h2>Time-travel through the agent's <span class=gold>persisted memory</span></h2>
  <ul>
    <li>31 snapshots &#8212; CockroachDB &#8594; Amazon S3</li>
    <li>drag to replay every hypothesis, finding &amp; guilt score</li>
    <li class=g>green = a suspect the agent just uncovered</li>
    <li>it lives in the database &#8212; a chatbot has nothing to replay</li>
  </ul>
</div></body></html>"""

SCENES += [
 ("clip", (CLIP_SRC, CAP_HTML),
  "This is that memory, replayed. Each session snapshots the agent's full state "
  "to CockroachDB and S3. Drag the slider, and its thinking evolves -- a stateless "
  "chatbot has nothing to replay."),
]

# --- Enron corpus intro (opening scene) ---
SCENES += [
 ("html", wrap("""<div class=kick>The evidence &middot; real data</div>
   <h2>Half a million real emails from <span class=grn>history's largest fraud</span></h2>
   <div class=row>
     <div class=stat><div class=n>517,401</div><div class=l>Enron emails</div></div>
     <div class=stat><div class=n>22</div><div class=l>SEC filings</div></div>
     <div class=stat><div class=n>18</div><div class=l>convicted execs</div></div>
   </div>
   <p style="font-size:38px">The benchmark corpus for legal e-discovery &mdash; and because we
   know who was convicted, it's <b class=gold>ground truth we can measure against.</b></p>"""),
  "First, the data. Enron's collapse was one of history's largest corporate frauds, "
  "leaving half a million real emails and the company's SEC filings. Known convictions "
  "give us ground truth to measure against."),
]


def clone(text, out_wav):
    if os.path.exists(out_wav) and os.path.getsize(out_wav) > 4000:
        print("  (cached)", os.path.basename(out_wav)); return
    with open(REF, "rb") as f:
        r = requests.post(CLONE_URL, files={"prompt_audio": ("ref.wav", f, "audio/wav")},
            data={"text": text, "lang": "en"}, timeout=900)
    assert r.status_code == 200 and len(r.content) > 4000, r.text[:300]
    open(out_wav, "wb").write(r.content)
    print(f"  cloned {os.path.basename(out_wav)} ({len(r.content)//1024} KB)")

def render_html(html, png):
    hp = png.replace(".png", ".html")
    open(hp, "w", encoding="utf-8").write(html)
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
        "--window-size=1920,1080", "--force-device-scale-factor=1",
        f"--screenshot={png}", "file:///" + hp.replace("\\", "/")], timeout=60)

def dur(wav):
    out = subprocess.run(["ffprobe", "-v", "quiet", "-of", "csv=p=0",
        "-show_entries", "format=duration", wav], capture_output=True, text=True)
    return float(out.stdout.strip() or 3.0)

def main():
    clips = []
    for i, (kind, content, text) in enumerate(SCENES):
        wav = os.path.join(HERE, f"v2_seg{i}.wav"); clone(text, wav)
        img = os.path.join(HERE, f"v2_img{i}.png")
        d = dur(wav) + 0.55
        clip = os.path.join(HERE, f"v2_clip{i}.mp4")
        if kind == "clip":
            clip_src, cap_html = content
            render_html(cap_html, img)                      # dark canvas + caption + empty frame
            subprocess.run(["ffmpeg", "-y", "-loop", "1", "-t", f"{d:.2f}", "-i", img,
                "-ss", "2.0", "-i", clip_src, "-i", wav,
                "-filter_complex",
                "[1:v]scale=-2:930,setsar=1[v];[0:v][v]overlay=112:65:shortest=0,setsar=1[o]",
                "-map", "[o]", "-map", "2:a", "-c:v", "libx264", "-t", f"{d:.2f}",
                "-r", "25", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
                "-af", "apad=pad_dur=0.45", clip], check=True)
        else:
            if kind == "html": render_html(content, img)
            else: img = content
            subprocess.run(["ffmpeg", "-y", "-loop", "1", "-i", img, "-i", wav,
                "-c:v", "libx264", "-t", f"{d:.2f}", "-r", "25", "-pix_fmt", "yuv420p",
                "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,"
                       "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=#0d1117,setsar=1",
                "-c:a", "aac", "-b:a", "160k", "-af", "apad=pad_dur=0.45", clip], check=True)
        clips.append(clip); print(f"scene {i}: {d:.1f}s ({kind})")
    # concat order: Enron corpus intro (9), then hero (1), Fastow (0), live memory (8),
    # then ablations/spoliation/fusion/enterprise/MCP/close (2-7).
    order = [9, 1, 0, 8, 2, 3, 4, 5, 6, 7]
    ordered = [clips[k] for k in order]
    final = os.path.join(HERE, "nota_suite_demo_v2.mp4")
    args = ["ffmpeg", "-y"]
    for c in ordered:
        args += ["-i", c]
    fc = "".join(f"[{k}:v:0][{k}:a:0]" for k in range(len(ordered)))
    fc += f"concat=n={len(ordered)}:v=1:a=1[v][a]"
    args += ["-filter_complex", fc, "-map", "[v]", "-map", "[a]",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "25",
             "-c:a", "aac", "-b:a", "160k", final]
    subprocess.run(args, check=True)
    print(f"\nDONE -> {final} ({os.path.getsize(final)//1024} KB, {dur(final):.0f}s)")

if __name__ == "__main__":
    main()
