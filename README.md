# cumcm-triad-workflow

面向单人备赛、AI 协作、争取省级以上成绩的数模工作流。它把三项责任分开：人类作出关键判断，执行代理实现并记录，独立审核员检查证据并能阻断。本仓库是 Experimental / Release Candidate：架构已实现，部分机制有 Benchmark 02 历史单轮证据；当前打包版本的行为冷启动尚未完成验证。

本项目参考已公布的 CUMCM 2026 竞赛规则和 AI 工具使用规定设计，与 CUMCM 组织委员会无隶属或背书关系。使用者必须在训练或比赛前核对最新官方规则。

## 为什么需要它

Benchmark-01 的阶段化技能链已有数据审计、基线、稳健性、数字冻结和最终 QA。内部记录 33 条失败，自评给出 `PASS WITH MATERIAL LIMITATIONS`；冻结后的独立盲审仍发现 1 个 Critical、5 个 Major、3 个 Minor：论文缺源码附录、README 无法按说明冷启动、阈值选择与评价复用标签等。

这两组记录分开保留，不能直接相加为故障总数，也不能以修复后的自评分数证明能力。Benchmark-02 进一步把决定、执行与审核分开：边界口径未获人类批准、节点覆盖假通过、候选包误称人工确认，都被阻断或收窄。参见 [演进证据](references/evolution.md)。

## 30 秒快速上手

发布仓库地址确定后，把下面的 `YOUR_REPOSITORY_URL` 替换为该地址。克隆仓库的根目录应直接包含 `SKILL.md`。

```sh
git clone YOUR_REPOSITORY_URL cumcm-triad-workflow
cd cumcm-triad-workflow
python3 scripts/doctor.py --help
python3 scripts/doctor.py --output-dir ../triad-doctor
```

创建干净项目可直接运行：

```sh
python3 scripts/init_project.py ../my-modeling-project
```

也可以用总控入口一次完成初始化和题面导入：

```sh
python3 scripts/triad.py start ../my-modeling-project --input problem.pdf attachments/
python3 scripts/triad.py status ../my-modeling-project
```

总控入口还可把一条人工决定写入正确台账，并生成独立审核包：

```sh
python3 scripts/triad.py record-human ../my-modeling-project --gate-id START --gate-class CORE_MODELING \
  --selected "线性基线" --contribution "我先用可解释基线检验变量关系，再决定是否增加非线性模型。" \
  --rationale "先保留可比较的基准。"
python3 scripts/triad.py review-packet ../my-modeling-project
```

`triad.py` 只自动处理文件搬运、状态汇总、台账格式和审核材料打包；它不会替人批准核心建模决定、关闭失败或冻结提交。

阶段控制命令还包括 `record-review`、`record-failure`、`close-failure`、`close-gate`、`freeze` 和 `validate`。它们只接受 `schemas/` 中的规范 Gate ID；审核 PASS 必须带项目内证据和独立上下文，冻结必须有所有前置门关闭、无开放 blocker 和实质性人工确认。状态文件是派生视图，事件追加保存在 `logs/events.jsonl`。

论文候选稿完成后，先用用户提供的同方向优秀论文做多维对比，并生成可在浏览器中勾选和备注的 HTML 自检页：

```sh
python3 scripts/paper_review.py --paper paper/draft.md \
  --reference references/example_a.pdf --reference references/example_b.pdf \
  --decision-log logs/human_decisions.jsonl \
  --figure-manifest paper/figures/figure_manifest.json \
  --output-html paper/paper_review.html
```

报告比较篇幅、结构、图表/公式/引用密度和验证线索，并标记套话、重复句式、强结论证据不足及人类贡献缺口。它不输出 AI 百分比，也不自动改写论文；用户决定修改项后，必须回到论文门复核。

然后打开 [bootstrap prompt](templates/prompts/bootstrap.md)，填入题面附件、项目路径、三角色、时钟和保护范围，再交给 Codex，并明确引用本目录的 `SKILL.md`。这一步可快速启动；环境探针及编译实际耗时不保证 30 秒。

无需先安装 28 个技能也可使用本协议；建模能力可由已有技能或项目工具完成。要作为个人 Skill 安装，可把整个目录放到个人 skills 目录，或通过已有技能安装工具安装发布仓库；克隆本身不代表已经安装。

## 脚本使用约定

五个脚本支持 Python 3.10+，脚本运行和参数处理使用标准库。`doctor.py` 检查的目标环境需要 NumPy、Matplotlib、XeLaTeX、ctex 和可用中文字体；这些是被测依赖，脚本不自动安装。`anonym_scan.py` 与 `paper_review.py` 读取 PDF 可选用 pypdf；缺失或无可提取文字时报告未完成，不给完整通过。完整参数和退出码以各脚本 `--help` 为准。

- 环境探针只在指定输出目录生成最小测试图、中文 PDF 和报告；成功不等于比赛代码可复现。
- `schemas/`：规范 Gate、事件、审核、失败和运行记录的版本化合同。
- SHA-256 清单需要可信的已知指纹；不要先给待测文件生成新指纹再以匹配证明正确。
- 匿名扫描需要补充真实学校、姓名、赛区等待排查词；默认模式只找可疑线索，人工仍需检查图片、元数据与误报。

正式比赛中，独立审核限队内成员或独立AI会话，不得据本Skill向队外真人交流赛题；赛外训练可安排外部真人盲审。具体条文见[官方规则](references/official_compliance.md)。

## 与 28-skill 的关系

原套件回答“每阶段生成和检查什么产物”；triad 回答“谁能决定、谁不能自证、何时回门”。原套件已有决策卡、JSONL 账本与审核技能，不能描述成“没有人类或审核”；新增价值是把上下文隔离、授权范围和否决权贯穿每一阶段。

28 是历史套件口径；当前本地目录总数不能直接当作原始版本清单。公开使用不绑定本机路径或固定技能安装数量。

## 三类核心决策

问题解释、目标与关键假设、模型族、目标函数、主要约束、评价方法、重大模型变化、关键结果解释和最终科学结论都属于 `CORE_MODELING`。人类需要先提出方向、修改 AI 提案，或用自己的话简短说明假设、取舍或解释；只回复“A/B/C”不能单独证明人类主导。实现、展示和行政门可以按预批准合同轻量记录。所有决定进入对应 JSONL schema，见 `templates/logs/`。

## 审核否决与修复

执行者产生版本后，独立审核员可返回 `PASS`、`REJECT`、`BLOCK` 或 `ESCALATE`。`REJECT/BLOCK` 必须由执行者或负责人生成新版本并保留失败证据，审核员再审新版本；审核员不能修改生产结果后自行签发通过，也不能覆盖人类拥有的建模决定。

## 成熟度与诚实边界

| 内容 | 证据范围 |
|---|---|
| 决策入账、失败如实、数字可追溯、证据实测 | 【两轮验证】 |
| 越权即停与完整三角色协议 | 【单轮验证】 |
| 30 分钟人类响应 SLA 与全程 72 小时时间轴 | 【未验证】 |
| 跨题型通用性 | 【未验证】，待第三套独立题验证 |

当前发布验证状态：静态仓库完整性为 `VERIFIED`；Benchmark 02 的三角色组织为 `SINGLE-RUN VERIFIED / historical`。使用当前打包 Skill 的空项目冷启动、执行者越权停止、审核员否决、修复复审、人工门超时和预授权回退仍为 `UNVERIFIED`，直到 [冷启动发布测试](validation/cold_start_release_test.md) 实际执行并记录结果。

不保证省奖或任何奖项。B02 最终记录官方提交资格 `READY`，科学准备度及奖项竞争力仍 `NOT_ASSESSED`；这不是全能力认证。官方赛程按当年通知读取，72 小时是内部训练目标，不能替代官方截止时间。

## 文件导航与发布状态

- [SKILL.md](SKILL.md)：代理入口与职责。
- [阶段门](references/stage_gates.md)、[历史论文风格档案](references/historical_style_profile.md)、[论文多维对比](references/paper_comparison.md)、[写作风险自查](references/ai_authorship_review.md)、[图表视觉规范](references/visual_style.md)、[五条铁律](references/five_rules.md)、[人工门 SLA](references/human_gate_sla.md)：执行协议。
- [官方合规](references/official_compliance.md)：2026 原文来源与逐条核对。
- [陷阱](references/pitfalls.md) 与 [两个案例](examples/benchmark_02_case_study.md)：真实事件教训。
- `templates/`：可复制的决策、交接、披露和启动提示；模板占位字段需要填写，不能作为已发生事实入账。

当前交付为公开发布候选。现有 `benchmark_01/...`、`benchmark_02/...` 仅是原始证据相对定位标识；原始 Benchmark 产物未打包，不要把这些标识解释成公开下载链接。发布前需由维护者选择 LICENSE、确认仓库 URL，并核查历史证据公开许可。
