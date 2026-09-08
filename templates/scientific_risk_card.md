# 科学风险卡：{子问题 ID}【动态模板；机制未验证】

- 风险卡 ID / 版本：`{RISK-CARD-ID}` / `{v1}`
- 题目 / 子问题：`{problem_id}` / `{subproblem_id}`
- 问题类型：`{回归 / 分类 / 优化 / 微分方程 / ...}`（不要预设 Q1–Q4）
- 当前状态：`DRAFT | HUMAN_REVIEW_REQUIRED | IN_TESTING | BLOCKED | MITIGATED | ACCEPTED`
- 成熟度：风险来源【两轮验证】；按题动态生成与自动消费【未验证】
- 人工决定引用：`{logs/human_decisions.jsonl#... 或 NONE}`

## 共同边界（所有候选都适用）

- 目标与评价口径：`{...}`
- 数据域、单位、时间/空间范围：`{...}`
- 不确定性含义：`{测量误差 / 参数不确定性 / 构造裕量 / 未知}`
- 搜索、阈值与外推禁止事项：`{...}`
- 允许的主张范围：`{...}`

共同边界不能只写在不推荐方案中；若尚未确定，状态保持 `REVIEW_REQUIRED`，不能由代理默选。

## 风险维度登记

每个维度都要留下适用性判断。`NOT_APPLICABLE` 必须说明为什么不适用并附可核对证据；无法判断写 `REVIEW_REQUIRED`。

| 风险 ID | 维度 | 适用性 | 观察到的风险 | 测试/复算计划 | 通过条件 | 状态 | 证据相对路径 / run_id | 责任角色 |
|---|---|---|---|---|---|---|---|---|
| `{R-01}` | `ASSUMPTIONS` 假设 | `APPLICABLE / NOT_APPLICABLE / REVIEW_REQUIRED` | `{...}` | `{量纲/边界/极端情形/守恒等}` | `{...}` | `OPEN` | `{...}` | `{human_decision_maker}` |
| `{R-02}` | `DATA` 数据 | `APPLICABLE / NOT_APPLICABLE / REVIEW_REQUIRED` | `{缺失、泄漏、切分、覆盖、来源}` | `{数据审计、切分复核、污染扫描}` | `{...}` | `OPEN` | `{...}` | `{execution_agent}` |
| `{R-03}` | `IDENTIFIABILITY` 识别性 | `APPLICABLE / NOT_APPLICABLE / REVIEW_REQUIRED` | `{参数/阈值/目标是否可由现有信息区分}` | `{不可识别情形、abstention、替代解释}` | `{不可识别时收窄主张或停门}` | `OPEN` | `{...}` | `{independent_reviewer}` |
| `{R-04}` | `SENSITIVITY` 敏感性 | `APPLICABLE / NOT_APPLICABLE / REVIEW_REQUIRED` | `{关键参数/边界/权重变化是否改排序或结论}` | `{局部/全局敏感性、扰动范围与依据}` | `{变化范围及影响被量化并写入限制}` | `OPEN` | `{...}` | `{execution_agent}` |
| `{R-05}` | `BASELINE` 基线 | `APPLICABLE / NOT_APPLICABLE / REVIEW_REQUIRED` | `{是否有可运行、同口径、可比较基线}` | `{先跑 baseline；固定评价、预算和停止条件}` | `{主方法相对基线收益和代价可复算}` | `OPEN` | `{...}` | `{human_decision_maker}` |
| `{R-06}` | `BOUNDARY_EXTRAPOLATION` 越界/外推 | `APPLICABLE / NOT_APPLICABLE / REVIEW_REQUIRED` | `{连续域、样本外、边界外或搜索族外推}` | `{边界、whole-cell/细网格、样本外或截断检验}` | `{主张限制与实际覆盖一致；越界即 BLOCK}` | `OPEN` | `{...}` | `{independent_reviewer}` |

## 人工确认（核心建模门）

请用自己的话填写至少五项：

- 采用/拒绝了哪些风险维度，为什么：`{...}`
- 一个关键假设及其影响：`{...}`
- 一个关键数据或识别性风险：`{...}`
- 一个关键结果、敏感性或基线比较：`{...}`
- 一个失败情景和收窄/停门边界：`{...}`

只有代理推荐、`A/B/C` 或“同意”不足以证明核心建模门的人类主导。更正追加新版本并用 `supersedes` 回指旧卡。

## 审核交接

- 执行者运行与输出：`{命令、退出码、run_id}`
- 独立审核读取范围：`{blind-review / provenance-audit；项目相对路径}`
- 当前 blocker：`{failure_id / NONE}`
- 允许主张：`{...}`；禁止主张：`{...}`
- 下一门及准入缺口：`{...}`
