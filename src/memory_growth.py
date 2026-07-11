"""Memory-growth chart from the real timestamped S3 case snapshots.

Shows the suspect board evolving as persisted memory accumulates:
 (a) real POIs on the board + flagged count over snapshots
 (b) score trajectory of key suspects (memory replay)
ADMIN ONLY (reads judge labels for coloring). Writes docs/memory_growth.png.
"""
import json
import os

import boto3
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import psycopg
from dotenv import load_dotenv

load_dotenv()
OUT = os.path.join(os.path.dirname(__file__), "..", "docs")
c = psycopg.connect(os.environ["CRDB_ADMIN_URL"])
_r = c.execute(
    "SELECT p.person_id, coalesce(p.real_name,p.full_name),"
    " coalesce(j.is_poi,false) FROM persons p"
    " LEFT JOIN judge.poi_labels j USING (person_id)"
    " WHERE p.person_id IN (SELECT person_id FROM suspects)").fetchall()
idmap = {str(r[0]): (r[1], bool(r[2])) for r in _r}

s3 = boto3.client("s3", region_name=os.environ["AWS_REGION"],
                  aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
                  aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"])
keys = sorted(o["Key"] for o in s3.list_objects_v2(
    Bucket=os.environ["S3_BUCKET"], Prefix="backups/").get("Contents", []))

snaps = []
for k in keys:
    d = json.loads(s3.get_object(Bucket=os.environ["S3_BUCKET"],
                                 Key=k)["Body"].read())
    board = sorted(d.get("suspects", []),
                   key=lambda x: -float(x["suspicion_score"]))
    snaps.append(board)
print(f"loaded {len(snaps)} snapshots")


pois_on_board, flagged_ct = [], []
for board in snaps:
    flagged = [s for s in board if float(s["suspicion_score"]) >= 0.5]
    pois = sum(1 for s in flagged
               if idmap.get(str(s["person_id"]), ("", False))[1])
    pois_on_board.append(pois)
    flagged_ct.append(len(flagged))

# track key suspects' score over snapshots
track = ["SKILLING JEFFREY K", "LAY KENNETH L", "HIRKO JOSEPH",
         "KOPPER MICHAEL J", "KAMINSKI WINCENTY J"]
name2id = {v[0]: k for k, v in idmap.items()}
traj = {n: [] for n in track}
for board in snaps:
    bs = {str(s["person_id"]): float(s["suspicion_score"]) for s in board}
    for n in track:
        traj[n].append(bs.get(name2id.get(n, ""), None))

plt.rcParams.update({"figure.facecolor": "#0d1117",
                     "axes.facecolor": "#161b22", "text.color": "#e6edf3",
                     "axes.labelcolor": "#e6edf3", "xtick.color": "#8b949e",
                     "ytick.color": "#8b949e", "axes.edgecolor": "#30363d",
                     "legend.facecolor": "#161b22"})
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.3))
x = range(1, len(snaps) + 1)
ax1.plot(x, flagged_ct, "-o", color="#8b949e", label="flagged suspects")
ax1.plot(x, pois_on_board, "-o", color="#3fb950", label="real POIs on board")
ax1.set_xlabel("memory snapshot"); ax1.set_ylabel("count")
ax1.set_title("Board grows as memory accumulates", color="#f0b429")
ax1.legend(); ax1.set_ylim(0, max(flagged_ct) + 1)

for n in track:
    ys = traj[n]
    poi = idmap.get(name2id.get(n, ""), ("", False))[1]
    ax2.plot(x, ys, "-o", lw=2 if poi else 1,
             label=n.split()[0] + (" ✓" if poi else ""))
ax2.set_xlabel("memory snapshot"); ax2.set_ylabel("suspicion score")
ax2.set_title("Suspect scores over time (memory replay)", color="#f0b429")
ax2.set_ylim(0, 1.05); ax2.legend(fontsize=8)
plt.tight_layout()
plt.savefig(os.path.join(OUT, "memory_growth.png"), dpi=130)
print("wrote docs/memory_growth.png")
print("POIs on board across snapshots:", pois_on_board)
