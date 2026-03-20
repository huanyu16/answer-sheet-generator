# Answer Sheet Generator

**HTML + SVG → Chromium PDF，像素级精确的答题卡生成器。**

[查看价值介绍页 →](https://huanyu16.github.io/answer-sheet-generator/)

## 快速开始

```bash
pip install -r requirements.txt
python -m playwright install chromium
python answer_sheet.py
```

## 核心问题

Guide Lines 用 CSS `repeating-linear-gradient` 画，浏览器预览完全正确，但转 PDF 后间距错乱。尝试过 ReportLab、WeasyPrint、Safari 打印、wkhtmltopdf，全部失败。

**解决方案**：不用 CSS Gradient，用 SVG `viewBox` + Playwright + Chromium。

```python
def build_svg_lines(box_h_mm):
    px_per_mm = 96 / 25.4          # CSS 屏幕 96dpi
    bh_px = int(box_h_mm * px_per_mm)
    # SVG viewBox 坐标和 Chromium PDF 坐标系完全对齐
```

## 效果

| 指标 | 目标 | 实测 |
|------|------|------|
| Guide Line 间距 | 7mm | **6.99mm** ✓ |
| 物理误差 | — | **< 0.5%** |
| HTML ↔ PDF 一致 | 100% | **100%** |

## License

MIT
