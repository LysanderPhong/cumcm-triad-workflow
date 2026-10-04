---
name: cumcm-triad-workflow
description: "Lightweight modeling collaboration: confirm scope and route, execute with traceable outputs, independently review results and final PDF, then explicitly freeze a delivery snapshot."
---

# 轻量数模协作

目标：将题面变成可解释、可复核的模型结果和论文。默认只有三个需要用户决定的节点：题意与口径、路线、最终交付。不要为了维护流程而反复询问、填表或编造批准。

## 执行

1. 读取题面和附件，汇总对象、任务、关键假设、指标及歧义。已有明确答复直接使用；仅有影响结果的缺失信息才问。用户回答登记为 SCOPE，关闭该阶段。
2. 给出一个可解释基线与必要的主方法，说明比较口径、预算和停止条件。用户确定 ROUTE 后，在已授权范围内执行，不逐项请示机械工作。
3. 编写并实际运行代码。使用 `triad.py run` 自动记录命令、退出码、输入和输出指纹；输出使用新版本文件名。失败修复和复测留证据。论文关键数字/结论登记为 Claim，关联真实输出，不另填六维风险卡。
4. 独立上下文读取原始题面、人工决定、当前代码与结果，复核语义、计算和结论边界，记录 RESULTS 审核。审核员提出问题，由执行者修复，审核员再审；同一上下文自查如实标 self-review-only。程序不能证明 context-id 真正独立。
5. 写论文、画图并生成候选 PDF。默认沿用 [参考论文版式](references/paper_format_profile.md) 与可编译的 [paper.tex](templates/paper.tex)：摘要首页、中文居中章标题、十进制小节、模型与结果分问展开、三线表、居中编号公式、参考文献和附录。先固定全文样式，再写入真实内容；另有用户或赛事模板时优先覆盖。内容由题目与证据决定，不强制摘要 700 字、20–30 页、每问两张图。只在解释变化影响科学主张时回到用户，排版和措辞调整直接执行。
6. DELIVERY 审核必须实际查看最终 PDF、图表、引用、匿名、真实 AI 披露及支撑材料。读取 [视觉检查](references/visual_style.md)、[页面检查](references/paper_format_profile.md)；涉及提交要求时核对 [官方清单](references/official_compliance.md) 与当年原文。先完成所有可执行修复，再请求用户确认具体版本。
7. 用户明确签发后 freeze 保存快照，不自动提交。冻结后用 reopen 建立新的候选工作目录；不写回已冻结项目。

## 实质检查

按题型选择需要的量纲、边界、残差、解析对照、数据切分、敏感性和基线检查。只有真实技术失败、未解决的关键歧义、授权冲突或缺少交付事实才阻断；不用字数、图数、色板偏好或风险表完成度阻断。

输入、代码、评价口径或产物改变后检查原运行与审核是否失效。后来的 REJECT 或人工撤回不能被历史 PASS 覆盖。失败不伪装成功，未知不填已检查。

## 工具

命令与最短流程见 [README](README.md)。只维护 logs/events.jsonl，所有状态由事件计算；代理自动登记，用户不手工写 JSON。核心命令：start、status、ingest、record-human、run、record-claim、record-review、close-gate、freeze；故障与修订按需使用。

paper_review.py 只提供解析和写作提示，不测 AI 率、不证明论证充分；不应因报告中的 REVIEW 项反复开人工门。doctor、匿名扫描、指纹检查按需要使用。

旧版项目保持原样；2.0 格式在新目录启动。不能把合成测试通过写成真实数模题、完整竞赛或获奖证明。
