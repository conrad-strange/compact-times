---
name: times
description: 查询当前 Codex 对话在本地日志中记录的上下文压缩次数。用于 /times、$times 或明确询问某个对话压缩了几次。
---

用本技能的 `scripts/times.py` 查询，保留当前执行环境的 `CODEX_THREAD_ID`。在当前对话直接执行，不委派给子代理。

将本 `SKILL.md` 旁 `scripts/times.py` 的绝对路径作为脚本路径。优先使用用户已有的 `compact-counter` conda 环境中的 Python；不要假定桌面应用继承了终端的激活状态。若 conda 在 PATH 中，可使用：

```text
conda run --no-capture-output -n compact-counter python -I "<本技能目录>/scripts/times.py"
```

若已知该环境解释器的绝对路径，直接用它执行脚本。未使用 conda 的用户也可用已有的 Python 3.11 或更新版本。Windows PowerShell 中调用带引号的解释器路径需要前置 `&`。运行时无需安装依赖。

只有用户指定其他对话时才加 `--thread-id <ID>`；可以用 `--codex-home <目录>` 指定日志根目录。缺少当前对话 ID 时说明原因，不使用其他对话的 ID 或最新修改时间代替。

直接返回脚本输出的一行，不额外分析。无法执行或找不到日志时说明原因，不凭记忆猜测次数。脚本只读本地记录，不触发压缩或修改会话。
