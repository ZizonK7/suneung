"""랜덤 추출. 시드와 결과를 draws.log에 남긴다.

  python tools/draw.py problems 5                        # 아직 정리 안 된 기출 문항 5개 (공통·미적분)
  python tools/draw.py cards 5 --from 2706_01,2306_19,...  # 정리한 문항마다 카드 1장씩 + 메인 1장 (D009부터)
  python tools/draw.py main 1                            # 제작 문항의 메인 영역(수1/수2/미적분) 1개
  python tools/draw.py logics 1 --target 공통              # 목표 문항에 허용되는 논리 카드 1개
  python tools/draw.py logics 1 --target 미적분 --area 미적분  # 허용 카드 중 미적분 영역 카드에서만 1개
"""
import argparse, csv, datetime, glob, os, random, re, sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
ALLOWED = {  # 목표 문항 -> 쓸 수 있는 논리 영역
    "공통": {"기초", "수1", "수2"},
    "미적분": {"기초", "수1", "수2", "미적분"},
    "확통": {"기초", "확통"},  # 수1·수2 허용 여부 미정
}
MAIN = ["수1", "수2", "미적분"]  # 제작 문항의 메인 영역 후보
SUBJECTS = {"공통", "미적분"}  # 기출 추출 대상 과목 (확통은 당분간 제외)


def log(line):
    with open(os.path.join(ROOT, "draws.log"), "a", encoding="utf-8") as fp:
        fp.write(f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} {line}\n")


def done_problems():
    return {os.path.basename(p)[:-3] for p in glob.glob(os.path.join(ROOT, "problems", "*.md"))}


def cards():
    out = []
    for p in sorted(glob.glob(os.path.join(ROOT, "logics", "L*.md"))):
        text = open(p, encoding="utf-8").read()
        area = re.search(r"^area:\s*\[(.*?)\]", text, re.M)
        name = re.search(r"^name:\s*(.*)$", text, re.M)
        out.append((os.path.basename(p)[:-3], {a.strip() for a in area.group(1).split(",")} if area else set(),
                    name.group(1).strip() if name else ""))
    return out


def problem_logics(pid):
    text = open(os.path.join(ROOT, "problems", f"{pid}.md"), encoding="utf-8").read()
    m = re.search(r"^logics:\s*\[(.*?)\]", text, re.M)
    return [x.strip() for x in m.group(1).split(",") if x.strip()] if m else []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=["problems", "logics", "main", "cards"])
    ap.add_argument("n", type=int)
    ap.add_argument("--target", choices=list(ALLOWED))
    ap.add_argument("--exclude", default="", help="쉼표로 구분한 제외 ID")
    ap.add_argument("--from", dest="src", default="", help="cards: 쉼표로 구분한 정리된 기출 ID")
    ap.add_argument("--area", help="logics: 영역에 이 값이 들어 있는 카드에서만 뽑는다(보장 추출용)")
    a = ap.parse_args()
    seed = int.from_bytes(os.urandom(4), "big")
    rng = random.Random(seed)
    excl = {x for x in a.exclude.split(",") if x}
    if a.kind == "problems":
        with open(os.path.join(ROOT, "pool.csv"), encoding="utf-8") as fp:
            pool = [r["id"] for r in csv.DictReader(fp) if r["subject"] in SUBJECTS]
        cand = [p for p in pool if p not in done_problems() and p not in excl]
        picked = rng.sample(cand, a.n)
        out = picked
    elif a.kind == "cards":
        info = {c[0]: c for c in cards()}
        src = [x for x in a.src.split(",") if x]
        pairs = []  # (기출, 카드) — 같은 카드가 겹치면 그 기출의 다른 카드로 대신한다
        for pid in src:
            left = [c for c in problem_logics(pid) if c in info and c not in excl and c not in [q for _, q in pairs]]
            if left:
                pairs.append((pid, rng.choice(left)))
        out = [c for _, c in pairs]
        main_card = rng.choice(out)
        # 목표 과목은 메인 카드의 영역으로 정한다(D014부터). 허용되지 않는 카드는 뺀다.
        target = "미적분" if "미적분" in info[main_card][1] else "공통"
        dropped = [c for c in out if not info[c][1] <= ALLOWED[target]]
        log(f"cards from={src} exclude={sorted(excl)} seed={seed} -> {out} main={main_card} target={target} dropped={dropped}")
        print(f"seed={seed} 목표 {target}, 메인 {main_card}" + (f", 영역 밖이라 제외 {dropped}" if dropped else ""))
        for pid, c in pairs:
            print(f"{pid}: {c} [{','.join(sorted(info[c][1]))}] {info[c][2]}" + ("  (제외)" if c in dropped else ""))
        return
    elif a.kind == "main":
        cand = [m for m in MAIN if m not in excl]
        out = picked = rng.sample(cand, a.n)
    else:
        if not a.target:
            sys.exit("--target 필요")
        cand = [c for c in cards() if c[1] and c[1] <= ALLOWED[a.target] and c[0] not in excl
                and (not a.area or a.area in c[1])]
        picked = rng.sample(cand, min(a.n, len(cand)))
        out = [f"{c[0]} [{','.join(sorted(c[1]))}] {c[2]}" for c in picked]
    log(f"{a.kind} n={a.n} target={a.target} area={a.area} exclude={sorted(excl)} seed={seed} pool={len(cand)} -> {[o.split()[0] for o in out]}")
    print(f"seed={seed} 후보 {len(cand)}개")
    print("\n".join(out))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
