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
    files = sorted(DATA_DIR.glob(f"{prefix}*.xlsx"), reverse=True)
    return files[0] if files else (DATA_DIR / f"{prefix}NOT_FOUND.xlsx")


FILES = {
    'PRIZE_SUM': _find_latest("PRIZE_SUM_OUT_"),
    'BRIDGE': _find_latest("PRIZE_6_BRIDGE_OUT_"),
    'MC': _find_latest("MC_LIST_OUT_"),
}

def get_data_date():
    """파일명: PRIZE_SUM_OUT_20260529.xlsx → 기준일 2026-05-28"""
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
    mgr_file = DATA_DIR / "2605_매니저.xlsx"
    if not mgr_file.exists():
        return {}
    try:
        df_m = pd.read_excel(mgr_file)
        out = {}
        for _, r in df_m.iterrows():
            raw = str(r.get('이름', '')).strip()
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
    - next_round_items: 추가 확보 가능 (실적 채우면 받음)
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

    # === 확정 시상금 항목 ===
    confirmed_items = []

    # 데이터 기준일에서 월 추출 (예: 6월 → "6월 정규 시상")
    data_date = get_data_date()
    cur_month = data_date.month
    prev_month = cur_month - 1 if cur_month > 1 else 12

    # 정규 인보험 시상금 (메리츠 단독 + 대리점 통합 정률) — 시상금계
    base_sang = int(gp('시상금계'))
    if base_sang > 0:
        confirmed_items.append((f'{cur_month}월 정규 시상', base_sang))

    if gb('브릿지시상금') > 0:
        confirmed_items.append((f'{prev_month}~{cur_month}월 브릿지 시상', int(gb('브릿지시상금'))))
    if gb('연속가동시상금') > 0:
        confirmed_items.append((f'{prev_month}~{cur_month}월 연속가동 시상', int(gb('연속가동시상금'))))

    # 대리점 prefix(유퍼스트 여부) 판별 → 유퍼간편 vs 종합자녀간편
    family_name = _g(ps, '영업가족명') or _g(br, '영업가족명') or ''
    is_yuper = '유퍼스트' in family_name
    yuper_label = '유퍼간편' if is_yuper else '종합자녀간편'

    for w in [1, 2, 3, 4]:
        base = int(gp(f'추가13회예정금_{w}주'))
        sang = int(gp(f'추가13회예정금_{w}주_상품'))
        yuper = int(gp(f'추가13회예정금_{w}주_유퍼간편'))
        if base > 0:
            confirmed_items.append((f'{w}주차 인보험 추가', base))
        if sang > 0:
            confirmed_items.append((f'{w}주차 상품 시책', sang))
        if yuper > 0:
            confirmed_items.append((f'{w}주차 {yuper_label}', yuper))

    choo1 = int(gp('추가13회예정금_1주_추가'))
    if choo1 > 0:
        confirmed_items.append(('1주차 추가 시책', choo1))

    # 5월 컬럼 (6월 이후 미존재시 0 반환)
    cont_extra = int(gp('추가13회예정금_주차연속가동'))
    if cont_extra > 0:
        confirmed_items.append(('주차 연속가동 시상', cont_extra))

    # 6월 신규 컬럼: 조기가동(6/1~3, 공통) + 프라임(6/4~7, 프라임에셋 전용)
    cho_g = int(gp('추가13회예정금_1주_조기가동'))
    if cho_g > 0:
        confirmed_items.append(('1주차 조기가동 시상', cho_g))

    prime = int(gp('추가13회예정금_1주_프라임'))
    if prime > 0:
        confirmed_items.append(('1주차 프라임 시상', prime))

    month_extra = int(gp('추가13회예정금_월누계'))
    if month_extra > 0:
        confirmed_items.append(('월누계 시책', month_extra))

    confirmed_total = sum(v for _, v in confirmed_items)

    sum13 = int(gp('추가13회예정금계'))
    sumbridge = int(gb('시상금합계'))
    expected_check = sum13 + sumbridge

    # === 다음 회차 잠재 시상금 (scheme_engine 통합) ===
    next_round_items = []
    try:
        from scheme_engine import find_scheme_for_agency, calculate_scheme_rewards
        family_name = _g(ps, '영업가족명') or _g(br, '영업가족명')
        if family_name:
            scheme = find_scheme_for_agency(family_name)
            if scheme:
                # 활성 주차: 카드 발송/생성 시점(오늘) 기준으로 결정.
                # 데이터가 전주말까지여도, 오늘이 2주차 화요일이면 2주차 시책으로 시뮬레이션해야 함
                # (지난 주차 시책으로 추가 실적 독려는 의미가 없으므로)
                from datetime import datetime
                today = datetime.now()
                cur_month = today.month
                day = today.day
                if day <= 7: active_week = 1
                elif day <= 14: active_week = 2
                elif day <= 21: active_week = 3
                else: active_week = 4

                # 시기 지난 누적 시책 제외 룰
                # - CONT_5_6 (연속가동 추가): 5월 4주(5/22~31) + 6월 1주(6/1~7)만 유효
                #   → 6월 2주차+에는 미적용 (데이터에서도 빠짐)
                # - BRIDGE_5_6 (연속가동): 5월 3~4주(5/15~31) + 6월 1~2주(6/1~14)만 유효
                #   → 6월 3주차+에는 미적용
                def is_expired(code: str) -> bool:
                    if cur_month > 6:
                        return code in ('CONT_5_6', 'BRIDGE_5_6')
                    if cur_month == 6:
                        if code == 'CONT_5_6' and day > 7:    # 6/8부터 제외
                            return True
                        if code == 'BRIDGE_5_6' and day > 14:  # 6/15부터 제외
                            return True
                    return False

                # 부족 실적 필터: 20만 → 50만으로 완화.
                # 누적 시책(연속가동 등)은 next_short가 30~40만 단위까지 가능
                NEXT_SHORT_MAX = 500000  # 50만

                results = calculate_scheme_rewards(scheme, data)
                for r in results:
                    if r['next_short'] <= 0 or r['delta_reward'] <= 0:
                        continue
                    if r['next_short'] > NEXT_SHORT_MAX:
                        continue
                    if r['week'] is not None and r['week'] != active_week:
                        continue
                    if is_expired(r['code']):
                        continue
                    next_round_items.append({
                        'label': r['label'],
                        'short': r['next_short'],
                        'target': r['next_tier_value'],
                        'current': r['current'],
                        'assumed_reward': r['delta_reward'],
                        'current_reward': r['current_reward'],      # 이미 확보 시상금
                        'next_reward': r['next_reward'],            # 다음 구간 도달시 총 시상금
                        'code': r['code'],
                    })
    except Exception as e:
        print(f"[WARN] scheme_engine 사용 실패: {e}")
        if gp('브릿지실적부족액_5_6월') > 0:
            next_round_items.append({
                'label': '5~6월 연속가동(브릿지)',
                'short': int(gp('브릿지실적부족액_5_6월')),
                'target': int(gp('브릿지실적목표_5_6월')),
                'current': int(gp('브릿지실적_5_6월')),
                'assumed_reward': int(gb('브릿지시상금')),
                'code': 'BRIDGE_5_6',
            })
        if gp('연속가동실적부족액_5_6월') > 0:
            next_round_items.append({
                'label': '5~6월 추가 연속가동',
                'short': int(gp('연속가동실적부족액_5_6월')),
                'target': int(gp('연속가동실적목표_5_6월')),
                'current': int(gp('연속가동실적_5_6월')),
                'assumed_reward': int(gb('연속가동시상금')),
                'code': 'CONT_5_6',
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
    matches = find_agent('�