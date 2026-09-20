"""Kill old server, clear cache, re-apply migrations, restart."""
import subprocess
import time
import urllib.request
import os
import sys
import shutil

BACKEND = r"C:\Users\USER\OneDrive\Desktop\hire\backend"

# 1. Kill old server processes
print("[1/4] Killing old uvicorn/python processes...")
subprocess.run(["taskkill", "/F", "/IM", "python.exe"], capture_output=True)
time.sleep(2)

# 2. Clear all __pycache__ dirs
print("[2/4] Clearing __pycache__...")
for root, dirs, files in os.walk(BACKEND):
    for d in dirs:
        if d == "__pycache__":
            p = os.path.join(root, d)
            shutil.rmtree(p, ignore_errors=True)
            print(f"  Removed {p}")

# 3. Apply migrations
print("[3/4] Applying alembic migrations...")
result = subprocess.run(
    [sys.executable, "-m", "alembic", "upgrade", "head"],
    cwd=BACKEND,
    capture_output=True,
    text=True,
    timeout=30,
)
print(result.stdout[-500:] if result.stdout else "  (no output)")
if result.returncode != 0:
    print(f"  STDERR: {result.stderr[-500:]}")

# 4. Start server
print("[4/4] Starting server on port 8000...")
proc = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
    cwd=BACKEND,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
)

# Wait for it
for i in range(15):
    time.sleep(1)
    try:
        urllib.request.urlopen("http://127.0.0.1:8000/docs", timeout=2)
        break
    except Exception:
        pass
else:
    print("WARNING: Server may not be ready yet")

print("\nServer started. Try the admin analytics page now.")
print("(Server is running in the background - close this window to stop it)")
proc.wait()
