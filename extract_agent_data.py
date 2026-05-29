"""설계사 시상 데이터 통합 추출 (pandas 기반)"""
import pandas as pd
import re
from pathlib import Path

# 데이터 경로: 환경변수 또는 스크립트 폴더 기준 자동 감지
import os as _os
_env = _os.environ.get('CARD_DATA_DIR')
if _env:
    DATA_DIR = Path(_env)
else:
    DATA_DIR = Path(__file__).resolve().parent
CACHE_DIR = DATA_DIR / "_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

def _find_latest(prefix):
    """날짜 suffix 가진 엑셀 중 가장 최신 파일"""
    files = sorted(DATA_DIR.glob(f"{prefix}*.xlsx"), reverse=True)
    return files[0] if files else (DATA_DIR / f"{prefix}NOT_FOUND.xlsx")


FILES = {
    'PRIZE_SUM': _find_latest("PRIZE_SUM_OUT_"),
    'BRIDGE': _find_latest("PRIZE_6_BRIDGE_OUT_"),
    'MC': _find_latest("MC_LIST_OUT_"),
}

def get_data_date():
    """데이터 파일의 기준일 (파일명의 YYYYMMDD - 1일).
    파일명: PRIZE_SUM_OUT_20260529.xlsx → 기준일 2026-05-28
    """
    from datetime import datetime, timedelta
    fname = FILES['PRIZE_SUM'].name
    m = re.search(r'(\d{8})\.xlsx', fname)
    if not m:
        return datetime.now() - timedelta(days=1)
    file_date = datetime.strptime(m.group(1), '%Y%m%d')
    return file_date - timedelta(days=1)



def _dec(s):
    if not isinstance(s, str):
        return s
    return re.sub(r'_x([0-9A-Fa-f]{4})_', lambda m: chr(int(m.group(1), 16)), s)


def _load(name):
    parquet_path = CACHE_DIR / f"{name}.parquet"
    excel_path = FILES[name]
    # 캐시가 엑셀보다 오래되면 무효화 (새 데이터 자동 반영)
    if parquet_path.exists() and excel_path.exists():
        if parquet_path.stat().st_mtime < excel_path.stat().st_mtime:
            try: parquet_path.unlink()
            except: pass
        else:
            return pd.read_parquet(parquet_path)
    elif parquet_path.exists():
        return pd.read_parquet(parquet_path)
    df = pd.read_excel(excel_path)
    df.columns = [_dec(c) for c in df.columns]
    for c in df.select_dtypes(include='object').columns:
        df[c] = df[c].map(lambda x: _dec(x) if isinstance(x, str) else x)
    df.to_parquet(parquet_path)
    return df


def find_agent(name, branch_keyword=None):
    df = _load('PRIZE_SUM')
    m = df[df['대리점설계사명'] == name]
    if branch_keyword:
        m = m[m['지점조직명'].str.contains(branch_keyword, na=False)]
    if len(m) == 0:
        return []
    cols = ['본인고객ID', '본인고객번호', '대리점설계사명', '지점조직명', '대리점지사명', '영업가족명']
    return m[cols].to_dict('records')


def get_agent_data(customer_id):
    out = {}
    for name in ['PRIZE_SUM', 'BRIDGE', 'MC']:
        df = _load(name)
        m = df[df['본인고객ID'] == customer_id]
        out[name] = m.iloc[0].to_dict() if len(m) > 0 else None
    return out


def _g(d, key):
    if d is None:
        return None
    v = d.get(key)
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    return v




def load_manager_contacts():
    """매니저명 → 연락처 매핑 로드. 파일 없으면 빈 dict 반환."""
    mgr_file = DATA_DIR / "2605_매니저.xlsx"
    if not mgr_file.exists():
        return {}
    try:
        df_m = pd.read_excel(mgr_file)
        out = {}
        for _, r in df_m.iterrows():
            raw = str(r.get('이름', '')).strip()
            # "GA3본부 심희숙 매니저님" → "심희숙"
            parts = raw.split()
            name = None
            for i, p in enumerate(parts):
                if '매니저' in p and i > 0:
                    name = parts[i-1]
                    break
            if not name:
                name = parts[-1] if parts else raw
            phone = str(r.get('연락처', '')).strip()
            branch = str(r.get('지점', '')).strip()
            if name and phone:
                out[name] = {'phone': phone, 'branch': branch}
        return out
    except Exception as e:
        print(f"[WARN] 매니저 연락처 로드 실패: {e}")
        return {}


def build_card_context(data):
    """카드뉴스 표시용 컨텍스트.
    - confirmed_items: 이미 확보한 시상금 항목별 (원 단위)
    - next_round_items: 5-6월 추가 확보 가능 (실적 채우면 받음)
    """
    ps = data.get('PRIZE_SUM')
    br = data.get('BRIDGE')
    mc = data.get('MC')

    def gp(k):
        v = _g(ps, k)
        return v if v else 0

    def gb(k):
        v = _g(br, k)
        return v if v else 0

    def gm(k):
        v = _g(mc, k)
        return v if v else 0

    # === 확정 시상금 항목 (이미 확보) ===
    confirmed_items = []

    # 4-5월 BRIDGE
    if gb('브릿지시상금') > 0:
        confirmed_items.append(('4~5월 브릿지 시상', int(gb('브릿지시상금'))))
    if gb('연속가동시상금') > 0:
        confirmed_items.append(('4~5월 연속가동 시상', int(gb('연속가동시상금'))))

    # 13회 예정 - 주차별
    for w in [1, 2, 3, 4]:
        base = int(gp(f'추가13회예정금_{w}주'))
        choo = int(gp(f'추가13회예정금_{w}주_추가'))  # 1주차에만 있음
        sang = int(gp(f'추가13회예정금_{w}주_상품'))
        yuper = int(gp(f'추가13회예정금_{w}주_유퍼간편'))
        if base > 0:
            confirmed_items.append((f'{w}주차 기본 시상', base))
        if choo > 0:
            confirmed_items.append((f'{w}주차 추가 시책', choo))
        if sang > 0:
            confirmed_items.append((f'{w}주차 상품 시책', sang))
        if yuper > 0:
            confirmed_items.append((f'{w}주차 유퍼간편 시책', yuper))

    cont_extra = int(gp('추가13회예정금_주차연속가동'))
    if cont_extra > 0:
        confirmed_items.append(('주차 연속가동 시상', cont_extra))

    month_extra = int(gp('추가13회예정금_월누계'))
    if month_extra > 0:
        confirmed_items.append(('월누계 시책', month_extra))

    confirmed_total = sum(v for _, v in confirmed_items)

    # 검증
    sum13 = int(gp('추가13회예정금계'))
    sumbridge = int(gb('시상금합계'))
    expected_check = sum13 + sumbridge

    # === 다음 회차 (5-6월) 잠재 시상금 ===
    next_round_items = []
    if gp('브릿지실적부족액_5_6월') > 0:
        # 가정: 5-6월 잠재 시상금 = 4-5월 브릿지시상금 (동일 정책 가정)
        next_round_items.append({
            'label': '5~6월 브릿지',
            'short': int(gp('브릿지실적부족액_5_6월')),
            'target': int(gp('브릿지실적목표_5_6월')),
            'current': int(gp('브릿지실적_5_6월')),
            'assumed_reward': int(gb('브릿지시상금')),
        })
    if gp('연속가동실적부족액_5_6월') > 0:
        next_round_items.append({
            'label': '5~6월 연속가동',
            'short': int(gp('연속가동실적부족액_5_6월')),
            'target': int(gp('연속가동실적목표_5_6월')),
            'current': int(gp('연속가동실적_5_6월')),
            'assumed_reward': int(gb('연속가동시상금')),
        })

    next_round_total = sum(i['assumed_reward'] for i in next_round_items)

    return {
        'name': _g(ps, '대리점설계사명') or _g(br, '대리점설계사명'),
        'branch': _g(ps, '지점조직명') or _g(br, '지점조직명'),
        'agency': _g(ps, '대리점지사명') or _g(br, '대리점지사명'),
        'family': _g(ps, '영업가족명') or _g(br, '영업가족명'),
        'manager': _g(ps, '지원매니저명') or _g(br, '지원매니저명') or _g(mc, '매니저명'),
        'continuous_months': int(gm('현재월연속가동')) if gm('현재월연속가동') else None,

        'confirmed_items': confirmed_items,
        'confirmed_total': confirmed_total,

        'next_round_items': next_round_items,
        'next_round_total': next_round_total,

        '_check': {
            '추가13회예정금계': sum13,
            'BRIDGE_시상금합계': sumbridge,
            '컬럼합계(예상)': expected_check,
            '본인_확정합산': confirmed_total,
            '검증_차이': confirmed_total - expected_check,
        }
    }


if __name__ == '__main__':
    import json
    matches = find_agent('이길범', '3-4')
    cid = matches[0]['본인고객ID']
    data = get_agent_data(cid)
    ctx = build_card_context(data)
    print(json.dumps(ctx, ensure_ascii=False, indent=2, default=str))
