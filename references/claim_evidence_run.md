# Claim → evidence → run 证据链【单轮验证】

论文中的每个可检验主张都登记在项目 `logs/claims.jsonl`。一条主张必须同时给出：可在项目内打开的 `evidence_refs`、产生这些文件的 `run_ids`，以及主张范围（`scope`）。运行台账 `logs/run_log.jsonl` 中的运行必须明确 `status: SUCCEEDED` 和 `output_refs`；检查器会拒绝不存在的运行、失败运行、越界路径、缺失文件，以及运行没有声明生成的“证据”。这能发现断链和伪造引用，但不能证明数学命题本身正确。

批准或可发布主张还要绑定 `decision_ref` 和 `review_ref`，两者必须能在事件/人工决定/审核台账中找到。仅由人工决定或参考资料支撑、没有运行输出的记录可写 `evidence_role: DECISION`，仍必须提供真实文件。

运行：

```text
python scripts/claim_check.py PROJECT
python scripts/claim_check.py PROJECT --claims logs/claims.jsonl --runs logs/run_log.jsonl
```

退出码 0 表示证据链通过；退出码 2 表示缺失、断链或伪造风险。它应在论文门、合规门和冻结前运行。当前整条科学主张图和跨题型有效性仍为【未验证】。

记录格式示例见 [`templates/claim_evidence_run.jsonl`](../templates/claim_evidence_run.jsonl)，字段约束见 [`schemas/claim.schema.json`](../schemas/claim.schema.json)。
