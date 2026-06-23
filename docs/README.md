# True Monad 工作台

这是一个以文件系统为唯一真相来源的本地工作台。它不需要安装第三方 Python 包。

## 启动

在项目根目录运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\docs\start.ps1
```

然后打开 <http://127.0.0.1:8051>。

## 首版已覆盖

- 查看 `current/compressed_monad.md` 和本轮指令理解
- 查看 Question、Advice、To Do、Work 状态
- 新建、编辑、删除 `next/` 指令文件
- 针对 Question、Advice、To Do 生成对应批复文件
- 查看 `end/` 本轮 Markdown 产出
- 检索 CSV 历史归档和轮次快照
- 检查 CSV 表头与指令命名契约
- 从 UI 或命令行归档并清理一轮数据
- 写入 `trigger.signal` 触发信号

## 触发器边界

工作台会把 `1`、`11` 或 `111` 写入项目根目录的 `trigger.signal`，状态为 `pending`。这只是稳定的文件协议，不会假装已经启动 AI。实际的 Codex/Agent 进程需要由外部监听器消费该信号，并在完成后更新或删除它。

## 归档命令

只校验，不改变文件：

```powershell
python .\docs\scripts\archive_round.py --check
```

明确归档并清理本轮：

```powershell
python .\docs\scripts\archive_round.py --confirm
```

归档会保留 `current/compressed_monad.md`，并清理 `next/*.md`、`end/*.md`、本轮指令理解及 current CSV 数据行。

## API 边界

服务默认只监听 `127.0.0.1`。它没有认证机制，不应直接暴露到局域网或公网。所有可访问路径和文件名均使用白名单约束，单次请求上限为 2 MB。
