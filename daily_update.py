"""매일 데이터 파일 업데이트 후 GitHub push.
사용:
  python daily_update.py
"""
import subprocess, sys
from datetime import datetime

def run(cmd):
    print(f"$ {cmd}")
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if r.stdout: print(r.stdout)
    if r.returncode != 0:
        print(f"ERROR: {r.stderr}")
        sys.exit(1)

today = datetime.now().strftime('%Y-%m-%d')
print(f"=== 데이터 업데이트 push: {today} ===\n")

# 새 데이터 파일이 폴더에 있다고 가정
# 1) parquet 캐시 삭제 (새 데이터 반영)
import shutil, os
cache = '_cache'
if os.path.exists(cache):
    shutil.rmtree(cache)
    print(f"[ok] {cache}/ 삭제 (새 데이터 반영용)")

# 2) git add / commit / push
run("git add *.xlsx schemes/")
run(f"git commit -m \"data: {today} 업데이트\" --allow-empty")
run("git push")

print("\n=== 완료 — Streamlit Cloud가 자동 재배포합니다 ===")
