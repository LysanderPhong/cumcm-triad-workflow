# Benchmark-01：完成产物之后，为什么仍需独立审核

这是脱敏历史案例，不是优秀论文或获奖证明。证据定位均相对原 Benchmark 档案，原档案未随 Skill 发布。内部账有33条失败（3 Critical / 12 Major / 18 Minor）；自报29条自动发现修复、2条外部反馈触发、1条人工重建、1条未解。冻结后阶段A外审又列1 Critical / 5 Major / 3 Minor。两组口径分开，不相加成“总失败数”。

本例提炼11条教训；每个事件是本轮历史证据【单轮验证】，相应五纪律的整体成熟度另见入口。

| 教训ID | 实际问题与影响 | 流程改变 | 原始出处 |
|---|---|---|---|
| B01-L01 | 217名首次观测已达标者被错误赋予70日下界；下游似然仍可能产生合理数字 | 定义事件、观察和删失区间，先做边界例 | benchmark_01/failures.md#F-001 |
| B01-L02 | 延迟损失边界与归一化混用，外部评价触发核查；预测层可用而策略层失效 | 损失独立于预测层登记，边界/单位/价值权重先确认 | benchmark_01/failures.md#F-002；human_interventions.md#H-006 |
| B01-L03 | 等患者权重与等记录权重敏感性缺失；人工还拒绝第一版Q1路线 | 估计对象与重建选择要留人工依据 | benchmark_01/failures.md#F-004、F-008 |
| B01-L04 | bootstrap切点被重估，时点计算却仍固定分组；论文声称联合不确定性 | 代码实际传播范围与论文主张逐项对账 | benchmark_01/external_review/blind_review.md#M1 |
| B01-L05 | OOF概率无训练泄漏，但用同批标签选阈值又评价阈值 | 阈值选择也需训练/测试分离 | benchmark_01/external_review/blind_review.md#M3 |
| B01-L06 | 支撑ZIP有代码，论文附录却没有源程序正文 | 实际PDF逐条核对，不能由包内存在推论文合规 | benchmark_01/external_review/blind_review.md#C1 |
| B01-L07 | README漏必填参数、默认smoke、已有marker阻止正式重放，依赖版本也不足 | 用干净输出目录和明确环境实测完整入口 | benchmark_01/external_review/blind_review.md#M2 |
| B01-L08 | AI披露发现得晚；后来详情仍仅代表摘要，并声称包含实际不存在的日志 | 从开始保存关键提示/回答，精确匹配包成员 | benchmark_01/failures.md#F-032；external_review/blind_review.md#M4 |
| B01-L09 | 旧损失实现仍可导入；附录路径与运行顺序和实际包不一致 | 历史版本与发布依赖分开，权威入口唯一明确 | benchmark_01/external_review/blind_review.md#m2、m3 |
| B01-L10 | 有日历日期和计算耗时，缺端到端人工活动账本 | 72小时只能标未验证，不能用程序快推流程快 | benchmark_01/external_review/blind_review.md#M5；vnext_acceptance_tests.md#AT-07 |
| B01-L11 | 自评仍是PASS WITH MATERIAL LIMITATIONS，外审判冻结稿不具提交条件 | 冻结候选不等于发布；独立审核和阻断项决定资格 | benchmark_01/final_benchmark_report.md；external_review/gap_matrix.md#G-15 |

B01-L02与B01-L04是不同缺陷：一个是损失定义，一个是bootstrap区间语义，不能把盲审M1当F-002的同一事件。外部意见还需核对原材料，不因其来自别的AI就直接采信。

继承到下一轮的重点是尽早分离定义、实现与审核。完整三角色机制在B02运行【单轮验证】；72小时闭环与获奖能力并未由本轮建立。
