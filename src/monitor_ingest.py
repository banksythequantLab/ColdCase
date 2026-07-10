import os
import time

import psycopg
from dotenv import load_dotenv

load_dotenv()
c = psycopg.connect(os.environ["CRDB_ADMIN_URL"])
a = c.execute("SELECT count(*) FROM emails").fetchone()[0]
t = time.time()
for i in range(6):
    time.sleep(30)
    b = c.execute("SELECT count(*) FROM emails").fetchone()[0]
    print(f"{time.time()-t:.0f}s emails={b} rate={(b-a)/30:.0f}/s", flush=True)
    a = b
