# True Monad（真元）

True Monad 是一个以“文件即契约”为核心的项目内人机协作框架。当前版本处于功能验证阶段：运行代码固定安装在本项目的 `true-monad/` 中，正式 Skill/Plugin 打包将在功能稳定后进行。

## 根目录四份原始设计文档

这四份文档由项目发起人提供，保留在根目录作为原始设计来源，不在重构中改写：

- `design.md`：系统架构、工作流、目录和工作台总体设计。
- `Workbench.md`：工作台功能范围与使用场景。
- `vocabulary.md`：核心概念、边界和术语。
- `compressed_monad.md`：Compressed Monad 专题说明。

## 目录职责

- `AGENTS.md`：Codex进入本项目后必须遵守的持久工作契约。
- `true-monad/`：项目本地固定版本的 Service、脚本、状态、产出与归档；它是唯一运行源。
- `docs/design/`：后续设计讨论、原始需求整理、架构取舍、审阅和迁移计划。
- `docs/reference/`：项目使用的稳定外部资料和规范。
- `docs/topic/`：围绕具体研究或开发主题形成的材料。
- `tests/`：框架代码的自动测试。

True Monad 只托管上述明确范围，不拥有 `docs/` 中其他潜在内容。

## 启动工作台

不需要第三方 Python 包。在项目根目录运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\true-monad\start.ps1
```

然后访问 <http://127.0.0.1:8051>。

## 校验与归档

```powershell
python .\true-monad\scripts\archive_round.py --check
python .\true-monad\scripts\archive_round.py --confirm
```

`next/current/end` 默认被 `true-monad/.gitignore` 忽略；完成归档后，`true-monad/archive/` 中的历史记录进入 Git。
