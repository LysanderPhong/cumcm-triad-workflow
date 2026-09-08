# Benchmark-02：三角色如何把错误退回正确的门

本例为另一道几何测线题的脱敏过程记录。引用只保留原档案相对文件与事件ID，不包含学校、个人目录或用户名。当前失败账36行、30个唯一failure ID；Critical 2 / Major 18 / Minor 15是35行非空severity字段的记录口径，其中含更正/关闭/复测，不能称30个唯一失败的严重度分布。

本例提炼13条教训。下列具体B02事件均为【单轮验证】；它们对五纪律的支持不把30分钟SLA、72小时闭环或跨题型能力升级。

| 教训ID | 表现与发现 | 处理/可复用纪律 | 原始出处 |
|---|---|---|---|
| B02-L01 | 受限检索仍返回某候选题解摘要 | 分析前剔除受污染候选；记录实际接触，不声称从未看见 | benchmark_02/logs/failures.jsonl#B02-F-002 |
| B02-L02 | 节点、边界样点和角点通过，单元内部却漏测3.314% | 改为whole-cell构造，连续截面与细网格复测；保留原FAIL | benchmark_02/logs/failures.jsonl#B02-Q4-NODE-COVER-001 |
| B02-L03 | 验证器展示了误差，但没有把关键方向/参考点检查写入通过条件 | 每个必要检查真正参与失败门 | benchmark_02/logs/failures.jsonl#B02-Q2-VERIFIER-GATE-001、B02-Q1-REFERENCE-GATE-001 |
| B02-L04 | 表格能打开不等于逐格数值正确；XLSX内部随机ID造成文件漂移 | 导出后逐格对权威指标；区分数值一致与文件一致 | benchmark_02/logs/failures.jsonl#B02-WORKBOOK-POSTEXPORT-001、B02-XLSX-REPLAY-001 |
| B02-L05 | 启发式含验证预计474.36分钟，超过180分钟预算 | 按预批准回退取消；随机种子未运行，不能宣称算法实证增益 | benchmark_02/logs/failures.jsonl#B02-Q4-HEURISTIC-BUDGET-001 |
| B02-L06 | 独立实现也采用域内截断宽度，却无人工决定替代原G2语义 | Cycle03阻断晋级；人工A后恢复资格，明确结果后裁决 | benchmark_02/reviews/g4_rho0/cycle_03/external_proof_verdict.md；planning/g2/g2_definitions_v3.md |
| B02-L07 | 权威状态已暂停，摘要正文仍保留当前推荐 | 不能只加顶部横幅；所有现行消费者同步暂停 | benchmark_02/reviews/g4_rho0/cycle_04/external_propagation_verdict.md |
| B02-L08 | 卡片误配B1松弛，且仅对一个选项写搜索族边界 | 人工看到前审核卡片事实、共同限制和选项平衡性 | benchmark_02/logs/failures.jsonl#B02-G4-FINAL-CARD-B1-SLACK-001；reviews/g4_rho0/cycle_06/external_final_route_card_verdict.md |
| B02-L09 | 高精度百分比不符同文件分母；候选README还留旧生成器名称 | 派生式回指canonical字段，包生成信息也要复核 | benchmark_02/logs/failures.jsonl#B02-G4-PERCENT-001；reviews/round17_provenance_fix_handoff.md |
| B02-L10 | 图形replay被误解为模型cold-start；正式解释器缺pypdf；后续脚本写完结果又序列化失败 | 标明证据层级；失败退出不能算成功；修后最小复测 | benchmark_02/reviews/repair_round_02/cold_start_scope_review.md；logs/failures.jsonl#B02-S3-2-PYPDF-RUNTIME-001、B02-R12-G4-PATH-SERIALIZATION-001 |
| B02-L11 | Round15说H1/H3已确认，人工台账没有对应记录 | 独立审核分离机器事实和人工授权；新决定引用补齐后才关闭 | benchmark_02/reviews/repair_round_16/round16_semantic_reconciliation.md；reviews/b02_r01_007_closure_verdict_v2.md |
| B02-L12 | 受限阶段仍扫了保护区元数据；另有授权时序争议 | 停止、记录越界；机器事实与人工陈述分开，事后追认不改写过去 | benchmark_02/logs/failures.jsonl#B02-PAPER-PROTECTED-MTIME-SCAN-001、B02-PAPER-UNAUTHORIZED-FREEZE-ATTEMPT-001 |
| B02-L13 | 规则runner合同不适配本流程，AI工具事实与源码附录又需多轮核对 | 停用不适配runner有人工依据；最终官方资格READY，不把科学/奖项状态自动升级 | benchmark_02/reviews/PROJECT_FROZEN_20260906.md；reviews/ai_disclosure_handoff_20260905.md |

实际循环为：人类批准 → 代理实施 → 独立审核发现并阻断 → 回到相应人类门/机械修复 → 定向复测 → 人工最终取舍。Cycle01/02已通过的结果仍被Cycle03的语义审查收窄，说明审核也要按所验证的命题解释。

最后冻结的四状态分别为官方资格READY、科学准备NOT_ASSESSED、奖项竞争力NOT_ASSESSED、可选安全NOT_RUN。冻结完成不等于科学能力被充分验证；省级以上只是训练目标。H54到H101的等待反例用于设计SLA，不能作为30分钟响应规则已验证的证据。
