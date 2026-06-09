"""GA3본부 산하 카드 멀티프로세스 생성 — 최적화 버전.
- device_scale_factor=1 (해상도 1/4)
- 페이지 사이즈 고정 (trim 제거)
- wait_for_load_state 최소화

사용법:
  python gen_parallel.py                # ver2 기본, 4워커 (부족분 독려 - 화~금)
  python gen_parallel.py 6               # ver2, 6워커
  python gen_parallel.py 4 ver1          # ver1 (지난주 결과 - 월요일)
  python gen_parallel.py 4 ver2          # ver2 명시
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed

# 인자 파싱
WORKERS = int(sys.argv[1]) if len(sys.argv) > 1 else 4
VERSION = sys.argv[2] if len(sys.argv) > 2 else 'ver2'
assert VERSION in ('ver1', 'ver2'), "version은 ver1 또는 ver2"

BASE_DIR = Path(__file__).resolve().parent / "cards_v2"
CARDS_DIR = BASE_DIR / VERSION
CARDS_DIR.mkdir(parents=True, exist_ok=True)


def render_chunk(chunk, version='ver2'):
    from playwright.sync_api import sync_playwright
    from extract_agent_data import get_agent_data, build_card_context
    from scheme_engine import find_scheme_for_agency, calculate_scheme_rewards
    from card_template import build_html, build_html_ver1

    cards_dir = Path(__file__).resolve().parent / "cards_v2" / version
    ok = 0
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx_p = browser.new_context(
            viewport={'width': 1080, 'height': 2400},
            device_scale_factor=1,
        )
        for cid, info in chunk:
            try:
                out = cards_dir / f"{cid}.png"
                data = get_agent_data(cid)
                if not data.get('PRIZE_SUM'): continue
                ctx = build_card_context(data)

                if version == 'ver1':
                    # 월요일 - 지난주 결과 (1주차)
                    html = build_html_ver1(ctx, prev_week=1)
                else:
                    # 화~금 - 부족분 독려
                    scheme = find_scheme_for_agency(info.get('영업가족명', ''))
                    sr = calculate_scheme_rewards(scheme, data) if scheme else None
                    html = build_html(ctx, scheme_rewards=sr)

                page = ctx_p.new_page()
                page.set_content(html, wait_until='domcontentloaded')
                h = page.evaluate('''() => {
                    const wrap = document.querySelector('.wrap');
                    if (wrap) return wrap.getBoundingClientRect().height;
                    return document.body.scrollHeight;
                }''')
                h = int(h) + 20
                page.set_viewport_size({'width': 1080, 'height': h})
                page.screenshot(path=str(out), clip={'x':0,'y':0,'width':1080,'height':h}, type='png')
                page.close()
                ok += 1
            except Exception as e:
                pass
        ctx_p.close()
        browser.close()
    return ok


def main():
    from extract_agent_data import _load
    df = _load('PRIZE_SUM')
    mgr_hq = df.groupby('지원매니저코드').agg(hq=('지역단조직명', lambda x: x.mode().iloc[0] if len(x.mode()) else None))
    ga3 = mgr_hq[mgr_hq['hq'] == 'GA3본부'].index.tolist()
    target = df[df['지원매니저코드'].isin(ga3) & (df['실적계'] >= 100000)].drop_duplicates(subset=['본인고객ID'])
    existing = {p.stem for p in CARDS_DIR.glob('*.png')}
    target = target[~target['본인고객ID'].isin(existing)]
    total = len(target)
    print(f"[{VERSION}] 출력: {CARDS_DIR}")
    print(f"기존: {len(existing)}장, 신규: {total}명, 워커: {WORKERS}")
    if total == 0: return

    agents = [(r['본인고객ID'], {
        '대리점설계사명': r['대리점설계사명'], '지점조직명': r['지점조직명'],
        '대리점지사명': r['대리점지사명'], '영업가족명': r['영업가족명'],
    }) for _, r in target.iterrows()]

    chunk_size = max(1, len(agents) // WORKERS + 1)
    chunks = [agents[i:i+chunk_size] for i in range(0, len(agents), chunk_size)]
    t0 = time.time()
    total_ok = 0
    with ProcessPoolExecutor(max_workers=WORKERS) as ex:
        futures = [ex.submit(render_chunk, c, VERSION) for c in chunks]
        for i, fut in enumerate(as_completed(futures), 1):
            ok = fut.result()
            total_ok += ok
            elapsed = time.time() - t0
            print(f"  worker {i}/{WORKERS} 완료: +{ok}장  누적 {total_ok}  ({total_ok/elapsed:.1f}/s)", flush=True)

    print(f"\n=== [{VERSION}] 완료: {total_ok}/{total}장, {(time.time()-t0)/60:.1f}분 ===")


if __name__ == '__main__':
    main()
