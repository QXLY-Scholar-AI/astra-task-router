# Astra Task Router · 模型任务调度

保留当前主模型，把值得拆分的工作交给适合的可用模型，并带着证据和验收标准收回结果。

名称沿用 astra-task-router；新版已从“固定 Astra 主线程”改为按任务调度。它适合有子代理能力的 Codex 宿主，核心是明确分工、减少重复，而非每道题都开多个模型。

## 当前路由

| 任务 | 首选模型 | 默认推理 | 典型工作 |
| --- | --- | --- | --- |
| 例行处理 | GPT-6 Luna | low | 明确字段提取、格式整理、重复性局部编辑 |
| 一般实现与分析 | GPT-6.1 Sol | medium | 跨文件实现、排查、常规分析与写作 |
| 高难判断与终审 | GPT-6 Astra | high | 冲突证据、复杂科研推断、架构取舍 |

当前主模型不变。简单任务直接完成；默认最多一个 worker；独立任务才考虑并行，写入范围不能重叠。型号、档位和并发限制以宿主实际能力为准。映射单独保存在 [routing-policy.json](references/routing-policy.json)，便于后续更新；Sol 的旧版本回退优先考虑 gpt-6-sol。

## 安装

下载仓库 ZIP 并解压，将包含 `SKILL.md` 的目录命名为 `astra-task-router`。可以把目录或 GitHub 地址交给 Codex：

> 请安装这个仓库中的 astra-task-router，保留脚本和资源文件，并检查是否能调用。

手动安装（在该仓库根目录运行 Windows PowerShell）：

```powershell
$skillHome = Join-Path $env:USERPROFILE '.agents\skills'
$skillTarget = Join-Path $skillHome 'astra-task-router'
New-Item -ItemType Directory -Force $skillHome | Out-Null
if (Test-Path -LiteralPath $skillTarget) { throw '已安装同名 Skill，请先备份再更新。' }
Copy-Item -LiteralPath (Get-Location).Path -Destination $skillTarget -Recurse
```

安装后确认 `astra-task-router/SKILL.md` 位于 Skill 目录的第一层，再重新打开对话。不要只复制 SKILL.md。其他宿主请使用它实际扫描的 Skill 目录。

macOS / Linux（同样在仓库根目录运行）：

```sh
mkdir -p ~/.agents/skills
test ! -e ~/.agents/skills/astra-task-router && cp -R . ~/.agents/skills/astra-task-router
```

## 临时使用

> 使用 astra-task-router 处理这个项目。先判断哪些部分值得分派，保留当前主模型，按宿主实际可用的 Luna、Sol、Astra 安排；各子任务带完成标准，最后统一检查结果。

每次交接给 worker 的内容包括目标、必要输入、允许范围、限制、交付格式和验收标准。返回结论、证据、产物和未决事项；主线程核对产物，默认最多一次定点纠正。无需把整段聊天重复传给每个模型。

## 持久启用规则

需要 Python 3.10+，无第三方 Python 依赖。临时使用不必初始化。要让项目后续对话读取规则，可以让 Codex 执行安装，或手动预览与应用：

```sh
python scripts/router.py install --scope project --root /path/to/project
python scripts/router.py install --scope project --root /path/to/project --apply
python scripts/router.py status --scope project --root /path/to/project
```

Windows 将路径换成实际项目路径并加引号。全局模式使用 `--scope global`，只维护 Codex 的 AGENTS.md 与自身状态。脚本会备份原文件，不改 config.toml、模型账号、密钥或沙箱配置。新对话才会可靠加载更新后的规则。

## 查看选择计划

调用者先根据宿主实际公开的能力生成 `host-models.json`：

```json
{"models":[{"id":"gpt-6.1-sol","reasoning_efforts":["low","medium","high"]}]}
```

上面只是格式示例，不是探测结果。然后运行：

```sh
python scripts/router.py plan --task standard --models host-models.json --delegation
```

task 可选 routine、standard、deep。脚本仅生成计划，不会发送模型请求。没有能力列表时返回 needs-capabilities；没有委派授权、任务很小或没有合适型号时留在主线程。宿主若未返回实际身份元数据，只能确认选择参数，不能声称已验证模型身份。

## 卸载与旧版迁移

```sh
python scripts/router.py uninstall --scope project --root /path/to/project
python scripts/router.py uninstall --scope project --root /path/to/project --apply
```

没有其他改动时恢复原 AGENTS 文件，备份留存。安装后文件被用户修改，脚本会停止覆盖，先合并差异。旧状态不会被静默重写。

旧版本可能写过固定 Astra / GPT-5.6 的全局模型默认值；升级本 Skill 不会直接覆盖这些配置。应根据旧状态与备份逐项核对，明确需要恢复的键后处理。新规则不依赖那些旧键。

## 测试与宿主要求

```sh
python -m unittest discover -s tests -v
```

测试覆盖选择计划、可用性与档位回退、预览、安装幂等、卸载恢复及用户修改保护。实际分派需要宿主提供子代理和显式选择模型的工具；仅安装 Skill 不会让单模型聊天获得多模型执行能力，也不会产生可验证的价格节省统计。
