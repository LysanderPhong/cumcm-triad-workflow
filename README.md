# cumcm-triad-workflow

这是给**单人参加数学建模竞赛、使用 AI 协作、希望冲击省级以上成绩**的人用的工作流 Skill。

它不负责替你“自动解题”。它负责把一篇数模论文从题面到冻结版本的过程管起来：

- 你决定题意、关键假设、模型路线和最终结论；
- 执行代理负责代码、实验、整理和修改；
- 独立审核员负责复核证据、指出问题并阻断不合格结果。

它和本地 28-skill 套件是互补关系：28-skill 负责各阶段的专业产物，`cumcm-triad-workflow` 负责“谁能决定、谁要留证据、什么时候必须停下来复核”。

当前版本是 **Experimental / Release Candidate**，不是获奖保证，也不是自动论文生成器。

## 你实际要做什么

你只需要持续完成三类动作：

1. **做决定**：用自己的话确认题意、假设、路线和主张范围，并把决定记入台账。
2. **看证据**：检查代码是否真的运行、数字是否能追溯、图表和论文是否符合要求。
3. **批准或退回**：审核通过才进入下一门；发现问题就退回执行代理修复。

AI 可以完成机械工作，但不能把它自己的建议伪装成人类决定，也不能自己审核并签发通过。

## 一步一步的完整流程

### 1. 准备环境和题面

需要 Python 3.10+。先下载仓库并检查本机环境：

```bash
git clone https://github.com/LysanderPhong/cumcm-triad-workflow.git
cd cumcm-triad-workflow
python3 scripts/doctor.py --output-dir ../doctor-result
```

`doctor.py` 只检查 NumPy、Matplotlib、XeLaTeX、ctex 和中文字体，并生成最小测试图、中文 PDF 和报告；它不会自动安装依赖。macOS 缺 XeLaTeX 时，训练用途装 BasicTeX（小）即可，需要完整宏包再考虑 MacTeX。

首次使用建议先跑一遍 `examples/minimal-cold-start/` 里的示例台账熟悉事件流，再上真题；`triad.py status` 会随时告诉你已关闭的门、下一门和未决失败。

### 2. 创建项目并导入题面

把题面 PDF 和附件放在项目外部，然后运行：

```bash
python3 scripts/triad.py start ../my-modeling-project \
  --input problem.pdf attachments/
python3 scripts/triad.py status ../my-modeling-project
```

初始化器会创建以下工作区：

- `raw/`：题面和附件的项目内副本；
- `planning/decision_cards/`：人工决定卡；
- `planning/risk_cards/`：逐子问题科学风险卡；
- `logs/`：决定、运行、失败、审核、Claim 和事件台账；
- `code/`、`results/`、`paper/`、`reviews/`、`compliance/`：执行和交付材料。

导入会拒绝符号链接、重名文件和覆盖已有 `raw/` 文件。

### 3. 通过启动门和选题门

你先确认：题目、附件范围、比赛规则、三角色、可修改目录和时间起点。

然后用决策卡记录选题和范围。核心建模门不能只回复“同意”或“A/B/C”，要写出自己的方向、假设、取舍或理由。

示例：

```bash
python3 scripts/triad.py record-human ../my-modeling-project \
  --gate-id START --gate-class CORE_MODELING \
  --selected "先验证可解释基线" \
  --contribution "我先用可解释基线检验变量关系，再决定是否增加非线性模型。" \
  --rationale "先保留同口径基准，便于比较。" \
  --evidence raw/problem.pdf
```

### 4. 为每个子问题填写科学风险卡

复制 `templates/scientific_risk_card.md` 到项目的 `planning/risk_cards/`，每个子问题至少登记六类风险：

- 假设；
- 数据；
- 识别性；
- 敏感性；
- 基线；
- 越界或外推。

你要确认哪些风险适用、允许声称什么、什么情况必须收窄结论或停门。未知不能直接填成“不适用”。

### 5. 确认路线，执行建模

在路线门确认 baseline、主方法、评价指标、预算、停止条件和独立复核方式。之后才让执行代理运行数据审计、模型代码、实验和稳健性检查。

28-skill 套件可以在这里提供专业工作，例如：

- `data-auditor-cleaner`：数据审计；
- `method-selector`：方法筛选；
- `python-model-code-generator` 或 `matlab-model-code-generator`：代码生成；
- `robustness-checker`：稳健性检验；
- `math-figure-generator`：图表生成；
- `paper-section-writer`：论文写作。

本 Skill 不替代这些技能，也不自动决定使用哪个模型。

### 6. 独立审核和失败修复

执行代理交付后，独立审核员读取必要的原始题面、决定和结果，返回四种结论之一：`PASS`、`REJECT`、`BLOCK`、`ESCALATE`。

```bash
python3 scripts/triad.py record-review ../my-modeling-project \
  --gate-id MODEL --verdict PASS \
  --context-id independent-review-001 \
  --evidence results/q1_metrics.csv
```

如果审核拒绝，必须保留原失败、生成新版本、重新审核。未关闭的 blocker 不允许关门或冻结。

两点约束：`record-review` 默认记为独立审核；如果只有同一上下文自查，必须加 `--self-review-only` 如实标注，这类 PASS 会入账但不能用于关门。关门还要求前序门均已关闭，且独立 PASS 晚于该门最近一次人工批准（否则需要重新审核）。

需要打包审核材料时：

```bash
python3 scripts/triad.py review-packet ../my-modeling-project
```

默认生成 blind-review 包；需要检查来源链时使用 `--mode provenance-audit`。

### 7. 登记论文主张和证据链

先为每次代码运行登记台账，再登记主张。每次运行：

```bash
python3 scripts/triad.py record-run ../my-modeling-project \
  --run-id Q1-BASELINE-001 --status SUCCEEDED \
  --command "python code/q1_baseline.py" \
  --output results/q1_metrics.csv
```

`--status` 可选 `SUCCEEDED` / `FAILED` / `CANCELLED`；SUCCEEDED 必须声明实际存在的输出文件。

论文里的关键数字和结论登记到 `logs/claims.jsonl`。每条 Claim 必须关联：

- 项目内真实证据文件；
- 产生这些文件的成功运行；
- 若已批准，还要关联人工决定和独立审核事件。

```bash
python3 scripts/triad.py record-claim ../my-modeling-project \
  --claim-id C-Q1-01 --text "基线模型在验证集上 RMSE=0.83" \
  --evidence results/q1_metrics.csv --run-id Q1-BASELINE-001
```

登记时即做校验：引用的运行不存在、未成功、或证据不在该运行的输出里，都会被当场拒绝。之后运行检查：

```bash
python3 scripts/claim_check.py ../my-modeling-project
```

退出码 0 表示证据链没有发现断裂；退出码 2 表示缺失、失败、越界或未声明的引用。它不能证明数学命题本身正确。

### 8. 写论文、做图和自查

论文完成后，先准备同方向优秀论文样本，再运行：

```bash
python3 scripts/paper_review.py \
  --paper paper/draft.md \
  --reference references/good-paper.pdf \
  --decision-log logs/human_decisions.jsonl \
  --figure-manifest paper/figures/figure_manifest.json \
  --output-html paper/paper_review.html
```

HTML 页面用于检查结构、篇幅、表达深度、验证线索、套话、重复句式和证据不足的强结论。用户逐条决定是否修改。

图表统一遵守 `references/visual_style.md` 和 `templates/figure_style.json`：低饱和色、统一字体字号、扁平风格、无阴影/3D/渐变，并按表达目的选择图表类型。

这个工具不计算 AI 百分比，不自动改写论文，也不建议为了降低所谓 AI 率而删除真实 AI 使用披露。

### 9. 合规、终审和冻结

最后检查：

- 当前年份官方论文格式；
- AI 使用规定和真实披露；
- 源码、附件、图表、引用和匿名信息；
- 四个独立状态：官方提交资格、科学准备度、奖项竞争力评估、可选安全检查。

所有前置门关闭、失败清零、独立审核通过、Claim 检查通过后，才可以冻结：

```bash
python3 scripts/triad.py close-gate ../my-modeling-project --gate-id COMPLIANCE
python3 scripts/triad.py freeze ../my-modeling-project \
  --confirmation "我确认冻结当前版本，已核对题面、证据、审核、论文和合规材料。"
```

## 你和 AI 的分工

| 事项 | 你 | 执行代理 | 独立审核员 |
|---|---|---|---|
| 题意、假设、路线和主张范围 | 决定 | 提供选项 | 挑战是否有依据 |
| 数据、代码、实验和排版 | 批准范围 | 执行并记录 | 复算和抽查 |
| 失败和修复 | 决定是否接受 | 修复并保留旧证据 | 复审 |
| 最终冻结 | 签发 | 准备材料 | 确认没有未决阻塞 |

如果只有同一个 AI 上下文自查，状态必须写成 `SELF_REVIEW_ONLY`，不能冒充独立审核。

## 与 28-skill 套件的关系

28-skill 套件主要回答“这个阶段要生成和检查哪些专业产物”；本 Skill 主要回答“谁有决定权、谁不能自证、证据不够时什么时候停”。两者可以一起使用，也可以先只使用本 Skill 的项目骨架和门控脚本。

## 常见误解

- **不是**把真题丢进去就自动得到正确论文。题意、假设、模型路线和结论仍需人类负责。
- **不是**有了审核脚本就代表数学正确。脚本只能发现证据、流程和文件问题。
- **不是**自评分数或历史 Benchmark 通过就等于获奖能力。
- **不是**通过一次最小环境检查就代表整篇论文可复现。
- **不是**用优秀论文对比就可以复制它的句子、数字或结论。

## 诚实边界

| 内容 | 当前状态 |
|---|---|
| 决策入账、失败如实、数字可追溯、证据实测 | 【两轮验证】 |
| 越权即停、完整三角色组织 | 【单轮验证】 |
| 科学风险卡的历史风险来源 | 【两轮验证】 |
| 风险卡动态生成和自动消费 | 【未验证】 |
| Claim→证据→运行链的当前完整科学效果 | 【单轮验证】 |
| 完整 A-H 冷启动、30 分钟 SLA、72 小时闭环 | 【未验证】 |
| 第三套题跨题型通用性 | 【未验证】 |

本 Skill 不保证获奖，也不输出 AI 百分比。正式比赛前必须核对当年官方规则和 AI 使用规定。

## 参考资料

- [SKILL.md](SKILL.md)：给 Codex 读取的入口协议；
- [阶段门](references/stage_gates.md)；
- [科学风险卡](references/scientific_risk_cards.md)；
- [Claim 证据链](references/claim_evidence_run.md)；
- [五条铁律](references/five_rules.md)；
- [论文对比与写作自查](references/paper_comparison.md)；
- [图表视觉规范](references/visual_style.md)；
- [官方合规清单](references/official_compliance.md)；
- [两个脱敏案例](examples/benchmark_01_lessons.md) 和 [B02 案例](examples/benchmark_02_case_study.md)。

当前公开版本：[v1.0.0-rc.6](https://github.com/LysanderPhong/cumcm-triad-workflow/releases/tag/v1.0.0-rc.6)。欢迎用独立旧题测试，但请把测试结果与正式第三套题验证分开记录。
