"""Streamlit Cloud용 카드뉴스 발송.
- 데이터 파일은 repo에 포함 (매일 git push로 업데이트)
- 카드는 실시간 생성
"""
import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import io, re, zipfile, tempfile
from pathlib import Path
from datetime import datetime
import pandas as pd

from extract_agent_data import _load, get_agent_data, build_card_context, load_manager_contacts
from scheme_engine import find_scheme_for_agency, calculate_scheme_rewards
from card_template import build_html
from render_png import html_to_png

st.set_page_config(page_title="메리츠 시상안내", page_icon="🎁", layout="wide")

st.markdown("""
<style>
.main, .stApp { background: #f2f4f6; }
h1, h2, h3 { color: #191f28; letter-spacing: -0.5px; }
.brand { color: #d6162e; font-weight: 900; font-size: 28px; }
.branch-header { background:#fff; border-radius:12px; padding:14px 20px; margin:14px 0 6px; font-size:17px; font-weight:800; color:#d6162e; }
.amt { color: #d6162e; font-weight: 800; }
</style>
""", unsafe_allow_html=True)

c1, c2 = st.columns([3, 1])
with c1:
    st.markdown('<div class="brand">메리츠 시상안내 카드뉴스 발송</div>', unsafe_allow_html=True)
with c2:
    st.markdown(f"<div style='text-align:right; color:#8b95a1; padding-top:14px;'>{datetime.now():%Y.%m.%d}</div>", unsafe_allow_html=True)
st.markdown("---")


@st.cache_data(show_spinner="데이터 로드 중...")
def load_view():
    df = _load('PRIZE_SUM')
    br = _load('BRIDGE')
    br_map = br.set_index('본인고객ID')['시상금합계'].to_dict() if '시상금합계' in br.columns else {}
    df = df.copy()
    df['_brsum'] = df['본인고객ID'].map(lambda x: br_map.get(x, 0) or 0)
    df['확정시상'] = df['추가13회예정금계'].fillna(0) + df['_brsum'].fillna(0)
    df = df.drop_duplicates(subset=['본인고객ID']).reset_index(drop=True)
    return df


@st.cache_data(show_spinner=False)
def load_contacts():
    return load_manager_contacts()


def manwon(v):
    if not v: return "0만원"
    v = int(v)
    return f"{v//10000:,}만원" if v % 10000 == 0 else f"{round(v/10000):,}만원"


def _on_mc():
    nv = st.session_state.get('mci', '').strip()
    if nv != st.session_state.get('mgr_code'):
        st.session_state.pop('mgr_code', None)
        st.session_state.pop('selected_card', None)
        for k in list(st.session_state.keys()):
            if k.startswith('chk_'): del st.session_state[k]


def render_card_bytes(cid, info):
    data = get_agent_data(cid)
    if not data.get('PRIZE_SUM'): return None
    ctx = build_card_context(data)
    scheme = find_scheme_for_agency(info.get('영업가족명', ''))
    sr = calculate_scheme_rewards(scheme, data) if scheme else None
    html = build_html(ctx, scheme_rewards=sr)
    with tempfile.NamedTemporaryFile('w', suffix='.html', delete=False, encoding='utf-8') as f:
        f.write(html); html_path = f.name
    png_path = html_path.replace('.html', '.png')
    html_to_png(html_path, png_path)
    return Path(png_path).read_bytes()


def build_kakao_msg(cid, name, branch):
    data = get_agent_data(cid)
    if not data.get('PRIZE_SUM'): return ''
    ctx = build_card_context(data)
    scheme = find_scheme_for_agency((data.get('PRIZE_SUM') or {}).get('영업가족명', ''))
    sr = calculate_scheme_rewards(scheme, data) if scheme else None
    total_pot = sum(r['delta_reward'] for r in sr if r['delta_reward'] > 0) if sr else 0
    best = max((r for r in (sr or []) if r['delta_reward'] > 0), key=lambda r: r['next_short'], default=None)
    contacts = load_contacts()
    mgr_name = (data.get('PRIZE_SUM') or {}).get('지원매니저명', '') or ''
    phone = contacts.get(mgr_name, {}).get('phone', '')
    lines = [f"[{name} 팀장님 시상안내]", "", f"5월 확정 시상금: {manwon(ctx['confirmed_total'])}"]
    if total_pot > 0:
        lines.append(f"5~6월 추가 가능: +{manwon(total_pot)}")
        if best:
            lines += ["", f"※ {manwon(best['next_short'])} 더하시면 +{manwon(total_pot)} 추가!"]
    lines += ["", f"담당 매니저 - {mgr_name}"]
    if phone: lines.append(f"📞 {phone}")
    return "\n".join(lines)


# 매니저 코드 입력
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
    df = load_view()
    agents = df[df['지원매니저코드'] == code]
    if len(agents) == 0:
        st.error(f"매니저 코드 '{code}' 산하 없음")
    else:
        mgr_name = agents['지원매니저명'].iloc[0]
        total = int(agents['확정시상'].sum())
        st.markdown(f"### **{mgr_name}** 매니저 산하 — {len(agents)}명 / 확정 **{manwon(total)}**")

        bc1, bc2, _ = st.columns([1, 1, 4])
        with bc1:
            if st.button("✅ 전체 선택", use_container_width=True, key='sel_all'):
                for _, r in agents.iterrows(): st.session_state[f'chk_{r["본인고객ID"]}'] = True
                st.rerun()
        with bc2:
            if st.button("⬜ 전체 해제", use_container_width=True, key='sel_none'):
                for k in list(st.session_state.keys()):
                    if k.startswith('chk_'): st.session_state[k] = False
                st.rerun()

        for agency in sorted(agents['대리점지사명'].dropna().unique()):
            sub = agents[agents['대리점지사명'] == agency].sort_values('대리점설계사명')
            st.markdown(f'<div class="branch-header">{agency} ({len(sub)}명)</div>', unsafe_allow_html=True)
            for _, row in sub.iterrows():
                cid = row['본인고객ID']; name = row['대리점설계사명']; amt = int(row['확정시상'])
                cc1, cc2, cc3, cc4 = st.columns([0.5, 3, 2, 1.5])
                with cc1: st.checkbox(" ", key=f"chk_{cid}", label_visibility="collapsed")
                with cc2: st.markdown(f"**{name}**")
                with cc3: st.markdown(f'<span class="amt">{manwon(amt)}</span>', unsafe_allow_html=True)
                with cc4:
                    if st.button("카드보기", key=f"v_{cid}", use_container_width=True):
                        st.session_state['selected_card'] = (cid, name, row['지점조직명'], agency, row['영업가족명'])

        st.markdown("---")
        sel = [(r['본인고객ID'], r['대리점설계사명'], r['지점조직명'], r['대리점지사명'], r['영업가족명'])
               for _, r in agents.iterrows() if st.session_state.get(f'chk_{r["본인고객ID"]}')]

        if st.button(f"📦 ZIP 다운로드 ({len(sel)}명)", type="primary", disabled=len(sel) == 0):
            with st.spinner(f"{len(sel)}명 카드 생성 중..."):
                buf = io.BytesIO()
                with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
                    for cid, nm, br, ag, fm in sel:
                        info = {'대리점설계사명': nm, '지점조직명': br, '대리점지사명': ag, '영업가족명': fm}
                        png = render_card_bytes(cid, info)
                        if png:
                            fname = re.sub(r'[\\/:*?"<>|]', '_', f"{nm}_{br}.png")
                            zf.writestr(fname, png)
                buf.seek(0)
            st.download_button(f"⬇️ ZIP 받기 ({len(sel)}명)", buf,
                              f"시상안내_{mgr_name}_{datetime.now():%Y%m%d}.zip", "application/zip")


if st.session_state.get('selected_card'):
    cid, name, branch, agency, family = st.session_state['selected_card']
    st.markdown("---")
    st.markdown(f"### {name} 팀장님 카드뉴스")
    with st.spinner("카드 생성 중..."):
        info = {'대리점설계사명': name, '지점조직명': branch, '대리점지사명': agency, '영업가족명': family}
        png = render_card_bytes(cid, info)
    if png:
        c1, c2 = st.columns([2, 1])
        with c1: st.image(png, use_container_width=True)
        with c2:
            st.download_button("📥 PNG 다운로드", png, f"{name}_{branch}_시상안내.png", "image/png",
                             use_container_width=True, key=f"dl_{cid}")
            contacts = load_contacts()
            mgr = (get_agent_data(cid).get('PRIZE_SUM') or {}).get('지원매니저명', '') or ''
            mi = contacts.get(mgr)
            if mi:
                st.markdown(f"""
                <a href='tel:{mi['phone'].replace('-','')}' style='text-decoration:none;'>
                <div style='background:#d6162e;color:#fff;padding:16px 20px;border-radius:10px;text-align:center;font-weight:900;margin-top:10px;font-size:18px;'>
                📞 {mgr} 매니저님<br><span style='font-size:22px;'>{mi['phone']}</span>
                </div></a>""", unsafe_allow_html=True)
            st.markdown("**💬 카톡 메시지**")
            st.code(build_kakao_msg(cid, name, branch), language='text')
