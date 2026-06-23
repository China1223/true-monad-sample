# True Monad 项目工作契约

本项目已应用项目本地版 True Monad。`true-monad/` 中的代码、工作流和数据契约是本项目的权威版本；不得改用外部 Skill 中版本不同的运行代码。

## 每轮入口

收到用户的新任务后，在执行实质工作前：

1. 将用户原始指令逐字写入新的 `true-monad/next/I-YYYYMMDD-HHMMSS.md`。只记录用户原文，不加入解释、标题、frontmatter 或系统消息。
2. 不得覆盖已有指令；同一条已经落盘的指令不得重复记录。
3. 读取 `true-monad/WORKFLOW.md`。
4. 按需读取 `true-monad/current/compressed_monad.md` 和 current CSV；只有任务需要时才读取 archive 与 `docs/reference/`、`docs/topic/`。

当用户消息仅为 `1`、`11` 或 `111` 时，它是触发信号：仍应扫描 `true-monad/next/`，不要解释数字语义。

## 每轮产出

1. 将 AI 对本轮指令的理解写入 `true-monad/current/instruction_understanding.md`。
2. 更新 `true-monad/current/compressed_monad.md`，只沉淀稳定事实、已决结论、当前焦点和真实状态。
3. 将给用户的持久化结果写入 `true-monad/end/`。
4. 按既有表头记录 Question、Advice、To Do 和 Work，不得自行改变 CSV 列。
5. Question 是未决请求，Decision 是已决结论，不得混用。
6. AI 不直接手工搬运归档；使用 `true-monad/scripts/archive_round.py` 或工作台执行校验、归档和清理。

## 版本与管理边界

- `true-monad/manifest.json` 存在即表示已经安装。任何安装器不得静默覆盖。
- 日常运行始终使用项目本地代码。升级必须是用户明确请求的独立操作，并先验证 Git、安全备份、当前轮次和 Schema 兼容性。
- True Monad 只管理 `AGENTS.md` 中本区块、`true-monad/`、`docs/reference/`、`docs/topic/` 和 `docs/design/`，不得覆盖其他项目文档。
- `next/current/end` 是未归档状态，默认不进入 Git；`archive`、框架代码、配置和设计文档进入 Git。
