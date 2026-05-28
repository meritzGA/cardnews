"""특정 매니저 산하 설계사의 카드 일괄 생성"""
import sys, time
sys.path.insert(0, '/sessions/charming-fervent-newton/mnt/outputs')
from extract_agent_data import _load, get_agent_data, build_card_context
from scheme_engine import find_scheme_for_agency, calculate_scheme_rewards
from card_template import build_html
from render_png import html_to_png
from pathlib import Path

CARDS_DIR = Path('/sessions/charming-fervent-newton/mnt/GA설계사 시상 안내 카드뉴스/cards')
CARDS_DIR.mkdir(exist_ok=True)


def main(mgr_code):
    df = _load('PRIZE_SUM')
    target = df[df['지원매니저코드'] == mgr_code]
    if len(target) == 0:
        print(f"매니저 코드 {mgr_code} 산하 설계사 없음")
        return
    mgr_name = target['지원매니저명'].iloc[0]
    print(f"[{mgr_name}] 매니저 산하 {len(target)}명 카드 생성")

    for i, row in enumerate(target.itertuples(index=False), 1):
        cid = row.본인고객ID
        out = CARDS_DIR / f"{cid}.png"
        if out.exists():
            print(f"  [{i}] {row.대리점설계사명} skip (이미 있음)")
            continue
        info = {
            '대리점설계사명': row.대리점설계사명,
            '지점조직명': row.지점조직명,
            '대리점지사명': row.대리점지사명,
            '영업가족명': row.영업가족명,
        }
        data = get_agent_data(cid)
        ctx = build_card_context(data)
        scheme = find_scheme_for_agency(info['영업가족명'])
        scheme_rewards = calculate_scheme_rewards(scheme, data) if scheme else None
        html = build_html(ctx, scheme_rewards=scheme_rewards)
        tmp_html = Path(f'/sessions/charming-fervent-newton/mnt/outputs/_mgr_{cid}.html')
        tmp_html.write_text(html, encoding='utf-8')
        html_to_png(str(tmp_html), str(out))
        print(f"  [{i}/{len(target)}] {row.대리점설계사명}")
    print(f"\n=== {mgr_name} 매니저 완료 ===")


if __name__ == '__main__':
    mgr_code = sys.argv[1] if len(sys.argv) > 1 else '320010476'  # 최효선
    main(mgr_code)
