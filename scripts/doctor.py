#!/usr/bin/env python3
"""Probe a modeling environment without installing or changing dependencies.

The launcher uses the standard library. NumPy and Matplotlib are dependencies
of the environment being tested, and are imported only by the child probe.
Exit codes: 0 READY, 1 NOT_READY, 2 invalid arguments/output or probe setup.
Generated artifacts are diagnostic evidence, not a contest reproducibility test.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time


PLOT_PROBE = r'''
import json, os, sys, warnings
from pathlib import Path
result = {"python": sys.version.split()[0], "ok": False}
try:
    if sys.version_info < (3, 10):
        raise RuntimeError("Target Python must be 3.10 or newer")
    import numpy as np
    result["numpy"] = np.__version__
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager, ft2font
    result["matplotlib"] = matplotlib.__version__
    sample = "中文环境测试数学建模图表与证据横轴纵轴最小编译，。：0123456789"
    required = {ord(c) for c in sample if not c.isspace()}
    requested = sys.argv[2]
    candidates = list(font_manager.fontManager.ttflist)
    if requested:
        candidates = [f for f in candidates if f.name.casefold() == requested.casefold()]
    preferred = ["Noto Sans CJK SC", "Source Han Sans SC", "PingFang SC", "Heiti SC", "Songti SC", "Arial Unicode MS"]
    candidates.sort(key=lambda f: (preferred.index(f.name) if f.name in preferred else len(preferred), f.name, f.fname))
    selected = None
    for item in candidates:
        try:
            if required.issubset(ft2font.FT2Font(item.fname).get_charmap()):
                selected = item
                break
        except (RuntimeError, OSError):
            continue
    if selected is None:
        raise RuntimeError("No font covers every probe character; provide --cjk-font with an installed family name")
    result["font_family"] = selected.name
    result["font_file"] = selected.fname
    prop = font_manager.FontProperties(fname=selected.fname)
    x = np.linspace(0, 1, 21)
    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        fig, ax = plt.subplots(figsize=(5, 3), constrained_layout=True)
        ax.plot(x, x ** 2)
        ax.set_title("中文环境测试：数学建模", fontproperties=prop)
        ax.set_xlabel("横轴", fontproperties=prop)
        ax.set_ylabel("纵轴", fontproperties=prop)
        ax.grid(alpha=0.25)
        fig.savefig(Path(sys.argv[1]) / "doctor_plot.png", dpi=150)
        plt.close(fig)
        result["warnings"] = [str(w.message) for w in recorded]
        if any("Glyph" in message and "missing" in message for message in result["warnings"]):
            raise RuntimeError("Matplotlib reported missing glyphs")
    result["ok"] = True
except Exception as exc:
    result["error"] = str(exc)
print(json.dumps(result, ensure_ascii=False))
sys.exit(0 if result["ok"] else 1)
'''


def run(command: list[str], directory: Path, timeout: float, env: dict[str, str]) -> dict:
    started = time.monotonic()
    try:
        proc = subprocess.run(command, cwd=directory, env=env, text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              timeout=timeout, encoding="utf-8", errors="replace")
        return {"command": command, "exit_code": proc.returncode,
                "seconds": round(time.monotonic() - started, 3), "output": proc.stdout}
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout or ""
        if isinstance(output, bytes):
            output = output.decode("utf-8", errors="replace")
        return {"command": command, "exit_code": None, "seconds": round(time.monotonic() - started, 3),
                "output": output, "error": "timeout"}
    except OSError as exc:
        return {"command": command, "exit_code": None,
                "seconds": round(time.monotonic() - started, 3), "output": "", "error": str(exc)}


def executable(value: str) -> str:
    return shutil.which(value) or str(Path(value).expanduser().resolve())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output-dir", default="triad-doctor", help="new or empty output directory; existing artifacts are never overwritten")
    parser.add_argument("--python", default=sys.executable, help="target Python executable (default: this interpreter)")
    parser.add_argument("--xelatex", default="xelatex", help="XeLaTeX executable, resolved through PATH or an explicit path")
    parser.add_argument("--cjk-font", default="", help="installed font family to test; default: select a font with all probe glyphs")
    parser.add_argument("--timeout", type=float, default=60, help="timeout in seconds for each child command")
    args = parser.parse_args()
    if sys.version_info < (3, 10) or args.timeout <= 0:
        parser.error("Python 3.10+ and a positive --timeout are required")
    output = Path(args.output_dir).expanduser().resolve()
    try:
        output.mkdir(parents=True, exist_ok=True)
        if any(output.iterdir()):
            parser.error("--output-dir must be empty; choose a new directory to preserve prior evidence")
        (output / "mpl-cache").mkdir()
    except OSError as exc:
        print(f"SETUP_ERROR: {exc}", file=sys.stderr)
        return 2
    report: dict = {"status": "NOT_READY", "scope": "minimal environment probe only", "checks": {}}
    env = dict(os.environ)
    env["MPLCONFIGDIR"] = str(output / "mpl-cache")
    target_python = executable(args.python)
    plotting = run([target_python, "-c", PLOT_PROBE, str(output), args.cjk_font], output, args.timeout, env)
    (output / "plot_probe.log").write_text(plotting["output"], encoding="utf-8")
    try:
        details = json.loads(plotting["output"].strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        details = {"ok": False, "error": plotting.get("error", "probe returned no readable JSON result")}
    report["checks"]["python_numpy_matplotlib_cjk_plot"] = {**details, "exit_code": plotting["exit_code"], "seconds": plotting["seconds"], "log": "plot_probe.log"}
    xe = executable(args.xelatex)
    version = run([xe, "--version"], output, args.timeout, env)
    (output / "xelatex_version.log").write_text(version["output"], encoding="utf-8")
    report["checks"]["xelatex"] = {"ok": version["exit_code"] == 0, "exit_code": version["exit_code"], "error": version.get("error"), "log": "xelatex_version.log"}
    latex = {"ok": False, "status": "NOT_RUN", "reason": "plot/font or XeLaTeX prerequisite failed"}
    png = output / "doctor_plot.png"
    if details.get("ok") and plotting["exit_code"] == 0 and version["exit_code"] == 0:
        family = details.get("font_family", "")
        # Font names become TeX input. Refuse control syntax, including newlines.
        if not family or re.search(r"[\\{}%#$&^~\r\n]", family):
            latex = {"ok": False, "status": "NOT_RUN", "reason": "font family contains unsupported TeX syntax"}
        else:
            tex = r"""\documentclass[UTF8,fontset=none]{ctexart}
\usepackage{graphicx}
\usepackage[margin=25mm]{geometry}
\setCJKmainfont{""" + family + r"""}
\pagestyle{empty}
\begin{document}
中文环境测试：数学建模，图表与证据。

最小编译测试。

\includegraphics[width=0.8\textwidth]{doctor_plot.png}
\end{document}
"""
            (output / "doctor.tex").write_text(tex, encoding="utf-8")
            compile_run = run([xe, "-no-shell-escape", "-interaction=nonstopmode", "-halt-on-error", "-file-line-error", "doctor.tex"], output, args.timeout, env)
            (output / "compile_console.log").write_text(compile_run["output"], encoding="utf-8")
            log = compile_run["output"]
            if (output / "doctor.log").exists():
                log += (output / "doctor.log").read_text(encoding="utf-8", errors="replace")
            missing = [line.strip() for line in log.splitlines() if "Missing character:" in line or "does not contain requested" in line]
            pdf = output / "doctor.pdf"
            pdf_ok = pdf.is_file() and pdf.stat().st_size > 100
            if pdf_ok:
                with pdf.open("rb") as source:
                    pdf_ok = source.read(5) == b"%PDF-"
            latex = {"ok": compile_run["exit_code"] == 0 and pdf_ok and not missing,
                     "status": "RAN", "exit_code": compile_run["exit_code"], "seconds": compile_run["seconds"],
                     "ctex": "ctexart loaded by real compile" if compile_run["exit_code"] == 0 else "not proven",
                     "font_family": family, "missing_glyphs": missing, "pdf": "doctor.pdf" if pdf_ok else None,
                     "console_log": "compile_console.log", "tex_log": "doctor.log", "error": compile_run.get("error")}
    report["checks"]["ctex_chinese_font_pdf_compile"] = latex
    report["checks"]["plot_artifact"] = {"ok": png.is_file() and png.stat().st_size > 100, "file": "doctor_plot.png"}
    report["status"] = "READY" if all(item.get("ok") for item in report["checks"].values()) else "NOT_READY"
    report["exit_code"] = 0 if report["status"] == "READY" else 1
    try:
        (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        print(f"REPORT_WRITE_ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
