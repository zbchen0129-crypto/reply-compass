# Reply Compass · 回话指南

根据聊天上下文，提供不同立场、语气和 Emoji 偏好的回复建议。

## 当前状态

已实现 Python 本地 API 与真实模型调用适配层：聊天提取 → 人工修改上下文 → 多方向生成 → 独立模型检查。2026-11-10 已用 gpt-4.1-mini 完成三个虚构案例的真实 API 联调和一次浏览器生成流程。发现立场偏移、编造可用时间及检查漏报；v2 已复测，局部改善但仍有角色反转、检查误报等问题，尚未完成模型质量评估。三个预置案例仍为人工编写的演示，不代表模型效果。

## 本地运行

在此目录运行：

```sh
python3 server.py
```

访问 http://127.0.0.1:8765 。Python 3.10+，无需第三方依赖。未配置模型时可以使用预置案例。真实功能需启动前在服务端设置 `OPENAI_API_KEY` 和 `OPENAI_MODEL`（账号可用且支持 Responses 结构化输出的模型 ID）。不要将密钥写入代码、前端或提交记录。服务启动时自动读取项目根目录 `.env`；已存在的环境变量优先。配置值按字面解析，不执行 shell 命令或变量展开。

“整理并预览”仅在本机运行，不调用模型。点击“确认并分析”才会将确认后的对话发送给 OpenAI；生成阶段还会发送已纠正的上下文。每次分析调用一次模型，每次生成调用两次模型（生成、检查），可能产生 API 费用。应用不持久化聊天，API 请求使用 `store: false`；这不等于服务商零保留承诺。

支持两种输入方式：

- 带姓名的聊天：每行 `姓名：内容`，可带 `[10:30]` 这类方括号时间戳；选择哪个名字是自己后，自动整理成“我／对方”，可继续修改。
- 对方的一条消息：直接粘贴内容，无需手写角色前缀；换行合并为同一条消息。

目前仅支持双人文字聊天，不支持截图、群聊或任意平台导出格式。整理入口最多 18,000 字符、240 行、80 条消息；至少需要一条对方消息。已有“我／对方”格式仍可直接使用：

```text
我：I might be free Saturday.
对方：Dinner Saturday?
```

修改聊天需要重新分析；修改偏好或摘要会清除旧结果。摘要可修改文本，当前不支持增删条目。模型检查仅作提示，不保证事实或语义完全正确。

## 第一版核心

1. 有消息来源的事实、待回答问题、承诺和待定事项。
2. 分开控制回复立场与语气。
3. 展示建议引入的承诺或需要用户确认的安排。

完整需求、数据契约、评估方案和开发清单见 [docs/plan.md](docs/plan.md)。

## 后续技术路线

原型使用无构建依赖的 HTML/CSS/JavaScript。当前采用原生 JavaScript 前端与 Python 标准库 API，减少本地安装依赖。TypeScript 迁移保留为后续任务；先验证流程，再决定是否加入数据库或历史检索。任何模型效果及相对基线提升均须实际评估后报告。

## 公开仓库规则

只提交虚构或明确授权公开的案例。密钥由服务端环境变量读取，真实聊天、本地数据库不入库。公开仓库：https://github.com/zbchen0129-crypto/reply-compass 。尚无公开托管演示。

## 验证

```sh
python3 -m unittest discover -s tests -v
```

使用假模型测试契约、引用校验、方向一致性、纠正后的上下文传递、检查失败、无凭据状态和 API 请求结构。测试通过不表示模型质量通过。

## 接口

- `GET /api/status`：配置是否齐全（不验证账号权限）。
- `POST /api/normalize`：`{text, mode, self_name?}`，本机整理与身份确认；不调用模型。
- `POST /api/extract`：`{chat}`，返回消息和带来源的上下文。
- `POST /api/generate`：`{chat, context, preferences, directions}`，返回候选与独立检查结果。

API 仅用于本机开发，绑定 127.0.0.1；不是面向公网的生产服务器。请求体上限 128 KB，聊天上限 20,000 字符/80 条，每次最多三个方向，单次上游超时 45 秒。

实现依据：[OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses)。

## 开发故事与实测证据

[开发问题与决策日志](docs/development-log.md) 持续记录失败、设计取舍、验证与剩余问题。每次复测另存文件，保留旧版本证据。

真实模型冒烟回归（需本机服务已启动；三个虚构案例，共 9 次模型调用，会消耗 API 额度）：

```sh
python3 scripts/live_smoke.py --output evidence/your-new-run.json --version v2
```

脚本校验运行版本，拒绝覆盖已有文件。开发样例回归不能代替独立评估。

### v3 复测状态

上下文新增人物关系字段（状态属于谁、请求者、执行者、接受者），页面可纠正；当前立场单独传给生成和检查阶段。20 项程序测试通过；原三案例和四个角色案例已真实运行，发现局部改善但仍有角色反转、元数据不一致和检查误报。详见 [v3 验证记录](evidence/verification-v3-2026-11-10.md)。代码更新后需要在原终端重启服务并刷新页面。

角色回归集共 4 例，预计 12 次模型调用：

```sh
python3 scripts/live_smoke.py --cases evals/role-regressions.json --output evidence/roles-v3-run1.json --version v3
```

原三个案例回归使用 `--version v3`。脚本会在调用模型前拒绝旧服务；不要将假模型测试或回归样例当作独立质量评估。

### 独立检查器评估

`POST /api/check` 接收与生成接口相同的聊天、上下文、偏好、方向，外加固定 `candidates`。只调用检查器一次，与生产流程共用代码；不调用提取或生成模型。

```sh
python3 scripts/evaluate_checker.py --validate-only
python3 scripts/evaluate_checker.py --output evidence/checker-new-run.json
```

真实评估需在配置好的原终端重新启动服务。8 条全部完成时调用模型 8 次；失败后停止，保存部分结果。标签不会发送给模型。输出包含误报/漏报计数及分母、类型命中、调用失败与未运行数。new_commitment 提醒不算错误。数据集为助手编写的开发样例，尚未独立审阅；类型分数还需结合原始解释核对，不代表正式准确率。

## 一次性保存本机模型配置

在本机终端运行：

```sh
cd reply-compass
python3 scripts/configure_local.py
```

按提示粘贴 API Key（输入不可见），模型名称直接回车使用 `gpt-4.1-mini`。脚本将密钥明文保存在项目 `.env`，权限为 600（仅当前用户可读写）。这不是加密保险库；不要分享此文件。`.env` 和配置临时文件已被 Git 忽略，`.env.example` 可以提交。

配置完成后重启 `python3 server.py` 即生效；不用每次 export。如果当前终端仍有旧 OPENAI_API_KEY / OPENAI_MODEL，它们会优先于文件；需要使用文件配置时，可在终端运行 `unset OPENAI_API_KEY OPENAI_MODEL` 后启动。不需要把密钥发到聊天里。

重复运行配置脚本可更新密钥和模型，保留已配置的 PORT。配置取消或输入校验失败不会覆盖原文件。脚本不支持非交互输入，防止密钥落入命令参数或执行记录。

首次独立检查器真实测试已完成：8 条开发样例、0 调用失败；正确候选误报 0/4，错误候选漏报 2/4，目标类型命中 1/4。仅一次小样本开发测试，不能作为正式质量指标。详见 [评估审阅](evidence/checker-v3-review-2026-11-11.md)。

### 逐项检查对照实验（2026-11-16）

新增 `checker_dimensions.py`，保持实验版本与生产检查器分离。12 条案例、24 次串行调用：两者各发现 3/6 错误候选，逐项版本耗时更长，因此没有替换生产。详见 [对照实验审阅](evidence/checker-comparison-review-2026-11-16.md)。

```sh
python3 scripts/compare_checkers.py --output evidence/unique-comparison.json --validate-only
python3 scripts/compare_checkers.py --output evidence/unique-comparison.json
```

脚本直接加载本机 .env，不需要启动服务器。最多24次调用，192 MiB进程峰值RSS停止阈值、单响应1 MiB上限；串行执行，无自动重试。记录调用耗时、内存、代码和数据哈希。`--validate-only` 不调用模型。新场景由开发助手编写，不是独立盲评。

### 事实来源核对实验

`checker_evidence.py` 是独立实验模块，要求候选断言分类、原消息逐字引文，以及角色/立场判断。程序拒绝不存在的引文，但不保证引用支持语义结论。

```sh
python3 scripts/compare_checkers.py --experiment evidence --output evidence/unique-evidence-run.json --validate-only
python3 scripts/compare_checkers.py --experiment evidence --output evidence/unique-evidence-run.json
```

2026-11-16 单轮结果：发现错误4/6（基线3/6），正确候选误报1/6（基线0/6），因此未替换生产。两条角色反转仍漏报。见 [实验审阅](evidence/checker-evidence-review-2026-11-16.md)。沿用24次串行调用和192 MiB内存停止阈值；不自动重试。
