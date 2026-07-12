"""Build the Cold Case demo video: clone Derek's voice for each narration
segment (VoxCPM2 on johnson:8300), then assemble a timed slideshow with
ffmpeg. Each scene = one visual + its narration.
"""
import os
import subprocess
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(HERE, "..", "docs")
REF = r"B:\freeclone-backend\derek-voice.wav"
CLONE_URL = "http://johnson:8300/api/clone"

# (visual, narration) — visuals are real files in docs/
SCENES = [
    ("flow.svg",
     "The Enron email corpus exists because of a real fraud investigation. "
     "Over half a million messages from the executives who were prosecuted. "
     "We gave an A.I. agent all of it, hid the list of who was convicted, and "
     "asked it to solve the case from scratch."),
    ("flow.svg",
     "The agent's memory is CockroachDB. Every email is embedded into a "
     "distributed vector index, alongside a communication graph and a "
     "transactional record of every hypothesis, finding, and piece of "
     "evidence. The database does not store the documents. It stores the "
     "investigation itself."),
    ("shot_dashboard.png",
     "Investigating blind, the agent's top suspects were Skilling, Lay, "
     "Hirko, and Kopper. All four are real Enron convictions. It found them "
     "using nothing but raw email, with one hundred percent precision on its "
     "top three."),
    ("ablation.png",
     "Here is the proof that memory is what matters. We ran the exact same "
     "agent twice. Without persistent memory, it found zero of eighteen. "
     "With CockroachDB memory, four of eighteen, at a hundred percent "
     "precision. Same model. Different memory. Different outcome."),
    ("shot_replay.png",
     "Because the memory persists, you can kill the agent mid-investigation "
     "and restart it. It resumes from exactly where it left off, without "
     "reprocessing a single document, because the memory was never in the "
     "process. It was always in CockroachDB."),
    ("shot_graph.png",
     "It surfaced Michael Kopper, Fastow's lieutenant, through the "
     "communication graph alone. And it worked through five hundred thousand "
     "documents in under nine hours of compute. The equivalent of thousands "
     "of attorney hours of first-pass review. CockroachDB turns a database "
     "into an e-discovery tool."),
]


def clone(text, out_wav):
    if os.path.exists(out_wav) and os.path.getsize(out_wav) > 4000:
        print("  (cached)", out_wav)
        return
    with open(REF, "rb") as f:
        r = requests.post(CLONE_URL,
                          files={"prompt_audio": ("ref.wav", f, "audio/wav")},
                          data={"text": text, "lang": "en"}, timeout=900)
    assert r.status_code == 200 and len(r.content) > 4000, r.text[:300]
    open(out_wav, "wb").write(r.content)
    print(f"  cloned {out_wav} ({len(r.content)//1024} KB)")


def svg_to_png(svg, png):
    chrome = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    html = os.path.join(HERE, "_wrap.html")
    open(html, "w").write(
        f'<html><body style="margin:0;background:#0d1117">'
        f'<img src="file:///{os.path.abspath(svg)}" width="1080"></body></html>')
    subprocess.run([chrome, "--headless=new", "--disable-gpu",
                    "--force-device-scale-factor=2",
                    "--window-size=1080,1400", f"--screenshot={png}",
                    "file:///" + html.replace("\\", "/")], timeout=60)


def dur(wav):
    out = subprocess.run(["ffprobe", "-v", "quiet", "-of", "csv=p=0",
                          "-show_entries", "format=duration", wav],
                         capture_output=True, text=True)
    return float(out.stdout.strip() or 3.0)


def main():
    clips = []
    for i, (vis, text) in enumerate(SCENES):
        wav = os.path.join(HERE, f"seg{i}.wav")
        clone(text, wav)
        src = os.path.join(DOCS, vis)
        img = os.path.join(HERE, f"img{i}.png")
        if vis.endswith(".svg"):
            svg_to_png(src, img)
        else:
            img = src
        d = dur(wav) + 0.6
        clip = os.path.join(HERE, f"clip{i}.mp4")
        subprocess.run([
            "ffmpeg", "-y", "-loop", "1", "-i", img, "-i", wav,
            "-c:v", "libx264", "-t", f"{d:.2f}", "-pix_fmt", "yuv420p",
            "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,"
                   "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=#0d1117,"
                   "setsar=1", "-c:a", "aac", "-b:a", "160k",
            "-af", "apad=pad_dur=0.5", clip], check=True)
        clips.append(clip)
        print(f"scene {i}: {d:.1f}s")
    listf = os.path.join(HERE, "clips.txt")
    open(listf, "w").write("\n".join(f"file '{c}'" for c in clips))
    final = os.path.join(HERE, "cold_case_demo.mp4")
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0",
                    "-i", listf, "-c", "copy", final], check=True)
    print("\nDONE ->", final, f"({os.path.getsize(final)//1024} KB,"
          f" {dur(final):.0f}s)")


if __name__ == "__main__":
    main()
