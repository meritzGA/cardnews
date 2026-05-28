# GitHub Push 가이드

저장소: https://github.com/meritzGA/cardnews

## 처음 push (한 번만)

cmd 또는 PowerShell에서:

```bash
cd "D:\GA설계사시상안내\GA설계사 시상 안내 카드뉴스"

# 1) git 초기화
git init
git branch -M main

# 2) 원격 저장소 연결
git remote add origin https://github.com/meritzGA/cardnews.git

# 3) 무엇이 커밋될지 확인 (엑셀/cards 제외 확인)
git add .
git status

# 4) 첫 커밋
git commit -m "feat: 메리츠 GA 시상안내 카드뉴스 시스템 초기 버전"

# 5) push
git push -u origin main
```

## 원격에 README나 다른 파일 이미 있을 때

```bash
git pull origin main --rebase --allow-unrelated-histories
git push -u origin main
```

## 이후 변경사항 push

```bash
git add .
git commit -m "fix: 액션 배너 max 부족액 로직"
git push
```

## 자동 제외되는 파일 (.gitignore)

- `*.xlsx` — 시상 원본 데이터 (개인정보)
- `2605_매니저.xlsx` — 매니저 연락처
- `cards/`, `cards_v2/` — 생성된 카드 PNG
- `2605_4/` — 시책 이미지 (저작권)
- `_cache/`, `*.parquet` — 캐시
- `__pycache__/`, `*.pyc` — Python 캐시
- `KakaoTalk_*.png` — 스크린샷
- `~$*.xlsx` — 엑셀 임시 잠금 파일

## 다른 사람이 clone해서 사용할 때

```bash
git clone https://github.com/meritzGA/cardnews.git
cd cardnews
pip install -r requirements.txt
playwright install chromium

# 다음 4개 파일을 폴더 루트에 복사 (별도 받기)
# - PRIZE_SUM_OUT_{YYYYMMDD}.xlsx
# - PRIZE_6_BRIDGE_OUT_{YYYYMMDD}.xlsx
# - MC_LIST_OUT_{YYYYMMDD}.xlsx
# - 2605_매니저.xlsx

streamlit run app.py
```

## 파일 깔끔하게 정리 (push 전 권장)

`cleanup_for_push.bat` 더블 클릭하면:
- 옛 버전 (`app_simple_v2~v7.py`, `extract_agent_data_v3~v4.py` 등) 삭제
- 최신 버전을 표준 이름(`app.py`, `extract_agent_data.py`)으로 통합

실행 후 `app.py` 파일을 열어 다음 한 줄만 수정:
```python
from extract_agent_data_v4 import ...
↓
from extract_agent_data import ...
```
