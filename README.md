# cumcm-triad-workflow

轻量的数模 AI 协作 Skill：人决定题意和路线，代理执行并保存证据，独立上下文复核结果，最后由人确认交付。

## 默认流程

| 阶段 | 必需动作 |
|---|---|
| SCOPE：题意与口径 | 人确认任务、关键假设与评价口径 |
| ROUTE：路线 | 人确认基线、主方法和预算；已授权的机械工作直接执行 |
| RESULTS：结果 | 运行模型和检验，登记关键主张，独立审核当前产物 |
| DELIVERY：交付 | 生成 PDF 和支撑包，独立检查最终页面、图表、引用、匿名与 AI 披露 |
| 冻结 | 人确认具体版本，保存交付快照 |

只有 SCOPE、ROUTE 和最终冻结是默认人工判断点。不再要求每一步填卡、写长理由或逐项批准排版。实质性新假设、评价口径或路线变化回到相应判断点。

## 使用方式

Python 3.10+。把本仓库作为 Skill 放入你的代理支持的 skills 目录，或直接让代理读取 [SKILL.md](SKILL.md)。脚本管理状态和证据，不调用模型；专业建模由你的代理完成，不依赖另一个 28-skill 套件。

```bash
git clone https://github.com/LysanderPhong/cumcm-triad-workflow.git
cd cumcm-triad-workflow
python3 scripts/triad.py start ../my-project --input /path/to/problem.pdf /path/to/attachments
python3 scripts/triad.py status ../my-project
```

代理从用户真实答复提取简短判断并登记：

```bash
python3 scripts/triad.py record-human ../my-project --gate-id SCOPE \
  --selected "按时间划分训练与验证集" --contribution "目标是评估未来预测，不能随机打乱时间。"
python3 scripts/triad.py close-gate ../my-project --gate-id SCOPE
python3 scripts/triad.py record-human ../my-project --gate-id ROUTE \
  --selected "先跑可解释基线" --contribution "复杂模型只有在同口径验证中改善结果才保留。"
python3 scripts/triad.py close-gate ../my-project --gate-id ROUTE
```

题意、假设、指标和预算写入这些真实决定即可，不另填风险卡。理由可选，不以字数判断实质贡献。

代理将代码放入项目 code/，使用 run 自动保存运行记录。输出使用新版本文件名；命令在项目目录运行，不经过 shell。题面附件和命令直接引用的脚本自动绑定；额外导入模块、外部数据等依赖使用可重复的 `--input-ref` 登记：

```bash
python3 scripts/triad.py run ../my-project --run-id R1 --output results/metrics-v1.csv \
  -- python3 code/model.py
python3 scripts/triad.py record-claim ../my-project --claim-id C1 \
  --text "主方法在固定验证集上降低误差；具体数值和口径见指标表。" \
  --evidence results/metrics-v1.csv --run-id R1
python3 scripts/triad.py review-packet ../my-project
```

独立上下文读取题面、决定、代码和结果，按 [独立审核提示](templates/prompts/independent_review.md) 复核。这里的 context-id 仅用于记录，程序不能证明模型会话真的独立。

```bash
python3 scripts/triad.py record-review ../my-project --gate-id RESULTS --verdict PASS \
  --context-id reviewer-session-1 --evidence results/metrics-v1.csv
python3 scripts/triad.py close-gate ../my-project --gate-id RESULTS
```

DRAFT Claim 可以重复登记同一 ID 来修订，日志保留每次版本。若需要逐条批准，可运行 approve-claim 并引用真实人工决定事件与独立 PASS 事件；默认最终签发覆盖经审核的主张，无需逐条额外审批。修改 Claim 的文字或证据后重新审核结果；只调整批准状态不会重复触发科学审核。

## 论文、图表与交付

正文根据实际子问题组织“任务、模型、求解、结果与检验、局限”。篇幅、摘要字数和图表数量由题目及用户要求决定，不设凑字数或每问图表配额。示例视觉配置见 [figure_style.json](templates/figure_style.json)，页面配置见 [paper_layout.json](templates/paper_layout.json)。

```bash
python3 scripts/paper_review.py --paper ../my-project/paper/final.pdf \
  --output-html ../my-project/reviews/paper_review.html
python3 scripts/claim_check.py ../my-project
```

参考论文和 figure_manifest.json 均可选。自检结果是解析与写作提示，不代替真实页面检查。复跑报告和审核包会自动生成新文件名。

交付审核实际查看最终 PDF，并明确记录以下检查：

```bash
python3 scripts/triad.py record-review ../my-project --gate-id DELIVERY --verdict PASS \
  --context-id reviewer-session-2 --evidence paper/final.pdf \
  --check rendered_pdf --check figures_tables --check references \
  --check anonymity --check ai_disclosure --check supporting_files
python3 scripts/triad.py close-gate ../my-project --gate-id DELIVERY
python3 scripts/triad.py freeze ../my-project --version v1 \
  --confirmation "我确认交付这一版，已核对结果、论文和支撑材料。"
```

freeze 重新检查有效审核、运行、Claim 和 PDF，再保存 releases/v1/ 快照与指纹清单。PDF 文件头检查仅证明存在候选 PDF；实际缺字、溢出、图表和页面问题必须由交付审核查看。冻结不提交比赛材料。

## 修复与继续

故障只登记具体问题，不重复创建风险卡。close-failure 需要真实修复与复测文件；修复后的新产物重新审核。后来的拒绝使旧 PASS 失效。修改输入、代码或产物后，旧运行或审核不能用于冻结。

```bash
python3 scripts/triad.py record-failure ../my-project --description "指标口径不一致"
# 按返回的 failure_id，修复并取得复测证据后执行：
python3 scripts/triad.py close-failure ../my-project FAILURE_ID \
  --repair-ref code/model.py --evidence results/metrics-v2.csv
```

新附件可用 ingest 导入；它保留题意和路线决定，将已有结果及交付批准失效。冻结后修改须另开工作版本：

```bash
python3 scripts/triad.py reopen ../my-project ../my-project-v2
```

## 文件与兼容性

只有 logs/events.jsonl 是权威记录；状态、故障与 Claim 都从事件生成，不再手动维护 project_state.json、十套专用台账或门注册表。运行控制台输出作为证据保存在 logs/，审核包在 reviews/，交付快照在 releases/。

这是 2.0 项目格式，旧版九门项目不原地迁移或覆盖。脚本会明确拒绝旧版目录；保留旧项目，在新目录试用，并按真实情况导入原始附件。旧的三套测试已由 [生命周期测试](validation/test_workflow.py) 替代。

```bash
python3 validation/test_workflow.py
```

可选工具：doctor.py 检查环境，anonym_scan.py 查找配置的身份线索，hash_check.py 核验已有指纹清单。它们按需求使用，不强迫开局先安装 XeLaTeX；可用自己的排版环境。

[图表检查要点](references/visual_style.md) · [论文页面检查](references/paper_format_profile.md) · [官方合规检查](references/official_compliance.md)。比赛要求以适用的当年官方原文为准。本工具不保证数学正确或获奖，不计算 AI 百分比。
