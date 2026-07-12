"""Bar chart of the memory vs no-memory ablation."""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = os.path.join(os.path.dirname(__file__), "..", "docs")
d = json.load(open(os.path.join(OUT, "ablation.json")))
mem, nb = d["memory"], d["no_memory_best"]

plt.rcParams.update({"figure.facecolor": "#0d1117",
                     "axes.facecolor": "#161b22", "text.color": "#e6edf3",
                     "axes.labelcolor": "#e6edf3", "xtick.color": "#e6edf3",
                     "ytick.color": "#8b949e", "axes.edgecolor": "#30363d"})
fig, (a1, a2) = plt.subplots(1, 2, figsize=(9, 4))
labels = ["No memory", "CockroachDB\nmemory"]
for ax, key, title, ymax in [
        (a1, "precision@3", "Precision@3", 1.05),
        (a2, "pois_found", "Real POIs found (of 18)", 5)]:
    vals = [nb[key], mem[key]]
    bars = ax.bar(labels, vals, color=["#ef4444", "#3fb950"], width=.6)
    ax.set_title(title, color="#f0b429")
    ax.set_ylim(0, ymax)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v,
                (f"{v:.0%}" if key == "precision@3" else str(v)),
                ha="center", va="bottom", color="#e6edf3",
                fontsize=14, fontweight="bold")
fig.suptitle("Ablation: persistent memory is what makes it work",
             color="#f0b429", fontsize=14, fontweight="bold")
plt.tight_layout()
plt.savefig(os.path.join(OUT, "ablation.png"), dpi=130)
print("wrote docs/ablation.png")
