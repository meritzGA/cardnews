"""GA3본부 산하 매니저들의 실적 10만원+ 설계사 카드 일괄 생성"""
import sys, os, time, subprocess, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract_agent_data import _load, get_agent_data, build_card_context
from scheme_engine import find_scheme_for_agency, calculate_scheme_rewards
from card_template import build_html
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from PIL import Image, ImageChops

CARDS_DIR = Path('/sessions/charming-fervent-newton/mnt/GA설계사 시상 안내 카드뉴스/cards')
CARDS_DIR.mkdir(exist_ok=True)
TMP_DIR = Path('/sessions/charming-fervent-newton/mnt/outputs/_batch_tmp')
TMP_DIR.mkdir(exist_ok=True)

BATCH_SIZE = 30
TARGET_W = 1080


def _trim(img, target_width=TARGET_W):
    bg_color = img.getpixel((0, 0))
    bg = Image.new(img.mode, img.size, bg_color)
    bbox = ImageChops.difference(img, bg).getbbox()
    if bbox:
        pad = 24
        l, t, r, b = bbox
        img = img.crop((max(0, l-pad), max(0, t-pad),
                        min(img.width, r+pad), min(img.height, b+pad)))
    if img.width != target_width:
        ratio = target_width / img.width
        img = img.resize((target_width, int(img.height * ratio)), Image.LANCZOS)
    return img


def process_batch(batch_idx, agents_batch):
    from weasyprint import HTML
    htmls = []
    cids = []
    for cid, info in agents_batch:
        out_path = CARDS_DIR / f"{cid}.png"
        if out_path.exists():
            continue
        try:
            data = get_agent_data(cid)
            if not data.get('PRIZE_SUM'):
                continue
            ctx = build_card_context(data)
            scheme = find_scheme_for_agency(info.get('영업가족명', ''))
            sr = calculate_scheme_rewards(scheme, data) if scheme else None
            htmls.append(build_html(ctx, scheme_rewards=sr))
            cids.append(cid)
        except Exception as e:
            print(f"  [b{batch_idx}] {cid} 컨텍스트 실패: {e}", flush=True)

    if not htmls:
        return 0

    # 각 HTML의 body 추출, head는 첫 카드 사용
    head = htmls[0].split('<head>')[1].split('</head>')[0]
    bodies = []
    for h in htmls:
        body = h.split('<body>')[1].split('</body>')[0]
        bodies.append(f'<div style="page-break-after: always;">{body}</div>')

    full_html = f"<!DOCTYPE html><html lang='ko'><head>{head}</head><body>{''.join(bodies)}</body></html>"
    tmp_html = TMP_DIR / f"b{batch_idx}.html"
    tmp_html.write_text(full_html, encoding='utf-8')
    pdf_path = TMP_DIR / f"b{batch_idx}.pdf"
    try:
        HTML(str(tmp_html)).write_pdf(str(pdf_path))
    except Exception as e:
        print(f"  [b{batch_idx}] PDF 실패: {e}", flush=True)
        return 0

    prefix = TMP_DIR / f"b{batch_idx}_p"
    for old in glob.glob(f"{prefix}-*.png"):
        try: os.remove(old)
        except: pass
    subprocess.run(['pdftoppm', '-r', '108', '-png', str(pdf_path), str(prefix)], check=True)
    def _page_num(p):
        import re as _re
        m = _re.search(r"-(\d+)\.png$", p)
        return int(m.group(1)) if m else 0
    pngs = sorted(glob.glob(f"{prefix}-*.png"), key=_page_num)

    ok = 0
    for cid, png in zip(cids, pngs):
        try:
            img = Image.open(png).convert('RGB')
            img = _trim(img, TARGET_W)
            img.save(CARDS_DIR / f"{cid}.png", 'PNG', optimize=True)
            ok += 1
        except Exception as e:
            print(f"  [b{batch_idx}] {cid} PNG 실패: {e}", flush=True)

    try: tmp_html.unlink()
    except: pass
    try: pdf_path.unlink()
    except: pass
    for p in pngs:
        try: os.remove(p)
        except: pass
    return ok


def main():
    df = _load('PRIZE_SUM')
    # GA3본부 산하 + 실적 10만+
    ga3 = df[(df['지역단조직명'] == 'GA3본부') | (df['본점관리조직명'] == 'GA3본부')]
    target = ga3[ga3['실적계'] >= 100000].copy()
    print(f"GA3본부 산하 실적 10만+: {len(target):,}명", flush=True)

    existing = {p.stem for p in CARDS_DIR.glob('*.png')}
    target = target[~target['본인고객ID'].isin(existing)]
    print(f"신규 생성: {len(target):,}명 (이미 있음 {len(existing):,}장)", flush=True)

    if len(target) == 0:
        print("생성할 카드 없음")
        return

    agents = [(r['본인고객ID'], {
        '대리점설계사명': r['대리점설계사명'],
        '지점조직명': r['지점조직명'],
        '대리점지사명': r['대리점지사명'],
        '영업가족명': r['영업가족명'],
    }) for _, r in target.iterrows()]

    batches = [agents[i:i+BATCH_SIZE] for i in range(0, len(agents), BATCH_SIZE)]
    print(f"배치 수: {len(batches)} (배치당 {BATCH_SIZE}명)", flush=True)

    workers = max(2, os.cpu_count() or 2)
    print(f"병렬 워커: {workers}개", flush=True)
    t0 = time.time()
    total_ok = 0

    with ProcessPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(process_batch, i, b): i for i, b in enumerate(batches)}
        done = 0
        for fut in as_completed(futures):
            i = futures[fut]
            try:
                ok = fut.result()
                total_ok += ok
            except Exception as e:
                print(f"  [b{i}] 실패: {e}", flush=True)
            done += 1
            elapsed = time.time() - t0
            rate = total_ok / elapsed if elapsed else 0
            remain = (len(agents) - total_ok) / rate if rate else 0
            print(f"  [{done}/{len(batches)} 배치] 누적 {total_ok}장 · {rate:.2f}장/초 · ETA {remain/60:.1f}분", flush=True)

    print(f"\n=== 완료: {total_ok}장, 총 {(time.time()-t0)/60:.1f}분 ===", flush=True)


if __name__ == '__main__':
    main()
