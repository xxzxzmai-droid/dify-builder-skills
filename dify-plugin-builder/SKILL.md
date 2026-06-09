---
name: dify-plugin-builder
description: >-
  Build and package a Dify plugin (a .difypkg file) from a description of what the tool should do.
  Use this whenever the user wants to create, build, or package a Dify plugin / tool plugin / 插件 /
  .difypkg — e.g. "做一个把文本转成可下载文件的Dify插件", "帮我做个Dify工具插件调用某个API",
  "build a Dify plugin that converts markdown to PDF", "package this as a .difypkg". Trigger even if
  they don't say ".difypkg". The skill scaffolds the plugin from a proven template, fills in the
  tool logic, and packages it correctly (including the offline-wheels path for air-gapped/内网 Dify).
---

# Dify Plugin Builder

Scaffold, implement, and package a **Dify tool plugin** into an installable `.difypkg`. The template
and packaging scripts encode several non-obvious gotchas that otherwise cost hours.

## Workflow

1. **Understand the tool.** What does it take in, what does it produce (text / structured JSON /
   a downloadable file)? Does it need network or a credential/API key?
2. **Copy the template:** `cp -r assets/plugin-template /tmp/<plugin_name>`.
3. **Fill it in** (see `references/plugin-guide.md` for the full SDK reference):
   - `manifest.yaml`: set `author`, `name`, labels, description. `author` must be lowercase
     `[a-z0-9_]`; it forms the `provider_id` prefix.
   - `provider/<provider>.yaml` + `.py`: rename, set identity. No credentials → leave
     `_validate_credentials` returning. Needs an API key → declare it and validate.
   - `tools/<tool>.yaml` + `.py`: define parameters and the `_invoke` logic. The template's example
     tool returns a downloadable file — adapt or replace it.
   - Rename the referenced files and update the `source:` / `tools:` paths to match.
4. **Choose online vs offline** (critical — see below).
5. **Package:** `bash scripts/pack_plugin.sh /tmp/<plugin_name> <plugin_name>.difypkg`
   The script uses `zip -D` (no directory entries) — required, or install fails with
   `read tools: is a directory`.
6. **Deliver the `.difypkg`** and tell the user how to install (Dify → 插件 → 安装插件 → 本地文件),
   plus any post-install step (select a model, fill credentials).

## Online vs offline — get this right or install fails

The Dify plugin daemon installs the plugin's Python deps at install time.

- **Internet-connected Dify** (can reach PyPI): leave `requirements.txt` as `dify_plugin`. Done.
- **Air-gapped / 内网 Dify** (cannot reach PyPI): you MUST bundle dependency wheels, or install
  fails with *"init environment for plugin … failed too many times … package is corrupted or your
  network is unstable"*. Run `bash scripts/fetch_offline_wheels.sh /tmp/<plugin_name> 3.12 <platform>`
  (platform must match the server, e.g. `manylinux2014_aarch64` for ARM64), which downloads wheels
  into `wheels/` and switches `requirements.txt` to `--no-index --find-links=./wheels/`. If pip can't
  get a wheel for that platform, the most reliable path is to copy the `wheels/` directory from an
  existing plugin that already installs offline on that same server.

## Output a downloadable file from a tool (common, and full of traps)

`self.create_blob_message(blob=bytes, meta={...})` is the way. Two traps the template already handles:

- **Filename:** dify-api reads `meta["filename"]` (NOT `file_name`). Wrong key → file is named with a
  random hash.
- **Extension / clickable download:** the file's URL ends in an extension guessed from the mime type
  (yaml/many types → `.bin`). The *downloaded* name comes from `meta["filename"]` only when the
  request URL has `?as_attachment=true`. So in the **workflow** that calls this tool, append
  `&as_attachment=true` to the file's `url` before presenting it (a small code node can do this).

Full SDK details (message types, `session.file.upload`, signing) are in
`references/plugin-guide.md` — read it before writing non-trivial tool logic.

## Sanity-check before packaging

```bash
python3 -m py_compile /tmp/<plugin_name>/main.py /tmp/<plugin_name>/provider/*.py /tmp/<plugin_name>/tools/*.py
python3 -c "import yaml,glob; [yaml.safe_load(open(f)) for f in glob.glob('/tmp/<plugin_name>/**/*.yaml',recursive=True)]"
```
After packaging, confirm `目录条目=0` and `manifest在根=1` (the script prints both).
