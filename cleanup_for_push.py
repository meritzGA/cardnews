"""GitHub Push 전 파일 정리.
- 옛 v 버전 파일 삭제
- 최신 v7 → 표준 이름(app.py, extract_agent_data.py)으로 통합
- app.py 안의 import 경로 자동 수정
"""
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# 삭제할 옛 버전 파일
OLD_FILES = [
    'app.py',  # 가장 옛 버전 (덮어쓸 거)
    'app_v2.py', 'app_v3.py', 'app_v4.py',
    'app_simple.py',
    'app_simple_v2.py', 'app_simple_v3.py', 'app_simple_v4.py',
    'app_simple_v5.py', 'app_simple_v6.py',
    'extract_agent_data_v3.py',
    'render_png_v2.py', 'render_png_v3.py',
    'requirements_v2.txt',
    'app_simple_v3_v2.py',  # 혹시 있을 수도
    '실행방법.md',
    'git_push_v2.md',
    'README_v2.md',
    'cleanup_for_push.bat',
]

deleted = []
for f in OLD_FILES:
    p = ROOT / f
    if p.exists():
        try:
            p.unlink()
            deleted.append(f)
        except Exception as e:
            print(f"[!] 삭제 실패 {f}: {e}")

print(f"[삭제] {len(deleted)}개 파일:")
for f in deleted:
    print(f"  - {f}")

# 임시 파일 정리
for pattern in ['~$*.xlsx', '_tmp_*', '_t_*', '_temp_*', '_batch_*', '_gen.log']:
    for p in ROOT.glob(pattern):
        try:
            if p.is_file(): p.unlink()
            elif p.is_dir(): shutil.rmtree(p)
        except: pass

# 최신 버전 → 표준 이름으로 복사
RENAMES = [
    ('app_simple_v7.py', 'app.py'),
    ('extract_agent_data_v4.py', 'extract_agent_data.py'),
]

for src, dst in RENAMES:
    src_path = ROOT / src
    dst_path = ROOT / dst
    if not src_path.exists():
        print(f"[!] {src} 없음 — 건너뜀")
        continue
    shutil.copy2(src_path, dst_path)
    print(f"[복사] {src} → {dst}")
    # 원본 옛 파일은 남겨둬도 됨 (걱정되면 삭제)

# app.py 내부의 import 경로 수정
app_path = ROOT / 'app.py'
if app_path.exists():
    content = app_path.read_text(encoding='utf-8')
    new_content = content.replace(
        'from extract_agent_data_v4 import',
        'from extract_agent_data import'
    )
    if new_content != content:
        app_path.write_text(new_content, encoding='utf-8')
        print("[수정] app.py 의 import 경로 → extract_agent_data")

# 옛 v 파일도 정리 (위에서 복사 끝났으니)
LAST_CLEAN = ['app_simple_v7.py', 'extract_agent_data_v4.py']
for f in LAST_CLEAN:
    p = ROOT / f
    if p.exists():
        try:
            p.unlink()
            print(f"[삭제] {f} (표준 이름으로 통합됨)")
        except Exception as e:
            print(f"[!] {f}: {e}")

print("\n=== 완료 ===")
print("이제 git 명령으로 push 가능:")
print("  git init")
print("  git branch -M main")
print("  git remote add origin https://github.com/meritzGA/cardnews.git")
print("  git add .")
print("  git commit -m \"feat: initial commit\"")
print("  git push -u origin main")
