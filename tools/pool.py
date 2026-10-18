"""기출 풀 인덱스 생성: 문항별 (시험, 번호, 과목, PDF, 페이지)를 pool.csv로 저장."""
import csv, glob, os, re, sys
import pymupdf

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "exams")
OUT = os.path.join(os.path.dirname(__file__), "..", "pool.csv")
SECS = {"확률과 통계": "확통", "미적분": "미적분", "기하": "기하"}


def section_of(text):
    m = re.search(r"\((미적분|확률과 통계|기하)\)\s*(?:홀수형\s*)?\d", text)
    return SECS[m.group(1)] if m else "공통"


def main():
    rows = []
    for f in sorted(glob.glob(os.path.join(SRC, "[0-9][0-9][0-9][0-9].pdf"))):
        exam = os.path.basename(f)[:4]
        doc = pymupdf.open(f)
        for pno, page in enumerate(doc, 1):
            text = page.get_text()
            sec = section_of(text)
            if sec == "기하":
                continue
            lo, hi = (1, 22) if sec == "공통" else (23, 30)
            nums = sorted({int(n) for n in re.findall(r"(?m)^\s*(\d{1,2})\.\s", text) if lo <= int(n) <= hi})
            for n in nums:
                rows.append({"id": f"{exam}_{n:02d}" + ("" if sec in ("공통", "미적분") else "_확통"),
                             "exam": exam, "num": n, "subject": sec, "pdf": os.path.basename(f), "page": pno})
    seen = {}
    for r in rows:
        seen.setdefault(r["id"], r)
    with open(OUT, "w", newline="", encoding="utf-8") as fp:
        w = csv.DictWriter(fp, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(seen.values())
    by = {}
    for r in seen.values():
        by.setdefault((r["exam"], r["subject"]), []).append(r["num"])
    for (e, s), ns in sorted(by.items()):
        exp = 22 if s == "공통" else 8
        print(e, s, len(ns), "" if len(ns) == exp else f"MISSING {sorted(set(range(1 if s=='공통' else 23, 23 if s=='공통' else 31)) - set(ns))}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
