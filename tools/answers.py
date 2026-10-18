"""answers.csv 생성: 로컬 해설 PDF의 정답표에서 문항별 정답을 뽑는다(해설 PDF 자체는 레포에 올리지 않는다).

  python tools/answers.py
"""
import csv, os, re, sys
import pymupdf

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SOL_DIR = os.environ.get("SUNEUNG_SOL_DIR", r"G:\내 드라이브\과외\수능 수학\평가원 기출 모음")
SEC_RE = {"미적분": r"선택\s*:?\s*미적분", "확통": r"선택\s*:?\s*확률과\s*통계"}
CIRCLE = str.maketrans("⓵⓶⓷⓸⓹", "①②③④⑤")
# 일부 해설 PDF는 숫자를 전용 글리프(U+E034~U+E03D)로 넣었다: E034~E03C = 1~9, E03D = 0
DIGITS = str.maketrans({chr(0xE034 + i): str(i + 1) for i in range(9)} | {chr(0xE03D): "0"})

# 2309는 정답표가 이미지라, 2211은 텍스트 순서가 뒤섞여 있어 정답표 이미지를 보고 직접 옮겨 적었다. 2709는 답지가 없다.
MANUAL = {
    "2211": {
        "공통": "② ⑤ ⑤ ④ ① ③ ① ① ④ ⑤ ③ ③ ② ③ ② 3 4 12 6 110 678 9".split(),
        "미적분": "⑤ ④ ② ③ ① ② 11 143".split(),
    },
    "2309": {
        "공통": "④ ① ② ① ③ ⑤ ⑤ ① ③ ④ ② ② ⑤ ⑤ ③ 7 16 13 4 80 220 58".split(),
        "확통": "① ③ ④ ② ⑤ ③ 175 260".split(),
        "미적분": "① ② ⑤ ③ ③ ④ 3 283".split(),
    },
}


# 정답표 텍스트의 배치가 어긋나 잘못 뽑히던 문항(해설 본문의 정답과 교차 확인 후 정답표 이미지로 확정)
FIXES = {"2311_12": "②", "2311_22": "13", "2406_06": "④", "2411_11": "①", "2511_12": "①", "2611_04": "③"}


def from_solution(text, subject, num):
    i = 0
    if subject != "공통":
        m = re.search(SEC_RE[subject], text)
        if not m:
            return None
        i = m.start()
    key = f"{num:02d}" if num < 10 else str(num)
    m = re.search(rf"(?<!\d){key}\.\s*([①②③④⑤⓵⓶⓷⓸⓹]|\d+)", text[i:])
    return m.group(1).translate(CIRCLE) if m else None


def main():
    with open(os.path.join(ROOT, "pool.csv"), encoding="utf-8") as fp:
        pool = list(csv.DictReader(fp))
    texts, rows = {}, []
    for r in pool:
        exam, subject, num = r["exam"], r["subject"], int(r["num"])
        ans, src = None, ""
        if exam in MANUAL:
            first = 1 if subject == "공통" else 23
            ans, src = MANUAL[exam][subject][num - first], "정답표(수기 입력)"
        else:
            p = os.path.join(SOL_DIR, f"{exam} 해설.pdf")
            if os.path.exists(p):
                if exam not in texts:
                    texts[exam] = "".join(pg.get_text() for pg in pymupdf.open(p)).translate(DIGITS)
                ans, src = from_solution(texts[exam], subject, num), "해설 정답표"
        if r["id"] in FIXES:
            ans, src = FIXES[r["id"]], "정답표 이미지 확인"
        rows.append({"id": r["id"], "answer": ans or "", "source": src if ans else "없음"})
    with open(os.path.join(ROOT, "answers.csv"), "w", newline="", encoding="utf-8") as fp:
        w = csv.DictWriter(fp, fieldnames=["id", "answer", "source"])
        w.writeheader()
        w.writerows(rows)
    missing = [r["id"] for r in rows if not r["answer"]]
    print(f"{len(rows)}문항 중 정답 {len(rows) - len(missing)}개, 없음 {len(missing)}개")
    print("없음(시험별):", sorted({m[:4] for m in missing}))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
