# 五条铁律及真实来源

来源使用 [演进记录](evolution.md) 的资料仓库相对标识。成熟度说明已有轮次证据，不能推成稳定成功率。日志与 JSON 只是承载证据的工具；内容、来源、时序和授权仍须分别判断。

## 1. 决策入账【两轮验证】

**纪律原文：人类选择必须追加到唯一台账；推荐、代理默认值、外部意见和人工理由分栏保存；没有人类记录就保持 PENDING/UNKNOWN，不靠“看起来合理”补齐。**

真实来源：

- B01 `benchmark_01/human_interventions.md` H-001/H-003/H-004 记录语义、Q1 重建和后续委托；`benchmark_01/failures.md` F-008 明确 Q1 round1 是人类拒绝后重建，不能写成 AI 自修。
- B02 `benchmark_02/planning/g2/g2_definitions_v3.md` 与 `benchmark_02/planning/decision_cards/g4_boundary_overlap_definition_v1.md` 明确用户只答 A、未提供理由，且为结果后的补充裁决。
- B02 `benchmark_02/reviews/repair_round_16/round16_semantic_reconciliation.md`：Round-15 把没有台账支持的 H1(a) 写成已确认；Round-14 卡仍 `selection_made=false`。机器对账成立，但授权视图回到 UNKNOWN/UNDECIDED、总体 BLOCKED。两项 Major 只记录于受限审计目录。

执行时保留答案原文、记录时间与事件时间之别、理由是否提供、批准范围和来源。等待或回退引用先前人类授权，不造一条新的人类选择。该纪律挡住机器建议冒充人类决定、用户粘贴意见冒充用户理由、后置裁决倒写成事前批准。

## 2. 失败如实【两轮验证】

**纪律原文：失败追加、不覆盖；区分科学失败、机械失败、合规 blocker、越权事件和未验证状态；修复追加关闭证据，不把历史 FAIL 改成从未发生。**

真实来源：

- B01 `benchmark_01/failures.md` F-001/F-002 是修复过的核心错误，F-007 的 NaN 仍保留在不可变正式证据，向写作侧提供兼容导出。
- B02 `benchmark_02/logs/failures.jsonl` 的 `B02-Q4-NODE-COVER-001` 保留初始漏测及后续 CLOSURE；同日志对 Q2 不可靠失败时间另写 CORRECTION，没有覆盖原行。
- B02 `benchmark_02/reviews/repair_round_11/repair_completion_handoff_20260905.md`：越权认定按人工陈述和可观察写入事实分别记录，事后追认不改成事前授权。
- B02 R11 生成文件后打印 Path 失败，R12 修复、R14 才补记，见 `benchmark_02/reviews/repair_round_14/repair_round_14_handoff.md` 与 `B02-R12-G4-PATH-SERIALIZATION-001`。

修复记录指向原 ID、实际退出码、复测范围及仍未解决项。受保护日志不许写时，在获准的新审查文件记录缺口并指出尚未入主台账。挡住隐去失败、把输出存在当整次成功、把机械故障说成科学方法失败或将未验证说成失败。

## 3. 数字可追溯【两轮验证】

**纪律原文：论文、图表、工作簿和摘要只消费注册的 canonical/frozen numbers；每个数字回指输入、脚本、口径、版本和复测证据；历史快照不得冒充当前头条来源。**

真实来源：

- B01 `benchmark_01/failures.md` F-014：原 500 次 bootstrap 区间缺可重放的预测和表格，后保存 OOF 与新配对抽样证据；`benchmark_01/external_review/blind_review.md` M1/M3 分别发现联合区间语义和工作阈值泛化解释不成立。
- B02 `benchmark_02/logs/failures.jsonl#B02-G4-PERCENT-001`：两项百分比分母不一致；`B02-G4-FINAL-CARD-B1-SLACK-001`：把 baseline 松弛误配给 B1。
- B02 `benchmark_02/reviews/round15_completion_handoff.md` 与 `benchmark_02/reviews/round17_provenance_fix_handoff.md`：140→141 实际成员变化、历史 G4 输入、README 生成器来源必须分别登记；`benchmark_02/reviews/ai_disclosure_handoff_20260905.md` #20 再区分当前 142 与历史 141。

数字证据必须同时回答“哪个值”和“这个值是什么意思”。百分比保留分子/分母，工作簿导出逐格对 canonical 值。版本完整性检查只用于用户授权的核对场景；相同字节不能证明估计语义正确。挡住抄对数但讲错含义、旧快照混入新论文以及来源链断裂。

## 4. 证据实测【两轮验证】

**纪律原文：状态由实际运行、复算、渲染、冷启动或盲审证据驱动；脚本存在、自评 PASS、曾经生成过不能替代当前门的实测。**

真实来源：

- B01 `benchmark_01/external_review/blind_review.md` C1/M2/M3/M5：缺源码附录、README 冷启动失败、阈值层泄漏、端到端时间不足证据均逃过原自评；`benchmark_01/external_review/gap_matrix.md` G-15 说明总分可能掩盖硬失败。
- B02 `benchmark_02/logs/failures.jsonl#B02-Q4-NODE-COVER-001`：节点/边界样点通过，cell-centre 漏测 3.314%；连续截面与 whole-cell 证书暴露并处理问题。
- B02 `benchmark_02/reviews/repair_round_02/cold_start_scope_review.md`：仅图形重放不是模型冷启动；`benchmark_02/reviews/s3_2_preflight_block_20260904.md`：同一 init 解释器缺 pypdf，exit=4。
- B02 `benchmark_02/reviews/official_preflight_v2_20260906.md`：普通调用 exit=0 但状态 BLOCKED；严格 `--require-ready` exit=3。退出码与状态都必须看。

检查方法围绕本题风险选择：量纲、边界、残差、守恒、解析/极端对照；统计重采样或连续几何证书只在适用题型使用。记录实际执行者、命令、输入、输出、退出码和不能推出的结论。挡住“脚本有了所以验过”、局部实测外推整条流程和自评分数当能力证明。

## 5. 越权即停【单轮验证】

**纪律原文：目标、口径、权限或保护范围不一致立即暂停受影响动作；不自行改题意、改损失、改验证器、换算法族、补人工事实，或用事后批准掩盖事前越权。**

真实来源：

- B01 `benchmark_01/human_interventions.md` H-004 提供委托边界的动机；它不单独证明完整停机机制已验证。
- B02 `benchmark_02/reviews/g4_rho0/cycle_03/external_proof_verdict.md` 与 `benchmark_02/logs/failures.jsonl#B02-Q4-BOUNDARY-ETA-SEMANTIC-001`：冻结定义与两个实现同时冲突，暂停 Q4 晋级、重开人工定义门。
- B02 `benchmark_02/logs/route_changes.jsonl#B02-Q4-HEURISTIC-CANCELLED` 与 `benchmark_02/planning/decision_cards/g4_route_freeze_v1.md`：474.3577 分钟投影超过 180 分钟，随机候选未运行，只机械保留已有候选，未替人决定最终路线。
- B02 `benchmark_02/logs/failures.jsonl#B02-PAPER-PROTECTED-MTIME-SCAN-001`：一次只读递归扫描也违反当时明确禁止重复扫描的范围；“只读”不抹掉已知范围约束。
- B02 `benchmark_02/logs/failures.jsonl#B02-G4-FINAL-CARD-COMMON-CLAIM-SCOPE-001`：外审要求两选项共同适用非全局最优边界，修卡复测后才交人类。

停的是依赖冲突的工作，其他已授权独立工作可继续。报告事实、冲突、受影响产物与最小待决定项；如已发生越权，保留原证据和事后处置时序。挡住结果驱动的规则放宽与范围扩张。跨第三套题能否稳定执行仍【未验证】。
