"""문항 명세(JSON)를 평가원 문제지 모양의 PDF로 조판한다. HTML + KaTeX를 Chromium(playwright)으로 인쇄한다.

  python tools/typeset.py mock/M001_r1.json mock/M001_r1.pdf

필요한 것(레포 밖):
  - KaTeX: `npm pack katex@0.16.11` 후 풀어서 환경변수 KATEX_DIR(= .../package/dist)로 지정
  - 한글 폰트: koreanize-matplotlib의 NanumGothic (pip install koreanize-matplotlib) 또는 KOREAN_FONT로 ttf 경로 지정
  - node + playwright(전역) + Chromium (/opt/pw-browsers)

명세 형식:
{
  "title": "...", "subtitle": "...", "note": "...",
  "sections": [
    {"heading": "5지선다형", "problems": [
      {"label": "12", "tag": "(D018)", "points": 4, "body": "<p>...$a\\sin bx$...</p>",
       "conditions": ["(가) ...", "(나) ..."], "box": "<p>빈칸 서술</p>",
       "question": "a × b의 값은?", "choices": ["20", "24", ...], "answer": "④"}
    ]}
  ]
}
body·conditions·box·question·choices 안의 수식은 $...$ (인라인) 또는 $$...$$ (별행)로 쓴다.
"""
import json, os, re, subprocess, sys, glob, html, tempfile

KATEX = os.environ.get("KATEX_DIR") or next(iter(glob.glob("/tmp/claude-0/*/*/scratchpad/pkgs/package/dist")), "")
FONT = os.environ.get("KOREAN_FONT") or next(iter(glob.glob("/usr/local/lib/python3*/dist-packages/koreanize_matplotlib/fonts/NanumGothic.ttf")), "")
FONT_B = FONT.replace("NanumGothic.ttf", "NanumGothicBold.ttf")
CIRCLED = "①②③④⑤"

CSS = """
@font-face{font-family:NG;src:url("file://%(font)s");font-weight:400}
@font-face{font-family:NG;src:url("file://%(fontb)s");font-weight:700}
@page{size:A4;margin:22mm 14mm 18mm 14mm}
html,body{margin:0;padding:0}
body{font-family:NG,serif;font-size:10.6pt;line-height:1.62;color:#111}
.katex{font-size:1.06em}
.sheet-title{text-align:center;border:1.2px solid #000;padding:5px 0;font-size:13pt;font-weight:700;letter-spacing:.3em;margin-bottom:3mm}
.sheet-sub{display:flex;justify-content:space-between;font-size:9pt;margin-bottom:4mm;color:#333}
.cols{column-count:2;column-gap:9mm;column-rule:1px solid #000;column-fill:auto}
.sec{font-weight:700;text-align:center;margin:2mm 0 4mm;break-after:avoid}
.prob{break-inside:avoid;margin-bottom:12mm}
.num{font-weight:700;font-size:11.2pt;margin-right:.35em}
.prob p{margin:0 0 .9em 0;text-align:justify}
.disp{text-align:center;margin:.7em 0 .9em}
.cond{border:1px solid #000;padding:.55em .9em .35em;margin:.6em 0 1em}
.cond p{margin:0 0 .45em}
.blankbox{border:1px solid #000;padding:.6em .9em .3em;margin:.6em 0 1em}
.blank{display:inline-block;border:1px solid #000;padding:0 .5em;min-width:2.2em;text-align:center;line-height:1.5}
.choices{display:flex;flex-wrap:wrap;gap:.3em 1.6em;margin-top:.5em}
.choices span{white-space:nowrap}
.pts{white-space:nowrap}
.tag{font-size:8pt;color:#777;margin-left:.6em;font-weight:400}
.key{break-before:page}
.key table{border-collapse:collapse;margin-top:3mm}
.key td,.key th{border:1px solid #000;padding:3px 10px;text-align:center}
.note{font-size:8.5pt;color:#555;margin:0 0 4mm}
"""

JS = """
document.addEventListener("DOMContentLoaded", function(){
  renderMathInElement(document.body, {delimiters:[{left:"$$",right:"$$",display:true},{left:"$",right:"$",display:false}],
    throwOnError:false, strict:false});
  window.__done = true;
});
"""

MATH = re.compile(r"\$\$.*?\$\$|\$.*?\$", re.S)

def esc_math(text):
    """수식 안의 <, >를 HTML 엔티티로 바꾼다(브라우저가 <k 같은 것을 태그로 읽지 않게)."""
    return MATH.sub(lambda m: m.group(0).replace("<", "&lt;").replace(">", "&gt;"), text)

def prob_html(p):
    p = {k: (esc_math(v) if isinstance(v, str) else [esc_math(x) for x in v] if isinstance(v, list) else v) for k, v in p.items()}
    out = [f'<div class="prob"><p><span class="num">{html.escape(str(p["label"]))}.</span>']
    body = p.get("body", "").strip()
    # 첫 <p>를 번호 뒤에 붙인다
    if body.startswith("<p>"):
        out[-1] += body[3:]
        body = ""
    else:
        out[-1] += "</p>" + body
        body = ""
    out.append(body)
    if p.get("conditions"):
        out.append('<div class="cond">' + "".join(f"<p>{c}</p>" for c in p["conditions"]) + "</div>")
    if p.get("box"):
        out.append('<div class="blankbox">' + p["box"] + "</div>")
    q = p.get("question", "")
    if q:
        pts = f' <span class="pts">[{p.get("points", 4)}점]</span>' if p.get("points") else ""
        out.append(f"<p>{q}{pts}</p>")
    if p.get("choices"):
        out.append('<div class="choices">' + "".join(f"<span>{CIRCLED[i]} {c}</span>" for i, c in enumerate(p["choices"])) + "</div>")
    if p.get("tag"):
        out.append(f'<p class="tag">{html.escape(p["tag"])}</p>')
    out.append("</div>")
    return "\n".join(out)

def build(spec):
    parts = [f'<!doctype html><html lang="ko"><head><meta charset="utf-8">',
             f'<link rel="stylesheet" href="file://{KATEX}/katex.min.css">',
             f'<script src="file://{KATEX}/katex.min.js"></script>',
             f'<script src="file://{KATEX}/contrib/auto-render.min.js"></script>',
             f"<style>{CSS % dict(font=FONT, fontb=FONT_B)}</style><script>{JS}</script></head><body>"]
    parts.append(f'<div class="sheet-title">{html.escape(spec.get("title", "수학 영역"))}</div>')
    parts.append(f'<div class="sheet-sub"><span>{html.escape(spec.get("subtitle", ""))}</span><span>{html.escape(spec.get("right", ""))}</span></div>')
    if spec.get("note"):
        parts.append(f'<p class="note">{spec["note"]}</p>')
    parts.append('<div class="cols">')
    for sec in spec["sections"]:
        if sec.get("heading"):
            parts.append(f'<div class="sec">{html.escape(sec["heading"])}</div>')
        for p in sec["problems"]:
            parts.append(prob_html(p))
    parts.append("</div>")
    # 정답표
    rows = [(p["label"], p.get("answer", "")) for sec in spec["sections"] for p in sec["problems"] if p.get("answer")]
    if rows:
        parts.append('<div class="key"><div class="sheet-title">정답</div><table><tr>' + "".join(f"<th>{html.escape(str(l))}</th>" for l, _ in rows) + "</tr><tr>" + "".join(f"<td>{a}</td>" for _, a in rows) + "</tr></table></div>")
    parts.append("</body></html>")
    return "\n".join(parts)

NODE = r"""
const { chromium } = require('playwright');
(async () => {
  const [,, inp, out, head] = process.argv;
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto('file://' + inp, { waitUntil: 'load' });
  await page.waitForFunction(() => window.__done === true, null, { timeout: 20000 });
  await page.waitForTimeout(300);
  await page.pdf({ path: out, format: 'A4', printBackground: true, preferCSSPageSize: true,
    displayHeaderFooter: true,
    headerTemplate: '<div style="width:100%;font-size:8pt;color:#444;padding:0 14mm;display:flex;justify-content:space-between;font-family:sans-serif"><span>' + head + '</span><span>수학 영역</span></div>',
    footerTemplate: '<div style="width:100%;text-align:center;font-size:8pt;color:#444;font-family:sans-serif"><span class="pageNumber"></span> / <span class="totalPages"></span></div>' });
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
"""

def main():
    spec_path, out_pdf = sys.argv[1], sys.argv[2]
    if not KATEX or not FONT:
        sys.exit(f"KATEX_DIR({KATEX!r}) 또는 한글 폰트({FONT!r})를 찾을 수 없다")
    spec = json.load(open(spec_path, encoding="utf-8"))
    out_html = os.path.join(tempfile.mkdtemp(prefix="typeset_"), "sheet.html")
    open(out_html, "w", encoding="utf-8").write(build(spec))
    js = os.path.join(os.path.dirname(out_html), "_render.js")
    open(js, "w").write(NODE)
    env = dict(os.environ, NODE_PATH=subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip())
    subprocess.run(["node", js, out_html, os.path.abspath(out_pdf), spec.get("subtitle", "")], check=True, env=env)
    os.remove(js)
    print("wrote", out_pdf)

if __name__ == "__main__":
    main()
