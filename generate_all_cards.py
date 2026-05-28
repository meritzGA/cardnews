"""
시상금이 있는 모든 설계사의 카드 PNG를 일괄 생성.
- D폴더 cards/ 에 저장
- 파일명: {본인고객ID}.png (Streamlit 앱에서 ID로 찾음)
"""
import sys, re, time
sys.path.insert(0, '/sessions/charming-fervent-newton/mnt/outputs')
from extract_agent_data import _load, get_agent_data, build_card_context
from scheme_engine import find_scheme_for_agency, calculate_scheme_rewards
from card_template import build_html
from render_png import html_to_png
from pathlib import Path

CARDS_DIR = Path('/sessions/charming-fervent-newton/mnt/GA설계사 시상 안내 카드뉴스/cards')
CARDS_DIR.mkdir(exist_ok=True)
TMP_DIR = Path('/sessions/charming-fervent-newton/mnt/outputs')


def render_one(cid, info):
    data = get_agent_data(cid)
    if not data.get('PRIZE_SUM'):
        return None
    ctx = build_card_context(data)
    scheme = find_scheme_for_agency(info.get('영업가족명', ''))
    scheme_rewards = calculate_scheme_rewards(scheme, data) if scheme else None
    html = build_html(ctx, scheme_rewards=scheme_rewards)
    tmp_html = TMP_DIR / f"_batch_{cid}.html"
    tmp_html.write_text(html, encoding='utf-8')
    out = CARDS_DIR / f"{cid}.png"
    if out.exists():
        return out  # 이미 생성됨, skip
    html_to_png(str(tmp_html), str(out))
    return out


def main(limit=None):
    df = _load('PRIZE_SUM')
    br = _load('BRIDGE')
    br_map = br.set_index('본인고객ID')['시상금합계'].to_dict() if '시상금합계' in br.columns else {}
    df = df.copy()
    df['_brsum'] = df['본인고객ID'].map(lambda x: br_map.get(x, 0) or 0)
    df['확정시상'] = df['추가13회예정금계'].fillna(0) + df['_brsum'].fillna(0)

    # 시상금이 있는 사람만
    target = df[df['확정시상'] > 0].copy()
    if limit:
        target = target.head(limit)

    print(f"대상: {len(target)}명")
    t_start = time.time()
    ok, skip, fail = 0, 0, 0
    for i, row in enumerate(target.itertuples(index=False), 1):
        cid = row.본인고객ID
        out = CARDS_DIR / f"{cid}.png"
        if out.exists():
            skip += 1
            continue
        info = {
            '대리점설계사명': row.대리점설계사명,
            '지점조직명': row.지점조직명,
            '대리점지사명': row.대리점지사명,
            '영업가족명': row.영업가족명,
        }
        try:
            render_one(cid, info)
            ok += 1
        except Exception as e:
            fail += 1
            print(f"  [{i}] {row.대리점설계사명} 실패: {e}")
        if i % 50 == 0:
            elapsed = time.time() - t_start
            rate = ok / elapsed if elapsed else 0
            eta = (len(target) - i) / rate if rate else 0
            print(f"  [{i}/{len(target)}] ok={ok} skip={skip} fail={fail}  {rate:.1f}건/초  남은 시간 {eta/60:.1f}분")
    print(f"\n=== 완료: ok={ok}, skip={skip}, fail={fail}, 총 {time.time()-t_start:.0f}초 ===")


if __name__ == '__main__':
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    main(limit)
