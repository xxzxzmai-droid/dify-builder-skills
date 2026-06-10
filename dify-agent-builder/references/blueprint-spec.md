# BlueprintSpec reference

You write a **BlueprintSpec** (one JSON object). `build_agent.py` renders it into a valid Dify 0.3.0
Chatflow YAML. You design the structure and write each LLM node's `system_prompt`; the engine wires
everything else. Read the design philosophy in `SKILL.md` first — minimalism and good prompts matter
more than knowing every field.

## Top-level schema

```jsonc
{
  "app": {
    "name": "中文名,≤30字",
    "description": "一句话",
    "opening_statement": "开场白",
    "suggested_questions": ["4-6 条贴合场景、点了能跑出效果的引导问题"]
  },
  "model": { "name": "DeepSeek-V4-Pro 或 DeepSeek-V4-Flash" },  // 简单→Flash；复杂/多能力→Pro
  "memory": true,
  "design_notes": ["1-4 条你做的关键设计决定/假设/占位,方便用户纠正"],
  "global_env_vars": [ {"name":"API_TOKEN","description":"...","value_type":"string|secret","default":""} ],
  "global_inputs":  [ {"variable":"user_role","label":"用户角色","type":"text-input","required":false} ],
  "routing": {
    "enabled": false,                      // false = 单链路(默认,绝大多数情况); true = 多路由
    "type": "classifier",                  // classifier = 按语义意图(问题分类器); condition = 代码+if-else(几乎不用)
    "classifier_instruction": "写给分类器的判断说明(仅 classifier)",
    "routes": [
      { "id":"main", "name":"主流程", "trigger":"什么时候进入本路线", "nodes":[ /* 有序节点流水线 */ ] }
    ]
  }
}
```

The model provider is fixed to `csg/ai_model_provider/ai_gateway_platform` by the engine; you only
pick the model `name`. (If a target Dify uses a different provider, change `MODEL_PROVIDER` at the
top of `assembler.py`.)

## Node kinds (inside each route's `nodes`, in data-flow order; usually ends with `answer`)

- `{"kind":"knowledge","dataset_ids":[]}` — knowledge-base retrieval. Leave `dataset_ids` empty; the
  user selects the dataset after import.
- `{"kind":"document-extractor"}` — extracts text from uploaded **documents** (Word/PDF/Excel/CSV/TXT)
  via `sys.files`. Empty (not an error) when no file. **Never** feed images here.
- `{"kind":"http","name":"查询","method":"GET","path":"/v1/...","query_param":"q","base_env":"API_BASE_URL","token_env":"API_TOKEN","auth":"bearer|none","body":""}`
  — calls an API. URL = `{{#env.BASE_ENV#}}` + path. Bearer token via `{{#env.TOKEN_ENV#}}`. Never
  hardcode secrets; declare them in `global_env_vars` (value_type `secret`). For `GET`, set
  `query_param` when the endpoint should receive the runtime user question, e.g.
  `?keyword={{#sys.query#}}`.
- `{"kind":"code","purpose":"做什么","python_lines":["def main(...) -> dict:","    ..."],"inputs":[{"variable":"x","from":"query|prev_llm|prev_http|prev_doc|prev_code"}]}`
  — only when an LLM genuinely can't read-and-do the task (precise counting, parsing, file output).
  Must define `def main(...) -> dict` returning a dict with a string `"result"`. `python_lines` is a
  list of lines (handles indentation/escaping cleanly). Defensive: `str(x or "")` before using any
  param that could be None. The engine also auto-rewrites `str(x).strip()` → `str(x or "").strip()`.
- `{"kind":"llm","system_prompt":"针对本路线的专属提示词"}` — a text LLM. **You only write
  `system_prompt`.** The engine injects `{{#sys.query#}}` + upstream knowledge/file/http/code results
  into the user message automatically. Do not write `user_template`.
- `{"kind":"llm","vision":true,"system_prompt":"识别图片并按要求输出"}` — multimodal LLM for images
  (OCR/截图/票据/证件). The user picks a vision-capable model after import.
- `{"kind":"file-export","format":"docx|xlsx|csv|html","filename_hint":"报告"}` — turns the upstream
  LLM (or code) output into a downloadable file. Place an `answer` after it.
- `{"kind":"answer","template":"自动"}` — terminal. Write `"自动"`; the engine points it at the
  right upstream output.

## Critical rules (learned the hard way)

1. **Never put the user's build-request text into any prompt.** `{{#sys.query#}}` is the *generated
   agent's* runtime input, a placeholder — not the request you're processing now. The engine forces
   the correct wiring, but write `system_prompt`s as generic role+rules anyway.
2. **Images → `vision:true` LLM, never document-extractor.** Documents → document-extractor.
3. **Default to no routing.** Conditions like "file uploaded or not" → one LLM that decides from the
   (possibly empty) injected file text. Multi-route only for genuinely different tool pipelines.
4. **Don't over-add `code`.** "Analyze / summarize / extract / review / classify from text" → the LLM
   does it directly. `code` is for precise/mechanical work only.
5. **Good `system_prompt` = role · task · grounding · output format · boundary**, in the business's
   real terms.

## Worked examples

### A. Single LLM with built-in judgement (the pattern to prefer)
Need: "analyze the document if uploaded, otherwise just answer normally." One chain, no routing.
```jsonc
{
  "app":{"name":"文档/问答双模助手","description":"上传文档则分析,否则普通问答。",
         "opening_statement":"你可以上传文档让我分析,也可以直接问我问题。",
         "suggested_questions":["分析我上传的这份文档","总结这份材料的要点","公司报销流程是怎样的"]},
  "model":{"name":"DeepSeek-V4-Flash"},"memory":true,
  "design_notes":["一个 LLM 智能判断:有上传文档就分析、没有就正常问答,无需路由,最稳"],
  "global_env_vars":[],"global_inputs":[],
  "routing":{"enabled":false,"routes":[{"id":"main","name":"主流程","trigger":"","nodes":[
    {"kind":"document-extractor"},
    {"kind":"llm","system_prompt":"你是文档分析与问答助手。先看系统注入的【上传文件文本】:非空说明用户上传了文档→基于文档内容输出[一句话结论→要点摘要→关键数据(日期/金额/责任人)→风险与待办];为空说明没传文档→作为通用助手直接、准确、分点地回答用户问题。只依据已有信息,不编造,不确定就说明。"},
    {"kind":"answer","template":"自动"}
  ]}]}
}
```

### B. Genuinely multi-tool (classifier multi-route)
Need: "office assistant that validates uploaded ledgers (Excel) AND answers policy questions."
```jsonc
{
  "app":{"name":"综合办公助手","description":"台账校验与制度问答。",
         "opening_statement":"我可以校验你上传的台账表格,也能回答制度流程问题。",
         "suggested_questions":["上传台账Excel帮我查缺失和重复","报销流程是怎样的","这张表有哪些异常数据"]},
  "model":{"name":"DeepSeek-V4-Pro"},"memory":true,
  "design_notes":["两条路线:表格校验+制度问答,用问题分类器自动分流","知识库ID留空,导入后选你的制度库"],
  "global_env_vars":[],"global_inputs":[],
  "routing":{"enabled":true,"classifier_instruction":"上传表格或要校验台账→表格校验;问制度流程规范→制度问答。","routes":[
    {"id":"sheet_check","name":"台账表格校验","trigger":"上传Excel/CSV台账,要查缺失/重复/异常。","nodes":[
      {"kind":"document-extractor"},
      {"kind":"code","purpose":"统计行数/缺失单元格/重复行","python_lines":[
        "import csv, io, json",
        "def main(file_text: str = '') -> dict:",
        "    rows = [r for r in csv.reader(io.StringIO(str(file_text or ''))) if any(c.strip() for c in r)]",
        "    if len(rows) < 2: return {'result': json.dumps({'note':'未识别到表格数据'}, ensure_ascii=False)}",
        "    header, data = rows[0], rows[1:]; seen=set(); dup=0; missing=0",
        "    for r in data:",
        "        k=tuple(c.strip() for c in r); dup += (k in seen); seen.add(k)",
        "        missing += sum(1 for c in r if not c.strip())",
        "    return {'result': json.dumps({'rows':len(data),'columns':header,'duplicate_rows':dup,'missing_cells':missing}, ensure_ascii=False)}"],
        "inputs":[{"variable":"file_text","from":"prev_doc"}]},
      {"kind":"llm","system_prompt":"你是台账校验助手。依据代码节点的统计结果说明:数据概览→缺失与重复→疑似异常→修复建议;只基于统计结果,不臆造。"},
      {"kind":"answer","template":"自动"}]},
    {"id":"policy_qa","name":"制度问答","trigger":"询问制度/流程/规范/审批/权限。","nodes":[
      {"kind":"knowledge","dataset_ids":[]},
      {"kind":"llm","system_prompt":"你是公司制度问答助手。仅依据知识库检索结果回答,给出[结论→适用范围→依据条款→办理步骤];无命中时明确说'未检索到明确依据'并建议咨询主管部门,不编造。"},
      {"kind":"answer","template":"自动"}]}
  ]}}
}
```

### C. Multimodal image recognition
```jsonc
{
  "app":{"name":"图片文字识别助手","description":"识别图片文字并结构化为JSON。",
         "opening_statement":"上传图片(票据/证件/截图),我识别其中文字并结构化返回。",
         "suggested_questions":["识别这张图片里的文字","把这张票据的关键信息提取成JSON"]},
  "model":{"name":"DeepSeek-V4-Pro"},"memory":true,
  "design_notes":["单链路 vision LLM;导入后在该节点选支持视觉的多模态模型"],
  "global_env_vars":[],"global_inputs":[],
  "routing":{"enabled":false,"routes":[{"id":"main","name":"图片识别","trigger":"上传图片要求识别。","nodes":[
    {"kind":"llm","vision":true,"system_prompt":"你是图像文字识别助手。识别图片中的全部文字,按严格JSON输出(无多余解释、无代码块标记):{\"doc_type\":\"票据/证件/表格/截图\",\"raw_text\":\"完整原始文字\",\"fields\":{\"字段名\":\"值\"},\"notes\":\"存疑之处\"}。图片不清或无文字时 raw_text 置空并在 notes 说明。"},
    {"kind":"answer","template":"自动"}
  ]}]}
}
```

## Condition routing (rare — usually avoid)
When you truly need a code-decided branch (not "file present", which a single LLM handles better),
set `routing.type:"condition"`, `pre_extract:true`, a `router` code node returning
`{"route_key":...}`, each route a `case`, and the fallback route `"is_else": true`. The engine builds
`document-extractor → router code → if-else → branches`. Always write `str(x or "").strip()` in the
router (the engine auto-hardens it anyway). Prefer Example A over this.

## After rendering
`build_agent.py` prints validation warnings and manual-config steps. Pass those to the user. If a
warning says a code node has a syntax problem or an env var is undeclared, fix the blueprint and
re-render.
