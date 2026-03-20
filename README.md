# Answer Sheet Generator

**用 HTML + SVG 画答题卡，用 Chromium 渲染 PDF——像素级精确。**

```bash
pip install -r requirements.txt
python answer_sheet.py
# → 生成 PDF + HTML 预览在 ./output/
```

---

## 问题

做答题卡印刷时遇到一个看似简单却绕不开的坑：

> **HTML 里看着对的 Guide Lines，转换成 PDF 后间距错乱、颜色失真、甚至直接消失。**

原因不在 HTML 本身，而是三个工具链的叠加：

| 环节 | 技术 | 问题 |
|------|------|------|
| 页面布局 | CSS `mm` 单位 | 不同浏览器/工具解释不一致 |
| Guide Lines | `repeating-linear-gradient` | 大多数 PDF 转换器不完全支持 CSS3 Gradient |
| 渲染引擎 | ReportLab / wkhtmltopdf | 不支持 CSS `mm` → 物理像素的精确映射 |

试过 WeasyPrint、wkhtmltopdf、ReportLab，全部在 Guide Lines 上出问题——间距偏差、颜色过深、线条消失。

---

## 方案

**不用 CSS Gradient，用 SVG Line；不用第三方转换器，用 Chromium 浏览器本身。**

```
HTML + SVG guide lines  →  Chromium Headless  →  Pixel-perfect PDF
```

**关键技巧：SVG `viewBox` 映射**

CSS 屏幕的逻辑分辨率是 96dpi，对应 `1mm ≈ 3.78 CSS px`。

```
box_h_mm × 3.78 = SVG viewBox 高度（CSS px）
```

这样 SVG 坐标和 Chromium 的 PDF 渲染坐标系完全对齐，Guide Lines 的物理间距误差 < 0.5%。

---

## 效果

| 指标 | 目标 | 实测 |
|------|------|------|
| Guide Line 物理间距 | 7mm | **6.99mm** ✓ |
| Guide Line 颜色 | `#D0D0D0` 浅灰 | `#D0D0D0` ✓ |
| Guide Line 宽度 | ~0.15mm | **0.14mm** ✓ |
| HTML ↔ PDF 一致性 | 100% | **100%** ✓ |

---

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
python -m playwright install chromium   # 下载 Chromium 浏览器
```

需要 Python 3.9+。

### 2. 配置答题卡

编辑 `config.py`，定义学校/科目信息：

```python
PAPERS = {
    '复旦': {
        'full': 400,
        'time': '120分钟',
        'sections': [
            {'label': '解答证明题', 'type': 'essay', 'qs': list(range(1, 21)), 'score': 20},
        ],
    },
    '交大': {
        'full': 100,
        'time': '90分钟',
        'sections': [
            {'label': '选择题',   'type': 'choice', 'qs': list(range(1, 9)),  'score': 3},
            {'label': '填空题',   'type': 'blank',  'qs': list(range(1, 9)),  'score': 3},
            {'label': '计算题',   'type': 'essay',  'qs': list(range(1, 6)),  'score': 10},
            {'label': '证明题',   'type': 'essay',  'qs': [1],                'score': 6},
        ],
    },
}
```

**section type 三种：**
- `choice` — 选择题，4选1方框
- `blank`  — 填空题，横线
- `essay`  — 解答/证明题，带 Guide Lines 的答题框

### 3. 生成

```bash
python answer_sheet.py
```

输出到 `./output/`：

```
output/
├── 复旦答题卡.html    # 屏幕预览（直接浏览器打开）
├── 复旦答题卡.pdf     # 印刷文件
├── 交大答题卡.html
├── 交大答题卡.pdf
└── ...
```

### 4. 直接打开 HTML 预览

```bash
open output/复旦答题卡.html
```

---

## 架构

```
┌─────────────────────────────────────────────────────────────┐
│                      answer_sheet.py                         │
├──────────────────┬──────────────────┬──────────────────────┤
│   build_html()   │  html_to_pdf()   │    page_layout()     │
│                  │                  │                      │
│  生成 HTML 页面   │  Playwright 调用  │  按 235mm 高度自动   │
│  用 SVG Line 画   │  Chromium 无头    │  分页，不切割题目    │
│  Guide Lines     │  渲染 PDF         │                      │
└────────┬─────────┴────────┬─────────┴──────────┬───────────┘
         │                  │                    │
         ▼                  ▼                    ▼
    SVG <line>      Chromium Headless       分页逻辑
    viewBox=794xh   Skia/PDF 引擎           续页标注
```

**核心模块：**

| 模块 | 职责 |
|------|------|
| `build_svg_lines()` | 将物理 mm 转为 SVG viewBox CSS px，生成 `<line>` 元素 |
| `build_html()` | 按题目配置生成完整 HTML，支持自动分页 |
| `html_to_pdf()` | Playwright 调 Chromium 无头渲染，输出 PDF |
| `essay_h()` | 根据分值计算答题框高度（20分→78mm，10分→55mm，6分→38mm）|

---

## 答题框高度规则

| 分值 | 高度 |
|------|------|
| ≥ 20 分 | 78mm |
| ≥ 12 分 | 65mm |
| ≥ 10 分 | 55mm |
| ≥ 8 分  | 46mm |
| ≥ 6 分  | 38mm |
| < 6 分  | 32mm |

---

## 技术栈

- **PDF 渲染** — Playwright + Chromium Headless（Skia/PDF 引擎）
- **Guide Lines** — SVG `<line>` + `viewBox` + `preserveAspectRatio="none"`
- **页面布局** — 纯 CSS `@page` + `mm` 单位 + Flexbox
- **分页逻辑** — Python，235mm 内容高度自动分页，不切割题目

---

## License

MIT
