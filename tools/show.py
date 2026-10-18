"""기출 문항 페이지를 cache/에 PNG로 렌더링하고 정답(answers.csv)을 출력한다.

  python tools/show.py 2611_21            # 문제 페이지
  python tools/show.py 2611_21 --sol      # 해설 페이지도 렌더링 (로컬에 해설 PDF가 있을 때만)
"""
import argparse, csv, os, re, sys
import pymupdf

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
EXAMS = os.path.join(ROOT, "exams")
# 해설(EBS) PDF는 레포에 없다. 로컬 경로가 있을 때만 --sol이 동작한다.
SOL_DIR = os.environ.get("SUNEUNG_SOL_DIR", r"G:\내 드라이브\과외\수능 수학\평가원 기출 모음")
SEC_TAG = {"공통": "공통", "미적분": "선택: 미적분", "확통": "선택: 확률과 통계"}


def answer(pid):
    with open(os.path.join(ROOT, "answers.csv"), encoding="utf-8") as fp:
        row = next((r for r in csv.DictReader(fp) if r["id"] == pid), None)
    return (row["answer"] or None, row["source"]) if row else (None, "없음")


def sol_pages(path, subject, num):
    doc = pymupdf.open(path)
    start = 0
    if subject != "공통":
        for i, pg in enumerate(doc):
            if SEC_TAG[subject] in pg.get_text():
                start = i
                break
    hits = []
    for i in range(start, len(doc)):
        if re.search(rf"(?m)^\s*{num}\.\s*출제의도", doc[i].get_text()):
            hits.append(i)
            break
    return doc, (hits + [hits[0] + 1] if hits and hits[0] + 1 < len(doc) else hits)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("id")
    ap.add_argument("--sol", action="store_true")
    a = ap.parse_args()
    with open(os.path.join(ROOT, "pool.csv"), encoding="utf-8") as fp:
        row = next(r for r in csv.DictReader(fp) if r["id"] == a.id)
    num, page = int(row["num"]), int(row["page"])
    os.makedirs(os.path.join(ROOT, "cache"), exist_ok=True)
    doc = pymupdf.open(os.path.join(EXAMS, row["pdf"]))
    out = os.path.join(ROOT, "cache", f"{a.id}.png")
    doc[page - 1].get_pixmap(dpi=170).save(out)
    print("문제:", os.path.abspath(out))
    ans, src = answer(a.id)
    print("정답:", ans if ans else "(확인 불가)", "|", src)
    path = os.path.join(SOL_DIR, f"{row['exam']} 해설.pdf")
    if a.sol and os.path.exists(path):
        sdoc, pages = sol_pages(path, row["subject"], num)
        for k, i in enumerate(pages):
            o = os.path.join(ROOT, "cache", f"{a.id}_sol{k + 1}.png")
            sdoc[i].get_pixmap(dpi=150).save(o)
            print("해설:", os.path.abspath(o))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
