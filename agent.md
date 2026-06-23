# True Monad Agent 工作契约

本文件是项目内 AI 执行者的固定入口。文件系统是唯一真相来源；不要把聊天上下文当作已落盘状态。

## 启动顺序

1. 读取本文件。
2. 判断上下文是否足够；不足时读取 `current/compressed_monad.md`。
3. 按需读取 `current/current_question.csv`、`current/current_advice.csv`、`current/current_todo.csv`、`current/current_work.csv`。
4. 读取 `next/` 中全部 `I/Q/A/T-*.md` 文件，并把它们视为本轮完整输入。
5. 只有任务需要时才定向读取 `archive/` 和 `refer/`。

当外部消息仅为 `1`、`11` 或 `111` 时，它只是触发信号：不要解释数字含义，直接执行以上扫描。

## 每轮写入

1. 将本轮输入的 AI 理解写入 `current/instruction_understanding.md`，不得改写 `next/` 中的人类原文。
2. 更新 `current/compressed_monad.md`，沉淀稳定事实、已决结论、当前焦点和真实轮次状态。
3. 将给人看的 Markdown 结果写入 `end/`。
4. 按现有 CSV 表头向对应 current 文件写入 Question、Advice、To Do 和实际 Work；使用合法 CSV，不得自行增删列。
5. Question 是未决请求，Decision 是已决结论，不得混用。

## 管理边界

- AI 不执行归档和清理；`docs/scripts/archive_round.py` 或工作台负责。
- 在交付归档前，Compressed Monad 的状态应写成“本轮执行完成，等待归档”，避免声称尚未完成。
- 归档完成后，下一位 AI 启动时应根据 `archive/archive_rounds.csv` 的最新记录校正 Compressed Monad 的轮次状态，再处理新输入。
- 业务专用规则不写入本契约，应由对应 Skill、参考文档或工具维护。
