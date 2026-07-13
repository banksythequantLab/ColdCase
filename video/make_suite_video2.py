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
   <h2>Cold Case missed Fastow. <span class=grn>The suite didn't.</span></h2>
   <div class=board style="margin-top:42px">
     <div><span class="ag red">Cold Case</span><span style="color:#8b949e">&mdash; nothing</span></div>
     <div><span class="ag grn">Witness</span>2 sworn contradictions</div>
     <div><span class="ag gold">Chronicle</span>LJM2 self-dealing timeline</div>
     <div><span class="ag blu">Gap Hunter</span>3 withheld documents</div>
     <div><span class="ag pur">Hold Firewall</span>hold on 200 docs, ACID</div>
   </div>
   <p style="font-size:40px">No single agent saw him. <b class=gold>The entwined memory did.</b></p>"""),
  "Andrew Fastow was the architect of the Enron fraud, yet he is nearly invisible "
  "in the email. Cold Case never flagged him. But because five agents share one "
  "CockroachDB memory, a single SQL query assembles his complete case file: his "
  "contradictions, his timeline, and his withheld documents, from all of them at once."),

 ("img", r"B:\ediscovery-suite\docs\hero.png",
  "This is Nota dot Lawyer: five specialized e-discovery agents feeding one "
  "transactional memory, which produces a single unified case file. Not chat "
  "history, not a vector cache. And with memory off, every agent's result "
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
   <h2>Ethical walls &amp; <span class=blu>data sovereignty</span></h2>
   <div class=row style="margin-top:40px">
     <div class=stat><div class="n" style="font-size:60px;color:#3fb950">RLS</div>
       <div class=l style="text-transform:none;font-size:30px;margin-top:20px">Row-level security: a reviewer
       <b>physically cannot</b> read another matter or a privileged document &mdash; zero rows, not filtered in code.</div></div>
     <div class=stat><div class="n" style="font-size:60px;color:#58a6ff">EU&nbsp;&rarr;&nbsp;EU</div>
       <div class=l style="text-transform:none;font-size:30px;margin-top:20px">Multi-region <b>REGIONAL BY ROW</b>: London
       custodians pinned to europe-west1 for GDPR &mdash; surviving a full regional outage.</div></div>
   </div>"""),
  "The database enforces the guarantees legal work demands. Row-level security "
  "walls off privileged and cross-matter data: a reviewer physically cannot read "
  "it. And multi-region domiciling pins European custodian data to Europe for "
  "G-D-P-R, surviving a full regional cloud outage."),

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
        if kind == "html": render_html(content, img)
        else: img = content
        d = dur(wav) + 0.55
        clip = os.path.join(HERE, f"v2_clip{i}.mp4")
        subprocess.run(["ffmpeg", "-y", "-loop", "1", "-i", img, "-i", wav,
            "-c:v", "libx264", "-t", f"{d:.2f}", "-pix_fmt", "yuv420p",
            "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,"
                   "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=#0d1117,setsar=1",
            "-c:a", "aac", "-b:a", "160k", "-af", "apad=pad_dur=0.45", clip], check=True)
        clips.append(clip); print(f"scene {i}: {d:.1f}s ({kind})")
    listf = os.path.join(HERE, "v2_clips.txt")
    open(listf, "w").write("\n".join(f"file '{c}'" for c in clips))
    final = os.path.join(HERE, "nota_suite_demo_v2.mp4")
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", listf,
        "-c", "copy", final], check=True)
    print(f"\nDONE -> {final} ({os.path.getsize(final)//1024} KB, {dur(final):.0f}s)")

if __name__ == "__main__":
    main()
