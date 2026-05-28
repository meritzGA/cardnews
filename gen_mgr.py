"""특정 매니저(들) 산하 카드 생성. 빠른 단일 호출용.
사용: python gen_mgr.py {매니저코드1} [{매니저코드2} ...]
     python gen_mgr.py --ga3   # GA3본부 산하 매니저 전체 (배치당)
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract_agent_data import _load
from generate_fast import process_batch
from pathlib import Path

CARDS_DIR = Path('/sessions/charming-fervent-newton/mnt/GA설계사 시상 안내 카드뉴스/cards')


def main():
    df = _load('PRIZE_SUM')

    if len(sys.argv) < 2:
        print("사용: python gen_mgr.py {매니저코드} [{매니저코드}...]")
        print("     python gen_mgr.py --ga3 [N]   # GA3본부 신규 N명만")
        return

    if sys.argv[1] == '--ga3':
        N = int(sys.argv[2]) if len(sys.argv) > 2 else 200
        ga3 = df[(df['지역단조직명'] == 'GA3본부') | (df['본점관리조직명'] == 'GA3본부')]
        target = ga3[ga3['실적계'] >= 100000]
        existing = {p.stem for p in CARDS_DIR.glob('*.png')}
        target = target[~target['본인고객ID'].isin(existing)].head(N)
        print(f"GA3본부 신규 {len(target)}명")
    else:
        codes = sys.argv[1:]
        target = df[df['지원매니저코드'].isin(codes)]
        target = target[target['실적계'] >= 100000]
        existing = {p.stem for p in CARDS_DIR.glob('*.png')}
        target = target[~target['본인고객ID'].isin(existing)]
        print(f"매니저 {codes} 산하 신규 {len(target)}명")

    if len(target) == 0:
        print("생성할 카드 없음")
        return

    agents = [(r['본인고객ID'], {
        '대리점설계사명': r['대리점설계사명'], '지점조직명': r['지점조직명'],
        '대리점지사명': r['대리점지사명'], '영업가족명': r['영업가족명']})
        for _, r in target.iterrows()]

    BATCH = 25
    batches = [agents[i:i+BATCH] for i in range(0, len(agents), BATCH)]
    t0 = time.time()
    total = 0
    for i, b in enumerate(batches):
        ts = time.time()
        ok = process_batch(9000+i, b)
        total += ok
        print(f"  batch {i+1}/{len(batches)}: +{ok}장 ({time.time()-ts:.1f}s) → 누적 {total}/{len(agents)}", flush=True)
    print(f"\n완료: {total}장, {(time.time()-t0)/60:.1f}분")


if __name__ == '__main__':
    main()
