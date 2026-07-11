"""Rigorous evaluation vs the 18 sealed POIs (ADMIN ONLY — reads judge schema).

Population = all people with a financial profile (the labeled universe).
Unscored people default to suspicion 0 (agent never flagged them).
Outputs PNG charts + a metrics JSON to docs/.
Usage: python src/eval_case.py
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import psycopg
from dotenv import load_dotenv
from sklearn.metrics import (precision_recall_curve, average_precision_score,
                             confusion_matrix)

load_dotenv()
OUT = os.path.join(os.path.dirname(__file__), "..", "docs")
c = psycopg.connect(os.environ["CRDB_ADMIN_URL"])

rows = c.execute("""
  SELECT coalesce(p.real_name, p.full_name),
         coalesce(s.suspicion_score, 0.0),
         coalesce(j.is_poi, false)
  FROM financial_profiles f
  JOIN persons p USING (person_id)
  LEFT JOIN suspects s ON s.person_id = f.person_id
  LEFT JOIN judge.poi_labels j ON j.person_id = f.person_id""").fetchall()
names = [r[0] for r in rows]
y_score = np.array([float(r[1]) for r in rows])
y_true = np.array([1 if r[2] else 0 for r in rows])
print(f"population={len(rows)} POIs={y_true.sum()}"
      f" scored={int((y_score>0).sum())}")


# --- metrics at operating threshold 0.5 ---
thr = 0.5
y_pred = (y_score >= thr).astype(int)
tp = int(((y_pred == 1) & (y_true == 1)).sum())
fp = int(((y_pred == 1) & (y_true == 0)).sum())
fn = int(((y_pred == 0) & (y_true == 1)).sum())
tn = int(((y_pred == 0) & (y_true == 0)).sum())
prec = tp / (tp + fp) if tp + fp else 0
rec = tp / (tp + fn) if tp + fn else 0
f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0
ap = average_precision_score(y_true, y_score) if y_true.sum() else 0
metrics = {"population": len(rows), "pois": int(y_true.sum()),
           "scored": int((y_score > 0).sum()), "threshold": thr,
           "precision": round(prec, 3), "recall": round(rec, 3),
           "f1": round(f1, 3), "average_precision": round(float(ap), 3),
           "tp": tp, "fp": fp, "fn": fn, "tn": tn}
json.dump(metrics, open(os.path.join(OUT, "eval_metrics.json"), "w"),
          indent=2)
print(metrics)

plt.rcParams.update({"figure.facecolor": "#0d1117",
                     "axes.facecolor": "#161b22", "text.color": "#e6edf3",
                     "axes.labelcolor": "#e6edf3", "xtick.color": "#8b949e",
                     "ytick.color": "#8b949e", "axes.edgecolor": "#30363d"})

# --- PR curve ---
p, r, _ = precision_recall_curve(y_true, y_score)
plt.figure(figsize=(6, 4.5))
plt.step(r, p, where="post", color="#f0b429", lw=2)
plt.fill_between(r, p, step="post", alpha=0.15, color="#f0b429")
plt.xlabel("Recall"); plt.ylabel("Precision")
plt.title(f"Precision-Recall vs 18 POIs (AP={ap:.2f})", color="#f0b429")
plt.ylim(0, 1.05); plt.tight_layout()
plt.savefig(os.path.join(OUT, "pr_curve.png"), dpi=130)
print("wrote docs/pr_curve.png")


# --- confusion matrix at 0.5 ---
cm = confusion_matrix(y_true, y_pred)
plt.figure(figsize=(4.5, 4))
plt.imshow(cm, cmap="cividis")
for (i, j), v in np.ndenumerate(cm):
    plt.text(j, i, str(v), ha="center", va="center",
             color="#f0b429", fontsize=16, fontweight="bold")
plt.xticks([0, 1], ["not flagged", "flagged"])
plt.yticks([0, 1], ["clean", "POI"])
plt.xlabel("agent"); plt.ylabel("truth")
plt.title(f"Confusion @0.5  (P={prec:.0%} R={rec:.0%})", color="#f0b429")
plt.tight_layout()
plt.savefig(os.path.join(OUT, "confusion.png"), dpi=130)
print("wrote docs/confusion.png")

# --- score calibration: for scored suspects, score vs POI ---
scored = [(names[i], y_score[i], y_true[i])
          for i in range(len(rows)) if y_score[i] > 0]
scored.sort(key=lambda x: -x[1])
plt.figure(figsize=(6, 4.5))
ys = [s[1] for s in scored]
cols = ["#22c55e" if s[2] else "#ef4444" for s in scored]
plt.barh(range(len(scored)), ys, color=cols)
plt.yticks(range(len(scored)), [s[0] for s in scored], fontsize=8)
plt.gca().invert_yaxis()
plt.xlabel("suspicion score")
plt.title("Suspect board  (green=real POI, red=not)", color="#f0b429")
plt.xlim(0, 1); plt.tight_layout()
plt.savefig(os.path.join(OUT, "board.png"), dpi=130)
print("wrote docs/board.png")
print("\nEVAL COMPLETE")
