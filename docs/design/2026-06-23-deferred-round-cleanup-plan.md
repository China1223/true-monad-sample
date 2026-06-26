# True Monad 延迟清理与下一轮启动检查方案

## 1. 状态与目标

- 状态：待用户审查，尚未实施
- 目标：归档成功后保留上一轮 `next/current/end`；在下一轮开始时验证上一轮已经完整归档，验证成功后才清理，再建立新一轮状态。
- 核心安全原则：没有可验证的完整归档回执，任何脚本都不得删除上一轮文件。

## 2. 当前能力确认

当前系统已经能够记录并归档：

- 用户原始指令；
- AI 指令理解；
- Compressed Monad 快照；
- Question、Advice、To Do 和 Work CSV；
- end 中的 Markdown 输出；
- round_id、归档时间和文件内容。

轮次 `R-20260623-192021` 已经完整走通上述链路。本轮原始指令也已经进入 `true-monad/next/I-20260623-194418.md`。

目前仍有两个可靠性缺口：

1. 直接聊天依靠 `AGENTS.md` 约束 AI 主动落盘，没有独立的会话桥接程序，因此不能声称任何环境下都绝对自动。
2. 当前 `archive_round()` 在归档成功后立即清理 next/end 和 current CSV，不满足延迟到下一轮再清理的要求。

## 3. 新生命周期

### 3.1 本轮开始前：Startup Preflight

AI 收到新一轮用户消息后，首先运行只读检查，不得先写入新的 current 或覆盖旧文件：

1. 读取 `true-monad/current/round_state.json`。
2. 检查 `next/current/end` 是否存在上一轮内容。
3. 查找对应的 `archive/receipts/<round_id>.json`。
4. 校验回执状态为 `committed`。
5. 重新计算上一轮所有受保护文件的 SHA-256，与回执逐项比较。
6. 确认所有归档目标都包含对应 round_id，且数量与回执一致。

检查结果分为：

- `CLEAN`：首次运行，没有上一轮。
- `ARCHIVED_AND_RETAINED`：上一轮已经归档，但工作文件仍保留，可以清理。
- `UNARCHIVED_PREVIOUS_ROUND`：存在旧数据，但没有完整归档回执。
- `ARCHIVE_MISMATCH`：存在回执，但文件哈希、数量或目标记录不一致。
- `INVALID_WORKSPACE`：CSV、状态文件或目录契约损坏。

### 3.2 已归档：先清理，再开始新轮次

当状态为 `ARCHIVED_AND_RETAINED`：

1. AI 第一时间向用户报告“上一轮归档已验证，正在清理上一轮工作区”。
2. 清理上一轮 next 文件、end 文件、instruction understanding 和 current CSV 数据行。
3. 保留 `compressed_monad.md`。
4. 再次验证 current CSV 只剩合法表头，next/end 没有旧业务文件。
5. 创建新的 round_id 和 `round_state.json`。
6. 将本轮用户原始指令写入 next。
7. 才开始本轮任务。

### 3.3 未归档：先报错和恢复，不得清理

当状态为 `UNARCHIVED_PREVIOUS_ROUND`：

1. 检查脚本返回非零退出码和结构化错误，不删除任何文件。
2. AI 必须在本轮对话的第一条进度信息中明确告诉用户：发现上一轮未归档，已暂停新轮次初始化，正在进行恢复归档。
3. 向 `current/current_work.csv` 写入“发现上一轮未归档”的恢复事件。
4. 运行幂等的恢复归档。
5. 在 `archive/archive_events.csv` 中永久记录事件、时间、旧 round_id、原因和恢复结果。
6. 生成并验证归档回执。
7. 只有验证成功后才能清理旧工作区并开始新轮次。
8. 如果恢复失败，保持所有旧文件不变并停止任务，不能继续写新一轮 current。

### 3.4 回执不匹配：按数据事故处理

当状态为 `ARCHIVE_MISMATCH`：

- 不得自动清理。
- 不得假设已有 CSV 行就是完整备份。
- 报告具体缺失或哈希不一致的文件。
- 如果是归档后工作文件又被修改，将差异作为 recovery revision 归档，而不是覆盖原归档。
- 修复完成并生成新的 committed 回执后，才能进入清理。

### 3.5 本轮结束：归档但不清理

本轮结束时：

1. 校验所有 current CSV、next 和 end。
2. 归档本轮输入、理解、状态、Work、输出和 Compressed Monad 快照。
3. 写入 committed 归档回执。
4. 将 `round_state.json` 标记为 `archived_retained`。
5. 保留 next/current/end 原内容，不立即清理。
6. 工作台显示“已归档，等待下一轮启动时清理”。

## 4. 建议增加的状态与回执

### 4.1 `current/round_state.json`

```json
{
  "round_id": "R-20260623-194418",
  "status": "open",
  "started_at": "2026-06-23T19:44:18+08:00",
  "archived_at": null,
  "receipt": null
}
```

允许状态：

- `open`
- `archiving`
- `archived_retained`
- `recovery_required`
- `recovery_failed`

### 4.2 `archive/receipts/<round_id>.json`

回执至少包含：

- round_id 和归档事务 ID；
- committed 时间；
- 每个源文件的相对路径、大小和 SHA-256；
- 每个归档目标、写入数量和唯一键；
- Schema 版本；
- 归档脚本版本；
- 最终状态 `committed`。

回执必须最后写入。没有 committed 回执，归档一律视为未完成。

## 5. 脚本边界

建议拆成三个明确命令：

### `prepare_round.py`

- 只负责启动检查、回执验证和已归档工作区清理。
- 发现未归档或不一致时返回错误，不自行掩盖。
- 输出机器可读 JSON，供 AI 和工作台展示。

### `archive_round.py`

- 归档当前轮次并生成回执。
- 成功后不再清理工作区。
- 使用 round_id 做幂等检查，重复执行不得产生重复记录。

### `recover_round.py`

- 只处理上一轮未归档、部分归档或归档后变更。
- 写入 current Work 恢复事件和永久 archive event。
- 恢复失败时不得删除源文件。

## 6. 必须解决的幂等性

现有追加 CSV 归档在中途失败后重试，可能重复写入。实施本方案时必须同时加入：

- round_id + record id 唯一检查；
- 归档事务状态；
- 写入前 staging；
- committed 回执最后落盘；
- 部分失败后可重放但不重复；
- 清理操作仅接受已验证回执。

否则“下一轮清理”只能检查是否存在记录，不能证明完整性。

## 7. AI 对话行为

下一轮开始时的用户可见信息应明确区分：

### 正常情况

> 已验证上一轮 `<round_id>` 归档完整；上一轮工作文件已清理，正在初始化本轮。

### 自动恢复情况

> 启动检查发现上一轮 `<round_id>` 未完整归档。已暂停本轮初始化，正在保留原文件并执行恢复归档；恢复结果会在继续任务前报告。

### 无法恢复

> 上一轮归档恢复失败，未删除任何旧文件。本轮尚未写入 current；需要先处理列出的文件契约错误。

第一条进度信息必须在实质任务执行前发出。

## 8. 覆盖性测试计划

### 8.1 单元测试

1. 空工作区返回 `CLEAN`。
2. committed 回执和全部哈希一致时返回 `ARCHIVED_AND_RETAINED`。
3. current 任一 CSV 有数据但无回执时返回 `UNARCHIVED_PREVIOUS_ROUND`。
4. next 或 end 单独存在旧文件时同样报未归档。
5. 回执缺失一个源文件时返回 `ARCHIVE_MISMATCH`。
6. 文件在归档后被修改时哈希检查失败。
7. 非法 CSV 返回 `INVALID_WORKSPACE`，不尝试清理。
8. 清理后 CSV 保留正确表头。
9. 清理不删除 Compressed Monad。
10. `.gitkeep` 和框架文件不被清理。

### 8.2 归档与恢复测试

1. 正常归档生成 committed 回执，但保留工作文件。
2. 重复归档同一 round_id 不产生重复 CSV 行。
3. 模拟写入一半失败，重试后归档完整且无重复。
4. 未归档 current CSV 触发恢复归档，并写入 Work 和 archive event。
5. 恢复归档失败时所有源文件保持字节级不变。
6. 已归档后新增数据时生成 recovery revision，不覆盖旧记录。
7. 只有完整回执才能授权清理。

### 8.3 生命周期集成测试

1. 连续完成两个轮次，验证上一轮只在下一轮启动时清理。
2. 第一轮归档后模拟进程崩溃，第二轮能验证并清理。
3. 第一轮未归档即崩溃，第二轮先报告、恢复、验证，再开始。
4. 恢复失败时第二轮不得创建新的 round_state 或 current 数据。
5. 新轮用户原始指令只能在上一轮检查完成后进入正式 next。

### 8.4 工作台与浏览器测试

1. 归档后工作台显示 `archived_retained`，仍能看到上一轮内容。
2. 下一轮准备成功后，工作台显示新 round_id 和空 current。
3. 未归档恢复事件和错误详情可见。
4. 浏览器控制台无错误，刷新不会触发重复归档或重复清理。

## 9. 验收条件

- 任意清理动作都能指出授权它的 committed receipt。
- 未归档、部分归档、哈希不一致和非法 CSV 情况下零删除。
- 恢复归档可重复执行且不产生重复记录。
- 上一轮内容在归档后、下一轮开始前始终可见。
- 下一轮开始时，AI 在实质工作前报告检查结果。
- 连续两轮及故障注入测试全部通过。

## 10. 待用户确认的取舍

1. 是否接受增加 `current/round_state.json` 和 `archive/receipts/`。
2. 未归档时是自动执行恢复归档，还是报告后等待用户确认；本文按“先报告、自动恢复、失败即停止”设计。
3. 归档后文件发生变化时，是否允许自动生成 recovery revision；本文建议允许并永久记录事件。
4. 长期是否把跨轮次追加 CSV 改为逐轮不可变目录；本方案可以先兼容现有 CSV，但逐轮目录更容易实现可靠回执。
