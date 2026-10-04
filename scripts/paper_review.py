#!/usr/bin/env python3
"""Generate an explainable paper review HTML.

The report compares a candidate paper with user-supplied reference papers and
flags writing/evidence patterns that deserve human review. It deliberately does
not estimate an AI percentage or rewrite the paper. PDF extraction uses pypdf
when installed and reports a warning when it is unavailable.

Exit codes: 0 report created, 1 input/extraction validation issue, 2 refused
output or invalid arguments. Python 3.10+, standard library first.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import html
import json
from pathlib import Path
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
import hashlib
import math


GENERIC_PHRASES = (
    "综上所述", "值得注意的是", "本文旨在", "通过上述分析", "可以看出",
    "在一定程度上", "具有重要意义", "显著提高", "从而为", "不难发现",
)
STRONG_CLAIMS = ("最优", "显著", "完全", "充分证明", "领先", "普适", "保证")
EVIDENCE_WORDS = ("误差", "置信", "基线", "敏感性", "稳健", "残差", "复算", "对照", "区间")


def extract(path: Path) -> tuple[str, list[str]]:
    warnings: list[str] = []
    suffix = path.suffix.lower()
    try:
        if suffix in {".md", ".markdown", ".txt", ".tex", ".rst"}:
            return path.read_text(encoding="utf-8", errors="replace"), warnings
        if suffix in {".html", ".htm"}:
            text = path.read_text(encoding="utf-8", errors="replace")
            return re.sub(r"<[^>]+>", " ", text), warnings
        if suffix == ".pdf":
            try:
                from pypdf import PdfReader  # type: ignore
            except ImportError:
                return "", ["pypdf 未安装，无法读取 PDF；该文件未纳入文本指标。"]
            try:
                reader = PdfReader(str(path))
                pages = [(page.extract_text() or "") for page in reader.pages]
            except Exception as exc:
                return '', [f'PDF 读取失败：{exc}']
            if not any(pages):
                warnings.append("PDF 没有可提取文字，文本指标不完整；仍需人工检查渲染结果。")
            return "\n".join(pages), warnings
        if suffix == ".docx":
            with zipfile.ZipFile(path) as archive:
                root = ET.fromstring(archive.read("word/document.xml"))
            ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
            return '\n\n'.join(''.join(t.text or '' for t in p.findall('.//w:t', ns)) for p in root.findall('.//w:p', ns)), warnings
        return path.read_text(encoding="utf-8", errors="replace"), [f"未专门识别扩展名 {suffix}，按文本读取。"]
    except (OSError, zipfile.BadZipFile, KeyError, ET.ParseError, ValueError) as exc:
        return "", [f"读取失败：{exc}"]


def pdf_pages(path: Path) -> int | None:
    if path.suffix.lower() != ".pdf":
        return None
    try:
        from pypdf import PdfReader  # type: ignore
        return len(PdfReader(str(path)).pages)
    except Exception:
        return None


def abstract_counts(text: str) -> tuple[int, int]:
    tex = re.search(r'\\begin\{abstract\}(.*?)\\end\{abstract\}', text, flags=re.S)
    if tex:
        section = tex.group(1)
        return len(section), sum('\u4e00' <= c <= '\u9fff' for c in section)
    match = re.search(r'(?im)^\s*(?:#{1,6}\s*)?(?:摘要|摘\s+要|abstract)\s*[:：]?\s*$', text)
    if not match:
        return 0, 0
    start = match.end()
    stops = [m.start() for m in re.finditer(r'(?im)^\s*(?:关键词|关键字|key\s*words)\s*[:：]', text) if m.start() >= start]
    end = min(stops) if stops else min(len(text), start + 5000)
    section = text[start:end]
    return len(section), sum("\u4e00" <= c <= "\u9fff" for c in section)


def metrics(text: str, source: Path | None = None) -> dict:
    sentences = [s.strip() for s in re.split(r"[。！？!?；;]+", text) if s.strip()]
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    headings = re.findall(r"^\s{0,3}#{1,6}\s+.+$|^\s*\\(?:sub)*section\*?\{[^}]+\}|^\s*(?:[一二三四五六七八九十]+[、．.]|\d+(?:\.\d+)*[、．. ]|第[一二三四五六七八九十]+[章节问]|摘要|结论|参考文献|附录).*$", text, flags=re.M)
    chinese = re.findall(r"[\u4e00-\u9fff]", text)
    latin_words = re.findall(r"[A-Za-z0-9_]+", text)
    abstract_chars, abstract_chinese_chars = abstract_counts(text)
    generic = {phrase: text.count(phrase) for phrase in GENERIC_PHRASES if text.count(phrase)}
    strong = {phrase: text.count(phrase) for phrase in STRONG_CLAIMS if text.count(phrase)}
    evidence_hits = sum(text.count(word) for word in EVIDENCE_WORDS)
    starts = Counter(s[:10] for s in sentences if len(s) >= 10)
    repeated = {k: v for k, v in starts.items() if v >= 3}
    question_hits = dict(Counter(m.group(1) for m in re.finditer(r'(?i)(?:问题|question|\bq)\s*([一二三四五六七八九十]+|\d+)', text)))
    return {
        "chars": len(text), "chinese_chars": len(chinese), "latin_tokens": len(latin_words),
        "pages": pdf_pages(source) if source else None,
        "abstract_chars": abstract_chars, "abstract_chinese_chars": abstract_chinese_chars,
        "paragraphs": len(paragraphs), "sentences": len(sentences),
        "avg_sentence_chars": round(sum(len(s) for s in sentences) / len(sentences), 1) if sentences else 0,
        "headings": len(headings), "figure_mentions": len(re.findall(r"图\s*\d+|Figure\s*\d+", text, re.I)),
        "table_mentions": len(re.findall(r"表\s*\d+|Table\s*\d+", text, re.I)),
        "equation_markers": text.count("$") // 2 + len(re.findall(r"\\begin\{(?:equation|align)", text)),
        "citation_markers": len(re.findall(r"\[[0-9,–-]+\]|\([A-Z][^)]*,\s*20\d{2}\)|\\cite[a-zA-Z]*\*?(?:\[[^\]]*\])*\{[^}]+\}", text)),
        "question_hits": question_hits, "generic_phrases": generic, "strong_claims": strong,
        "evidence_hits": evidence_hits, "repeated_sentence_starts": repeated,
    }


def flags(candidate: dict, decision_count: int | None, min_pages: int | None = None, max_pages: int | None = None, abstract_min_chinese: int = 0) -> list[dict]:
    result: list[dict] = []
    if sum(candidate["generic_phrases"].values()) >= 5:
        result.append({"level": "REVIEW", "title": "套话密度偏高", "detail": "常见转折/总结短语累计出现较多；请改成与你的具体数据和判断有关的句子。"})
    if candidate["repeated_sentence_starts"]:
        result.append({"level": "REVIEW", "title": "句式重复", "detail": "多个句子以相同前缀开始；检查是否由模板批量生成并补充真实推理。"})
    if candidate["strong_claims"]:
        result.append({"level": "REVIEW", "title": "核对强结论的适用范围", "detail": "识别到强结论用词。词频不能判断证据是否充分；按具体主张核对推导、实验和适用范围。"})
    if decision_count == 0:
        result.append({"level": "REVIEW", "title": "未发现人类决策记录", "detail": "检查 logs/events.jsonl 中的真实 SCOPE/ROUTE 决定；文本报告不证明作者贡献。"})
    if candidate["citation_markers"] == 0:
        result.append({"level": "REVIEW", "title": "未识别到引用标记", "detail": "可能是格式差异，也可能存在引用链缺口；人工核对参考文献。"})
    pages = candidate.get("pages")
    if isinstance(pages, int) and ((min_pages is not None and pages < min_pages) or (max_pages is not None and pages > max_pages)):
        result.append({"level": "REVIEW", "title": "篇幅超出用户配置", "detail": f"当前 {pages} 页；用户配置下限 {min_pages}、上限 {max_pages}。页数不能证明论文质量。"})
    abstract_cn = candidate.get("abstract_chinese_chars")
    if isinstance(abstract_cn, int) and abstract_cn < abstract_min_chinese:
        result.append({"level": "REVIEW", "title": "摘要短于用户配置", "detail": f"可提取中文摘要约 {abstract_cn} 字。字符数不能测量页面高度；请检查摘要是否完整及实际排版。"})
    return result


def style_checks(path: Path | None) -> list[dict]:
    if path is None:
        return [{"level": "UNKNOWN", "title": "未提供 figure_manifest.json", "detail": "无法自动核对字体、色板和效果；请按 visual_style.md 人工检查渲染图。"}]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [{"level": "HIGH", "title": "图表清单不可读", "detail": str(exc)}]
    if not isinstance(data, dict):
        return [{"level": "HIGH", "title": "图表清单格式错误", "detail": "清单应为 JSON 对象。"}]
    effects = data.get("effects", {})
    fonts = data.get('fonts', {})
    if not isinstance(effects, dict) or not isinstance(fonts, dict):
        return [{'level': 'HIGH', 'title': '图表清单格式错误', 'detail': 'effects 与 fonts 须为对象。'}]
    findings = []
    for key in ("shadows", "glow", "heavy_borders"):
        if effects.get(key) is True:
            findings.append({"level": "REVIEW", "title": f"检查装饰效果：{key}", "detail": "确认装饰没有遮挡数据或降低打印可读性。"})
    if fonts.get("family") in {None, "", "默认"}:
        findings.append({"level": "REVIEW", "title": "字体族未固定", "detail": "统一中文、英文、数字和图注字体。"})
    figures = data.get('figures', [])
    if not isinstance(figures, list) or not figures:
        findings.append({"level": "UNKNOWN", "title": "未登记实际图表文件", "detail": "仅声明字体和色板无法检查最终图；提供 figures 文件列表。"})
        figures = []
    root = path.resolve().parent.parent if path.parent.name == 'paper' else path.resolve().parent
    for index, item in enumerate(figures, 1):
        if not isinstance(item, dict) or not isinstance(item.get('path'), str):
            findings.append({'level': 'HIGH', 'title': f'图 {index} 格式错误', 'detail': '每项须有 path。'})
            continue
        file = (root / item['path']).resolve()
        if not file.is_relative_to(root) or not file.is_file():
            findings.append({'level': 'HIGH', 'title': f'图 {index} 文件缺失或越界', 'detail': item['path']})
            continue
        if not item.get('input_refs') or not item.get('script_ref'):
            findings.append({'level': 'REVIEW', 'title': f'图 {index} 来源未登记', 'detail': '补充真实数据 input_refs 和生成脚本 script_ref。'})
        input_refs = item.get('input_refs', [])
        if not isinstance(input_refs, list):
            findings.append({'level': 'HIGH', 'title': f'图 {index} 来源格式错误', 'detail': 'input_refs 须为文件路径列表。'})
            input_refs = []
        for ref in input_refs + ([item['script_ref']] if item.get('script_ref') else []):
            if not isinstance(ref, str) or not (root / ref).resolve().is_relative_to(root) or not (root / ref).is_file():
                findings.append({'level': 'HIGH', 'title': f'图 {index} 来源文件缺失或越界', 'detail': str(ref)})
        if file.suffix.lower() == '.png':
            with file.open('rb') as source:
                header = source.read(24)
            if len(header) >= 24 and header[:8] == b'\x89PNG\r\n\x1a\n':
                width = int.from_bytes(header[16:20], 'big')
                width_mm = item.get('final_width_mm')
                if isinstance(width_mm, (int, float)) and math.isfinite(width_mm) and width_mm > 0:
                    dpi = width / (width_mm / 25.4)
                    if dpi < 300:
                        findings.append({'level': 'REVIEW', 'title': f'图 {index} 插入后分辨率偏低', 'detail': f'约 {dpi:.0f} dpi；优先矢量输出，栅格图建议至少 300 dpi。'})
                else:
                    findings.append({'level': 'UNKNOWN', 'title': f'图 {index} 最终尺寸未登记', 'detail': '提供 final_width_mm，才能估计插入后的分辨率。'})
        if item.get('use_color_alone'):
            findings.append({'level': 'REVIEW', 'title': f'图 {index} 仅靠颜色区分', 'detail': '增加线型、标记或直接标签，并检查灰度版。'})
    return findings or [{"level": "REVIEW", "title": "文件登记检查完成", "detail": "仍需在最终 PDF 中检查字号、单位、遮挡和灰度可读性。"}]


def table_rows(candidate: dict, references: list[tuple[str, dict]]) -> tuple[str, str]:
    keys = ("pages", "abstract_chinese_chars", "chinese_chars", "paragraphs", "sentences", "headings", "figure_mentions", "table_mentions", "citation_markers", "equation_markers", "avg_sentence_chars")
    labels = {"pages": "页数", "abstract_chinese_chars": "摘要中文字符", "chinese_chars": "中文字符", "paragraphs": "段落", "sentences": "句子", "headings": "标题", "figure_mentions": "图引用", "table_mentions": "表引用", "citation_markers": "引用标记", "equation_markers": "公式标记", "avg_sentence_chars": "平均句长"}
    rows = [f"<tr><th>候选稿</th>{''.join(f'<td>{html.escape(str(candidate.get(k, 0)))}</td>' for k in keys)}</tr>"]
    for name, item in references:
        rows.append(f"<tr><th>{html.escape(name)}</th>{''.join(f'<td>{html.escape(str(item.get(k, 0)))}</td>' for k in keys)}</tr>")
    return "\n".join(rows), "".join(f"<th>{labels[k]}</th>" for k in keys)


def render(args: argparse.Namespace, candidate: dict, references: list[tuple[str, dict]], warnings: list[str], findings: list[dict], style: list[dict], decision_count: int | None) -> str:
    rows, headers = table_rows(candidate, references)
    finding_html = "".join(f"<li class='{html.escape(x['level'])}'><b>{html.escape(x['title'])}</b>：{html.escape(x['detail'])}</li>" for x in findings + style)
    warning_html = "".join(f"<li>{html.escape(w)}</li>" for w in warnings) or "<li>无</li>"
    generated = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    payload = json.dumps({"generated_at": generated, "candidate": candidate, "references": references, "findings": findings, "style_findings": style}, ensure_ascii=False).replace('<', '\\u003c')
    storage_key = 'paper-review-' + hashlib.sha256((str(args.paper.resolve()) + args.paper.read_text(encoding='utf-8', errors='replace')).encode()).hexdigest()[:20] + '-'
    return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>论文自检与对比报告</title><style>
body{{font-family:system-ui,-apple-system,"PingFang SC","Noto Sans CJK SC",sans-serif;color:#263238;background:#f6f8f9;line-height:1.6;margin:0}}
main{{max-width:1100px;margin:32px auto;padding:0 20px}} h1{{font-size:26px}} h2{{font-size:19px;margin-top:28px}}
.note,.card{{background:#fff;border:1px solid #d9e1e4;border-radius:12px;padding:16px;margin:12px 0;box-shadow:none}}
.warning{{background:#fff8ed;border-color:#e5c997}} .HIGH{{color:#9a4d3a}} .REVIEW{{color:#806b2f}} .PASS{{color:#4c7564}} .UNKNOWN{{color:#667085}}
table{{width:100%;border-collapse:collapse;background:#fff;border:1px solid #d9e1e4}}th,td{{padding:8px;border-bottom:1px solid #e7edef;text-align:right}}th:first-child,td:first-child{{text-align:left}}
textarea{{width:100%;min-height:120px;border:1px solid #b8c8cc;border-radius:8px;padding:10px;box-sizing:border-box;font:inherit}}button{{background:#587c8c;color:#fff;border:0;border-radius:8px;padding:9px 13px;cursor:pointer;margin-right:8px}}
small{{color:#667085}} ul{{padding-left:22px}}
</style></head><body><main>
<h1>论文自检与优秀论文多维对比</h1>
<div class="note warning"><b>使用边界：</b>这不是 AI 率检测器，也不提供可信的“AI 百分比”。提示项是可解释的写作、证据和人类贡献风险；请由作者决定修改，并保留真实 AI 使用披露。</div>
<p><small>生成时间：{generated}　候选稿：{html.escape(args.paper.name)}</small></p>
<h2>一、候选稿指标</h2><div class="card"><ul>
<li>页数：{candidate.get('pages') if candidate.get('pages') is not None else '未读取'}（篇幅按用户配置）；摘要中文字符：{candidate.get('abstract_chinese_chars', 0)}；中文字符：{candidate['chinese_chars']}；段落：{candidate['paragraphs']}；句子：{candidate['sentences']}；平均句长：{candidate['avg_sentence_chars']}</li>
<li>标题：{candidate['headings']}；图引用：{candidate['figure_mentions']}；表引用：{candidate['table_mentions']}；公式标记：{candidate['equation_markers']}；引用标记：{candidate['citation_markers']}</li>
<li>问题标记识别：{html.escape(json.dumps(candidate['question_hits'], ensure_ascii=False))}；提供的决策记录数：{decision_count if decision_count is not None else '未提供'}</li>
</ul></div>
<h2>二、多维对比</h2><table><thead><tr><th>文稿</th>{headers}</tr></thead><tbody>{rows}</tbody></table>
<p><small>对比结果用于发现结构和论证差距；不同题目、年份和篇幅不可直接换算为获奖概率。</small></p>
<h2>三、写作与证据风险</h2><ul>{finding_html or '<li class="PASS">暂未发现启发式风险；仍需人工逐段检查。</li>'}</ul>
<h2>四、图表风格</h2><p>按 <code>references/visual_style.md</code> 和 <code>templates/figure_style.json</code> 检查低饱和、统一字体、扁平效果和表达目的。自动结果：</p><ul>{''.join(f"<li class='{html.escape(x['level'])}'><b>{html.escape(x['title'])}</b>：{html.escape(x['detail'])}</li>" for x in style)}</ul>
<h2>五、作者修改决定</h2><p>勾选后写下你决定修改的具体段落、理由和证据来源。此区内容只保存在本地浏览器。</p>
<label><input type="checkbox" data-item="human"> 我已补充核心建模的人类方向/取舍/解释</label><br>
<label><input type="checkbox" data-item="evidence"> 我已为强结论绑定实际验证证据</label><br>
<label><input type="checkbox" data-item="style"> 我已检查渲染图、灰度打印和字体</label><br>
<textarea id="notes" placeholder="修改计划、保留意见、需要回到人工门的问题"></textarea><br>
<button onclick="saveNotes()">保存本地检查记录</button><button onclick="downloadNotes()">下载检查记录</button><span id="saved"></span>
<h2>六、读取警告</h2><ul>{warning_html}</ul>
</main><script>
const payload={payload};
const storageKey={json.dumps(storage_key)};
for(const el of document.querySelectorAll('[data-item]')) el.checked=localStorage.getItem(storageKey+el.dataset.item)==='true';
document.getElementById('notes').value=localStorage.getItem(storageKey+'notes')||'';
function saveNotes(){{for(const el of document.querySelectorAll('[data-item]')) localStorage.setItem(storageKey+el.dataset.item,el.checked);localStorage.setItem(storageKey+'notes',document.getElementById('notes').value);document.getElementById('saved').textContent=' 已保存';}}
function downloadNotes(){{saveNotes();const out={{report:payload,checks:Object.fromEntries([...document.querySelectorAll('[data-item]')].map(x=>[x.dataset.item,x.checked])),notes:document.getElementById('notes').value}};const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(out,null,2)],{{type:'application/json'}}));a.download='paper-review-decisions.json';a.click();}}
</script></body></html>'''


def decision_count(path: Path | None) -> int | None:
    if path is None or not path.exists():
        return None
    try:
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        return sum(row.get('type') == 'human_decision' or row.get('event_type') == 'human_decision' or row.get('decision_owner') == 'human' for row in rows if isinstance(row, dict))
    except (OSError, json.JSONDecodeError):
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paper", required=True, type=Path)
    parser.add_argument("--reference", action="append", type=Path, default=[], help="user-supplied comparable paper; repeatable")
    parser.add_argument("--output-html", required=True, type=Path)
    parser.add_argument("--figure-manifest", type=Path)
    parser.add_argument("--decision-log", type=Path)
    parser.add_argument("--min-pages", type=int, help="optional user page minimum")
    parser.add_argument("--max-pages", type=int, help="optional user page maximum")
    parser.add_argument("--abstract-min-chinese", type=int, default=0, help="optional advisory abstract length; disabled by default")
    args = parser.parse_args()
    if not args.paper.is_file():
        print(f"ERROR: paper not found: {args.paper}", file=sys.stderr)
        return 2
    text, warnings = extract(args.paper)
    if not text.strip():
        print("ERROR: candidate paper has no readable text", file=sys.stderr)
        return 1
    candidate = metrics(text, args.paper)
    references = []
    for path in args.reference:
        if not path.is_file():
            warnings.append(f"reference not found: {path}")
            continue
        ref_text, ref_warnings = extract(path)
        warnings.extend(f"{path.name}: {item}" for item in ref_warnings)
        if ref_text.strip():
            references.append((path.name, metrics(ref_text, path)))
    count = decision_count(args.decision_log)
    if (args.min_pages is not None and args.min_pages < 1) or (args.max_pages is not None and args.max_pages < 1) or (args.min_pages is not None and args.max_pages is not None and args.max_pages < args.min_pages) or args.abstract_min_chinese < 0:
        print("ERROR: invalid page or abstract range", file=sys.stderr)
        return 2
    findings = flags(candidate, count, args.min_pages, args.max_pages, args.abstract_min_chinese)
    style = style_checks(args.figure_manifest)
    output = args.output_html.expanduser().resolve()
    if output.exists():
        output = output.with_name(output.stem + '-' + datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f') + output.suffix)
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(render(args, candidate, references, warnings, findings, style, count), encoding="utf-8", newline="\n")
    except OSError as exc:
        print(f"ERROR: cannot write report: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"status": "CREATED", "output_html": str(output), "references": len(references), "findings": len(findings), "style_findings": len(style), "warnings": len(warnings)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
