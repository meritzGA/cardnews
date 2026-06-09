"""Streamlit Cloud용 — 인덱스 + 미리 만든 카드 PNG 사용 (엑셀/렌더 불필요)
빌드:
  로컬: python build_index.py + python gen_parallel.py 4 ver1 + python gen_parallel.py 4 ver2
Cloud: index.json + messages.json + cards_v2/{ver1|ver2}/ 사용

발송 모드:
- ver1: 월요일 (지난주 결과 + 격려)
- ver2: 화~금 (부족 실적 독려)
"""
import streamlit as st
import json, io, re, zipfile
from pathlib import Path
from datetime import datetime

st.set_page_config(page_title="메리츠 시상안내", page_icon="🎁", layout="wide")

ROOT = Path(__file__).resolve().parent
INDEX_PATH = ROOT / 'index.json'
MSG_PATH = ROOT / 'messages.json'
BASE_CARDS_DIR = ROOT / 'cards_v2'

# ver1=월요일, ver2=화~금. 요일 기반 자동 추천
_today = datetime.now().weekday()  # 0=월
DEFAULT_VERSION = 'ver1' if _today == 0 else 'ver2'


def get_cards_dir(version: str) -> Path:
    """버전 폴더 우선, 없으면 cards_v2/ 직접 (하위 호환)."""
    ver_dir = BASE_CARDS_DIR / version
    if ver_dir.exists() and any(ver_dir.glob('*.png')):
        return ver_dir
    return BASE_CARDS_DIR


st.markdown("""
<style>
.main, .stApp { background: #f2f4f6; }
h1, h2, h3 { color: #191f28; }
.brand { color: #d6162e; font-weight: 900; font-size: 28px; }
.branch-header { background:#fff; border-radius:12px; padding:14px 20px; margin:14px 0 6px; font-size:17px; font-weight:800; color:#d6162e; }
.amt { color: #d6162e; font-weight: 800; }
.ver-hint { color:#8b95a1; font-size:13px; text-align:right; padding-top:34px; }
</style>
""", unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def load_index():
    if not INDEX_PATH.exists():
        return {}
    with open(INDEX_PATH, encoding='utf-8') as f:
        return json.load(f)


@st.cache_data(show_spinner=False)
def load_messages():
    if not MSG_PATH.exists():
        return {}
    with open(MSG_PATH, encoding='utf-8') as f:
        return json.load(f)


def manwon(v):
    if not v: return "0만원"
    v = int(v)
    return f"{v//10000:,}만원" if v % 10000 == 0 else f"{round(v/10000):,}만원"


def ver1_message(agent, mgr_name, mgr_phone):
    """ver1 (월요일) 카톡 메시지 — 지난주 결과 + 격려"""
    confirmed = agent.get('amt', 0)
    cur_month = datetime.now().month  # 데이터 기준 월에 맞추려면 build_index에서 저장 필요

    if confirmed >= 1000000:
        cheer = "멋진 1주차 성과예요! 🎉"
    elif confirmed >= 300000:
        cheer = "1주차 수고하셨어요!"
    elif confirmed > 0:
        cheer = "1주차 첫 발걸음 응원합니다!"
    else:
        cheer = "이번 주부터 함께 시작해봐요!"

    lines = [
        f"[{agent['name']} 팀장님] {cur_month}월 1주차 결과 안내",
        "",
        cheer,
        "",
        f"1주차 확정 시상금: {manwon(confirmed)}",
        "",
        "이번 주(2주차)도 함께 달려봐요!",
        "",
        f"담당 매니저 - {mgr_name}",
    ]
    if mgr_phone:
        lines.append(f"📞 {mgr_phone}")
    return "\n".join(lines)


# 헤더
c1, c2 = st.columns([3, 1])
with c1:
    st.markdown('<div class="brand">메리츠 시상안내 카드뉴스 발송</div>', unsafe_allow_html=True)
with c2:
    weekday_str = ['월','화','수','목','금','토','일'][_today]
    st.markdown(f"<div style='text-align:right; color:#8b95a1; padding-top:14px;'>{datetime.now():%Y.%m.%d} ({weekday_str})</div>", unsafe_allow_html=True)

# 버전 선택 (요일 기반 자동 추천)
vc1, vc2 = st.columns([4, 1])
with vc1:
    version_label = st.radio(
        "발송 모드",
        options=['ver1', 'ver2'],
        index=0 if DEFAULT_VERSION == 'ver1' else 1,
        format_func=lambda v: {
            'ver1': '📅 ver1 — 월요일용 (지난주 결과 + 격려)',
            'ver2': '🔥 ver2 — 화~금용 (부족 실적 독려)',
        }[v],
        horizontal=True,
        key='card_version',
    )
with vc2:
    st.markdown(f"<div class='ver-hint'>오늘 추천: {DEFAULT_VERSION}</div>", unsafe_allow_html=True)

CARDS_DIR = get_cards_dir(version_label)
if not (BASE_CARDS_DIR / version_label).exists():
    st.warning(f"⚠️ `cards_v2/{version_label}/` 폴더 미존재 → 임시로 `cards_v2/` 사용 중. 로컬에서 `python gen_parallel.py 4 {version_label}` 후 push 필요")
st.markdown("---")


index = load_index()
messages = load_messages()

if not index:
    st.error("인덱스가 없습니다. 로컬에서 `python build_index.py` 실행 후 push 필요")
    st.stop()


def _on_mc():
    nv = st.session_state.get('mci', '').strip()
    if nv != st.session_state.get('mgr_code'):
        st.session_state.pop('mgr_code', None)
        st.session_state.pop('selected_card', None)
        for k in list(st.session_state.keys()):
            if k.startswith('chk_'): del st.session_state[k]


st.markdown("### 매니저 조회")
c1, c2 = st.columns([3, 1])
with c1:
    st.text_input("매니저 코드", value=st.session_state.get('mgr_code', ''),
                  placeholder="예: 320010476", label_visibility="collapsed",
                  key='mci', on_change=_on_mc)
with c2:
    if st.button("조회", type="primary", use_container_width=True):
        st.session_state['mgr_code'] = st.session_state.get('mci', '').strip()
        st.session_state.pop('selected_card', None)
        for k in list(st.session_state.keys()):
            if k.startswith('chk_'): del st.session_state[k]


if st.session_state.get('mgr_code'):
    code = st.session_state['mgr_code']
    mgr = index.get(code)
    if not mgr:
        st.error(f"매니저 코드 '{code}' 산하 없음")
    else:
        agents = mgr['agents']
        total = sum(a['amt'] for a in agents)
        st.markdown(f"### **{mgr['mgr_name']}** 매니저 산하 — {len(agents)}명 / 확정 **{manwon(total)}**")

        bc1, bc2, _ = st.columns([1, 1, 4])
        with bc1:
            if st.button("✅ 전체 선택", use_container_width=True, key='sel_all'):
                for a in agents: st.session_state[f'chk_{a["cid"]}'] = True
                st.rerun()
        with bc2:
            if st.button("⬜ 전체 해제", use_container_width=True, key='sel_none'):
                for k in list(st.session_state.keys()):
                    if k.startswith('chk_'): st.session_state[k] = False
                st.rerun()

        agencies = sorted({a['agency'] for a in agents if a.get('agency')})
        for agency in agencies:
            sub = [a for a in agents if a['agency'] == agency]
            st.markdown(f'<div class="branch-header">{agency} ({len(sub)}명)</div>', unsafe_allow_html=True)
            for a in sub:
                cid = a['cid']
                cc1, cc2, cc3, cc4 = st.columns([0.5, 3, 2, 1.5])
                with cc1: st.checkbox(" ", key=f"chk_{cid}", label_visibility="collapsed")
                with cc2: st.markdown(f"**{a['name']}**")
                with cc3: st.markdown(f'<span class="amt">{manwon(a["amt"])}</span>', unsafe_allow_html=True)
                with cc4:
                    if st.button("카드보기", key=f"v_{cid}", use_container_width=True):
                        st.session_state['selected_card'] = a

        st.markdown("---")
        sel = [a for a in agents if st.session_state.get(f'chk_{a["cid"]}')]
        if st.button(f"📦 ZIP 다운로드 ({len(sel)}명)", type="primary", disabled=len(sel) == 0):
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
                for a in sel:
                    png = CARDS_DIR / f"{a['cid']}.png"
                    if png.exists():
                        fname = re.sub(r'[\\/:*?"<>|]', '_', f"{a['name']}_{a['branch']}_{version_label}.png")
                        zf.write(png, fname)
            buf.seek(0)
            st.download_button(f"⬇️ 받기 ({len(sel)}명)", buf,
                              f"시상안내_{mgr['mgr_name']}_{version_label}_{datetime.now():%Y%m%d}.zip", "application/zip")


# 선택된 카드 표시
if st.session_state.get('selected_card'):
    a = st.session_state['selected_card']
    st.markdown("---")
    st.markdown(f"### {a['name']} 팀장님 카드뉴스 ({version_label})")
    png = CARDS_DIR / f"{a['cid']}.png"
    if not png.exists():
        st.warning(f"`{version_label}` 카드 PNG 없음 - 로컬에서 `python gen_parallel.py 4 {version_label}` 후 push 필요")
    else:
        c1, c2 = st.columns([2, 1])
        with c1: st.image(str(png), use_container_width=True)
        with c2:
            st.download_button("📥 PNG 다운로드", png.read_bytes(),
                             f"{a['name']}_{a['branch']}_{version_label}.png", "image/png",
                             use_container_width=True, key=f"dl_{a['cid']}")
            code = st.session_state.get('mgr_code')
            mgr = index.get(code, {})
            if mgr.get('mgr_phone'):
                p = mgr['mgr_phone'].replace('-', '')
                st.markdown(f"""
                <a href='tel:{p}' style='text-decoration:none;'>
                <div style='background:#d6162e;color:#fff;padding:16px 20px;border-radius:10px;text-align:center;font-weight:900;margin-top:10px;font-size:18px;'>
                📞 {mgr['mgr_name']} 매니저님<br><span style='font-size:22px;'>{mgr['mgr_phone']}</span>
                </div></a>""", unsafe_allow_html=True)

            # 카톡 메시지 (버전별)
            if version_label == 'ver1':
                msg = ver1_message(a, mgr.get('mgr_name', ''), mgr.get('mgr_phone', ''))
            else:
                msg = messages.get(a['cid'], '')

            if msg:
                st.markdown(f"**💬 카톡 메시지 ({version_label})**")
                st.code(msg, language='text')
                st.caption("위 박스의 📋로 복사 → 카톡에 PNG 첨부 후 붙여넣기")
