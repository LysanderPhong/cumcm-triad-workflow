# 最小冷启动示例

这是一个完全合成的机械示例，只演示台账和审核状态的流转，不包含竞赛题、真实答案、个人信息或 Benchmark 文件。

任务：对三组观测值选择“均值”或“中位数”作为描述统计量。人类在核心定义门说明“观测值含离群点，因此采用中位数”；执行者按已批准定义计算；审核员发现第一次报告把均值写成中位数并 `REJECT`；执行者修复为版本 2，审核员复核后 `PASS`。

文件顺序：

1. `logs/human_decisions.jsonl`：一次 `CORE_MODELING` 人类决定，含简短实质理由；
2. `logs/autonomous_decisions.jsonl`：一次已授权的计算参数决定；
3. `logs/failures.jsonl`：一次保留的版本 1 数字错误及修复引用；
4. `logs/reviews.jsonl`：审核员 `REJECT` 后对版本 2 `PASS`；
5. `logs/ai_usage.jsonl`：一次按用途分组的 AI 使用记录。

这些记录是示例输入，不能冒充实际运行证明。正式项目应使用 `scripts/init_project.py` 创建目录，并由真实参与者追加事件。
