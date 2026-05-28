"""
메리츠 시상안내 발송 (단순화 버전)
- 카드 PNG는 이미 cards/ 폴더에 생성되어 있다고 가정
- 매니저 코드 입력 → 산하 설계사 목록 → 카드 표시/다운로드/ZIP
"""
import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import io, re, zipfile
from pathlib import Path
from datetime import datetime
from extract_agent_data import _load, get_agent_data, load_manager_contacts, build_card_context
from scheme_engine import find_scheme_for_agency, calculate_scheme_rewards

st.set_page_config(page_title="메리츠 시상안내 발송", page_icon="🎁", layout="wide")

CARDS_DIR = Path(__file__).resolve().parent / "cards_v2"

st.markdown("""
<style>
.main, .stApp { background: #f2f4f6; }
h1, h2, h3 { color: #191f28; letter-spacing: -0.5px; }
.branch-header {
  background: #fff; border-radius: 12px;
  padding: 14px 20px; margin: 14px 0 6px;
  font-size: 17px; font-weight: 800; color: #d6162e;
}
.amt { color: #d6162e; font-weight: 800; }
.brand { color: #d6162e; font-weight: 900; font-size: 28px; }
.warn { background:#fff5f6; border-left:4px solid #d6162e; padding:12px 16px; border-radius:8px; color:#9d0e1c; }
</style>
""", unsafe_allow_html=True)

c1, c2 = st.columns([3, 1])
with c1:
    st.markdown('<div class="brand">메리츠 시상안내 카드뉴스 발송</div>', unsafe_allow_html=True)
with c2:
    st.markdown(f"<div style='text-align:right; color:#8b95a1; padding-top:14px;'>{datetime.now().strftime('%Y.%m.%d')}</div>", unsafe_allow_html=True)
st.markdown("---")


@st.cache_data(show_spinner="데이터 로드 중...")
def load_data():
    df = _load('PRIZE_SUM')
    br = _load('BRIDGE')
    br_map = br.set_index('본인고객ID')['시상금합계'].to_dict() if '시상금합계' in br.columns else {}
    df = df.copy()
    df['_brsum'] = df['본인고객ID'].map(lambda x: br_map.get(x, 0) or 0)
    df['확정시상'] = df['추가13회예정금계'].fillna(0) + df['_brsum'].fillna(0)
    df = df.drop_duplicates(subset=['본인고객ID'], keep='first').reset_index(drop=True)
    return df


@st.cache_data(show_spinner=False)
def load_contacts():
    return load_manager_contacts()


def manwon(v):
    if not v: return "0만원"
    v = int(v)
    return f"{v//10000:,}만원" if v % 10000 == 0 else f"{round(v/10000):,}만원"


def build_kakao_message(cid, name, branch):
    """카톡 발송용 메시지 텍스트 생성"""
    data = get_agent_data(cid)
    if not data.get('PRIZE_SUM'):
        return ''
    ctx = build_card_context(data)
    confirmed = ctx['confirmed_total']
    scheme = find_scheme_for_agency((data.get('PRIZE_SUM') or {}).get('영업가족명', ''))
    sr = calculate_scheme_rewards(scheme, data) if scheme else None
    total_pot = sum(r['delta_reward'] for r in sr if r['delta_reward'] > 0) if sr else 0
    best = max(sr, key=lambda r: r['delta_reward'], default=None) if sr else None

    # 매니저 정보
    mgr_name = (data.get('PRIZE_SUM') or {}).get('지원매니저명', '') or ''
    contacts = load_contacts()
    mgr_info = contacts.get(mgr_name, {})
    phone = mgr_info.get('phone', '')

    lines = [
        f"[{name} 팀장님 시상안내]",
        "",
        f"5월 확정 시상금: {manwon(confirmed)}",
    ]
    if total_pot > 0:
        lines.append(f"5~6월 추가 가능: +{manwon(total_pot)}")
        if best and best['delta_reward'] > 0:
            lines.append("")
            lines.append(f"※ {manwon(best['next_short'])} 더하시면 +{manwon(best['delta_reward'])} 추가!")
    lines.append("")
    lines.append(f"담당 매니저 - {mgr_name}")
    if phone:
        lines.append(f"📞 {phone}")
    return "\n".join(lines)



# 매니저 코드 입력
st.markdown("### 매니저 조회")
def _on_mc_change():
    # 입력이 현재 조회된 코드와 다르면 결과 초기화
    new_val = st.session_state.get('mc_input', '').strip()
    cur = st.session_state.get('mgr_code', '')
    if new_val != cur:
        st.session_state.pop('mgr_code', None)
        st.session_state.pop('selected_card', None)
        for k in list(st.session_state.keys()):
            if k.startswith('chk_'): del st.session_state[k]


col1, col2 = st.columns([3, 1])
with col1:
    mc_input = st.text_input("매니저 코드",
                              value=st.session_state.get('mgr_code', ''),
                              placeholder="예: 320010476",
                              label_visibility="collapsed",
                              key='mc_input',
                              on_change=_on_mc_change)
with col2:
    if st.button("조회", type="primary", use_container_width=True):
        st.session_state['mgr_code'] = mc_input.strip()
        st.session_state.pop('selected_card', None)
        for k in list(st.session_state.keys()):
            if k.startswith('chk_'): del st.session_state[k]


if st.session_state.get('mgr_code'):
    df = load_data()
    code = st.session_state['mgr_code']
    agents = df[df['지원매니저코드'] == code]

    if len(agents) == 0:
        st.error(f"매니저 코드 '{code}' 산하 설계사 없음")
    else:
        mgr_name = agents['지원매니저명'].iloc[0]
        total = int(agents['확정시상'].sum())
        st.markdown(f"### **{mgr_name}** 매니저 산하 — {len(agents)}명 / 확정 **{manwon(total)}**")

        missing = []
        for _, row in agents.iterrows():
            if not (CARDS_DIR / f"{row['본인고객ID']}.png").exists():
                missing.append(row['대리점설계사명'])
        if missing:
            st.markdown(f'<div class="warn">⚠️ 미생성 카드 {len(missing)}명: {", ".join(missing[:5])}{"..." if len(missing) > 5 else ""}<br>워크스페이스에서 <code>python generate_manager_cards.py {code}</code> 실행 필요</div>', unsafe_allow_html=True)

        # 일괄 선택/해제 버튼
        bc1, bc2, bc3 = st.columns([1, 1, 4])
        with bc1:
            if st.button("✅ 전체 선택", use_container_width=True, key="select_all"):
                for _, _row in agents.iterrows():
                    cid_ = _row['본인고객ID']
                    if (CARDS_DIR / f"{cid_}.png").exists():
                        st.session_state[f'chk_{cid_}'] = True
                st.rerun()
        with bc2:
            if st.button("⬜ 전체 해제", use_container_width=True, key="deselect_all"):
                for k in list(st.session_state.keys()):
                    if k.startswith('chk_'):
                        st.session_state[k] = False
                st.rerun()

        agencies = sorted(agents['대리점지사명'].dropna().unique())
        for agency in agencies:
            sub = agents[agents['대리점지사명'] == agency].sort_values('대리점설계사명')
            st.markdown(f'<div class="branch-header">{agency} ({len(sub)}명)</div>', unsafe_allow_html=True)
            for _, row in sub.iterrows():
                cid = row['본인고객ID']
                name = row['대리점설계사명']
                amt = int(row['확정시상'])
                png_path = CARDS_DIR / f"{cid}.png"
                exists = png_path.exists()

                c1, c2, c3, c4 = st.columns([0.5, 3, 2, 1.5])
                with c1:
                    if exists:
                        st.checkbox(" ", key=f"chk_{cid}", label_visibility="collapsed")
                    else:
                        st.markdown("🚫")
                with c2:
                    st.markdown(f"**{name}**" + ("" if exists else " <small style='color:#9d0e1c;'>(카드 미생성)</small>"), unsafe_allow_html=True)
                with c3:
                    st.markdown(f'<span class="amt">{manwon(amt)}</span>', unsafe_allow_html=True)
                with c4:
                    if exists:
                        if st.button("카드보기", key=f"view_{cid}", use_container_width=True):
                            st.session_state['selected_card'] = (cid, name, row['지점조직명'])

        st.markdown("---")
        selected = [(row['본인고객ID'], row['대리점설계사명'], row['지점조직명'])
                    for _, row in agents.iterrows()
                    if st.session_state.get(f'chk_{row["본인고객ID"]}')]

        zc1, zc2 = st.columns([1, 3])
        with zc1:
            zip_clicked = st.button(f"📦 ZIP 다운로드 ({len(selected)}명)",
                                    type="primary", disabled=len(selected) == 0)
        with zc2:
            if selected:
                st.markdown(f"<div style='padding-top:10px; color:#3182f6; font-weight:700;'>선택: {len(selected)}명</div>", unsafe_allow_html=True)

        if zip_clicked and selected:
            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, 'w', zipfile.ZIP_DEFLATED) as zf:
                for cid, name, branch in selected:
                    png_path = CARDS_DIR / f"{cid}.png"
                    if png_path.exists():
                        fname = re.sub(r'[\\/:*?"<>|]', '_', f"{name}_{branch}_시상안내.png")
                        zf.write(png_path, fname)
            zip_buf.seek(0)
            st.download_button(
                f"⬇️ {len(selected)}명 ZIP 다운로드",
                data=zip_buf,
                file_name=f"시상안내_{mgr_name}_{datetime.now().strftime('%Y%m%d')}.zip",
                mime="application/zip",
            )


if st.session_state.get('selected_card'):
    cid, name, branch = st.session_state['selected_card']
    st.markdown("---")
    st.markdown(f"### {name} 팀장님 카드뉴스")
    png_path = CARDS_DIR / f"{cid}.png"
    if png_path.exists():
        c1, c2 = st.columns([2, 1])
        with c1:
            st.image(str(png_path), use_container_width=True)
        with c2:
            with open(png_path, 'rb') as f:
                png_bytes = f.read()
            fname = re.sub(r'[\\/:*?"<>|]', '_', f"{name}_{branch}_시상안내.png")
            st.download_button("📥 PNG 다운로드", data=png_bytes,
                               file_name=fname, mime="image/png",
                               use_container_width=True, key=f"dl_{cid}")
            # 매니저 연락처 (해당 설계사의 매니저)
            contacts = load_contacts()
            data = get_agent_data(cid)
            mgr_name = (data.get('PRIZE_SUM') or {}).get('지원매니저명', '') or ''
            mgr_info = contacts.get(mgr_name)
            if mgr_info:
                phone = mgr_info['phone']
                phone_clean = phone.replace('-', '')
                st.markdown(f"""
                <a href='tel:{phone_clean}' style='text-decoration:none;'>
                  <div style='background:#d6162e; color:#fff; padding:16px 20px; border-radius:10px; text-align:center; font-weight:900; margin-top:10px; font-size:18px;'>
                    📞 {mgr_name} 매니저님<br>
                    <span style='font-size:22px;'>{phone}</span>
                  </div>
                </a>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div style='background:#f2f4f6; color:#6b7684; padding:14px 18px; border-radius:10px; text-align:center; font-weight:700; margin-top:10px;'>
                  📞 매니저 연락처 없음
                </div>
                """, unsafe_allow_html=True)

            # 카톡 발송용 메시지
            st.markdown("<div style='margin-top:18px; font-weight:800; color:#191f28; font-size:15px;'>💬 카톡 발송용 메시지</div>", unsafe_allow_html=True)
            msg = build_kakao_message(cid, name, branch)
            st.code(msg, language='text')
            st.markdown("""
            <div style='font-size:12px; color:#6b7684; padding-top:4px;'>
              위 박스 우측의 📋 버튼으로 복사 → 카톡에 PNG 첨부 후 메시지 붙여넣기
            </div>
            """, unsafe_allow_html=True)
