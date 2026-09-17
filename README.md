# compact-times

在 Codex 对话中调用 `times`，查看当前对话在本地日志中记录的上下文压缩次数。

```text
你：$times
Codex：该对话压缩了 6 次（按本地保留记录）。
```

只有一个技能文件和一个 Python 脚本。按需读取，执行后退出；统计核心只用 Python 标准库，无后台服务、MCP 服务或模型 API 依赖。

## 使用

安装后，在要查询的对话中输入 **`$times`**。

也可以在桌面端 `/` 菜单输入 `times`，选择该技能并发送。官方文档说明启用的技能会出现在斜杠命令列表；这使用的是技能入口，并未向客户端注册一个新的内置命令。直接输入 `/times` 后回车是否自动匹配，取决于客户端行为，当前未做桌面输入框自动化验证。[官方调用说明](https://learn.chatgpt.com/docs/reference/slash-commands)

技能由 Codex 执行脚本并返回一行结果，仍可能消耗一次模型交互。单独运行脚本则完全在本地计算。

## 安装

需要 Python 3.11 或更新版本，以及能够读取目标会话本地日志的 Codex 环境。当前已在 Windows、Python 3.11 和 Codex CLI `0.154.0-alpha.6.2` 记录格式上验证；其他客户端版本的日志兼容性需要验证。

先克隆本仓库并进入目录，也可以下载 ZIP 后在解压目录打开终端：

```sh
git clone https://github.com/conrad-strange/compact-times.git
cd compact-times
```

### 1. 准备 Python

推荐使用独立 conda 环境：

```sh
conda env create -f environment.yml
conda activate compact-counter
```

已有 `compact-counter` 环境时只需激活。已有合适的 Python 时也可以直接使用，无需安装任何 pip 依赖。详细说明见 [ENVIRONMENT.md](ENVIRONMENT.md)。

### 2. 安装技能

在上述 Python 环境中执行，适用于 PowerShell、macOS 和 Linux shell：

```sh
python -c "import os, shutil; from pathlib import Path; target = Path(os.environ.get('CODEX_HOME') or Path.home() / '.codex') / 'skills' / 'times'; shutil.copytree('skills/times', target, ignore=shutil.ignore_patterns('__pycache__', '*.pyc')); print(target)"
```

这会将技能复制到 `CODEX_HOME/skills/times`，未设置 `CODEX_HOME` 时为 `~/.codex/skills/times`。如果目标目录已存在，命令会停止；确认已安装版本后再手动更新其中的 `SKILL.md` 和 `scripts/times.py`，避免覆盖自己的修改。

重新打开目标对话并调用 `$times`。如果新技能尚未出现，重启 Codex 后再打开原对话。桌面应用的执行环境也需要能找到 Python；可以直接告知 Codex 已安装的 conda 环境解释器路径，无需修改计数脚本。

### 卸载

删除安装位置中的 `times` 技能目录即可。该技能没有后台进程，也不创建统计数据库；卸载不会影响会话日志。

## 命令行用法

从仓库根目录执行：

```sh
# 在 Codex 的执行环境中查询当前对话
python -I skills/times/scripts/times.py

# 在普通终端中指定对话 ID（请替换示例 UUID）
python -I skills/times/scripts/times.py --thread-id 11111111-1111-4111-8111-111111111111

# 指定其他本地 Codex 数据目录
python -I skills/times/scripts/times.py --thread-id 11111111-1111-4111-8111-111111111111 --codex-home /path/to/codex-home

python -I skills/times/scripts/times.py --help
```

可以从 Codex 的 `/status` 获取对话 ID。[官方命令说明](https://learn.chatgpt.com/docs/reference/slash-commands)

| 参数或环境变量 | 用途 |
| --- | --- |
| `--thread-id` | 指定对话 UUID，优先于环境变量 |
| `CODEX_THREAD_ID` | 未指定参数时使用的当前对话 ID；普通终端通常没有此变量 |
| `--codex-home` | 指定 Codex 本地数据目录，优先于环境变量 |
| `CODEX_HOME` | 默认数据目录；未设置时使用 `~/.codex` |

成功时退出码为 `0`；无法可靠统计时为 `1`；命令行参数用法错误时为 `2`。业务结果和简短统计错误输出到 stdout，参数解析错误输出到 stderr。

## 统计口径

脚本按对话 ID 定位 `sessions/` 或 `archived_sessions/` 中的 `rollout-*-<ID>.jsonl`，核验 `session_meta.id`，只计算顶层 `type == "compacted"` 的记录。

- 消息正文、工具输出和嵌套历史中的压缩关键词不计数。
- 有 `compaction_response_id` 或 `window_id` 时按标识去重；缺少标识的旧格式按顶层记录数统计，无法判断记录本身是否由外部复制。
- 不用 token 数量、turn ID 或最大窗口编号推算次数。
- 每次重新读取目标日志，扫描范围固定为打开文件时的长度；统计的是当次快照。

这反映**本地保留日志中的压缩记录**，不保证包含已删除、未同步或其他设备上的历史，也不统计没有压缩记录的普通上下文切换。

## 限制与常见问题

| 情况 | 处理方式 |
| --- | --- |
| 无法获取当前对话 ID | 在目标 Codex 对话中调用，或显式传入 `--thread-id` |
| 未找到日志 | 检查 `CODEX_HOME`、对话 ID，以及该对话是否保存在本机 |
| 存在父任务、fork 信息或多段会话元数据 | 当前版本拒绝给出确定次数，避免混入继承历史 |
| 同 ID 匹配多个文件 | 返回来源不明确，不擅自选择或合并 |
| 文件坏行、未知格式或未写完的尾行 | 返回说明；尾行未完成时可稍后重试 |
| 文件读取权限不足 | 由用户为目标日志目录提供必要读取权限 |

当前版本没有修改内置 `/status`。必要性调研、替代方案和后续计划见 [ROADMAP.md](ROADMAP.md)。

## 开发与测试

```sh
python -B -m unittest discover -s tests -v
```

测试使用临时生成的合成日志，覆盖次数、去重、正文误匹配、身份校验、继承历史、归档定位、坏行和命令行调用。测试不会读取开发者的真实对话。

Windows 本地测试与真实长对话读取已通过。仓库提供 Windows / Ubuntu 的 GitHub Actions 测试配置，远端结果以实际运行记录为准。

```text
skills/times/SKILL.md          技能入口
skills/times/scripts/times.py  计数脚本
tests/test_times.py            标准库测试
environment.yml               可选 conda 环境
ENVIRONMENT.md                环境与开发说明
ROADMAP.md                    设计依据与范围
```

报告兼容性问题时，请附 Python / Codex 版本、错误信息和最小合成样本；不要提交真实会话正文。查询脚本只读日志，不保存摘要、修改记录或发起网络请求；技能仅把一行结果返回给 Codex。

## 许可证

[MIT](LICENSE)。本项目是独立社区技能，与 OpenAI 无隶属关系。
