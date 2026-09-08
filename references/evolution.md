# cumcm-triad-workflow：两轮 Benchmark 的演进逻辑

> 状态：按人工审核通过的演进草稿定稿；保持已批准成熟度。
>
> 资料边界：本稿只根据 Benchmark-01、Benchmark-02 的本地产物与当前已安装技能目录归纳；没有把自评分数、未运行的 72 小时回放或跨题型推断写成能力证明。
>
> 成熟度标记：
> - **【两轮验证】**：Benchmark-01 与 Benchmark-02 均有直接证据。
> - **【单轮验证】**：只有一轮有直接证据，或另一轮只提供相似迹象。
> - **【未验证】**：当前两轮没有足够证据，必须保留为假设、待测或边界。

## 证据定位约定

`benchmark_01/...` 与 `benchmark_02/...` 是原始资料仓库 `benchmark/` 下的相对来源标识；未随 Skill 复制的原始文件不伪装成公开附件。`planning/reviews/deepseek_review_audit_2026-08-27.md` 是原项目根目录下的 B01 上游记录。独立发布时保留标识并补获准脱敏的证据镜像或索引。这里更新 Skill，不改原始证据。

成熟度表示已有几轮支持该做法，不是成功率、获奖率或外部认证。四纪律【两轮验证】与完整三角色实现【单轮验证】分开。30 分钟 SLA 是由等待失败导出的新设计【未验证】。本文件记录的是历史机制证据；当前发布候选的静态完整性可单独标为 `VERIFIED`，但空项目冷启动、核心门实质人类贡献、执行者越权停止、审核否决与修复复审必须用当前打包 Skill 另行测试，未测试时均为 `UNVERIFIED`。

## 1. 先核对素材，而不是接受预设叙述

草稿核对时，本地技能目录实际有 31 个含 `SKILL.md` 的非系统技能目录。按数学建模核心套件口径，可对应 28 个；另外 3 个是 `big-jump`、`competition-2026` 和 `competition-2026-practical`。因此下文使用“28-skill 核心套件（目录总数 31）”这一口径，避免把目录计数误写成已确认事实。

Benchmark-01 是 2025 C 题的单人建模回放，原有技能未修改；冻结文件显示解答/清单哈希已冻结，但最终报告和外部审查仍可在冻结后追加。Benchmark-02 是 2023B 的另一轮回放，使用 G2/G3/G4 决策卡、人工与代理台账、独立只读审核、repair round 01–25，并在 `benchmark_02/reviews/PROJECT_FROZEN_20260906.md` 记录了最终冻结状态。

## 2. Benchmark-01 暴露了什么

### 2.1 首要问题是“语义翻译晚于建模”

题面自然语言被翻译为事件、删失区间、损失函数和目标后，错误会产生合理外观的数字，普通拟合诊断未必能发现。

| 真实事件 | 证据文件 | 自查/外审情况 | 后果 | 成熟度 |
|---|---|---|---|---|
| 首次观测已阳性的 217 名患者被编码为 `[70,U]`，应为 `(0,U]` | `benchmark_01/failures.md` F-001；`benchmark_01/final_benchmark_report.md` §2–§3 | 系统语义审计后来抓到，但发生在下游建模之后 | Q2/Q3 似然、分布排名、分组及时点全部需要重建 | 【单轮验证】 |
| Q3 延迟损失混用旧边界与归一化，AFT 层本身正确但策略层错误 | `benchmark_01/failures.md` F-002；`benchmark_01/human_interventions.md` H-006；原项目 `planning/reviews/deepseek_review_audit_2026-08-27.md` | 用户提供的外部 DeepSeek 审查先指出，系统再按题面独立核对 | 推荐日和风险解释失真；最终统一为 70/91/196 日口径 | 【单轮验证】 |
| Q2 bootstrap 重新估计分组边界，却用固定 `30.5/32.9` 计算时点 | `benchmark_01/external_review/blind_review.md` M1 | 冻结前自查没有阻断，阶段 A 外部盲审逃逸发现 | 论文把条件区间写成联合不确定性，区间语义错误 | 【单轮验证】 |
| Q4 工作阈值用全部 OOF 标签选择，又在同一标签上报告性能 | `benchmark_01/external_review/blind_review.md` M3 | 普通患者隔离和 OOF 检查通过，但独立盲审发现阈值层泄漏 | PR-AUC 等主排序仍有证据，阈值 0.0780 的泛化解释不成立 | 【单轮验证】 |

这说明“患者隔离”“有基线”“有 bootstrap”并不自动保证题意、损失和操作点正确。最大风险在定义层，而不是算法名称层。

### 2.2 发布合规和复现合同被放到了太后面

| 真实事件 | 证据文件 | 外部才发现的内容 | 成熟度 |
|---|---|---|---|
| 冻结论文附录只有目录，没有源程序正文；ZIP 有源码不能替代论文附录 | `benchmark_01/external_review/blind_review.md` C1；`benchmark_01/external_review/gap_matrix.md` G-01 | 阶段 A 盲审才把它定为 Critical；原最终自评没有拦截 | 【单轮验证】 |
| README 复现命令缺 `--mode`、默认 smoke、正式 marker 会阻断重跑，且无精确依赖锁 | `benchmark_01/external_review/blind_review.md` M2 | 外部在干净目录重放时发现；“有代码”被误当成“可冷启动复现” | 【单轮验证】 |
| AI 使用详情只有代表性摘要，且声称 ZIP 含不存在的 Benchmark 日志 | `benchmark_01/external_review/blind_review.md` M4；`benchmark_01/final_benchmark_report.md` §3 | 外部合规审查才发现关键交互证据不足；需要补真实关键提示—回答和精确包成员核对 | 【单轮验证】 |
| 2025 规则要求的 AI 标注/工具引用/详情文件在首版 QA 漏掉 | `benchmark_01/failures.md` F-032；`benchmark_01/final_benchmark_report.md` §3–§4 | 最终 QA 独立检查才发现；数学结果已冻结仍不能称正式合规 | 【单轮验证】 |

### 2.3 自评分数为什么不可信

Benchmark-01 内部记录了 33 条 failure（3 Critical、12 Major、18 Minor），其中 29 条由系统自动发现并修复，2 条由用户外部审查触发后修复，1 条需要人工拒绝 Q1 round1 并重建，另有 1 条 Minor 的 `NaN` 仍保留。`benchmark_01/final_benchmark_report.md` 的 `PASS WITH MATERIAL LIMITATIONS` 只描述修复链完成度，不证明第一次运行正确。

更强的反例来自冻结后的阶段 A 外部盲审：在不依赖自评叙述的情况下，又逃逸出 1 个 Critical、5 个 Major、3 个 Minor（C1、M1–M5、m1–m3）。`benchmark_01/external_review/gap_matrix.md` G-15 进一步构造了“缺源码附录、README 冷启动失败、Q4 阈值复用”仍可被连续评分掩盖的情形。由此可得：**自评可作为状态摘要，不能作为发布资格的唯一证据。**【单轮验证】

### 2.4 人工并不是“多点一下继续”，而是承担不可自动化的责任

`benchmark_01/human_interventions.md` 记录的实质干预包括：确认 Q2/Q3 早失败与延迟风险语义、确认 Q4 的 AB-any 目标、选择实验预算、拒绝 Q1 round1、授权后续 A/B/C 选择、提供外部批评、启用隔离与独立审查。它们共同表明：价值函数、目标语义、路线改变和最终签发不能从数字自动推出。【单轮验证】

B01 的 F-002 与阶段 A 的 M1 是不同失败：前者是延迟损失边界，后者是 bootstrap 的联合不确定性误述，不能混用来源。B01 外审的 AI 交互要求针对当轮适用的 2025 规则；不得移植为 2026 强制条款，见 [官方合规](official_compliance.md)。

## 3. 为什么 Benchmark-02 引入三角色

Benchmark-01 的阶段 checklist 已经能保存失败、冻结数字、做患者级验证和多种审计；它仍存在同源盲区：同一执行链可以定义目标、运行模型、写报告，再用自己的摘要证明自己完成了这些步骤。Benchmark-02 因此把“阶段”之外的权责拆开：

1. **人类决策者（Human decision）**：确认题意、目标、损失/偏好、方法路线、范围和最终放行；只对自己实际说过或批准过的内容负责。
2. **执行代理（Execution agent）**：只执行已批准卡片，运行代码、生成结果、记录失败和交接；不能把默认值升级为人类决定，不能改变目标后继续运行。
3. **独立审核（Independent review）**：不共享执行代理的自评结论，沿不同证据路径做静态核对、复算、冷启动或盲审；发现 blocker 就阻断状态，不替生产链润色成 PASS。

三角色不是把一个 checklist 再切成三份，而是把“谁有权决定、谁负责执行、谁不能自证”横切到每个阶段。Benchmark-02 的 G2/G3/G4 卡、`logs/human_decisions.jsonl`、`logs/failures.jsonl`、`logs/ai_usage.jsonl`、`logs/route_changes.jsonl` 与独立审核目录共同把这层区分落到文件和状态上。【单轮验证】

## 4. 五条纪律与真实失败映射

### 4.1 决策入账（decision ledger）

**纪律**：人类选择必须追加到唯一台账；选择卡推荐、代理默认值、外部意见和人工理由分栏保存；没有人类记录就保持 `PENDING/UNKNOWN`，不能靠“看起来合理”补齐。

**真实来源**：

- Benchmark-01 H-001、H-003、H-004：Q2/Q3 语义、Q1 重建和后续委托若不区分，最终方法归因会被 AI 叙述吞掉；见 `benchmark_01/human_interventions.md`。
- Benchmark-01 F-008：Q1 round1 不是机器自动“修好”，而是人类拒绝后才重建；见 `benchmark_01/failures.md`。
- Benchmark-02 `benchmark_02/planning/decision_cards/g4_boundary_overlap_definition_v1.md` 与 `benchmark_02/planning/g2/g2_definitions_v3.md`：Cycle 03 发现 Q4 边界口径虽已被 AI 写入方法卡，却没有人工授权；用户后来只回复 A，且文件明确记录为“结果后补充裁决”，不能伪装成事前决定。

- Benchmark-02 Round-16：Round-15 manifest 声称 H1(a) 已确认，但 Round-14 卡仍 `selection_made=false`，台账没有对应 H1(a)、H3 和历史输入边界决定。审查保留 141 项对账的技术事实，却将授权视图置为 `UNKNOWN/UNDECIDED`，总体 `BLOCKED`。两个 Major 只写入本轮受限审查目录，没有改日志。见 `benchmark_02/reviews/repair_round_16/round16_semantic_reconciliation.md`、`benchmark_02/reviews/repair_round_16/human_decision_card_round16.md`。Round-17 才引用人工本人补记的 `CONFIRM_ROUND14_THREE_FACTS`，见 `benchmark_02/reviews/round17_provenance_fix_handoff.md`。

**成熟度**：Benchmark-01 已有人工干预日志，Benchmark-02 已把选择卡、JSONL 和后置裁决时序连起来，故此纪律【两轮验证】；“所有题型都能用同样卡片解决”仍【未验证】。

### 4.2 失败如实（failure honesty）

**纪律**：失败追加、不覆盖；区分科学失败、机械失败、合规 blocker、越权事件和未验证状态；修复只能追加关闭证据，不能把历史 FAIL 改写为从未发生。

**真实来源**：

- Benchmark-01 F-001/F-002 与未解决的 `NaN`：修复成功不等于首轮没错；见 `benchmark_01/failures.md`。
- Benchmark-02 Q4 节点刺点覆盖失败 `B02-Q4-NODE-COVER-001`：离散节点通过但单元内部连续覆盖漏测 3.314%，随后追加关闭证据；见 `benchmark_02/logs/failures.jsonl`。
- Benchmark-02 `B02-S3-2-PYPDF-RUNTIME-001`：正式 preflight 因同一 init 解释器缺 `pypdf` 返回退出码 4，不能把 init 成功写成 preflight PASS；见 `benchmark_02/reviews/s3_2_preflight_block_20260904.md`。
- Benchmark-02 Round-11 越权事件 `B02-PAPER-UNAUTHORIZED-FREEZE-ATTEMPT-001`：按人工要求记录为事后追认，未改写成事前授权，也未推断意图；见 `benchmark_02/reviews/repair_round_11/repair_completion_handoff_20260905.md`。

**成熟度**：两轮都保留失败历史并区分状态，故【两轮验证】。

### 4.3 数字可追溯（number provenance）

**纪律**：论文、图表、工作簿和摘要只消费注册过的 canonical/frozen numbers；每个数字能回指输入、脚本、口径、版本和复测证据；历史快照不得冒充当前头条源。

**真实来源**：

- Benchmark-01 M1/M3：边界区间语义与阈值性能虽然有数字，却不能按论文叙述回指到正确的估计过程；见 `benchmark_01/external_review/blind_review.md`。
- Benchmark-02 `B02-G4-PERCENT-001`：G4 两项百分比的派生分母不一致，绝对差和排序仍对，但高精度百分比无法由同一 canonical 分母复算；见 `benchmark_02/logs/failures.jsonl`。
- Benchmark-02 `B02-G4-FINAL-CARD-B1-SLACK-001`：决策卡把 baseline 的松弛误配给 Q4-B1，且可能把 `rho` 构造参数说成现实误差稳健性；修复后才交给人工；见 `benchmark_02/planning/decision_cards/g4_rho0_final_route_v1.md` 与对应 failure 台账。
- Benchmark-02 Round-15/17：候选 ZIP 从 140 项变为实际 141 项，历史 G4 JSON 明确标为 `HISTORICAL_SNAPSHOT`，Round-17 又修正 README 生成器 provenance；见 `benchmark_02/reviews/round15_completion_handoff.md`、`benchmark_02/reviews/round17_provenance_fix_handoff.md`。

**成熟度**：冻结数字、来源链和历史快照在两轮均有证据，故【两轮验证】；统一跨语言、跨题型 schema 仍需第三轮检验，标【未验证】。

### 4.4 证据实测（evidence must be measured）

**纪律**：状态只由实际运行、复算、渲染、冷启动或盲审证据驱动；“脚本存在”“自评 PASS”“曾经生成过”不能替代当前门的实测。

**真实来源**：

- Benchmark-01 C1/M2/M3/M5：论文附录、干净复现、阈值层和端到端时限都在外部实测下失败；见 `benchmark_01/external_review/blind_review.md`。
- Benchmark-02 `B02-Q4-NODE-COVER-001`：节点/边界采样通过不等于 whole-cell 连续覆盖，实测连续截面才发现漏测；见 `benchmark_02/logs/failures.jsonl`。
- Benchmark-02 S3-1 空字体缓存导致真实绘图脚本 preservation guard 失败，复制缓存后才形成证据；见 `benchmark_02/logs/failures.jsonl` 与 `benchmark_02/reviews/s3_1_figure_latex_evidence_81fe191d-f780-4b30-8437-27061c503ed4.json`。
- Benchmark-02 `PROJECT_FROZEN_20260906.md` 最终把四个发布状态分开：官方资格 READY，但科学准备度和奖项竞争力仍 `NOT_ASSESSED`，安全保证 `NOT_RUN`；这不是把一项实测外推成全部通过。

**成熟度**：实测门禁与 fail-closed 在两轮都出现，故【两轮验证】；完整 72 小时端到端回放仍【未验证】。

### 4.5 越权即停（stop on scope/authority breach）

**纪律**：执行代理发现目标、口径、权限或保护范围不一致时立即停；不自行改题意、改损失、改验证器、换算法族、补人工事实或用事后批准掩盖事前越权。

**真实来源**：

- Benchmark-01 H-004 明确了委托边界；没有这条边界，后续 A/B/C 选择会变成未声明的 AI 决策；见 `benchmark_01/human_interventions.md`。
- Benchmark-02 `B02-Q4-BOUNDARY-ETA-SEMANTIC-001`：独立审核发现 G2 冻结语义与实现不一致，立即暂停 Q4 技术晋级，生成 A/B/C 人工重冻结卡；见 `benchmark_02/reviews/g4_rho0/cycle_03/external_proof_verdict.md`。
- Benchmark-02 `B02-Q4-HEURISTIC-BUDGET-001`：启发式投影 474.36 分钟超过 180 分钟上限，随机数生成器未实例化，按预登记回退保留 B1/B0；见 `benchmark_02/logs/failures.jsonl`、`planning/decision_cards/g4_route_freeze_v1.md`。
- Benchmark-02 G4 最终路线卡：外部审核发现 A/B 共同的搜索族和“不得声称无约束全局最优”边界只写进 A，先修卡再交人工；见 `B02-G4-FINAL-CARD-COMMON-CLAIM-SCOPE-001`。

**成熟度**：至少有 Q4 语义 blocker、预算取消和卡片修复三类直接证据，故【单轮验证】；要证明代理在第三套题中仍能稳定停住，暂【未验证】。

## 5. G2/G3/G4 如何把三角色写进流程

- **G2：先定语义再算。** `benchmark_02/planning/g2/g2_definitions_v3.md` 只在用户选择 A 后才把 Q4 边界 `W/O/η` 的“目标域内有效条带”定为权威口径；文件明确这是结果和 Cycle 03 审查之后的人工补充裁决。它把“实现已经这样做”与“人类已经批准这样做”分开。【单轮验证】
- **G3：先 baseline，再授权复杂度。** `benchmark_02/planning/decision_cards/g3_route_and_parameters_v1.md` 规定 A/B/C 完整包、不同分辨率独立验证、收益门槛、回退条件和随机预算；Benchmark-02 实际冻结为 B-CAPPED，未因潜在收益而启动超预算启发式。【单轮验证】
- **G4：技术通过不等于最终路线。** `benchmark_02/planning/decision_cards/g4_route_freeze_v1.md` 和 `benchmark_02/planning/decision_cards/g4_rho0_final_route_v1.md` 将 Q4-B1、固定 `rho=0` 候选、零设计裕量、共同搜索族边界和“不得声称无约束全局最优”分开；Cycle 06 外审先修共同 claim scope，人工随后才冻结 `rho=0` 为主方案。【单轮验证】

repair round 01–25 的教训不是“多做几轮就会自动正确”，而是把同一控制原则反复落地：R01–R02 证明图形 replay 不能升级为模型 cold-start；R03–R05 收窄“最优/PASS”措辞并暴露附录/排版政策缺口；R06–R10 把脚本角色、发布状态和人工事实改成 `NEEDS_HUMAN`/`BLOCKED`，不让自报字段冒充外部事实；R11–R12 记录越权审查、路径修复和首次 `PosixPath` 序列化失败；R13–R17 对账候选包、Round-16 无依据人工确认和 README provenance；#18–#20 收尾 141/142 当前与历史口径；#21–#25 反复补齐 AI 披露、源码附录、预检依赖与最终冻结。当前 B02 `benchmark_02/logs/failures.jsonl` 为 **36 行、30 个非空唯一 failure ID**。**Critical 2 / Major 18 / Minor 15** 是含关闭/复测的记录行口径，另有 1 行无严重度的时间更正；不是 30 个唯一失败的严重度分布。同一 `B02-F-001` 有重复历史行。Round-16 的两项 Major 不在该台账中，不暗中加入统计。不与 B01 内部 33 条或外审 9 条直接相加。【单轮验证】

## 6. Benchmark-02 说明了什么变化

### 6.1 变化不是“多写几份日志”，而是把决策、执行、审核分离

Benchmark-02 先记录候选题源隔离和误触公开解答的 `B02-F-002`，随后在 Q1/Q2/Q3/Q4 逐题采用 baseline→主方法→独立验证；G2/G3/G4 选择卡规定人工必须选择的点；`logs/` 台账保存决定、失败、AI 使用和路线变化；repair round 01–25 不断纠正 provenance、事实归因、排版/附录边界、AI 披露和 preflight 误报。最终冻结报告明确：论文与支撑包冻结，官方提交资格 READY，但科学准备度和奖项竞争力仍 NOT_ASSESSED。【单轮验证】

### 6.2 这些纪律分别挡住了什么

- 决策入账挡住“AI 推荐被写成人类选择”和“结果后口径被伪装为事前批准”。
- 失败如实挡住“修复后删除原 FAIL”“init 成功冒充 preflight 通过”“越权动作被改写成授权内动作”。
- 数字可追溯挡住“历史快照、错误分母、错误 slack、图表口径和当前头条数字混用”。
- 证据实测挡住“节点采样当连续覆盖”“脚本存在当冷启动成功”“自评分数当提交资格”。
- 越权即停挡住“语义未定继续算”“预算超限仍启动随机搜索”“审核发现 blocker 后论文继续解锁”。

## 7. 与 28-skill 核心套件的本质区别

### 7.1 28-skill 套件回答“什么时候做什么产物”

从已读 `SKILL.md` 看，核心套件普遍采用：YAML `name/description` → Purpose/Role → Preconditions/Inputs → 编号 workflow → canonical output/schema → 禁止事项 → Verification → Handoff。典型链是：

`problem-parser → problem-classifier → data-auditor-cleaner → method-selector/risk probe → human choice(G2.5) → model-code-analyzer/generator → language reviewer(G3) → result/robustness → solution-package/freeze(G4) → paper/figures → consistency/completeness/QA(G6)`。

它把数据、方法、代码、稳健性、图表、写作和 QA 分成可复用职能，靠 manifest、JSONL、冻结数字、失败分类和 fail-closed 状态组织阶段。它最强的价值是产物完整、证据链可复用和流程可编排。【两轮验证】

### 7.2 triad workflow 回答“谁有权做、谁不能自证、何时必须停”

三角色横切所有阶段：人类拥有语义/价值/责任决定权，执行代理只能按卡片执行，独立审核必须从不同证据路径挑战生产结论。它直接处理 28-skill checklist 不会自动解决的同源问题：

- 同一个 AI 既写定义又写自评，容易把合理外观当正确；
- 机器推荐、人工决定、用户粘贴外部意见容易在叙述中混为一谈；
- 状态评分可能掩盖一个 release-blocking 硬失败；
- 结果后补充的口径容易被倒写成事前批准；
- “没有证据”容易被写成“已通过”或“可以提交”。

因此两者是互补关系，不是替代关系：28-skill 负责阶段能力和产物合同，triad 负责权责分离、独立性、事实归因和停止纪律。【单轮验证】

## 8. 成熟度与诚实边界

| 主张/环节 | 当前结论 |
|---|---|
| 失败追加、冻结数字、独立审核、人工决策与执行分离的必要性 | 【两轮验证】 |
| 三角色流程作为一个可复用 Skill 的完整实现 | 【单轮验证】；Benchmark-02 已运行，尚未经历第三套题 |
| 72 小时单人端到端时间轴 | 【未验证】。Benchmark-01 外审明确缺连续起止与人工活动账本；Benchmark-02 的官方时钟记录也不能自动证明 72 小时单人闭环 |
| 跨题型通用性 | 【未验证】。两轮题型与资料结构不同，但不足以支持“通用”结论，必须由 Benchmark-03 验证 |
| 自评分数是能力证明 | 否。分数只能是当前证据摘要；Benchmark-01 的外部逃逸问题已反证这一点 |
| 获奖或奖项竞争力 | 不作承诺。Benchmark-02 冻结时 `AWARD_COMPETITIVENESS_REVIEW=NOT_ASSESSED` |
| 官方合规 | 只能逐轮、逐规则、逐文件实测。Benchmark-02 冻结报告记录本轮官方资格 READY，但不把它外推到其他年份或其他比赛 |
| 哈希 | 只用于用户明确要求的完整性/版本指纹场景；哈希本身不能证明数学正确、语义正确或获奖 |


## 9. H54→H101：等待也是比赛耗时

**等待教训【单轮验证】；30 分钟 SLA 与 72 小时时间轴【未验证】。**

`benchmark_02/logs/time_log.jsonl` 的 `TIME_POLICY` 将 2026-08-29 17:52:34+08:00 设为演练起点，明确官方演练时钟包括人工等待、不暂停。最后正式时钟快照在 2026-09-01 00:12:58+08:00 为 H54.3400，active-agent 为 9.2531 小时。`benchmark_02/logs/run_log.jsonl` 同刻记录仍等待 Q4 最终人工路线。

2026-09-02 23:32:09+08:00 的盘点 `benchmark_02/reviews/progress_human_audit_20260902.md` 写明墙钟约 H101.61，仍停在该门；run_log 记录同刻创建该盘点。两观察间隔为 47 小时 19 分 11 秒，但不能断言每一分钟都属于同一种活动，没有补写活动或用户回复到达时刻。此前 G2 等待有单独日志：2026-08-31 01:21:37 至 23:27:54，共 79577 秒；两段不能混算。

B02 原计划是 **74 小时**（run_log 的 `RUNTIME_CONSTRAINTS_FROZEN_AND_G2_GATE_OPENED`），B01 外审 M5 同样指出当轮官方窗口为 74 小时。72 小时属于更紧的训练设计【未验证】，不等于当年官方赛时。见 [人工门时限](human_gate_sla.md)。

## 10. 修复链的实际来源索引【单轮验证】

编号载体并不统一：有 `repair_round_01` 至 `repair_round_16` 目录，也有 `round17_*`、`round21_*`、`round23_*`、`round24_*`、`round25_*` 和同一交接内追加的人工指令编号。不存在 `repair_round_18/19/20` 目录，不补造来源或声称 25 次同构独立实验。下表均相对 `benchmark_02/`。

| 记录段 | 实际文件 | 不能省略的教训 |
|---|---|---|
| R01 | `reviews/repair_round_01/blocker_register.md` | 139 项文件对账通过，仍缺依赖、源码附录、AI 详情、来源角色和正式状态证据。 |
| R02 | `reviews/repair_round_02/cold_start_scope_review.md`、`reviews/repair_round_02/round_02_review.md` | 图形 replay 不证明模型冷启动；ROOT、Node、解释器和输出隔离合同未闭合。 |
| R03 | `reviews/repair_round_03/round_03_review.md` | R02 声称未编译却有编译日志；R03 exit=0/0 且缺字/溢出消除，却达 302 页，不能把警告减少当版式验收。 |
| R04–R05 | `reviews/repair_round_04/round_04_review.md`、`reviews/repair_round_05/round_05_review.md` | 两个 24 页/exit=1 输出是缺源码树的不完整 staging；可行性复验不扩大搜索最优性范围。 |
| R06–R10 | `reviews/repair_round_06/round_06_review.md`、`reviews/repair_round_07/round_07_review.md`、`reviews/repair_round_08/round_08_review.md`、`reviews/repair_round_09/round_09_review.md`、`reviews/repair_round_10/round_10_review.md` | 派生生成器不等于搜索器；日志自报不是独立事实；历史是否执行与未来是否打包分开。 |
| R11–R12 | `reviews/repair_round_11/repair_completion_handoff_20260905.md`、`reviews/repair_round_12/repair_round_12_handoff.md` | 越权历史按人工陈述记录；先写出结果仍可能 exit=1，序列化修复后 exit=0 也不能倒填历史生产角色。 |
| R13–R14 | `reviews/repair_round_13/repair_completion_handoff_20260905.md`、`reviews/repair_round_14/repair_round_14_handoff.md` | 包 140 项、论文目录 139 项；历史输入缺失使自足重放不成立；R11 机械失败在 R14 才补记。 |
| R15–R17 | `reviews/round15_completion_handoff.md`、`reviews/repair_round_16/round16_semantic_reconciliation.md`、`reviews/round17_provenance_fix_handoff.md` | 140→141、无依据 H1 确认、旧生成器来源是三个问题，技术 PASS 不产生授权。 |
| 源码附录修复 | `reviews/submission_readiness_handoff_20260905.md` §6–§7、`reviews/source_appendix_scope_decision_card_20260905.md`、`reviews/listings_fix_handoff_20260905.md` | 14 个主文件仍漏几何核心和比较/绘图/工作簿链；入口不等于全部源码，正文与附录页数分开。 |
| #17–#20、#21–#24 | `reviews/ai_disclosure_handoff_20260905.md`（含 #18、#19R、#20、#22–#24 追加节） | 当前/历史包 141→142、工具关系逐次确认、早期旧副本无法恢复、中文路径缺字都须如实保留。 |
| Round25 与冻结 | `reviews/official_preflight_v2_20260906.md`、`reviews/official_spec_compliance_20260906.md`、`reviews/round25_support/manifest_142.json`、`benchmark_02/reviews/PROJECT_FROZEN_20260906.md` | 隔离 runner exit=0 仍 BLOCKED，严格模式 exit=3；最终按人工裁决处理不适配内部合同、另按官方规范冻结，科学/奖项未评估。 |

Round-16 的第二个 Major 是 README 把实际 Round-15 生成器写成 Round-13，与无依据人工确认分别记录。最终 `PROJECT_FROZEN_20260906.md` 的官方 READY 是该轮冻结记录的事实；本 Skill 没有重新执行该项目的合规检查，也不把该状态当作官方组织认证。
