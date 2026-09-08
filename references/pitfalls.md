# 反复出现的陷阱

每行指向一个可核对的历史事件；【单轮验证】描述该事件的证据范围。两轮共同支持的上位纪律仍按 [五条铁律](five_rules.md) 标注，不把单个修复升级成跨题型可靠性。

| 编号 | 表现 | 真实事件出处 | 对策 | 成熟度 |
|---|---|---|---|---|
| P01 | 第一次已阳性仍人为加 70 日下界 | `benchmark_01/failures.md` F-001 | 先把题意转为左/区间/右删失定义；对最早已阳性等极端样例复核，再写似然 | 【单轮验证】 |
| P02 | AFT 正确但损失边界/归一化错误，仍给出合理推荐日 | `benchmark_01/failures.md` F-002；原项目 `planning/reviews/deepseek_review_audit_2026-08-27.md` | 价值/损失口径先由人类确认；逐段核对单位和边界；只废止受影响策略层。该事件不是盲审 M1 | 【单轮验证】 |
| P03 | bootstrap 重估边界却不把边界传给时点计算，声称联合不确定性 | `benchmark_01/external_review/blind_review.md` M1 | 沿数据流核对每次抽样；实施联合传播，或如实改成条件区间，不凭函数名称验收 | 【单轮验证】 |
| P04 | 全部 OOF 标签选阈值并在同批标签报性能 | `benchmark_01/external_review/blind_review.md` M3 | 阈值选择嵌入外层训练数据；只在外层测试数据评工作点，区分排序指标与阈值泛化 | 【单轮验证】 |
| P05 | 缺源码附录但支持 ZIP 有源码，自评仍高 | `benchmark_01/external_review/blind_review.md` C1；`benchmark_01/external_review/gap_matrix.md` G-15 | 按真实论文检查完整源码；提交 blocker 单独阻断，禁止被总分平均掉 | 【单轮验证】 |
| P06 | README 缺 mode，默认 smoke，一次性 marker 阻断，依赖漂移 | `benchmark_01/external_review/blind_review.md` M2 | 按 README 在隔离根实际执行；记录依赖、输出目录和正式/演示模式，保护正式证据 | 【单轮验证】 |
| P07 | bootstrap 数字存在但无预测/抽样表可重放 | `benchmark_01/failures.md` F-014 | 保存形成区间的预测和重采样证据；区间必须能回到实际估计过程 | 【单轮验证】 |
| P08 | AI 摘要自称包里有实际不存在的日志 | `benchmark_01/external_review/blind_review.md` M4 | 披露逐项对包成员；按当年规则区分必填与可选，不把 2025 交互规则写成 2026 原文 | 【单轮验证】 |
| P09 | 辅助模型不收敛使已批准主路线被同一 gate 判 FAIL | `benchmark_01/failures.md` F-015 | gate 按待判断对象分开；保留原失败，附独立裁决，不静默改验证器掩盖失败 | 【单轮验证】 |
| P10 | 同包残留旧损失和错运行顺序 | `benchmark_01/external_review/blind_review.md` m2/m3 | 标出历史文件和当前入口；依赖图、论文清单、README、实际包成员对账 | 【单轮验证】 |
| P11 | 计算很快，就声称单人 72 小时闭环 | `benchmark_01/external_review/blind_review.md` M5 | 连续记录墙钟、等待和可观察活动；当轮窗口 74 小时，72 小时方案仍未验证 | 【单轮验证】；72 小时能力【未验证】 |
| P12 | 只看离散节点，单元内部连续漏测 | `benchmark_02/logs/failures.jsonl#B02-Q4-NODE-COVER-001` | 根据连续覆盖主张构造 whole-cell 充分条件，并用独立细网格/截面检验 | 【单轮验证】 |
| P13 | 两个实现都用裁剪口径，因此以为已符合人工定义 | `benchmark_02/reviews/g4_rho0/cycle_03/external_proof_verdict.md`；`benchmark_02/planning/g2/g2_definitions_v3.md` | 回到人类冻结定义，暂停晋级；后置裁决明确时序，不能两份同源实现相互证明语义 | 【单轮验证】 |
| P14 | baseline 的 slack 误配 B1；把 rho 收缩当现实误差稳健性 | `benchmark_02/logs/failures.jsonl#B02-G4-FINAL-CARD-B1-SLACK-001` | 每个数字绑定具体候选；区分构造参数、设计裕量和测量误差；共同限制对所有选项生效 | 【单轮验证】 |
| P15 | 检查只打印误差，却没有进入 PASS 条件 | `benchmark_02/logs/failures.jsonl#B02-Q2-VERIFIER-GATE-001`、`B02-Q1-REFERENCE-GATE-001` | 用实际失败样例确认验收门会阻断，而不只查报告字段存在 | 【单轮验证】 |
| P16 | 导出工作簿“能打开”就当数值通过 | `benchmark_02/logs/failures.jsonl#B02-WORKBOOK-POSTEXPORT-001`、`B02-Q1-WORKBOOK-AXIS-001` | 对导出成品逐格核对 canonical 值、位置轴和模板保留单元格 | 【单轮验证】 |
| P17 | 图形 replay、依赖安装成功或文件存在被升级为模型/preflight 成功 | `benchmark_02/reviews/repair_round_02/cold_start_scope_review.md`；`benchmark_02/reviews/repair_round_11/repair_completion_handoff_20260905.md` | 分开依赖探针、图形重放、派生重放、模型冷启动、提交预检的证据类型 | 【单轮验证】 |
| P18 | 编译 exit=0 就认为 PDF 可交；缺源树的 24 页输出被看成瘦身 | `benchmark_02/reviews/repair_round_03/round_03_review.md`；`benchmark_02/reviews/repair_round_04/round_04_review.md` | 检查完整输入树、缺字/溢出、正文与附录页数、关键页渲染；保存失败夹具身份 | 【单轮验证】 |
| P19 | 生成器写了输出，打印 Path 时 exit=1，却想当有效运行 | `benchmark_02/reviews/repair_round_11/repair_completion_handoff_20260905.md`；`benchmark_02/reviews/repair_round_12/repair_round_12_handoff.md` | 保留失败和不完整输出，修复后隔离复测，验收完整执行而非存在性 | 【单轮验证】 |
| P20 | 141 项文件技术对账成立，就宣称 H1 已人工批准 | `benchmark_02/reviews/repair_round_16/round16_semantic_reconciliation.md` | 机器事实、人工决定和今后打包偏好分栏；无台账支持保持 UNKNOWN/BLOCKED | 【单轮验证】 |
| P21 | 更新候选包后沿用旧生成器名、旧 141 项头条，或伪称旧副本还在 | `benchmark_02/reviews/round17_provenance_fix_handoff.md`；`benchmark_02/reviews/ai_disclosure_handoff_20260905.md` #20/#22 | successor 单独保留；当前 142 与历史 141 明确区分；无法恢复的旧版如实说明 | 【单轮验证】 |
| P22 | 把主入口列全文当全部源码附录 | `benchmark_02/reviews/source_appendix_scope_decision_card_20260905.md`；`benchmark_02/reviews/submission_readiness_handoff_20260905.md` §6–§7 | 沿实际使用链检查几何核心、图表、派生与工作簿辅助代码，按官方第5条保留完整源程序 | 【单轮验证】 |
| P23 | 长时间等待未计官方时钟，或把只读扫描当永远许可 | `benchmark_02/reviews/progress_human_audit_20260902.md`；`benchmark_02/logs/time_log.jsonl`；`benchmark_02/logs/failures.jsonl#B02-PAPER-PROTECTED-MTIME-SCAN-001` | 墙钟不暂停；按已授权范围做独立工作；试行30分钟+预登记回退但不默替人决策 | 【单轮验证】；30分钟SLA【未验证】 |
| P24 | runner exit=0、官方READY被扩为科学/奖项全通过 | `benchmark_02/reviews/official_preflight_v2_20260906.md`；`benchmark_02/reviews/PROJECT_FROZEN_20260906.md` | 同时查退出码/状态/适用合同；四状态分列，不用内部适配修复冒充科学审查 | 【单轮验证】 |

P01–P11 来自 B01，P12–P24 来自 B02；这是 24 条提炼教训，不是失败总数。B01 内部 33 条、外审 9 条与 B02 36 行/30 唯一 ID 的统计不得与此列表相加。
