# CUMCM Repository Architecture Audit

审计日期：2026-10-04。范围：Phase 1，仅阅读、验证和生成报告；本轮不修改实现，不创建新的 Agent 或工作流框架。

## 0. 审计范围与结论

审计对象是 `lean-workflow` 分支、提交 `3a92fdf12598723597f3de185ace177ebdaa04c6` 的完整工作树。逐文件阅读了全部 19 个受版本控制文件，检查了脚本入口、导入关系、命令分派、状态重放、产物绑定和现有测试，并在临时目录执行了 9 项针对性复现。

这是前轮精简和论文格式更新后的本地版本。此前拉取的 `origin/main` 位于 `7aeddd2`，有 60 个受版本控制文件；本报告不把此前已经删除的设计重复计为本轮发现，也不把本地提交等同于已上传 GitHub。

**当前项目是 Skill 指令与证据管理 CLI，尚不是能自行执行的 Multi-Agent Mathematical Modeling Pipeline。** README 明确写明脚本不调用模型，专业建模由读取 Skill 的外部代理完成。当前没有运行时 Agent、LLM 客户端、模型实现或数学建模端到端示例。

因此，主要问题是入口与状态复杂、跨工具接口不一致、运行故障难恢复，以及建模与审核仍依赖外部代理自行遵守文本指令。没有证据支持“几十个 Agent、Manager/Factory 泛滥、复杂框架依赖”这一描述。

### 当前规模

| 指标 | 审计基线 |
|---|---:|
| 受版本控制文件 | 19 |
| 全部文件物理行数，包括文档、配置和空行 | 2,272 |
| 运行脚本 | 7 个 Python 文件 |
| 运行脚本物理行数 | 1,490 |
| Python 总物理行数，包括测试 | 1,628 |
| 业务类 / 运行时 Agent | 0 / 0 |
| Skill 逻辑角色 | 人、执行代理、独立审核上下文，共 3 类 |
| `triad.py` 子命令 | 16 |
| 已有测试方法 | 32 |

新增本报告后的文件数与行数不属于以上基线。行数按文件文本的 `splitlines()` 统计，不将文档行数称作代码行数。

## 1. 当前架构与逐文件职责

目录层级较浅，最深的业务文件路径是 `templates/prompts/independent_review.md`。没有大型 `utils.py`、服务拆分、数据库、消息队列、向量记忆或依赖注入容器。

| 文件 / 目录 | 行数 | 实际职责与依赖 |
|---|---:|---|
| `README.md` | 119 | 安装方式、四门流程、CLI 示例、证据与交付边界 |
| `SKILL.md` | 32 | 给外部代理的执行指令；定义人工判断、执行与独立审核 |
| `scripts/triad.py` | 662 | 主入口；项目创建、输入导入、日志、运行、主张、审核、状态、冻结及重开 |
| `scripts/claim_check.py` | 20 | 独立 CLI；调用 `triad.check_claims/require_project/rows` |
| `scripts/init_project.py` | 19 | 兼容入口；调用 `triad.start`，不支持 `--input` |
| `scripts/hash_check.py` | 125 | 核验可信 SHA-256 清单；严格路径、重复项、符号链接与读取期间变化检查 |
| `scripts/anonym_scan.py` | 160 | 文本/PDF 身份线索扫描；可选 `pypdf`；不修改原文件 |
| `scripts/doctor.py` | 189 | 在子进程检查 NumPy、Matplotlib、中文字体、XeLaTeX 与实际最小编译 |
| `scripts/paper_review.py` | 315 | 文本抽取、论文结构提示、可选参考稿对比、图表清单检查、HTML 报告 |
| `references/official_compliance.md` | 63 | 官方规则来源与核对清单；本轮只审计文档职责，未重新验证网站规则 |
| `references/paper_format_profile.md` | 32 | 从参考论文学到的版式与最终页面检查要求 |
| `references/visual_style.md` | 21 | 图形选择、单位、字体、灰度与来源检查；含图表清单示例 |
| `templates/ai_usage_disclosure.md` | 44 | 真实 AI 使用详情模板；不构成已完成披露 |
| `templates/figure_style.json` | 69 | 绘图默认样式，供代理或外部绘图工具读取 |
| `templates/paper_layout.json` | 115 | 页面、文字、章节、图表、附录的默认格式配置 |
| `templates/paper.tex` | 127 | 可填写的 XeLaTeX/ctex 论文模板，包含三线表与源码附录位置 |
| `templates/prompts/independent_review.md` | 8 | 唯一独立审核 Prompt；定义 RESULTS 与 DELIVERY 检查 |
| `validation/test_workflow.py` | 138 | 26 项生命周期测试、6 项论文提示/报告测试 |

另有 1 个忽略配置文件，共 14 行。没有 `pyproject.toml`、依赖锁文件、CI 或 lint 配置。

### 依赖与调用边界

- 核心 CLI 使用 Python 标准库，README 要求 Python 3.10+。
- PDF 提取按需使用 `pypdf`；DOCX 使用标准库 ZIP/XML，并遍历正文 XML 内的段落，包括表格单元格中的段落。
- `doctor.py` 的 NumPy/Matplotlib 位于被检查的子进程中；XeLaTeX/ctex/字体属于可选排版环境，不是核心 CLI 的强制依赖。
- `claim_check.py`、`init_project.py` 导入 `triad.py`；`triad.py` 不反向调用其他检查工具。
- `paper_review.py`、匿名扫描、环境检查和指纹检查都是独立命令，没有被统一工作流自动串联。
- 没有模型 API、重试客户端或 Prompt Registry。不能通过重构“删除”并不存在的模型调用重复层。

## 2. 当前 workflow、状态和输入输出

### 入口与执行路径

主入口为 `python3 scripts/triad.py <command> <project>`。

`main()` 解析参数 → `require_project()` 校验项目与日志 → 查询命令调用 `status/validate`，写命令进入 `locked()` → `handle()` 分派具体操作 → 输出 JSON。

`run` 分支执行：检查新输出路径 → 收集题面和显式依赖指纹 → `subprocess.run()` → 保存控制台日志 → 校验输出与输入版本 → 登记运行事件。它执行用户提供的命令，**不生成模型或代码**；也没有执行沙箱。证据追踪与沙箱是不同职责。

### 流程语义

当前的逻辑顺序是：

1. `start/ingest` 保存题面和附件。
2. 外部代理分析题目；登记真实 SCOPE 决定并关闭 SCOPE。
3. 外部代理提出路线；登记 ROUTE 决定并关闭 ROUTE。
4. 外部代理编写代码，`run` 执行，登记关键 Claim。
5. 独立上下文审核，登记 RESULTS PASS 后关闭 RESULTS。
6. 外部代理写论文、生成图表和 PDF。
7. 独立上下文检查交付，登记 DELIVERY PASS 和六项检查，关闭 DELIVERY。
8. 人确认具体版本，`freeze` 保存快照；以后用 `reopen` 另开目录。

这是指令与人工登记流程。程序只限制关闭门的次序，不能保证分析、实验、审核和写作真的按上述顺序执行。例如，未关闭 SCOPE 时 `run` 仍能成功；`next` 只是 `status` 的别名，不会调用下一角色。

### 状态来源

唯一权威状态是 `logs/events.jsonl`，10 种事件类型由 `rows()` 校验。`state()` 重放事件，计算 `current_gate/closed_gates/frozen/open_failures`。

修改决定、运行、Claim 或审核会使对应门及后续门重新打开。`valid_review()` 还比较整个生产文件集合和记录上下文，拒绝旧版本 PASS。`append()` 每次读出所有事件，写完整临时文件，再原子替换日志。

没有 `INIT/PROBLEM_ANALYZED/.../COMPLETED` 这样的建模阶段状态机，也没有 `problem.json/model_plan.json/experiment.json/review.json` 等角色输出。已有门状态不等于用户要求的流水线状态。

### 项目产物目录

| 当前目录 | 实际用途 | 第一阶段可复用性 |
|---|---|---|
| `raw/` | 原始题面、附件；自动绑定运行输入 | 保留，承担 input 的职责 |
| `code/` | 外部代理写的模型与绘图程序 | 保留，承担 src 的职责 |
| `results/` | 实验结果，可放 `results/figures/` | 保留 |
| `paper/` | 论文、PDF、可选图表及图表清单 | 保留 |
| `reviews/` | 全量审核 ZIP、HTML 报告 | 保留产物，减少重复打包 |
| `compliance/` | 使用详情等交付文件 | 按需保留 |
| `logs/` | 事件日志、运行日志、写锁 | 保留日志；简化其状态职责 |
| `releases/` | 冻结快照 | 保留 |

没有 Excel/CSV 数据分析器、自动 EDA 或 PDF 题目结构化解析器。`ingest` 只是复制文件，`paper_review.extract()` 的 PDF 文本抽取也不等于题目解析。不要把这些未实现能力写成已有功能。

## 3. Agent 列表与实际职责

| 当前逻辑角色 | 实际职责 | 当前实现方式 | 边界问题 |
|---|---|---|---|
| 人 | 确认题意、路线、具体交付版本 | 外部答复＋CLI 登记 | CLI 无法证明答复真实来自人 |
| 执行代理 | 读题、处理数据、建模、实现、实验、画图、写论文 | `SKILL.md` 指令，宿主代理执行 | 职责集中；无法定位失败属于哪一建模阶段 |
| 独立审核上下文 | 数学与证据审核、最终页面及交付检查 | 单一 Prompt＋`record-review` | 无自动调用、结构化问题列表、分数或定向修订动作 |

当前没有 Agent class 或运行时调度器，也没有 Agent 互相聊天的代码。不能把独立审核角色按“只调用一次”删掉：它承担实质质量控制。

### 与目标六角色的差距

| 目标角色 | 可复用的现有部分 | 尚缺的边界 / 产物 |
|---|---|---|
| Orchestrator | CLI 参数解析、门检查、失败与冻结逻辑 | 明确阶段转换、角色调用、有限修订、终止条件 |
| Problem | Skill 中题意分析要求、`raw/` | 六个结构化字段的 `state/problem.json` |
| Data | 原始文件导入、`doctor` 环境诊断 | schema、缺失/异常、统计、EDA 产物 |
| Modeling | Skill 的基线与路线要求 | 每问候选比较、变量/目标/约束/评价的模型计划 |
| Experiment | 真实子进程执行、版本指纹、结果目录 | 将计划落实为代码、数值校验和实验汇总 |
| Critic | 独立审核 Prompt、旧审核失效与 Claim 检查 | score、blocking/minor issues、recommended_action 及对应阶段重试 |
| Paper | TeX 模板、版式文档、文本/图表提示 | 只消费通过审核的模型与结果；数字和来源映射 |

这张表描述后续边界，不表示本轮已经新增这些模块。应复用有效执行和检查代码，不重建所有目录或强行引入 Agent 框架。

## 4. 已确认的功能与体验问题

优先级含义：P1 为稳定执行或证据边界问题，P2 为接口和呈现问题。以下均以当前提交为准。

| ID | 优先级 | 证据位置 | 确认事实 | 用户影响 |
|---|---|---|---|---|
| A01 | P1 | `triad.locked()`，108–118；`main()`，651–654 | 锁只有 UUID；强制终止进程后留下 `write.lock`，后续写入被永久拒绝，未检查持有者是否仍存活 | 中断后看起来一直“有人正在写”，需要人工识别和清理 |
| A02 | P1 | `triad.handle()`，473–477 | 超时只保存 `str(exc)`，丢弃 `TimeoutExpired.stdout/stderr` 中已经捕获的内容 | 长实验失败后缺少最后输出，难定位具体阶段 |
| A03 | P1 | `triad.run_inputs/current_run`，165–173；运行依赖收集，466–471 | 自动绑定 raw 和命令直接引用文件；未登记的 import 模块不绑定。修改 `code/helper.py` 后运行仍被认为 current | 忘填 `--input-ref` 时，代码依赖与旧结果可能不一致；README 已披露手工登记要求，但自动流水线不能默默依赖记忆 |
| A04 | P1 | `triad.main()`，651–654；`subprocess.run()`，473 | 整次外部命令执行期间持有项目写锁 | 一个长实验阻止故障登记、决定登记等写操作；不利于后续角色协作 |
| A05 | P2 | `triad.freeze`，542；`hash_check.load_manifest()`，34–38 | freeze 输出 `{path: sha256}`，hash_check 要求 `{algorithm, files}` | 仓库自己的核验工具不能直接读取仓库自己的冻结清单；会返回退出码 2 |
| A06 | P2 | `paper_review.abstract_counts()`，79–91；`templates/paper.tex`，41–53 | 自带 TeX 模板使用格式命令中的“摘要”和关键词，解析器只识别 abstract 环境或纯文本标题 | 对自带模板的 TeX 源码统计摘要为 0，且无解析警告；启用字数阈值会产生误导性提示 |
| A07 | P2 | `paper_review.render()`，212、238–239 | style findings 同时进入“写作与证据风险”和“图表风格” | 同一条图表问题可见两次，制造检查噪音 |
| A08 | P2 | `triad.handle()`，454–459 | `run --output figures/q1.png` 被拒绝，只允许 results/ 或 paper/ 下的新文件 | 与目标顶层 figures/ 约定冲突；当前可以复用 `results/figures/` 或 `paper/figures/`，不必搬动全部目录 |
| A09 | 目标差距 | `triad.handle()` run 分支、`SKILL.md` 执行顺序 | 未完成 SCOPE/ROUTE 仍能 run；没有程序化 Critic→Paper 阶段入口 | 现在能管理运行证据，但不能保证用户要求的自动流水线阶段顺序 |

A01 的复现是对本次创建的隔离进程组强制终止，不是普通 Python 异常。普通退出会经过 `finally` 清理；不能把所有失败都归因于残留锁。

A03 不代表所有修改都绕过审核：`valid_review()` 的全量 bundle 会发现生产树改变。问题是运行自身的依赖声明不完整，新审核仍需人工判断旧结果是否必须重跑。

### 代码阅读确认的额外限制

- `run` 使用 `capture_output=True`，中途不显示进度；stdout/stderr 最后拼接，无法还原交错顺序。日志量未做流式上限，实际大日志性能尚未 benchmark。
- `review_context()` 绑定 raw/code/results/paper/compliance 的全部文件和所有人工决定、运行、失败事件 ID。增加无关文件也会令审核失效；每次审核包包含历史结果和完整日志，没有当前有效产物清单。
- `state/status/checks/valid_review` 多次读完整日志，`append` 重写全部日志。调用路径和重复 IO 已确认，随项目规模增长的实际耗时尚未测量，不能声称已出现性能崩溃。
- `check_claims()` 校验登记的主张，但零条 Claim 时循环直接通过；程序没有检查论文中的所有关键数字是否登记，也不比较文字数字与结果字段。
- `record-review` 接收外部 PASS 和可选 notes；`context-id` 只是自报标识。DELIVERY 检查项也是外部登记，程序本身没有渲染、逐页看图或验证数学。
- 目前 `validate` 表示记录一致性，不表示题目已解答或论文合格。未冻结项目的 validate 不检查全部阶段是否完成。
- 没有定向 `fix_data/redo_model/redo_experiment`、最大修订次数或自动终止失败状态。修复后如何重跑由外部代理判断。

## 5. 冗余、重复实现与 Prompt

| 项目 | 证据 | 判断与处理方向 |
|---|---|---|
| `next` 与 `status` | `main()` 将二者交给同一 `status(p)` | 确认功能完全重复；可去掉别名或只保留内部兼容 |
| `init_project.py` 与 `triad.py start` | 包装 `start()` 并固定空 inputs | 纯兼容入口；仓库内部没有调用。确认外部使用情况后可删除 |
| `claim_check.py` 与 `triad.py validate` | 都调用 `check_claims()`；validate 还检查冻结状态 | 实现已共享，不是复制了主张算法。CLI 可合并到未来 audit，但要保留“仅主张核验”和“完整状态核验”的范围差异 |
| PDF 打开/抽取 | `paper_review.extract/pdf_pages`、`anonym_scan.pdf_text` | 同一稿在 paper_review 内打开两次；匿名扫描还有元数据、加密、空页、附件检查，不能简单用宽松提取器替代 |
| 子进程执行 | `triad.handle(run)` 与 `doctor.run()` | timeout/编码/日志逻辑重复；doctor 已保存超时部分输出。可提取小函数，分别保留证据登记与环境探测职责，不创建执行 Manager |
| SHA-256 与路径检查 | `triad.digest/evidence`、`hash_check.check_file/load_manifest` | 有相似实现，但严格性不同；先统一清单协议与校验边界，再共享必要函数 |
| 格式事实多处描述 | JSON 配置、TeX 硬编码、两份样式文档 | 是供不同工具使用的格式合同，不是死配置；缺少一致性验证，存在漂移风险 |
| 审核 HTML 的 style 列表 | `render()` | 确认重复呈现，直接去重即可 |
| Prompt / 指令 | SKILL、README、独立审核 Prompt | 仅 1 个专用审核 Prompt，没有庞大重复 Prompt 系统。操作文档与审核职责说明部分重合，可压缩但不应盲删 |

重复算法与多个合法调用入口分开判断。例如 `claim_check.py` 是 wrapper，但没有重复实现 Claim 逻辑；为去掉 20 行文件而破坏现有用户命令不值得。

## 6. Dead Code 检查

当前没有确认的整块死业务模块，也没有找到无引用的 Agent、Manager 或 Registry。主要函数可从 CLI 入口、共享校验或测试到达。

- `init_project.py` 是唯一明显的兼容入口候选：当前 README/SKILL/测试没有使用它。但独立 CLI 没有内部调用，不足以证明外部无人使用，应标为“删除候选”，不是“已确认死代码”。
- `next` 是有效但重复的公开子命令，不属于不可达代码。
- 两份样式 JSON 没有 Python 消费者，但 README/SKILL 和版式文档明确引用，供外部代理/工具使用；不能据此宣布无效配置。
- TeX、AI 披露模板、官方核对文档与唯一审核 Prompt 均有明确引用或用途。

后续可以删除已确认不再支持的兼容入口，但不应编造 unused function 数量或借静态搜索一次没有命中就删脚本。

## 7. 过度设计与状态管理

### 真正需要简化的地方

1. **事件日志兼任状态数据库。** `rows/state/latest/valid_decision/valid_review/check_claims/checks` 共同解释流程，理解门为何打开需要跟踪事件历史、文件指纹和当前审核上下文。用户要求普通 JSON 状态，下一阶段应把当前阶段与有效产物存为小型显式 state，事件日志只承担追踪；迁移时必须保留已有失效规则。
2. **命令分派与业务混在大文件。** `handle()` 157 行处理 11 类操作，`main()` 92 行负责 CLI、锁、状态与校验分派。不是几千行巨石，但一个开发者仍需读较长文件才能定位不同阶段的问题。适合按清楚职责拆少量函数，不需要 BaseAgent/Factory。
3. **公开入口偏证据维护。** 16 个子命令加多个独立脚本，用户或外部代理需自行串联 run、Claim、review、close-gate 和 freeze。可以在现有实现上建立一个 solve 入口，把登记作为内部操作，避免把每个内部步骤都暴露成工作流决策。
4. **审核上下文过宽。** 全量生产文件和全历史记录混成一个版本边界；无法明确区分 Data、Modeling、Experiment、Paper 的依赖。应让角色读取当前有效产物与相关依赖，避免把无限增长的 ZIP 当作 Agent 上下文。

### 没有发现的过度设计

没有 LangChain/LangGraph/CrewAI，没有多层 supervisor、Agent voting、自进化 Prompt、memory server、Redis、消息队列、数据库或微服务。没有必要以“简化”为由先引入框架，再用更多抽象包装现有函数。

## 8. 用户体验与论文呈现

### 与差体验有关的可验证因素

- 启动与证据登记很多，但没有 `solve <problem>`；用户难以判断“已经开始解题”还是“只是完成登记”。
- 出错层次是门、Claim、事件和文件版本，不能直接告诉用户是题目解析、数据、模型、实验还是论文阶段失败。
- 长实验没有实时状态，强制停止后可能残留锁，超时又缺最后输出。
- 重跑必须自己选择 run-id 和新输出路径；这是防旧产物冒充新运行的有效约束，但应由调度器生成版本，减少人工负担。
- 全量审核失效与重复报告提示可能引发不必要重审；字数/词频提示无法代替数学与图形核验。
- 旧项目格式被明确拒绝，当前只支持新目录试用；安全边界清楚，但现有用户继续工作需要迁移指引。不能直接覆盖旧记录。

这些是代码与复现支持的影响判断。本轮没有取得同学的具体操作记录、机器环境或失败样例，因此不能断言它们就是同学差评的全部根因。

### 已有论文能力与具体问题

保留从参考论文学到的摘要首页、中文章标题、十进制小节、三线表、连续公式、图表和附录格式；参考稿的题名、问题数量、模型与数值不应移入新论文。模板是有效资产。

当前不足主要在验证衔接，而非需要新增更多“写作 Agent”：

1. A06：TeX 模板与摘要提取器不兼容，应建立针对实际模板的验证，而非只测试手写 abstract 环境。
2. A07：图表提示重复；HTML 仍写“低饱和”等旧偏好，与当前默认科学配色及允许按变量调整的原则不完全一致。
3. 图表清单只核对文件/来源路径与 PNG 插入分辨率，不能验证单位、曲线数值、遮挡、实际字体、灰度或图文结论一致性。
4. PDF 检查仅部分依赖文本提取；DELIVERY 的 PDF 文件头检查不能发现缺字、溢出、无效交叉引用或正文/附录页数划分。
5. `--min-pages/--max-pages` 比较总 PDF 页数，无法自动区分正文与附录。用户配置不能直接当作正文页数限制。
6. Paper 没有程序化的证据输入合同，不能保证每个关键数字都来自已通过 Critic 的实际结果。

本轮未修改用户论文，也没有把私人题面、论文 PDF 或同学记录复制进仓库。

## 9. 建议删除、合并或简化的内容

这是审计建议，正式修改顺序、风险和回归验证留到 Phase 2 的 `REFACTOR_PLAN.md`。

| 建议 | 内容 | 保留条件 / 删除边界 |
|---|---|---|
| DELETE 候选 | `next` 别名；`init_project.py` | 先确认兼容承诺与外部入口；不宣称已经删除 |
| DELETE | HTML 中重复的 style 展示、旧色板偏好措辞 | 不删除真实的图表问题和 UNKNOWN 提示 |
| MERGE | 主张核验 CLI 与未来 audit；必要的进程/指纹小函数 | 不合并不同严格度的检查，不增加 Manager |
| SIMPLIFY | 权威事件重放状态、全量审核上下文、过多公开登记命令 | 保留可追踪日志、旧审核失效、真实运行证据与冻结快照 |
| SIMPLIFY | 手工版本编号与修复后流程串联 | 内部自动编号；限定最大修订次数，只重跑受影响阶段 |
| 修复 | 写锁生命周期、超时日志、冻结清单协议、模板摘要识别 | 先加对应回归案例，再作小范围修改 |

不要删除独立审核、真实实验、输入追踪或最终页面检查来换取表面上的“更少步骤”。也不要立即重写整个 `triad.py`。

## 10. 建议保留的有效实现

- 标准库优先和当前浅目录结构。
- 原始输入不覆盖、路径/符号链接检查、重复输入检查与导入回滚。
- 实际子进程执行、退出码、输出存在性、新版本产物约束与输入/输出指纹。
- Claim 与运行产物绑定，旧运行/审核失效，后来的 REJECT 覆盖旧 PASS。
- 冻结前重查、暂存后提交、不可写冻结项目、另开版本与快照核验。
- 独立审核 Prompt 的数学、证据、结论边界与最终交付检查。
- PDF/DOCX 文本提取、匿名扫描、环境诊断、图表来源与分辨率检查；保留它们明确说明的不确定边界。
- 学到的论文格式、实际 TeX 模板、绘图样式和真实 AI 披露模板。
- 现有 32 项生命周期与呈现回归，作为后续改动的保护网。

## 11. 验证记录与测试缺口

### 本轮实际执行

环境为 Python 3.12.14。

```bash
python3 validation/test_workflow.py
```

结果：32/32 通过，约 8.9 秒。所有受版本控制 Python 文件均经 AST 解析通过。没有现成 lint 配置或可用 ruff，未声称 lint 已通过。

### 9 项隔离复现

各案例使用临时项目和合成文件，没有调用模型或修改生产项目。正常退出不影响原仓库。

| 复现 | 实测结果 |
|---|---|
| 在 INIT/SCOPE 未确认时执行产生结果的 Python 脚本 | run 退出码 0，SUCCEEDED；current_gate 仍为 SCOPE |
| model.py 导入 helper.py，运行后只改 helper.py | 自动 inputs 仅含 model.py；`current_run()` 仍为 True |
| 声明顶层 `figures/q1.png` 输出 | 退出码 2；要求 results/ 或 paper/ |
| 脚本先 flush 输出，再等待直到超时 | FAILED；日志有超时说明，没有先前的输出 |
| 实验运行时登记 failure | 退出码 2；提示另一个写入正在进行 |
| 强制终止该隔离实验进程组，再登记 failure | write.lock 残留；下一写入仍退出码 2 |
| 用现有测试 fixture 真正 freeze，再运行 hash_check | 退出码 2；拒绝仓库生成的 manifest 协议 |
| 对当前 `templates/paper.tex` 执行 extract/metrics | 包含摘要标题，但摘要中文字符数为 0；warnings 为空 |
| 无图表清单时生成 HTML | “未提供 figure_manifest.json” 在可见 HTML 中出现 2 次 |

### 可重跑的短复现入口

不要求安装模型或数学框架。以下命令在仓库根目录运行：

```bash
python3 - <<'PY'
from pathlib import Path
import sys
sys.path.insert(0, 'scripts')
import paper_review
p = Path('templates/paper.tex')
text, warnings = paper_review.extract(p)
print(paper_review.metrics(text)['abstract_chinese_chars'], warnings)
PY
```

当前输出为 `0 []`。对于已冻结的合成项目，可执行：

```bash
python3 scripts/hash_check.py --manifest /path/to/project/releases/v1/manifest.json
```

当前返回协议错误，而 `triad.py validate` 的内部快照核验仍可正常工作；这是工具互操作问题，不是所有冻结校验失效。

### 未覆盖与未验证

1. 没有 Problem/Data/Modeling/Experiment/Critic/Paper 的独立模块测试或结构化状态 round-trip 测试。
2. 没有真实小题的 `Problem → Modeling → Experiment → Critic → Paper` 数学建模 integration test。已有完整生命周期测试写入固定合成指标与 PDF 文件头，只证明证据流程。
3. 没有对新增 TeX 模板的摘要解析、一致格式和真实编译的仓库内自动测试；此前人工排版验证不等于持续集成覆盖。
4. 没有强制中断锁恢复、超时部分输出、import 依赖、冻结清单互操作与重复提示的回归测试。
5. 没有项目规模、审核包大小、实际模型正确性或同学体验 benchmark。审计不把这些未知项说成已修复成果。

## 12. Phase 1 完成边界

本轮新增的仓库内容仅为 `ARCHITECTURE_AUDIT.md`。没有修改 Python、Prompt、配置、模板或测试，没有执行大规模重构，也没有安装新的 Agent 框架。

下一阶段应以本报告证据生成 `REFACTOR_PLAN.md`，先解决已复现故障和冗余入口，再逐步建立六角色产物合同、普通 JSON 状态、有限定向修订与最小真实 demo。保留当前有效实现，不用全量重写替代理解。
