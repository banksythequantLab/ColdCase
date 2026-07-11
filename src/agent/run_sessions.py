"""Run N investigation sessions back-to-back on the latest open case."""
import subprocess
import sys

n = int(sys.argv[1]) if len(sys.argv) > 1 else 3
for i in range(n):
    print(f"\n===== SESSION {i + 1}/{n} =====", flush=True)
    subprocess.run([sys.executable, "src/agent/investigator.py"],
                   check=False)
print("\nALL SESSIONS DONE", flush=True)
