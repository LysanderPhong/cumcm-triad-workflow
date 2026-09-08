# 人工门响应时限与预登记回退

30 分钟 SLA 是由 Benchmark-02 长等待导出的**新设计【未验证】**，不是两轮已经实施的制度。预登记预算触发后机械回退在 B02 有一次直接实践【单轮验证】；将其推广到所有人工门仍【未验证】。

## 可执行规则

1. 完整选择卡送达后开始 30 分钟响应预算。卡必须给出真实选项、代价、影响、待决定项、允许/禁止动作；如提供 AI 建议，单独署名并列依据，学习模式可不推荐；技术检查不应包装成让人随意选 PASS/FAIL 的问题。
2. 记录 `asked_at`、`deadline_at`、`answered_at`、用户答案原文、理由是否提供、写入者、决定 ID 和证据路径。平台未给精确到达时间时写 `null/UNKNOWN`，另记 `written_at`；不要用文件时间冒充用户发言时间。
3. 到时未答，只能执行**该门打开前人类已批准**的预登记回退。回退必须完整指定触发条件、动作范围、预算和停止点，不能临场把 AI 推荐改名叫“默认方案”。
4. 无预授权、授权无法定位、触发证据不足或回退需要新题意/价值判断时，保持 `WAITING_HUMAN/BLOCKED`。等待期间仅推进不依赖该决定的已授权工作。
5. 回退执行只追加代理执行记录及路线变化；`human_decisions` 引用原预授权，不把超时写成人类新选择。后到的人类决定记录真实时序，并检查是否使刚完成工作失效。
6. 最终签发、比赛提交、未知工具调用和人工核验事实不可用超时回退代填。人类批准只解决权限或偏好，不把未通过的科学/技术验证变成 PASS。

这些字段可放入 [决策卡](../templates/decision_card.md) 与 [代理决定台账](../templates/autonomous_decision.jsonl)。本 Skill 不要求平台必须有后台定时器；若任务不持续运行，记录下一次观测到的超时，不伪称在截止瞬间执行了动作。

## 预登记写法【单轮验证的预算回退；通用模板未验证】

以下是需人类实际批准的模板，不是本文件给予的授权：

```yaml
gate_id: Q4_ROUTE
prior_human_decision_id: null  # 人工批准后填写，不能保留空值却执行回退
asked_at: null
response_budget_minutes: 30
fallback:
  approved_by_human: false
  trigger: "30 分钟未答且 baseline 已通过冻结的独立验证"
  action: "保留已批准 baseline 为工作候选；继续整理其证据"
  allowed_changes: ["候选比较报告", "代理执行日志"]
  forbidden_changes: ["题意", "目标函数", "验证器", "最终路线", "论文冻结"]
  max_execution_minutes: 10
  stop_at: "WAITING_HUMAN_FINAL_ROUTE"
  human_final_signoff_still_required: true
```

可参考的真实机械回退是 B02 `benchmark_02/logs/route_changes.jsonl` 的 `B02-Q4-HEURISTIC-CANCELLED`：完整工作量投影 474.3577 分钟超过人工预登记的 180 分钟预算，随机候选数为 0，保留 B1/B0，`human_final_route_decision=false`。这证明已批准规则可由机器执行，不证明“等待 30 分钟就自动批准”有效。证据另见 `benchmark_02/planning/decision_cards/g4_route_freeze_v1.md`、`benchmark_02/logs/failures.jsonl#B02-Q4-HEURISTIC-BUDGET-001`。

## H54→H101 的反面案例【单轮验证】

| 证据点 | 可确认事实 | 来源 |
|---|---|---|
| 演练起点 | 2026-08-29 17:52:34+08:00；官方演练时钟包含人工等待、不暂停 | `benchmark_02/logs/time_log.jsonl`，`TIME_POLICY` |
| G2 的已记录等待 | 2026-08-31 01:21:37 至 23:27:54，79577 秒；结束点依据首次本地写入的 A 决定，用户原始到达时间未知 | 同文件，`human_wait_for_g2_boundary_eta_option` |
| H54.3400 | 2026-09-01 00:12:58+08:00；active-agent 9.2531 小时，仍等待 Q4 最终人工路线 | 同文件最后 `OFFICIAL_CLOCK_CHECKPOINT`；`benchmark_02/logs/run_log.jsonl` 的 `FINAL_HUMAN_GATE_LOCAL_INTEGRITY_CHECK_PASS` |
| 约 H101.61 | 2026-09-02 23:32:09+08:00 盘点时，仍在最终 Q4 人工门 | `benchmark_02/reviews/progress_human_audit_20260902.md`（结论与未决风险）；run_log 的 `HUMAN_AUDIT_STATUS_REPORT_CREATED` |

两个观察点相隔 47 小时 19 分 11 秒。报告能证明墙钟继续流逝且人工门在盘点时仍未闭合；它不提供中间每分钟活动，也不提供精确答复到达时间。不得把整个差值都标为已精确测量的纯等待，不能用 9.2531 小时代理活动美化总时长。

B02 原计划为 74 小时，见 `benchmark_02/logs/run_log.jsonl` 的 `RUNTIME_CONSTRAINTS_FROZEN_AND_G2_GATE_OPENED`；B01 外审 M5 也核对过当轮 74 小时窗口。72 小时是训练目标【未验证】，不是由以上记录证明的实际闭环。真正比赛的截止时间以当年官方通知为准。
