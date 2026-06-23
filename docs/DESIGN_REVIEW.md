# True Monad 设计审阅与优化建议

本文记录实现首版工作台时发现的设计问题。首版已经采用可运行的默认方案，不以这些问题作为阻塞项。

## 已在首版中处理

### 1. 历史轮次还原与“不归档 Compressed Monad”冲突

原设计要求 Compressed Monad 原地覆盖且不归档，同时要求工作台能完整还原任意历史轮次。这两个目标不能同时成立。

首版方案：`current/compressed_monad.md` 仍不移动、不清空；每次归档额外把只读快照写入 `archive/archive_rounds.csv`。这不是将当前文件归档，而是为轮次追溯保存当时状态。

实际测试补充：归档发生在 AI 完成本轮写入之后，因此保留文件可能仍显示“等待归档”。`agent.md` 已要求下一位 AI 启动时用最新 `archive_rounds.csv` 校正轮次状态。正式版可考虑把“归档事务状态”从认知正文中拆成 Python 管理的独立元数据，彻底消除职责冲突。

### 2. 指令理解缺少本轮物理载体

原设计只说明它最终进入 `archive_instruction_understanding.csv`，没有定义归档前由谁、写到哪里，因此 Python 无法可靠找到待归档内容。

首版方案：增加 `current/instruction_understanding.md`，由 AI 写入、由归档脚本读取并清空。

### 3. 历史产出结构存在两个版本

`design.md` 要求产出进入 `archive_end.csv`，`Workbench.md` 又引用 `archive/end/Round_XXX/`。首版遵循“CSV 是归档载体”的总体原则，统一使用 `archive_end.csv`。

### 4. “一键触发 AI”缺少进程协议

浏览器不能仅凭字符可靠启动一个未定义的 AI 进程。直接在 Web 服务中拼接 shell 命令也会破坏职责分离并引入安全问题。

首版方案：工作台原子写入根目录 `trigger.signal`，明确展示 `pending`，由后续独立监听器消费。下一版需要确定消费方、幂等键、完成状态和失败重试策略。

### 5. CSV 转义职责表述不准确

合法 CSV 的转义应在写出时由 CSV writer 完成，而不是先修改字段内容。对引号再次手工转义会造成双重转义。

首版方案：所有归档使用 Python `csv.DictWriter`，并在写入前严格检查 current CSV 表头。

## 建议下一轮明确

### 1. 状态模型

需要为 Question、Advice、To Do 定义统一且封闭的状态枚举、允许的状态迁移和结案规则。当前首版只把 `resolved/closed/done/completed` 视为已结案，以兼容尚未定稿的数据。

### 2. 稳定标识与关联

建议所有记录使用不可复用的稳定 ID，并增加 `source_instruction_id`、`parent_interaction_id`、`decision_id`。仅靠文件名和 round_id 无法严谨表达一条 Advice 如何坍缩为 Decision。

### 3. Decision 的正式载体

Decision 是核心概念，但目录结构中没有 `current_decision.csv` 或 `archive_decisions.csv`。建议增加独立决策账本，不要只把结论塞进 Question/Advice 的 `decision` 字段。

### 4. 原子归档与故障恢复

当前归档适合单用户本地首版，但多文件追加过程中如果机器断电，可能形成部分归档。正式版应先写 staging 包和清单，校验哈希后再一次性提交，并记录归档事务状态。

### 5. 并发所有权

应明确 AI、工作台和归档脚本能否同时写同一文件。建议约定单写者、文件锁或乐观版本号；否则自动保存与 AI 更新可能互相覆盖。

### 6. 敏感信息边界

认知环境、指令和归档可能含敏感数据。正式版应补充备份、脱敏、保留周期、仓库忽略规则，以及本地服务从不监听公网地址的默认约束。

## UI 方向

首版使用“聚焦页 + 分区深入”的结构：首屏只展示当前是否可推进、待决事项、指令数、产出数和认知焦点；复杂历史表格放入二级视图。下一轮可在不改变文件契约的前提下补充 Markdown 渲染、轮次对比、键盘快捷键和更细的批量操作。
