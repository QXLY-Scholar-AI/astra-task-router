---
name: astra-task-router
description: 按任务难度和宿主实际可用模型，在 GPT-6 Luna、GPT-6.1 Sol、GPT-6 Astra 之间规划有边界的子任务分工，保留当前主模型。用于模型任务调度、减少重复工作，以及项目或全局路由规则的安装、查看与卸载。
---

# Astra Task Router

先判断拆分是否值得，再选模型。保留用户当前主模型；主线程负责需求、关键判断、验收与交付。这个 Skill 提供规则与本地计划脚本，不提供模型账号或外部 API，也不自动切换正在运行的模型。

## 路由流程

1. 明确交付物、可检查的完成条件和允许操作的文件。一次短读或小改能完成的任务，由主线程直接处理。
2. 只有宿主提供子代理且用户或适用规则已授权委派时，才分派任务。缺少授权时继续主线程工作；用户要求评估这个 Skill 不等于要求初始化环境。
3. 从宿主工具说明或能力列表读取实际模型 ID、推理档位与并发上限。使用确切 ID，不凭品牌名推测可用性。
4. 按下表选择；可用型号以宿主为准。版本映射集中在 [references/routing-policy.json](references/routing-policy.json)，未来更新映射后复核档位。

| 任务 | 首选 | 默认推理 | 验收重点 |
| --- | --- | --- | --- |
| 明确字段提取、格式整理、重复性局部处理 | gpt-6-luna | low | 字段、数量与格式、未改无关内容 |
| 编码实现、跨文件排查、一般分析与写作 | gpt-6.1-sol | medium | 运行结果、证据、集成检查 |
| 高难科研判断、冲突证据、架构取舍与独立终审 | gpt-6-astra | high | 判断依据、替代解释、验收标准 |

Sol 不可用时可用宿主明确提供的 gpt-6-sol；其他回退按映射顺序进行。回退到能力或成本不同的型号要说明原因，遵守用户指定的预算与模型范围。没有合适可用模型时留在主线程，不反复重试或私接其他厂商 API。只有上下文长，不足以判定需要 Astra；先缩小输入并明确要查什么。

## 分派与返回

默认一个 worker。只有任务相互独立、文件不重叠且有实际并发收益时才并行，并遵守宿主槽位上限。不要同时让主线程和 worker 做同一遍工作。

每次交接包含：task_id、objective、allowed_paths、必要 inputs、constraints、deliverable、done_when。只给必需材料和上下文；宿主要求显式模型覆盖时使用新任务和最小上下文，不携带整段历史。

返回包含：status（complete/partial/blocked）、summary、evidence、artifacts、checks、open_questions。不要返回冗长思考过程。主线程打开产物并核对完成条件；默认最多一次定点纠正，仍不达标则重新规划或接手。模型不可用可按映射重选一次；反复失败则留在主线程。新目标开启新 worker，不把原任务无限续长。

显式选择模型不等于验证了实际运行身份；宿主若没有返回身份元数据，只报告选择参数及实际结果。

## 本地工具

SCRIPT 为本 Skill 的 scripts/router.py，Python 3.10+。脚本不调用模型。

```text
python SCRIPT plan --task standard --models host-models.json --delegation
```

host-models.json 由实际宿主能力生成，格式：`{"models":[{"id":"实际模型ID","reasoning_efforts":["low","medium","high"]}]}`。不要把示例当成实际探测结果。没有能力文件时只返回待核实计划。

## 持久安装、状态与卸载

用户临时使用调度时无需写设置。要求持久安装且未指定范围时，仅询问“当前项目还是全局”；已明确的授权直接执行，先显示脚本预览，再应用同一变更。不重复请求已经给出的批准。

```text
python SCRIPT install --scope project --root PROJECT
python SCRIPT install --scope project --root PROJECT --apply
python SCRIPT status --scope project --root PROJECT
python SCRIPT uninstall --scope project --root PROJECT --apply
```

全局使用 --scope global，默认只维护 ~/.codex/AGENTS.md 和自身状态；不会写入未经宿主核验的 config.toml 参数。项目模式不修改全局文件。备份、预览、幂等检查与冲突保护由脚本实现。规则块见 [references/managed-block.md](references/managed-block.md)。读取现有父级规则，项目规则优先；新对话才会可靠加载更新后的 AGENTS 指令。

发现旧版本状态或旧路由块时，先读取其备份和变更字段。保留用户无关内容及当前模型设置，只迁移本 Skill 的规则。旧版曾写入的 TOML 模型键，仅在确认仍为旧版值、有明确先前值及授权时恢复；不得直接覆盖用户后续修改。无法确认时保留并列出具体差异。卸载遇到安装后的文件变化时脚本会拒绝覆盖，应先按变更范围合并处理。
