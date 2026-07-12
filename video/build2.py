"""Rebuild the demo video with readable full-frame slides + cached narration."""
import os
import subprocess
from slides import SLIDES

HERE = os.path.dirname(os.path.abspath(__file__))
CHROME = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"


def render_slide(i, html):
    path = os.path.join(HERE, f"slide{i}.html")
    open(path, "w", encoding="utf-8").write(html)
    png = os.path.join(HERE, f"slide{i}.png")
    subprocess.run([CHROME, "--headless=new", "--disable-gpu",
                    "--hide-scrollbars", "--default-background-color=00000000",
                    "--force-device-scale-factor=1", "--window-size=1920,1080",
                    "--virtual-time-budget=3000", f"--screenshot={png}",
                    "file:///" + path.replace("\\", "/")], timeout=60)
    return png


def dur(f):
    o = subprocess.run(["ffprobe", "-v", "quiet", "-of", "csv=p=0",
                        "-show_entries", "format=duration", f],
                       capture_output=True, text=True)
    return float(o.stdout.strip() or 3.0)


clips = []
for i, html in enumerate(SLIDES):
    png = render_slide(i, html)
    wav = os.path.join(HERE, f"seg{i}.wav")   # cached from make_video.py
    d = dur(wav) + 0.7
    clip = os.path.join(HERE, f"c{i}.mp4")
    subprocess.run(["ffmpeg", "-y", "-loop", "1", "-i", png, "-i", wav,
                    "-c:v", "libx264", "-t", f"{d:.2f}", "-r", "30",
                    "-pix_fmt", "yuv420p", "-vf", "scale=1920:1080,setsar=1",
                    "-c:a", "aac", "-b:a", "192k", "-af", "apad=pad_dur=0.6",
                    clip], check=True)
    clips.append(clip)
    print(f"slide {i}: {d:.1f}s")

listf = os.path.join(HERE, "clips2.txt")
open(listf, "w").write("\n".join(f"file '{c}'" for c in clips))
final = os.path.join(HERE, "cold_case_demo.mp4")
subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", listf,
                "-c", "copy", final], check=True)
print(f"\nDONE -> {final} ({os.path.getsize(final)//1024} KB, {dur(final):.0f}s)")
