"""메리츠화재 카드뉴스 v16 — 토스 스타일 (콘텐츠 압축)"""
import sys
sys.path.insert(0, '/sessions/charming-fervent-newton/mnt/outputs')
from extract_agent_data import find_agent, get_agent_data, build_card_context
from scheme_engine import find_scheme_for_agency, calculate_scheme_rewards
from datetime import datetime
import random
import re


QUOTES = [
    ("기회는 준비된 자에게 와요.", "파스퇴르"),
    ("꾸준함이 가장 큰 무기예요.", "워렌 버핏"),
    ("한 걸음이 가장 멀리 가는 길.", "노자"),
    ("작은 노력이 성공을 만들어요.", "로버트 콜리어"),
    ("준비된 사람에게 행운이 와요.", "세네카"),
]


CARD_CSS = """
@page { size: 1080px 3000px; margin: 0; }
* { margin:0; padding:0; box-sizing:border-box; }
html, body {
  font-family: 'NanumSquare', 'NanumGothic', 'Malgun Gothic', '맑은 고딕', 'Apple SD Gothic Neo', sans-serif;
  background: #f2f4f6;
  color: #191f28;
  width: 1080px;
  margin: 0;
}
.wrap { width: 1080px; padding: 24px 24px; background: #f2f4f6; }

/* 브랜드 바 */
.brand-bar {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 16px;
  padding: 0 6px;
}
.brand-bar .brand { font-size: 38px; font-weight: 900; color: #d6162e; letter-spacing: -0.5px; }
.brand-bar .date { font-size: 38px; color: #8b95a1; font-weight: 700; }

/* 그리팅 카드 */
.greeting {
  background: #ffffff;
  border-radius: 22px;
  padding: 26px 32px;
  margin-bottom: 12px;
}
.greeting .hl1 { font-size: 38px; color: #8b95a1; font-weight: 700; margin-bottom: 8px; }
.greeting .hl2 { font-size: 78px; font-weight: 900; color: #191f28; line-height: 1.05; letter-spacing: -3px; display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap; }
.greeting .hl2 .ms { font-size: 44px; font-weight: 800; color: #6b7684; }
.greeting .badge {
  background: #eff6ff; color: #3182f6;
  font-size: 30px; font-weight: 900;
  padding: 6px 16px; border-radius: 999px;
}

/* 듀얼 박스 (좌우) */
.dual-row { display: flex; gap: 14px; margin-bottom: 12px; }
.amount-card {
  flex: 1;
  background: #333d4b;
  border-radius: 22px;
  padding: 26px 28px;
  color: #fff;
  box-shadow: 0 6px 22px rgba(51,61,75,0.18);
}
.amount-card .label { font-size: 32px; color: rgba(255,255,255,0.92); font-weight: 800; margin-bottom: 14px; line-height: 1.25; }
.amount-card .amount {
  font-size: 78px; font-weight: 900;
  color: #fff; line-height: 1.0;
  letter-spacing: -3px;
}
.amount-card .amount .unit { font-size: 36px; font-weight: 800; color: #fff; margin-left: 4px; }

.opp-card {
  flex: 1;
  background: #d6162e;
  border-radius: 22px;
  padding: 26px 28px;
  color: #fff;
  box-shadow: 0 6px 22px rgba(214,22,46,0.2);
}
.opp-card .opp-label { font-size: 32px; color: rgba(255,255,255,0.88); font-weight: 800; margin-bottom: 14px; line-height: 1.25; }
.opp-card .opp-amount {
  font-size: 78px; font-weight: 900;
  color: #fff; line-height: 1.0;
  letter-spacing: -3px;
}
.opp-card .opp-amount .plus { color: #ffd84a; margin-right: 4px; }
.opp-card .opp-amount .unit { font-size: 36px; font-weight: 800; margin-left: 4px; }

/* 가로 전체 폭 강조 액션 박스 */
.action-banner {
  background: linear-gradient(135deg, #fff8db 0%, #ffe080 100%);
  border: 5px solid #d4961c;
  border-radius: 22px;
  padding: 32px 28px;
  margin-bottom: 14px;
  text-align: center;
  font-size: 60px;
  font-weight: 900;
  color: #1a202c;
  line-height: 1.25;
  letter-spacing: -2px;
}
.action-banner .hl { color: #d6162e; font-weight: 900; }
.action-banner .plus { color: #9d0e1c; font-size: 72px; font-weight: 900; text-shadow: 0 1px 0 rgba(157,14,28,0.15); }

/* 섹션 라벨 */
.section-label {
  font-size: 38px; font-weight: 800; color: #8b95a1;
  margin: 16px 8px 10px;
}

/* 시상금 리스트 (2열 그리드) */
.list-card {
  background: #ffffff;
  border-radius: 22px;
  padding: 22px 28px 18px;
  margin-bottom: 12px;
}
.list-grid {
  column-count: 2;
  column-gap: 36px;
}
.list-grid .row {
  break-inside: avoid; -webkit-column-break-inside: avoid;
  display: flex; justify-content: space-between; align-items: baseline;
  padding: 14px 0;
  border-bottom: 1.5px solid #f2f4f6;
  font-size: 36px;
}
.list-grid .row .k { color: #333d4b; font-weight: 700; white-space: nowrap; display: flex; align-items: baseline; gap: 8px; }
.list-grid .row .num { color: #333d4b; font-weight: 900; }
.list-grid .row .v { color: #191f28; font-weight: 900; white-space: nowrap; }
.list-sum {
  display: flex; justify-content: space-between; align-items: baseline;
  border-top: 2px solid #191f28;
  margin-top: 8px;
  padding-top: 16px;
}
.list-sum .k { color: #191f28; font-weight: 900; font-size: 38px; }
.list-sum .v { color: #d6162e; font-size: 44px; font-weight: 900; }

/* 시책 통합 박스 */
.scheme-box {
  background: #ffffff;
  border-radius: 22px;
  padding: 8px 32px;
  margin-bottom: 12px;
}
.sch-row {
  padding: 20px 0;
  border-bottom: 1.5px solid #f2f4f6;
}
.sch-row:last-child { border-bottom: none; }
.sch-row .sl { font-size: 36px; font-weight: 900; color: #191f28; margin-bottom: 8px; }
.sch-row .sm { font-size: 32px; font-weight: 800; color: #6b7684; line-height: 1.4; }
.sch-row .sm .cur { color: #333d4b; font-weight: 900; }
.sch-row .sm .add { color: #d6162e; font-weight: 900; }

/* 매니저+명언 통합 - 옅은 블루 톤 */
.mc-card {
  background: #eff6ff;
  border-radius: 22px;
  padding: 24px 32px;
  margin-top: 14px;
}
.mc-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.mc-label { font-size: 32px; color: #8b95a1; font-weight: 700; margin-bottom: 4px; }
.mc-name { font-size: 54px; color: #191f28; font-weight: 900; letter-spacing: -1.5px; line-height: 1.0; white-space: nowrap; }
.mc-name .ms { font-size: 36px; color: #6b7684; font-weight: 800; margin-left: 8px; }
.mc-chip { background: #d6162e; color: #fff; border-radius: 999px; padding: 12px 24px; font-size: 36px; font-weight: 900; white-space: nowrap; }
.mc-divider { height: 2px; background: #d6e7ff; margin-bottom: 14px; }
.mc-quote { font-size: 36px; color: #333d4b; font-weight: 800; line-height: 1.4; }
.mc-quote .mc-qa { color: #8b95a1; font-weight: 700; }
"""


def _manwon(n):
    if not n: return "0만원"
    n = int(n)
    if n % 10000 == 0:
        return f"{n // 10000:,}만원"
    return f"{round(n / 10000):,}만원"


def _manwon_num(n):
    if not n: return "0"
    n = int(n)
    if n % 10000 == 0:
        return f"{n // 10000:,}"
    return f"{round(n / 10000):,}"


def _agency_short(agency):
    if not agency: return ''
    m = re.search(r'\(([^()]+)\)\s*$', agency)
    suffix = f'({m.group(1)})' if m else ''
    short_map = {
        '유퍼스트': '유퍼스트', '글로벌금융판매': '글로벌',
        '에프엠에셋': '에프엠에셋', '인스밸리': '인스밸리',
        '인카금융서비스': '인카금융', '어센틱금융그룹': '어센틱',
        '프라임에셋': '프라임', '굿리치': '굿리치',
        '토스인슈어런스': '토스', '카라멜에셋': '카라멜',
    }
    base = None
    for k, v in short_map.items():
        if k in agency:
            base = v; break
    if base is None:
        m2 = re.match(r'^([^(]+)', agency)
        base = m2.group(1).strip().replace('(주)', '').replace('주식회사', '').strip() if m2 else agency
    return f"{base} {suffix}".strip()


def _label_short(label):
    if '브릿지' in label: return '브릿지 (4~5월)'
    if '연속가동' in label and '주차' not in label: return '연속가동 (4~5월)'
    if '주차 연속가동' in label: return '주차 연속가동'
    return label


def _consolidate_items(confirmed_items):
    grouped = {}
    order = []
    for label, amount in confirmed_items:
        m = None
        for w in [1, 2, 3, 4]:
            if label.startswith(f'{w}주차'):
                m = f'{w}주차 시상'
                break
        if m is None:
            m = _label_short(label)
        if m not in grouped:
            grouped[m] = 0
            order.append(m)
        grouped[m] += amount
    return [(k, grouped[k]) for k in order]


def build_html(ctx, scheme_rewards=None, base_date=None):
    name = ctx['name']
    agency = _agency_short(ctx['agency'] or '')
    branch = ctx['branch'] or ''
    manager = ctx['manager'] or ''
    cont_months = ctx.get('continuous_months')
    base_date = base_date or datetime(2026, 5, 27)
    date_str = base_date.strftime('%m/%d 기준')

    confirmed_items = _consolidate_items(ctx['confirmed_items'])
    confirmed_total = ctx['confirmed_total']

    total_potential = 0
    action_banner_text = ''
    if scheme_rewards:
        total_potential = sum(r['delta_reward'] for r in scheme_rewards if r['delta_reward'] > 0)
        best = max(scheme_rewards, key=lambda r: r['delta_reward'], default=None)
        if best and best['delta_reward'] > 0:
            action_banner_text = f'<span class="hl">{_manwon(best["next_short"])}</span> 더하면 <span class="plus">+{_manwon(best["delta_reward"])}</span>'

    # 세부 내역 (2열 그리드) — ①②③ 번호 추가
    NUM = ['①','②','③','④','⑤','⑥','⑦','⑧','⑨','⑩']
    grid_rows = ''
    for i, (label, amount) in enumerate(confirmed_items):
        n = NUM[i] if i < len(NUM) else f'{i+1}.'
        grid_rows += f'<div class="row"><span class="k"><span class="num">{n}</span>{label}</span><span class="v">{_manwon(amount)}</span></div>'

    # 시책 (현재 실적 + 더하면 + 받는 금액 두 줄 구조)
    sch_items = ''
    if scheme_rewards:
        rows = ''
        for r in scheme_rewards:
            sl = '5~6월 추가 연속가동' if '추가' in r['label'] else '5~6월 연속가동 (브릿지)'
            cur = _manwon(r["current"])
            if r['delta_reward'] > 0:
                sm = f'현재 실적 <span class="cur">{cur}</span>, <span class="add">{_manwon(r["next_short"])}</span> 더하면 <span class="add">+{_manwon(r["delta_reward"])}</span>'
            else:
                sm = f'현재 실적 <span class="cur">{cur}</span>, <span class="add">시상 {_manwon(r["current_reward"])}</span> 확보'
            rows += f'<div class="sch-row"><div class="sl">{sl}</div><div class="sm">{sm}</div></div>'
        sch_items = f'<div class="scheme-box">{rows}</div>'

    qt, qa = random.choice(QUOTES)
    badge_html = ''
    if cont_months and cont_months >= 12:
        badge_html = f'<span class="badge">{cont_months}개월 연속 MC 달성</span>'

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<style>{CARD_CSS}</style>
</head>
<body>
<div class="wrap">

  <div class="brand-bar">
    <div class="brand">메리츠화재</div>
    <div class="date">{date_str}</div>
  </div>

  <div class="greeting">
    <div class="hl1">{agency} · {branch}</div>
    <div class="hl2">{name}<span class="ms">팀장님</span>{badge_html}</div>
  </div>

  <div class="dual-row">
    <div class="amount-card">
      <div class="label">지금까지 확정된 시상</div>
      <div class="amount">{_manwon_num(confirmed_total)}<span class="unit">만원</span></div>
    </div>
    <div class="opp-card">
      <div class="opp-label">5~6월에 더 받을 수 있어요</div>
      <div class="opp-amount"><span class="plus">+</span>{_manwon_num(total_potential)}<span class="unit">만원</span></div>
    </div>
  </div>

  <div class="action-banner">{action_banner_text}</div>

  <div class="section-label">시상금 세부</div>
  <div class="list-card">
    <div class="list-grid">{grid_rows}</div>
    <div class="list-sum"><span class="k">합계</span><span class="v">{_manwon(confirmed_total)}</span></div>
  </div>

  <div class="section-label">5~6월 추가 기회</div>
  {sch_items}

  <div class="mc-card">
    <div class="mc-top">
      <div>
        <div class="mc-label">담당 매니저</div>
        <div class="mc-name">{manager}<span class="ms">매니저님</span></div>
      </div>
      <div class="mc-chip">문의 환영</div>
    </div>
    <div class="mc-divider"></div>
    <div class="mc-quote">"{qt}" <span class="mc-qa">— {qa}</span></div>
  </div>

</div>
</body>
</html>
"""
    return html


if __name__ == '__main__':
    matches = find_agent('이길범', '3-4')
    cid = matches[0]['본인고객ID']
    data = get_agent_data(cid)
    ctx = build_card_context(data)
    scheme = find_scheme_for_agency(matches[0]['영업가족명'])
    scheme_rewards = calculate_scheme_rewards(scheme, data) if scheme else None

    html = build_html(ctx, scheme_rewards=scheme_rewards)
    out = '/sessions/charming-fervent-newton/mnt/outputs/preview_이길범.html'
    with open(out, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"saved: {out}")
