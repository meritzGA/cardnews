"""
대리점별 시책 JSON을 로드하고 데이터의 부족금액/실적과 매칭해서
정확한 시상금을 계산.
"""
import json
import re
from pathlib import Path

SCHEME_DIR = Path(__file__).resolve().parent / "schemes"


def _normalize(s):
    """매칭용 정규화"""
    if not s:
        return ''
    s = re.sub(r'[\(\)\s\-_\.,/]', '', s)
    s = s.replace('(주)', '').replace('주식회사', '')
    return s.lower()


def load_all_schemes():
    """schemes 폴더의 모든 JSON 로드"""
    out = []
    for f in SCHEME_DIR.glob("*.json"):
        with open(f, 'r', encoding='utf-8') as fp:
            out.append(json.load(fp))
    return out


def find_scheme_for_agency(agency_family_name):
    """대리점/영업가족명으로 시책 JSON 매칭. 없으면 _default_meritz 사용."""
    schemes = load_all_schemes()
    norm_target = _normalize(agency_family_name)
    default_sc = None
    for sc in schemes:
        if sc.get('is_default'):
            default_sc = sc
            continue
        candidates = [sc.get('agency_full_name', '')] + sc.get('agency_alias', [])
        for cand in candidates:
            norm_cand = _normalize(cand)
            if norm_cand and (norm_cand in norm_target or norm_target in norm_cand):
                return sc
    return default_sc


def _find_tier(tiers, value):
    """value(현재 실적)에 해당하는 구간 찾기. tiers는 실적 오름차순."""
    # 가장 큰 도달 구간 찾기
    sorted_tiers = sorted(tiers, key=lambda t: t['실적'])
    matched = None
    for t in sorted_tiers:
        if value >= t['실적']:
            matched = t
        else:
            break
    return matched


def _next_tier(tiers, value):
    """value보다 큰 다음 구간 (목표 구간)"""
    sorted_tiers = sorted(tiers, key=lambda t: t['실적'])
    for t in sorted_tiers:
        if value < t['실적']:
            return t
    return None


def calculate_scheme_rewards(scheme, agent_data):
    """시책 + 설계사 데이터 → 항목별 정확한 시상금 계산.

    반환:
      [{
        'code': 'BRIDGE_5_6',
        'label': '5~6월 연속가동 시상',
        'period': '5/18 ~ 6/14',
        'current': 370290,
        'target_short': 129710,        # 다음 구간까지 부족
        'current_tier': {실적, 시상},  # 현재 도달한 구간 (없으면 None)
        'current_reward': 1000000,     # 현재 확정 시상금
        'next_tier': {실적, 시상},     # 다음 도달 가능한 구간
        'next_reward': 1800000,        # 다음 구간 시상금
        'delta_reward': 800000,        # 차액 (다음 - 현재)
      }, ...]
    """
    ps = agent_data.get('PRIZE_SUM') or {}
    results = []
    for item in scheme['schemes']:
        cur_col = item['map_to']['current']
        current = int(ps.get(cur_col) or 0)
        target_col = item['map_to'].get('target')
        short_col = item['map_to'].get('short')
        target = int(ps.get(target_col) or 0) if target_col else 0
        short = int(ps.get(short_col) or 0) if short_col else 0

        tiers = item['tiers']
        current_tier = _find_tier(tiers, current)
        next_tier = _next_tier(tiers, current)

        current_reward = current_tier['시상'] if current_tier else 0
        next_reward = next_tier['시상'] if next_tier else 0
        delta = next_reward - current_reward if next_tier else 0

        # 다음 구간까지 부족 (시책 구간 기준)
        next_short = (next_tier['실적'] - current) if next_tier else 0

        results.append({
            'code': item['code'],
            'label': item['label_card'],
            'period': item.get('period', ''),
            'current': current,
            'data_target': target,
            'data_short': short,
            'current_tier_value': current_tier['실적'] if current_tier else None,
            'current_reward': current_reward,
            'next_tier_value': next_tier['실적'] if next_tier else None,
            'next_reward': next_reward,
            'delta_reward': delta,
            'next_short': next_short,
            'all_tiers': tiers,
        })
    return results


if __name__ == '__main__':
    import sys
    sys.path.insert(0, '/sessions/charming-fervent-newton/mnt/outputs')
    from extract_agent_data import find_agent, get_agent_data

    matches = find_agent('이길범', '3-4')
    cid = matches[0]['본인고객ID']
    data = get_agent_data(cid)

    family = matches[0]['영업가족명']
    print(f"영업가족: {family}")
    scheme = find_scheme_for_agency(family)
    print(f"매칭된 시책: {scheme.get('agency_full_name') if scheme else 'None'}")

    if scheme:
        results = calculate_scheme_rewards(scheme, data)
        print("\n=== 계산 결과 ===")
        for r in results:
            print(f"\n[{r['code']}] {r['label']} ({r['period']})")
            print(f"  현재 실적: {r['current']:,}원")
            print(f"  현재 도달 구간: {r['current_tier_value']:,}원 → 시상 {r['current_reward']:,}원" if r['current_tier_value'] else "  현재 구간 미달성")
            if r['next_tier_value']:
                print(f"  다음 구간: {r['next_tier_value']:,}원 → 시상 {r['next_reward']:,}원")
                print(f"  → {r['next_short']:,}원 더하면 추가 시상 +{r['delta_reward']:,}원")
            else:
                print("  최고 구간 달성")
