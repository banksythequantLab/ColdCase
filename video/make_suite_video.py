"""Suite demo video (<3min): the entwined CockroachDB E-Discovery Suite.
Reuses the readable 1920x1080 slide style + VoxCPM2 voice clone (johnson:8300)
+ ffmpeg assembly. Scenes mix purpose-built slides and existing suite visuals.
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
h1{font-size:132px;font-weight:900;line-height:.96;letter-spacing:-.04em}
h2{font-size:66px;font-weight:800;line-height:1.08}
p{font-size:44px;font-weight:400;color:#c9d1d9;line-height:1.4;margin-top:32px;max-width:1560px}
.gold{color:#f0b429}.grn{color:#3fb950}.blu{color:#58a6ff}.red{color:#f85149}.pur{color:#bc8cff}
.board div{display:flex;align-items:center;gap:30px;font-size:46px;font-weight:700;margin:18px 0}
.board .ag{width:340px;font-weight:800}
.mono{font-family:'JetBrains Mono',monospace}
</style>"""

def wrap(inner):
    return f"<!doctype html><html><head><meta charset=utf-8>{CSS}</head><body>{inner}</body></html>"

# (kind, content, narration)  kind: 'html' slide or 'img' existing PNG
SCENES = [
 ("html", wrap("""<div class=kick>CockroachDB &times; AWS &middot; Agentic Memory</div>
   <h1>Nota.Lawyer</h1>
   <p style="font-size:50px;font-style:italic;color:#f0b429;font-weight:600;margin-top:26px">
   &ldquo;Metadata is not documentation. It is evidence.&rdquo;</p>
   <p>A CockroachDB e-discovery suite: <span class=gold>five legal agents,
   one entwined memory.</span></p>"""),
  "Metadata is not documentation. It is evidence. This is Nota dot Lawyer: a "
  "CockroachDB e-discovery suite. Five specialized legal agents that share one "
  "memory, and every one of them proves that persistent memory changes the outcome."),

 ("img", r"B:\Chronicle\docs\suite_ablations.png",
  "Five agents, five experiments, each run with memory on and off. Cold Case "
  "names four of the real convicted insiders; with memory off, zero. Chronicle's "
  "theory converges on the truth instead of oscillating to the wrong answer. "
  "Witness keeps a twelve of twelve impeachment file. Gap Hunter isolates every "
  "withheld document. And Hold Firewall destroys zero evidence under load, where "
  "naive isolation loses over a hundred."),

 ("img", r"B:\ediscovery-suite\docs\architecture.png",
  "They are not five separate demos. They live in one CockroachDB database: the "
  "same corpus, the same people, the same case memory. So a single SQL statement "
  "can assemble any person's complete file across all five agents at once."),
]

SCENES += [
 ("html", wrap("""<div class=kick>One SQL statement &middot; five agents &middot; one database</div>
   <h2>Cold Case missed Fastow. <span class=grn>The suite didn't.</span></h2>
   <div class=board style="margin-top:46px">
     <div><span class="ag red">Cold Case</span><span style="color:#8b949e">&mdash; nothing</span></div>
     <div><span class="ag grn">Witness</span>2 sworn contradictions</div>
     <div><span class="ag gold">Chronicle</span>LJM2 self-dealing timeline</div>
     <div><span class="ag blu">Gap Hunter</span>3 withheld documents</div>
     <div><span class="ag pur">Hold Firewall</span>hold on 200 docs, ACID</div>
   </div>
   <p style="font-size:42px">No single tool saw him. <b class=gold>The entwined memory did.</b></p>"""),
  "Here is why that matters. Andrew Fastow, the architect of the fraud, is almost "
  "invisible in the email, so Cold Case never flagged him. But the same query "
  "still pulls his contradictions, his timeline, and his withheld documents from "
  "the other agents. No single tool saw him. The entwined memory did."),

 ("html", wrap("""<div class=kick>Why CockroachDB, not a vector store</div>
   <h2>The memory <span class=blu>is</span> the product</h2>
   <p>Vectors alone can't do this. Contradictions, gaps, timelines, and legal
   holds need <span class=gold>transactional state</span>, real
   <span class=gold>relationships</span>, and strict
   <span class=gold>SERIALIZABLE</span> consistency.</p>
   <p style="font-size:40px;margin-top:40px">Five agents writing one memory at
   once &mdash; and never losing a truth.</p>"""),
  "This is the case for CockroachDB over a bolt-on vector store. Vectors alone "
  "can't do this. Contradictions, gaps, timelines, and legal holds need "
  "transactional state, real relationships, and strict serializable consistency. "
  "Five agents writing one memory at once, and never losing a truth."),

 ("html", wrap("""<div class=kick>github.com/banksythequantLab/ediscovery-suite</div>
   <h2>One memory backbone. <span class=grn>Five legal agents.</span> Entwined.</h2>
   <p style="font-size:52px;margin-top:48px"><b class=gold>CockroachDB turns a
   database into an e-discovery tool</b> &mdash; doing in hours what would take
   <span class=grn>thousands of attorney-hours</span> of first-pass review.</p>"""),
  "One memory backbone. Five legal agents. Entwined. In hours, the suite does "
  "what would take thousands of attorney hours of first pass review. CockroachDB "
  "turns a database into an e-discovery tool."),
]


def clone(text, out_wav):
    if os.path.exists(out_wav) and os.path.getsize(out_wav) > 4000:
        print("  (cached)", os.path.basename(out_wav)); return
    with open(REF, "rb") as f:
        r = requests.post(CLONE_URL,
            files={"prompt_audio": ("ref.wav", f, "audio/wav")},
            data={"text": text, "lang": "en"}, timeout=900)
    assert r.status_code == 200 and len(r.content) > 4000, r.text[:300]
    open(out_wav, "wb").write(r.content)
    print(f"  cloned {os.path.basename(out_wav)} ({len(r.content)//1024} KB)")

def render_html(html, png):
    hp = png.replace(".png", ".html")
    open(hp, "w", encoding="utf-8").write(html)
    subprocess.run([CHROME, "--headless=new", "--disable-gpu",
        "--hide-scrollbars", "--window-size=1920,1080", "--force-device-scale-factor=1",
        f"--screenshot={png}", "file:///" + hp.replace("\\", "/")], timeout=60)

def dur(wav):
    out = subprocess.run(["ffprobe", "-v", "quiet", "-of", "csv=p=0",
        "-show_entries", "format=duration", wav], capture_output=True, text=True)
    return float(out.stdout.strip() or 3.0)

def main():
    clips = []
    for i, (kind, content, text) in enumerate(SCENES):
        wav = os.path.join(HERE, f"s_seg{i}.wav")
        clone(text, wav)
        img = os.path.join(HERE, f"s_img{i}.png")
        if kind == "html":
            render_html(content, img)
        else:
            img = content
        d = dur(wav) + 0.6
        clip = os.path.join(HERE, f"s_clip{i}.mp4")
        subprocess.run(["ffmpeg", "-y", "-loop", "1", "-i", img, "-i", wav,
            "-c:v", "libx264", "-t", f"{d:.2f}", "-pix_fmt", "yuv420p",
            "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,"
                   "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=#0d1117,setsar=1",
            "-c:a", "aac", "-b:a", "160k", "-af", "apad=pad_dur=0.5", clip],
            check=True)
        clips.append(clip); print(f"scene {i}: {d:.1f}s ({kind})")
    listf = os.path.join(HERE, "s_clips.txt")
    open(listf, "w").write("\n".join(f"file '{c}'" for c in clips))
    final = os.path.join(HERE, "nota_suite_demo.mp4")
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", listf, "-c", "copy", final], check=True)
    print(f"\nDONE -> {final} ({os.path.getsize(final)//1024} KB, {dur(final):.0f}s)")

if __name__ == "__main__":
    main()
