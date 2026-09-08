---
name: cumcm-triad-workflow
description: "Run a human-led CUMCM workflow with decision gates, bounded AI execution, independent review, traceable failures and submission checks. Use for single-person mathematical-modeling rehearsals or contest collaboration; complements stage-specific modeling skills. Do not use for a standalone calculation or assume it authorizes submission."
metadata:
  short-description: "数模三角色协作与证据门禁"
---

# cumcm-triad-workflow

适合以单人参赛、AI 协作、争取省级以上成绩为目标的数模训练或 CUMCM 参赛工作；成绩是使用者的目标，不是本 Skill 的能力证明。它与 28-skill 套件互补：后者组织各阶段产物，本 Skill 约束决策权、执行范围和独立审核。当前发布候选为 Experimental / Release Candidate：部分机制有 Benchmark 02 历史单轮证据，当前打包版本的冷启动行为仍待验证。参赛资格与当年规则另行核实。

## 三角色协议【单轮验证】

| 角色 | 职责 | 不能自行完成的事 |
|---|---|---|
| 人类决策者 | 理解题意，批准目标、关键假设、价值取舍、路线、解释与最终冻结；在核心建模门留下简短但实质的方向、修改或理由 | 不能用一句“同意”把未完成的技术检查变成通过 |
| 执行代理 | 提出选项，在明确授权范围内实现、运行、记录、修复并准备可审查交接 | 不能把自己的建议或默认值冒充人工答案；不能自行关闭独立审核发现 |
| 独立审核员 | 用原始题面、决策与当前产物挑战语义、数字、执行和合规；可阻断、退回、复测 | 不能为通过审核改生产结果，也不能替人工选择价值取舍 |

角色是权限和上下文边界，不要求不同品牌模型。独立审核使用独立上下文，读取必要原始材料；执行代理摘要只作为待核对主张。独立实现也可能共享错误假设（B02 Cycle 03），必须把“实现一致”与“语义获批”分别检查。若只有同一上下文自查，标为 `SELF_REVIEW_ONLY`，不冒充独立审核。

## 核心建模与门类别

每张决定卡填写 `gate_class`：`CORE_MODELING`、`IMPLEMENTATION`、`PRESENTATION` 或 `ADMINISTRATIVE`。问题解释、目标与关键假设、模型族、目标函数、主要约束、评价方法、重大模型变化、关键结果解释和最终科学结论均是 `CORE_MODELING`。核心门中，单独回复“A/B/C”或“同意”不能证明人类主导；人类须先提出方向、修改代理提案，或用自己的话简短说明相关假设、取舍或解释，并写入 `logs/human_decisions.jsonl`。这不是长篇作文要求。图形格式、文件名、已批准模型内的执行参数、存储位置和预授权回退可属于其他类别，按合同做轻量记录。

训练中可以安排外部真人盲审；正式比赛按参赛规则只用队内人类或独立 AI 会话审核，单人参赛者仍须逐项核验核心成果。不得把三角色当作比赛期间向队外真人咨询赛题的许可，见 [官方角色边界](references/official_compliance.md)。

尊重已存在的明确授权：预批准的机械处理或回退不用重复请示；新的目标、关键语义、路线取舍或冻结必须有相应人工记录。未提供的理由记 `NOT_PROVIDED`，未捕获的事件时间记 `UNKNOWN`。

## 阶段门

启动 → 选题 → 定义 → 路线 → 逐问建模 → 论文 → 排版 → 合规 → 终审冻结。只推进当前具备证据的一门；缺少前置事实时只做不依赖它的工作。

读取 [阶段门清单](references/stage_gates.md)，按每门准入、准出及成熟度执行。G2/G3/G4 是 B02 的历史门名，不能直接套用其他技能中同名门的含义。完整三角色组织【单轮验证】；阶段表中的 30 分钟响应 SLA 是拟定规则【未验证】，见 [人工门时限](references/human_gate_sla.md)。超时不是授权：只有事前明确批准的回退能执行，否则停止依赖该决定的工作。

## 五条铁律

| 纪律 | 最小执行要求 | 成熟度 |
|---|---|---|
| 决策入账 | 人工原话、代理建议与自主执行分开；变更追加 `supersedes`；结果后裁决显式披露 | 【两轮验证】 |
| 失败如实 | 保留原失败，追加修复、复测和关闭；未知、取消、运行失败不写成成功 | 【两轮验证】 |
| 数字可追溯 | 主张绑定实际运行、指标口径和权威数据字段；历史结果与当前结果分开 | 【两轮验证】 |
| 证据实测 | 代码存在、退出码、自报 PASS 各有范围；按主张做边界、残差、独立复算、渲染或冷启动 | 【两轮验证】 |
| 越权即停 | 授权、语义、预算或保护范围冲突时停止相关动作，记录并回门 | 【单轮验证】 |

首次使用读 [五条纪律与事件](references/five_rules.md)；出现相似问题时读 [陷阱清单](references/pitfalls.md)。两轮验证只表示两轮均有相关证据，不代表统计保证或第三套题通过。

## 启动与交接

1. 在空目录运行 `python scripts/triad.py start path/to/project --input problem.pdf attachments/`，即可初始化并导入题面；也可单独运行 `init_project.py`。随后用 `triad.py status` 查看下一步。初始化器只创建标准目录和空台账，不复制 Benchmark 数据，也不覆盖已有生成路径。
2. 填入题面附件、角色、时钟和已有授权。没有上下文不要假定任何 Gate 已过；核心门必须取得实质人类贡献。
3. 使用 Python 3.10+ 运行 `python scripts/doctor.py --help`，在独立输出目录做环境探针。失败报告不能冒充环境就绪，也不自动授权安装依赖。
4. 用 [决策卡](templates/decision_card.md) 和 [人工门提示](templates/prompts/gate_human.md) 准备一个真实判断点。人工答案进入项目 `logs/human_decisions.jsonl`；机械决定或已批准回退才使用 [自主决定模板](templates/autonomous_decision.jsonl)。
5. 执行后提交 [交接报告](templates/handoff_report.md)，由隔离审核任务采用 [独立审核提示](templates/prompts/independent_review.md)。审核员只能 PASS、REJECT、BLOCK 或 ESCALATE；REJECT/BLOCK 后由执行者生成新版本，审核员重新审核，不能自修生产结果后自证 PASS。
6. 从开局按阶段、用途和影响范围保存真实 AI 交互，使用 [AI 使用详情模板](templates/ai_usage_disclosure.md) 和 `templates/logs/ai_usage.jsonl` 分组记录；高影响或代表性事件保留精确原始引用，不要求复制每条聊天。提交前读 [2026 官方合规清单](references/official_compliance.md)，核对当年官方原文与实际 PDF/支撑包。
7. 冻结时分别记录官方提交资格、科学证据准备、奖项评估、可选安全检查。任一状态的 PASS 不传递给其他状态；本 Skill 的脚本也不会替人签发或自动发布。

`scripts/triad.py` 只编排可逆的机械工作：导入文件、汇总状态、追加人工决定和生成审核包。它不替人批准核心模型、关闭失败或冻结提交；审核包交给独立上下文后仍须人工处理 `REJECT/BLOCK/ESCALATE`。

## 工具和证据边界

- `scripts/doctor.py`：检查指定 Python 与排版运行时并生成最小图/PDF；只证明本机最小环境探针。
- `scripts/hash_check.py`：按指定清单核对文件 SHA-256；仅证明文件与给定指纹一致，不证明数学或语义正确。只在授权的完整性或版本指纹场景使用，遵守项目计算次数约束。
- `scripts/anonym_scan.py`：查找身份线索；不能替代人工审查或 OCR，PDF 无法提取时必须报告未完成。

历史因果和全部出处见 [演进记录](references/evolution.md)；应用实例见 [B01 教训](examples/benchmark_01_lessons.md) 与 [B02 案例](examples/benchmark_02_case_study.md)。历史 Benchmark 证据与当前打包版本验证分开：静态文件检查可为 `VERIFIED`，Benchmark 02 三角色仅为 `SINGLE-RUN VERIFIED / historical`；当前 Skill 的冷启动、越权停止、审核否决、修复复审和人工门行为在实际运行前均为 `UNVERIFIED`。案例来源是文件证据，不把自评当成绩证明。不保证获奖；72 小时时间轴及跨题型通用性【未验证】，须由第三套独立题目检验。
