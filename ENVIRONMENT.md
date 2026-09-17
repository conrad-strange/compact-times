# 开发环境

项目仅使用 Python 标准库。建议 Python 3.11；不需要额外安装 pip 包。

## conda

在仓库根目录运行：

```sh
conda env create -f environment.yml
conda activate compact-counter
python --version
```

已有同名环境时直接激活。`environment.yml` 固定 Python 3.11 系列，允许补丁版本更新，不是精确平台锁文件。conda 可能自动带入 pip、setuptools、wheel 及运行库，这些不是统计功能的业务依赖。

无需激活也可运行：

```sh
conda run --no-capture-output -n compact-counter python -I skills/times/scripts/times.py --help
```

如果桌面应用中没有 `conda` 命令，在已激活环境的终端运行下面的命令获取解释器路径，再让 Codex 使用这个绝对路径：

```sh
python -c "import sys; print(sys.executable)"
```

Windows PowerShell 调用带引号的解释器路径时，在前面加 `&`。不要把自己的机器路径写进准备提交的技能源文件。

## 不使用 conda

已有 Python 3.11 或更新版本时可直接运行脚本和测试，无需虚拟环境或依赖安装。Linux/macOS 的命令名可能是 `python3`，相应替换下文的 `python`。

## 测试

```sh
python -B -m unittest discover -s tests -v
python -I skills/times/scripts/times.py --help
```

测试数据全部在临时目录生成，测试不会读取真实会话。命令行集成测试会使用当前 Python 解释器创建子进程，并验证 UTF-8 输出及退出码。

技能格式可额外通过 Codex 自带 `skill-creator` 的 `quick_validate.py` 校验。这个开发工具需要 PyYAML；可以使用该工具已有的运行环境，无需将其加入技能的运行依赖。

## 验证范围

开发时在 Windows、Python 3.11.16 上通过了单元与命令行测试。真实长对话的次数从首次读取的 5 次变为稍后读取的 6 次，与新增压缩记录及独立事件 ID 核对一致。项目没有收录该对话的标题、ID、正文或日志文件。

GitHub Actions 配置了 Windows / Ubuntu、Python 3.11 的测试。远端 CI 只有在推送后才会运行，配置存在不代表已在这两个远端平台通过。
