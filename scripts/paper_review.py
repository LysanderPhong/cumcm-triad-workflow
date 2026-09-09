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
            reader = PdfReader(str(path))
            pages = [(page.extract_text() or "") for page in reader.pages]
            if not any(pages):
                warnings.append("PDF 没有可提取文字，文本指标不完整；仍需人工检查渲染结果。")
            return "\n".join(pages), warnings
        if suffix == ".docx":
            with zipfile.ZipFile(path) as archive:
                xml = archive.read("word/document.xml").decode("utf-8", errors="replace")
            return re.sub(r"<[^>]+>", " ", xml), warnings
        return path.read_text(encoding="utf-8", errors="replace"), [f"未专门识别扩展名 {suffix}，按文本读取。"]
    except (OSError, zipfile.BadZipFile) as exc:
        return "", [f"读取失败：{exc}"]


def pdf_pages(path: Path) -> int | None:
    if path.suffix.lower() != ".pdf":
        return None
    try:
        from pypdf import PdfReader  # type: ignore
        return len(PdfReader(str(path)).pages)
    except Exception:
        return None


def metrics(text: str, source: Path | None = None) -> dict:
    sentences = [s.strip() for s in re.split(r"[。！？!?；;]+", text) if s.strip()]
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    headings = re.findall(r"^\s{0,3}#{1,6}\s+.+$|^\s*(?:第[一二三四五六七八九十]+[章节问]|摘要|结论|参考文献|附录).*$", text, flags=re.M)
    chinese = re.findall(r"[\u4e00-\u9fff]", text)
    latin_words = re.findall(r"[A-Za-z0-9_]+", text)
    generic = {phrase: text.count(phrase) for phrase in GENERIC_PHRASES if text.count(phrase)}
    strong = {phrase: text.count(phrase) for phrase in STRONG_CLAIMS if text.count(phrase)}
    evidence_hits = sum(text.count(word) for word in EVIDENCE_WORDS)
    starts = Counter(s[:10] for s in sentences if len(s) >= 10)
    repeated = {k: v for k, v in starts.items() if v >= 3}
    question_hits = {f"Q{i}": len(re.findall(rf"(?i)(?:问题|question|q)\s*{i}", text)) for i in range(1, 5)}
    return {
        "chars": len(text), "chinese_chars": len(chinese), "latin_tokens": len(latin_words),
        "pages": pdf_pages(source) if source else None,
        "paragraphs": len(paragraphs), "sentences": len(sentences),
        "avg_sentence_chars": round(sum(len(s) for s in sentences) / len(sentences), 1) if sentences else 0,
        "headings": len(headings), "figure_mentions": len(re.findall(r"图\s*\d+|Figure\s*\d+", text, re.I)),
        "table_mentions": len(re.findall(r"表\s*\d+|Table\s*\d+", text, re.I)),
        "equation_markers": text.count("$") // 2 + len(re.findall(r"\\begin\{(?:equation|align)", text)),
        "citation_markers": len(re.findall(r"\[[0-9,–-]+\]|\([A-Z][^)]*,\s*20\d{2}\)", text)),
        "question_hits": question_hits, "generic_phrases": generic, "strong_claims": strong,
        "evidence_hits": evidence_hits, "repeated_sentence_starts": repeated,
    }


def flags(candidate: dict, decision_count: int | None, min_pages: int = 20, max_pages: int = 30) -> list[dict]:
    result: list[dict] = []
    if sum(candidate["generic_phrases"].values()) >= 5:
        result.append({"level": "REVIEW", "title": "套话密度偏高", "detail": "常见转折/总结短语累计出现较多；请改成与你的具体数据和判断有关的句子。"})
    if candidate["repeated_sentence_starts"]:
        result.append({"level": "REVIEW", "title": "句式重复", "detail": "多个句子以相同前缀开始；检查是否由模板批量生成并补充真实推理。"})
    if candidate["strong_claims"] and candidate["evidence_hits"] < sum(candidate["strong_claims"].values()) * 2:
        result.append({"level": "HIGH", "title": "强结论证据不足风险", "detail": "存在“最优/显著/保证”等强断言，但可识别的验证词较少；逐条绑定实验或降低措辞。"})
    if decision_count == 0:
        result.append({"level": "HIGH", "title": "未发现人类决策记录", "detail": "核心建模段需要人类方向、修改或自己的解释；请检查 logs/human_decisions.jsonl。"})
    if candidate["citation_markers"] == 0:
        result.append({"level": "REVIEW", "title": "未识别到引用标记", "detail": "可能是格式差异，也可能存在引用链缺口；人工核对参考文献。"})
    pages = candidate.get("pages")
    if isinstance(pages, int) and not (min_pages <= pages <= max_pages):
        result.append({"level": "REVIEW", "title": "篇幅超出目标区间", "detail": f"当前 {pages} 页；默认目标为 {min_pages}-{max_pages} 页，建议围绕约 25 页压缩或补充。"})
    return result


def style_checks(path: Path | None) -> list[dict]:
    if path is None:
        return [{"level": "UNKNOWN", "title": "未提供 figure_manifest.json", "detail": "无法自动核对字体、色板和效果；请按 visual_style.md 人工检查渲染图。"}]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [{"level": "HIGH", "title": "图表清单不可读", "detail": str(exc)}]
    effects = data.get("effects", {})
    findings = []
    for key in ("shadows", "three_dimensional", "gradients", "glow", "heavy_borders"):
        if effects.get(key) is True:
            findings.append({"level": "HIGH", "title": f"图表效果未关闭：{key}", "detail": "按扁平风格规范关闭该效果。"})
    colors = data.get("colors", {}).get("categorical", [])
    if any(c.casefold() in {"#ff0000", "#00ff00", "red", "green"} for c in colors):
        findings.append({"level": "HIGH", "title": "主色包含高饱和红/绿", "detail": "换成低饱和、色盲友好的分类色板。"})
    if data.get("fonts", {}).get("family") in {None, "", "默认"}:
        findings.append({"level": "REVIEW", "title": "字体族未固定", "detail": "统一中文、英文、数字和图注字体。"})
    return findings or [{"level": "PASS", "title": "登记的图表规范未发现违规", "detail": "仍需实际渲染和灰度打印复核。"}]


def table_rows(candidate: dict, references: list[tuple[str, dict]]) -> str:
    keys = ("pages", "chinese_chars", "paragraphs", "sentences", "headings", "figure_mentions", "table_mentions", "citation_markers", "equation_markers", "avg_sentence_chars")
    labels = {"pages": "页数", "chinese_chars": "中文字符", "paragraphs": "段落", "sentences": "句子", "headings": "标题", "figure_mentions": "图引用", "table_mentions": "表引用", "citation_markers": "引用标记", "equation_markers": "公式标记", "avg_sentence_chars": "平均句长"}
    rows = [f"<tr><th>候选稿</th>{''.join(f'<td>{html.escape(str(candidate.get(k, 0)))}</td>' for k in keys)}</tr>"]
    for name, item in references:
        rows.append(f"<tr><th>{html.escape(name)}</th>{''.join(f'<td>{html.escape(str(item.get(k, 0)))}</td>' for k in keys)}</tr>")
    return "\n".join(rows), "".join(f"<th>{labels[k]}</th>" for k in keys)


def render(args: argparse.Namespace, candidate: dict, references: list[tuple[str, dict]], warnings: list[str], findings: list[dict], style: list[dict], decision_count: int | None) -> str:
    rows, headers = table_rows(candidate, references)
    finding_html = "".join(f"<li class='{html.escape(x['level'])}'><b>{html.escape(x['title'])}</b>：{html.escape(x['detail'])}</li>" for x in findings + style)
    warning_html = "".join(f"<li>{html.escape(w)}</li>" for w in warnings) or "<li>无</li>"
    generated = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    payload = json.dumps({"generated_at": generated, "candidate": candidate, "references": references, "findings": findings, "style_findings": style}, ensure_ascii=False)
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
<li>页数：{candidate.get('pages') if candidate.get('pages') is not None else '未读取'}（目标 20–30 页，约 25 页）；中文字符：{candidate['chinese_chars']}；段落：{candidate['paragraphs']}；句子：{candidate['sentences']}；平均句长：{candidate['avg_sentence_chars']}</li>
<li>标题：{candidate['headings']}；图引用：{candidate['figure_mentions']}；表引用：{candidate['table_mentions']}；公式标记：{candidate['equation_markers']}；引用标记：{candidate['citation_markers']}</li>
<li>Q1–Q4 识别：{html.escape(json.dumps(candidate['question_hits'], ensure_ascii=False))}；人类决策记录数：{decision_count if decision_count is not None else '未提供'}</li>
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
for(const el of document.querySelectorAll('[data-item]')) el.checked=localStorage.getItem('paper-review-'+el.dataset.item)==='true';
document.getElementById('notes').value=localStorage.getItem('paper-review-notes')||'';
function saveNotes(){{for(const el of document.querySelectorAll('[data-item]')) localStorage.setItem('paper-review-'+el.dataset.item,el.checked);localStorage.setItem('paper-review-notes',document.getElementById('notes').value);document.getElementById('saved').textContent=' 已保存';}}
function downloadNotes(){{saveNotes();const out={{report:payload,checks:Object.fromEntries([...document.querySelectorAll('[data-item]')].map(x=>[x.dataset.item,x.checked])),notes:document.getElementById('notes').value}};const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(out,null,2)],{{type:'application/json'}}));a.download='paper-review-decisions.json';a.click();}}
</script></body></html>'''


def decision_count(path: Path | None) -> int | None:
    if path is None or not path.exists():
        return None
    try:
        return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    except OSError:
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paper", required=True, type=Path)
    parser.add_argument("--reference", action="append", type=Path, default=[], help="user-supplied comparable paper; repeatable")
    parser.add_argument("--output-html", required=True, type=Path)
    parser.add_argument("--figure-manifest", type=Path)
    parser.add_argument("--decision-log", type=Path)
    parser.add_argument("--min-pages", type=int, default=20, help="advisory target minimum page count (default: 20)")
    parser.add_argument("--max-pages", type=int, default=30, help="advisory target maximum page count (default: 30)")
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
    if args.min_pages < 1 or args.max_pages < args.min_pages:
        print("ERROR: invalid page range", file=sys.stderr)
        return 2
    findings = flags(candidate, count, args.min_pages, args.max_pages)
    style = style_checks(args.figure_manifest)
    output = args.output_html.expanduser().resolve()
    if output.exists():
        print(f"ERROR: refusing to overwrite existing output: {output}", file=sys.stderr)
        return 2
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
