#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
答题卡生成器 — SVG + Playwright PDF
将 HTML + SVG 布局转换为像素级精确的 A4 PDF。
"""

import os

# ─── 配置区域（修改这里定制答题卡）──────────────────────────────

PAPERS = {
    '交大': {
        'full': 100, 'time': '90分钟',
        'sections': [
            {'label': '选择题', 'type': 'choice', 'qs': list(range(1, 9)),  'score': 3},
            {'label': '填空题', 'type': 'blank',  'qs': list(range(1, 9)),  'score': 3},
            {'label': '计算题', 'type': 'essay',  'qs': list(range(1, 6)),  'score': 10},
            {'label': '证明题', 'type': 'essay',  'qs': [1],                'score': 6},
        ],
    },
}

# 输出目录
OUT_DIR = './output'

# ─── 内部逻辑（一般无需修改）────────────────────────────────────

CN = ['一', '二', '三', '四', '五', '六', '七', '八']


def essay_h(score):
    """根据分值计算答题框高度（mm）"""
    if score >= 20: return 78
    if score >= 12: return 65
    if score >= 10: return 55
    if score >= 8:  return 46
    if score >= 6:  return 38
    return 32


def build_svg_lines(box_h_mm, line_gap=7, color='#D0D0D0'):
    """
    生成 SVG guide lines。
    关键：viewBox 用 CSS 像素尺寸（= 物理mm × 96dpi/25.4），
    与 Chromium PDF 渲染坐标系完全对齐。
    """
    px_per_mm = 96 / 25.4                          # ≈ 3.78 px/mm
    bh_px     = int(box_h_mm * px_per_mm)           # viewBox 高度
    gap_px    = int(line_gap  * px_per_mm)           # line gap
    sw_px     = max(1.0, px_per_mm * 0.15)           # stroke-width ≈ 0.15mm

    lines = []
    y = gap_px
    while y < bh_px:
        lines.append(
            f'<line x1="0" y1="{y}" x2="100%" y2="{y}" '
            f'stroke="{color}" stroke-width="{sw_px:.1f}" />'
        )
        y += gap_px
    return '\n'.join(lines), bh_px


CSS = r'''@page { size: A4; margin: 0; }
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: -apple-system, "SF Pro Text", "SF Pro Display",
               "Helvetica Neue", "PingFang SC", "Microsoft YaHei", sans-serif;
  color: #111; background: #f0f0f0;
}
.page {
  width: 210mm; height: 297mm; margin: 12mm auto; background: white;
  padding: 12mm 18mm 12mm 15mm; box-shadow: 0 2px 12px rgba(0,0,0,.15);
  position: relative; overflow: hidden; page-break-after: always;
}
.page:last-child { page-break-after: auto; }

.hdl { border-top: 1.2px solid #000; border-bottom: 0.6px solid #000;
       padding: 3mm 0; margin-bottom: 2mm; }
.hdl::before { content:''; display:block; height:0.6px; background:#000; margin-bottom:3mm; }
.ht { text-align:center; font-size:15pt; font-weight:600; margin:4mm 0 5mm; }
.hi { font-size:9pt; line-height:2; } .hi span { margin-right:18mm; }
.hn { margin-top:3mm; border-top:0.6px solid #999; padding-top:3mm;
      font-size:7pt; color:#666; line-height:1.6; }
.hb { border-top:0.6px solid #000; border-bottom:1.2px solid #000;
      margin-top:2mm; height:1.8mm; }
.st { font-size:9.5pt; font-weight:600; padding:2mm 0 1.5mm;
      border-bottom:0.8px solid #000; margin-bottom:2mm; letter-spacing:0.5px; }

.cr { display:flex; align-items:center; height:7mm; margin-bottom:1mm; font-size:9pt; }
.ci { display:flex; align-items:center; flex:1; }
.ci .qn { margin-right:2mm; font-weight:500; min-width:4mm; }
.ci .bb { display:inline-flex; align-items:center; }
.ci .bb label {
  display:inline-flex; align-items:center; justify-content:center;
  width:5mm; height:5mm; border:0.8px solid #000; margin-right:1mm;
  font-size:7.5pt; cursor:default; border-radius:0.3mm;
}

.br { display:flex; align-items:baseline; height:8mm; margin-bottom:1mm; font-size:9pt; }
.bi { flex:1; display:flex; align-items:baseline; }
.bi .qn { margin-right:2mm; font-weight:500; min-width:4mm; }
.bi .ul { flex:1; border-bottom:1px solid #000; height:4mm; }

.eq { margin-bottom:3mm; page-break-inside:avoid; }
.eqh { font-size:8.5pt; margin-bottom:2mm; font-weight:500; }
.eb { position:relative; background:#fff; border:0.7px solid #000;
      width:100%; overflow:hidden; }
.eb .gl-svg {
  position:absolute; top:0; left:0; width:calc(100% - 10mm);
  height:100%; overflow:visible; display:block;
}
.eb .sc {
  position:absolute; right:0; top:0; bottom:0; width:10mm;
  border-left:0.5px solid #000; display:flex; flex-direction:column;
  align-items:center; justify-content:flex-start; padding-top:3mm;
  font-size:6pt; color:#999;
}
.eb .sc span { writing-mode:vertical-rl; letter-spacing:4mm; }

.pf { position:absolute; bottom:5mm; left:0; right:0; text-align:center;
      font-size:6.5pt; color:#999; }
.sd { border:none; border-top:0.4px solid #ccc; margin:2mm 0; }
'''


def build_html(school, cfg):
    """生成答题卡 HTML"""
    MAX_H = 235

    pages_html = []
    cur  = ''
    cur_h = 0

    def flush():
        nonlocal cur, cur_h
        if cur:
            pages_html.append(cur)
            cur = ''
            cur_h = 0

    def need_new(h):
        return cur_h + h > MAX_H

    def new_page(cont_label=''):
        nonlocal cur, cur_h
        flush()
        if cont_label:
            cur = f'  <div class="hdl">\n    <div style="font-size:8pt;color:#999;">{cont_label}</div>\n  </div>\n'
            cur_h = 10

    def add(html, h):
        nonlocal cur, cur_h
        if need_new(h):
            new_page()
        cur += html
        cur_h += h

    def add_force(html, h):
        nonlocal cur, cur_h
        cur += html
        cur_h += h

    cur_h = 45  # header 占用高度

    for si, sec in enumerate(cfg['sections']):
        cn    = CN[si]
        label = f"{cn}、{sec['label']}"
        n     = len(sec['qs'])
        total = n * sec['score']
        score = sec['score']
        title_html = f'    <div class="st">{label}（共{n}题，每题{score}分，共{total}分）</div>\n'
        title_h = 6
        cont    = f"{label}（续）"

        if sec['type'] == 'choice':
            first = True
            for rs in range(0, len(sec['qs']), 3):
                rq = sec['qs'][rs:rs+3]
                cells = ''.join(
                    f'      <div class="ci"><span class="qn">{q}.</span>'
                    f'<span class="bb"><label>A</label><label>B</label>'
                    f'<label>C</label><label>D</label></span></div>\n'
                    for q in rq
                ) + '      <div class="ci"></div>\n' * (3 - len(rq))
                row_html = f'    <div class="cr">\n{cells}    </div>\n'
                row_h = 8
                if first:
                    if need_new(title_h + row_h):
                        new_page(cont)
                        add_force(title_html, title_h)
                        add_force(row_html, row_h)
                    else:
                        add(title_html + row_html, title_h + row_h)
                    first = False
                else:
                    if need_new(row_h):
                        new_page(cont)
                    add(row_html, row_h)

        elif sec['type'] == 'blank':
            first = True
            for rs in range(0, len(sec['qs']), 3):
                rq = sec['qs'][rs:rs+3]
                cells = ''.join(
                    f'      <div class="bi"><span class="qn">{q}.</span>'
                    f'<div class="ul"></div></div>\n'
                    for q in rq
                ) + '      <div class="bi"></div>\n' * (3 - len(rq))
                row_html = f'    <div class="br">\n{cells}    </div>\n'
                row_h = 9
                if first:
                    if need_new(title_h + row_h):
                        new_page(cont)
                        add_force(title_html, title_h)
                        add_force(row_html, row_h)
                    else:
                        add(title_html + row_html, title_h + row_h)
                    first = False
                else:
                    if need_new(row_h):
                        new_page(cont)
                    add(row_html, row_h)

        else:  # essay
            for qi, q in enumerate(sec['qs']):
                bh        = essay_h(sec['score'])
                svg_lines, vb_h = build_svg_lines(bh)
                q_html = (
                    f'    <div class="eq">\n'
                    f'      <div class="eqh">{q}.（{sec["score"]}分）</div>\n'
                    f'      <div class="eb" style="height:{bh}mm;">\n'
                    f'        <svg class="gl-svg" '
                    f'viewBox="0 0 794 {vb_h}" '
                    f'preserveAspectRatio="none" '
                    f'xmlns="http://www.w3.org/2000/svg">\n'
                    f'          {svg_lines}\n'
                    f'        </svg>\n'
                    f'        <div class="sc"><span>得 分</span></div>\n'
                    f'      </div>\n'
                    f'    </div>\n'
                )
                q_h = bh + 8
                if qi == 0:
                    if need_new(title_h + q_h):
                        new_page(cont)
                        add_force(title_html, title_h)
                        add_force(q_html, q_h)
                    else:
                        add(title_html + q_html, title_h + q_h)
                else:
                    if need_new(q_h):
                        new_page(cont)
                    add(q_html, q_h)

        if si < len(cfg['sections']) - 1:
            add('    <hr class="sd">\n', 3)

    flush()

    header = f'''  <div class="hdl">
    <div class="ht">{school}插班生数学考试  答题卡</div>
    <div class="hi">
      <span>姓名：________________</span>
      <span>准考证号：________________</span>
      <span>满分{cfg['full']}分  {cfg['time']}</span>
    </div>
    <div class="hi">
      <span>院校：________________</span>
      <span>座位号：________</span>
    </div>
    <div class="hn">
      注意事项：1. 选择题用2B铅笔填涂，修改时用橡皮擦干净。
      2. 非选择题用0.5mm黑色签字笔书写。 3. 在答题区域内作答，超出无效。
    </div>
  </div>
  <div class="hb"></div>\n'''

    if pages_html:
        pages_html[0] = header + pages_html[0]

    page_divs = [
        f'<div class="page">\n{c}  '
        f'<div class="pf">{school}插班生数学答题卡   第 {i+1} 页</div>\n</div>'
        for i, c in enumerate(pages_html)
    ]

    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>{school}答题卡</title>
<style>
{CSS}
</style>
</head>
<body>
{chr(10).join(page_divs)}
</body>
</html>'''


def html_to_pdf(html_path, pdf_path):
    """用 Playwright 将 HTML 转为 PDF"""
    from playwright.sync_api import sync_playwright
    abs_html = os.path.abspath(html_path)
    abs_pdf  = os.path.abspath(pdf_path)
    with sync_playwright() as p:
        b  = p.chromium.launch()
        pg = b.new_page()
        pg.set_viewport_size({'width': 1240, 'height': 1754})
        pg.goto(f'file://{abs_html}')
        pg.pdf(
            path=abs_pdf,
            format='A4',
            print_background=True,
            margin={'top': '0', 'right': '0', 'bottom': '0', 'left': '0'},
        )
        b.close()


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    print("＝" * 50)
    print("  Answer Sheet Generator — SVG + Playwright PDF")
    print("＝" * 50)

    ok = 0
    for school, cfg in PAPERS.items():
        html_path = os.path.join(OUT_DIR, f'{school}答题卡.html')
        pdf_path  = os.path.join(OUT_DIR, f'{school}答题卡.pdf')

        html = build_html(school, cfg)
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html)

        try:
            html_to_pdf(html_path, pdf_path)
            size = os.path.getsize(pdf_path) // 1024
            print(f"  ✓ {school} 答题卡.pdf  ({size}KB)")
            ok += 1
        except Exception as e:
            print(f"  ✗ {school} 失败: {e}")
            print(f"    HTML 仍已保存: {html_path}")

    print(f"\n  生成 {ok}/{len(PAPERS)} 份")
    print(f"  → {os.path.abspath(OUT_DIR)}")


if __name__ == '__main__':
    main()
