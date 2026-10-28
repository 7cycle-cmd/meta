# temp: check why other endpoints 500
import subprocess
import time
import urllib.request
import urllib.error
import sys
import os

srv = subprocess.Popen(
    [sys.executable, "-m", "source.rest_api", "--port", "9512"],
    cwd=r"c:\projects\meta",
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
time.sleep(2.5)

def hit(path):
    url = f"http://127.0.0.1:9512{path}"
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")[:300]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")[:300]
    except Exception as e:
        return 0, str(e)

st, body = hit("/sources")
print("GET /sources ->", st)
print("body:", body[:500])

# capture server error output for the 500
time.sleep(1)
out = srv.stdout.read(2000).decode("utf-8", errors="replace") if srv.stdout else ""
print("\n--- server output tail ---")
print(out[-1500:])
srv.terminate()
