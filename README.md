# Dify Builder Skills

两个用于 **Dify 自动化开发** 的 Codex/Claude 技能（Agent Skills）。装上之后，你只要用大白话说需求，
agent 就能直接产出可用的成品：

- **`dify-agent-builder`** —— 说"做一个 X 的 Dify 智能体"，直接产出**可导入的 Dify 0.3.0
  Chatflow `.yml`**。agent 充当架构师设计结构化蓝图，由确定性引擎 `assembler.py` 忠实拼装成
  合法、接好线的 YAML（节点ID/连线/环境变量/数据接线/校验全自动）。
- **`dify-plugin-builder`** —— 说"做一个 X 的 Dify 插件"，直接产出**可安装的 `.difypkg`**。从经过
  验证的模板脚手架开始，填好工具逻辑并正确打包（含内网/离线 wheels 路径、`zip -D` 等踩坑规避）。

这两个技能把一路打磨出来的全部经验沉淀了下来：Dify 各节点 schema、"少即是多/把智能交给大模型"的
设计哲学、可下载文件的 `meta["filename"]` + `as_attachment` 真相、`.difypkg` 的 `zip -D` 与离线
wheel 等等——都是踩了坑才知道的。

## 安装

把任一技能目录放到 Claude 能发现技能的位置即可（如 `~/.claude/skills/`），或作为插件的一部分分发。
每个技能都是自包含的：

```
dify-agent-builder/    SKILL.md + scripts/(assembler.py, build_agent.py) + references/
dify-plugin-builder/   SKILL.md + scripts/(scaffold_plugin.py, pack_plugin.sh, fetch_offline_wheels.sh) + assets/plugin-template/ + references/
```

## 怎么用

装好后直接说人话即可，例如：

- "做一个能查公司制度知识库、回答制度问题的 Dify 智能体"
- "帮我做个上传文档就分析、没传就普通问答的 Dify 助手"
- "做一个识别图片文字并结构化输出的多模态 Dify 智能体"
- "做一个把 markdown 转成可下载 PDF 文件的 Dify 工具插件"

agent 会自动触发对应技能、产出 `.yml` 或 `.difypkg` 给你，并告诉你导入后要配置什么。

## 本地验证

```bash
python3 -m unittest discover -s tests
```

测试覆盖智能体 DSL 的知识库、文档、HTTP、多路由、条件分流、图片识别，以及插件脚手架和 `.difypkg`
打包结构。

## 设计原则（为什么生成的东西好用）

- **少即是多**：优先最少节点 + 一个写好提示词的 LLM，把判断/条件/逻辑写进提示词，而不是拆成
  脆弱的路由和代码。最好的工作流往往是 `(检索/抽取/接口) → 一个好 LLM → answer`。
- **不自作主张**：只做用户要的或场景明显必需的；尊重否定；不编造接口/字段/规则。
- **好提示词**：每个 LLM 节点都写清角色·任务·依据·输出格式·边界，用真实业务术语。
- **接线归引擎**：你只写 `system_prompt`，运行时输入 `{{#sys.query#}}` 和上下文由引擎自动接好。

## 适用版本

针对 Dify 0.3.0 Chatflow DSL 与 Dify 1.x 插件（`dify_plugin` SDK）。模型 provider 默认
`csg/ai_model_provider/ai_gateway_platform`（可在 `assembler.py` 顶部改）。

## License

MIT
