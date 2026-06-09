"""메리츠화재 카드뉴스 v16 — 토스 스타일 (콘텐츠 압축)"""
import sys
sys.path.insert(0, '/sessions/charming-fervent-newton/mnt/outputs')
from extract_agent_data import get_data_date, find_agent, get_agent_data, build_card_context
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
    ("할 수 있다 믿으면 절반은 이룬 것.", "시어도어 루즈벨트"),
    ("성공의 비결은 시작입니다.", "마크 트웨인"),
    ("꿈을 좇는 사람만 잡을 수 있어요.", "헨리 포드"),
    ("오늘의 노력이 내일의 결과예요.", "콘라드 힐튼"),
    ("포기하지 않는 자가 결국 이겨요.", "윈스턴 처칠"),
    ("끈기는 재능을 이깁니다.", "에디슨"),
    ("기회는 어려움 한가운데 있어요.", "아인슈타인"),
    ("오늘 흘린 땀은 내일의 보석.", "이소룡"),
    ("성공은 작은 노력의 합이에요.", "로버트 콜리어"),
    ("도전하는 자에게 기회가 와요.", "마윈"),
    ("실패는 성공의 어머니예요.", "토머스 에디슨"),
    ("천재는 1% 영감과 99% 노력.", "에디슨"),
    ("운명은 도전하는 자에게 미소.", "버질"),
    ("작은 시작이 큰 성공으로.", "탈무드"),
]


CARD_CSS = """
@page { size: 1080px 1500px; margin: 0; }
* { margin:0; padding:0; box-sizing:border-box; }
html, body {
  font-family: 'NanumSquare', 'NanumGothic', 'Malgun Gothic', '맑은 고딕', 'Apple SD Gothic Neo', sans-serif;
  background: #f2f4f6;
  color: #191f28;
  width: 1080px;
  margin: 0;
}
.wrap { width: 1080px; padding: 24px 24px; background: #f2f4f6; page-break-after: always; break-after: page; }

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
  background: #ffe9a1;
  border: 5px solid #d4961c;
  border-radius: 22px;
  padding: 28px 28px;
  margin-bottom: 14px;
  text-align: center;
  font-size: 44px;
  font-weight: 900;
  color: #1a202c;
  line-height: 1.35;
  letter-spacing: -1.5px;
}
.action-banner .have { color: #1f6feb; font-weight: 900; }       /* 이미 확보 - 파랑 */
.action-banner .hl { color: #d6162e; font-weight: 900; }         /* 더할 실적 - 빨강 */
.action-banner .plus { color: #9d0e1c; font-size: 56px; font-weight: 900; text-shadow: 0 1px 0 rgba(157,14,28,0.15); }
.action-banner .addsmall { color: #d6162e; font-size: 32px; font-weight: 800; display: block; margin-top: 4px; }

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
.sch-row .sm { font-size: 30px; font-weight: 700; color: #6b7684; line-height: 1.55; }
.sch-row .sm .cur { color: #333d4b; font-weight: 900; }
.sch-row .sm .have { color: #1f6feb; font-weight: 900; }          /* 이미 확보 - 파랑 */
.sch-row .sm .arrow { color: #6b7684; font-weight: 700; }
.sch-row .sm .total { color: #191f28; font-weight: 900; font-size: 34px; }
.sch-row .sm .add { color: #d6162e; font-weight: 900; }            /* 추가분 - 빨강 */

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
    base_date = base_date or get_data_date()
    date_str = base_date.strftime('%m/%d 기준')

    confirmed_items = _consolidate_items(ctx['confirmed_items'])
    confirmed_total = ctx['confirmed_total']

    # 잠재 시상은 next_round_items 기반 (활성 주차 + 5_6) — 일관성 유지
    nr_items = ctx.get('next_round_items') or []
    total_potential = sum(i['assumed_reward'] for i in nr_items)
    action_banner_text = ''
    if nr_items:
        # 같은 실적 풀을 공유 → max 부족액만 채우면 모두 충족
        max_short = max((i['short'] for i in nr_items), default=0)
        if total_potential > 0:
            # 친절한 흐름: 현재 X만 확보 → Y만 더하면 → 총 Z만 (+추가 ?만)
            grand_total = confirmed_total + total_potential
            action_banner_text = (
                f'지금 <span class="have">{_manwon(confirmed_total)}</span> 확보 ・ '
                f'<span class="hl">{_manwon(max_short)}</span> 더하면 '
                f'<span class="plus">총 {_manwon(grand_total)}</span> '
                f'<span class="addsmall">(+{_manwon(total_potential)} 추가)</span>'
            )

    # 세부 내역 (2열 그리드) — ①②③ 번호 추가
    NUM = ['①','②','③','④','⑤','⑥','⑦','⑧','⑨','⑩']
    grid_rows = ''
    for i, (label, amount) in enumerate(confirmed_items):
        n = NUM[i] if i < len(NUM) else f'{i+1}.'
        grid_rows += f'<div class="row"><span class="k"><span class="num">{n}</span>{label}</span><span class="v">{_manwon(amount)}</span></div>'

    # 시책 (next_round_items만 — 활성 주차 + 5_6 BRIDGE/CONT, 각각 정확한 라벨)
    # 표시 흐름: ① 현재 실적·확보 시상금 → ② 부족 실적 → ③ 총 시상금(다음 구간) + 추가분
    sch_items = ''
    nr = ctx.get('next_round_items') or []
    if nr:
        rows = ''
        for item in nr:
            sl = item['label']
            cur = _manwon(item['current'])
            short = item['short']
            reward = item['assumed_reward']            # 추가로 받게 되는 금액 (delta)
            cur_reward = item.get('current_reward', 0)  # 이미 확보 시상금
            next_reward = item.get('next_reward', cur_reward + reward)  # 다음 구간 도달시 총 시상금

            sm = (
                f'실적 <span class="cur">{cur}</span> · '
                f'현재 확보 <span class="have">{_manwon(cur_reward)}</span>'
                f'<br><span class="arrow">+ {_manwon(short)} 더 채우면</span> → '
                f'총 <span class="total">{_manwon(next_reward)}</span> '
                f'<span class="add">(추가 +{_manwon(reward)})</span>'
            )
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
      <div class="opp-label">조금만 더하면<br>추가로 받을 시상</div>
      <div class="opp-amount"><span class="plus">+</span>{_manwon_num(total_potential)}<span class="unit">만원</span></div>
    </div>
  </div>

  <div class="action-banner">{action_banner_text}</div>

  <div class="section-label">시상금 세부</div>
  <div class="list-card">
    <div class="list-grid">{grid_rows}</div>
    <div class="list-sum"><span class="k">합계</span><span class="v">{_manwon(confirmed_total)}</span></div>
  </div>

  <div class="section-label">추가로 받을 시상 (시책별)</div>
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


def build_html_ver1(ctx, base_date=None, prev_week=1):
    """ver1 — 월요일 발송용: 지난 주(prev_week 주차) 결과 안내 + 격려 + 다음주 도전 권유.

    초점:
    - 1주차 동안 확정된 시상금 강조
    - "메리츠 하니까 이만큼 받을 수 있구나" 동기부여
    - 다음 주(2주차) 챌린지 권유
    """
    name = ctx['name']
    agency = _agency_short(ctx['agency'] or '')
    branch = ctx['branch'] or ''
    manager = ctx['manager'] or ''
    cont_months = ctx.get('continuous_months')
    base_date = base_date or get_data_date()
    date_str = base_date.strftime('%m/%d 기준')

    # 지난주(prev_week) 항목만 필터 + 정규시상 + 브릿지·연속가동 같은 비주차 항목
    items_all = ctx['confirmed_items']
    week_items = []
    non_week_items = []
    for label, amount in items_all:
        if label.startswith(f'{prev_week}주차'):
            week_items.append((label, amount))
        elif label.startswith(('1주차','2주차','3주차','4주차','5주차')):
            continue  # 다른 주차 제외
        else:
            non_week_items.append((label, amount))

    # 1주차 합계 + 정규시상(매월 시상금계 일부) — 보수적으로 주차 항목만
    week_total = sum(v for _, v in week_items)
    non_week_total = sum(v for _, v in non_week_items)
    confirmed_total = week_total + non_week_total

    # 세부 그리드 (지난주 + 비주차)
    grid_items = week_items + non_week_items
    NUM = ['①','②','③','④','⑤','⑥','⑦','⑧','⑨','⑩']
    grid_rows = ''
    for i, (label, amount) in enumerate(grid_items):
        n = NUM[i] if i < len(NUM) else f'{i+1}.'
        grid_rows += f'<div class="row"><span class="k"><span class="num">{n}</span>{label}</span><span class="v">{_manwon(amount)}</span></div>'

    # 다음주 챌린지 — next_round_items 활용 (있으면 보여주기)
    next_week_total = sum(i.get('assumed_reward',0) for i in ctx.get('next_round_items') or [])

    qt, qa = random.choice(QUOTES)
    badge_html = ''
    if cont_months and cont_months >= 12:
        badge_html = f'<span class="badge">{cont_months}개월 연속 MC 달성</span>'

    # 격려 메시지 (시상금 규모에 따라 톤 조정)
    if confirmed_total >= 1000000:
        cheer_main = "메리츠와 함께한 1주차, 멋진 성과예요! 🎉"
        cheer_sub = "이번 주(2주차)도 같이 달려봐요"
    elif confirmed_total >= 300000:
        cheer_main = "1주차 수고하셨어요! 좋은 시작이에요"
        cheer_sub = "2주차에는 더 큰 시상금에 도전!"
    elif confirmed_total > 0:
        cheer_main = "1주차 첫 발걸음 응원합니다!"
        cheer_sub = "2주차는 분명 더 좋아질 거예요"
    else:
        cheer_main = "이번 주(2주차)부터 함께 시작해봐요!"
        cheer_sub = "메리츠 시상의 기회가 매주 기다리고 있어요"

    # 다음주 챌린지 박스 (있을 때만)
    challenge_html = ''
    if next_week_total > 0:
        challenge_html = f"""
  <div class="challenge-banner">
    <div class="ch-label">2주차 도전 ▶</div>
    <div class="ch-main">실적 채우면 <span class="ch-plus">+{_manwon(next_week_total)}</span> 추가 가능</div>
  </div>
        """

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<style>{CARD_CSS}
.result-hero {{
  background: linear-gradient(135deg, #ff6b35 0%, #d6162e 100%);
  border-radius: 24px;
  padding: 44px 36px;
  margin-bottom: 14px;
  color: #fff;
  text-align: center;
  box-shadow: 0 8px 24px rgba(214,22,46,0.25);
}}
.result-hero .rh-label {{ font-size: 32px; font-weight: 800; opacity: 0.95; margin-bottom: 12px; letter-spacing: -1px; }}
.result-hero .rh-amount {{ font-size: 132px; font-weight: 900; line-height: 1; letter-spacing: -4px; }}
.result-hero .rh-unit {{ font-size: 56px; font-weight: 800; margin-left: 6px; }}
.result-hero .rh-sub {{ font-size: 28px; font-weight: 700; opacity: 0.9; margin-top: 12px; }}

.cheer-banner {{
  background: #fff7ed;
  border: 5px solid #fb923c;
  border-radius: 22px;
  padding: 26px 28px;
  margin-bottom: 14px;
  text-align: center;
}}
.cheer-banner .cm {{ font-size: 44px; font-weight: 900; color: #d6162e; letter-spacing: -1.5px; }}
.cheer-banner .cs {{ font-size: 30px; font-weight: 700; color: #6b7684; margin-top: 8px; letter-spacing: -1px; }}

.challenge-banner {{
  background: #eff6ff;
  border: 4px solid #1f6feb;
  border-radius: 18px;
  padding: 22px 26px;
  margin-bottom: 14px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}}
.challenge-banner .ch-label {{ font-size: 30px; font-weight: 900; color: #1f6feb; }}
.challenge-banner .ch-main {{ font-size: 36px; font-weight: 800; color: #191f28; letter-spacing: -1px; }}
.challenge-banner .ch-plus {{ color: #d6162e; font-weight: 900; }}
</style>
</head>
<body>
<div class="wrap">

  <div class="brand-bar">
    <div class="brand">메리츠화재 · 지난주 결과</div>
    <div class="date">{date_str}</div>
  </div>

  <div class="greeting">
    <div class="hl1">{agency} · {branch}</div>
    <div class="hl2">{name}<span class="ms">팀장님</span>{badge_html}</div>
  </div>

  <div class="result-hero">
    <div class="rh-label">{prev_week}주차 확정 시상금</div>
    <div class="rh-amount">{_manwon_num(confirmed_total)}<span class="rh-unit">만원</span></div>
    <div class="rh-sub">메리츠 시상으로 받게 된 추가 금액이에요</div>
  </div>

  <div class="cheer-banner">
    <div class="cm">{cheer_main}</div>
    <div class="cs">{cheer_sub}</div>
  </div>

  {challenge_html}

  <div class="section-label">{prev_week}주차 시상금 세부</div>
  <div class="list-card">
    <div class="list-grid">{grid_rows}</div>
    <div class="list-sum"><span class="k">합계</span><span class="v">{_manwon(confirmed_total)}</span></div>
  </div>

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
    print(out)
