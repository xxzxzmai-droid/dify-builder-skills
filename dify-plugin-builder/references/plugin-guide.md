# Dify plugin reference

Everything needed to write and package a Dify **tool** plugin. The template in
`assets/plugin-template/` is a working starting point; this explains the SDK and the gotchas.

## Structure

```
my_plugin/
├── manifest.yaml            # plugin meta; plugins.tools points to provider yaml
├── main.py                  # fixed entrypoint (Plugin(...).run())
├── requirements.txt         # dify_plugin  (or offline --no-index form)
├── PRIVACY.md
├── _assets/icon.svg         # referenced as `icon: icon.svg`
├── provider/
│   ├── my_provider.yaml      # identity + tools list + python source path
│   └── my_provider.py        # ToolProvider._validate_credentials
└── tools/
    ├── my_tool.yaml          # identity + description + parameters + python source path
    └── my_tool.py            # Tool._invoke
```

`provider_id` (how a workflow's `tool` node references the tool) = `author/plugin_name/provider_name`,
e.g. `yourname/my_plugin/my_provider`; the tool is referenced by `tool_name` = the tool yaml's
`identity.name`.

For current Dify compatibility notes (manifest shape, author matching, SDK-version caveats), see
`../../dify-agent-builder/references/compatibility.md` in the repository root context.

## Scaffold CLI

Use `scripts/scaffold_plugin.py` when starting a new plugin. It copies `assets/plugin-template/`,
renames provider/tool files, updates `manifest.yaml`, updates `source:` paths, and writes starter
Python classes.

```bash
python3 scripts/scaffold_plugin.py /tmp/work_order_exporter \
  --name work_order_exporter \
  --author yourname \
  --provider work_order_provider \
  --tool export_work_order \
  --label-zh "工单导出" \
  --label-en "Work Order Exporter" \
  --description-zh "把工单内容导出为可下载文件。" \
  --description-en "Export work order content as a downloadable file." \
  --filename-default work-order.txt
```

Modes:

- `downloadable-file` (default): emits a text message plus `create_blob_message(..., meta={"filename": ...})`.
- `text`: emits one text message.
- `json`: emits a JSON message with content and length.

## SDK essentials (package `dify_plugin`, import as `dify_plugin`)

**Tool:**
```python
from collections.abc import Generator
from typing import Any
from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

class MyTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        yield self.create_text_message("...")        # plain text output
        # yield self.create_json_message({...})       # structured JSON
        # yield self.create_blob_message(blob=b, meta={"mime_type": "...", "filename": "x.ext"})  # file
        # yield self.create_link_message("https://...")
```
Message creators available: `create_text_message`, `create_json_message`, `create_image_message(url)`,
`create_link_message(url)`, `create_blob_message(blob, meta)`, `create_variable_message`,
`create_log_message`. There is **no** `create_file_message`; files come from `create_blob_message`.

**Provider** (no credentials needed for a pure-compute tool):
```python
from dify_plugin import ToolProvider
from dify_plugin.errors.tool import ToolProviderCredentialValidationError
class MyProvider(ToolProvider):
    def _validate_credentials(self, credentials): return
```

**Tool parameters** (`tools/*.yaml`): each has `name`, `type` (string/number/boolean/select/...),
`required`, `form` (`llm` = the agent/workflow fills it; both forms are bindable to variables in a
workflow tool node), optional `default`, and i18n `label`/`*_description`.

## Outputting a downloadable file — the traps (verified against dify-api source)

1. **`meta["filename"]`, not `meta["file_name"]`.** dify-api's message transformer does
   `filename = meta.get("filename")` and stores the tool file with it. Using `file_name` → ignored →
   the file gets a random hash name.
2. **URL extension is mime-guessed, defaulting to `.bin`.** The served URL is
   `/files/tools/<id><guess_extension(mime) or ".bin">`. YAML and many types aren't in Python's
   `mimetypes`, so the URL path ends in `.bin`. This is just the path; it doesn't change the content.
3. **Correct download name needs `as_attachment=true`.** The tool-file controller only sets
   `Content-Disposition: attachment; filename*=...<meta filename>` when the request URL carries
   `?as_attachment=true`. So whoever presents the file URL (e.g. a workflow code node that reads the
   tool node's `files[0].url`) should append `&as_attachment=true`. Then the browser saves it with
   the proper name and extension regardless of the `.bin` in the path.

`UploadFileResponse` / `session.file.upload(filename, content, mimetype)` exists for uploading a file
into Dify's regular storage (returns id/preview_url), but for tool *output* the blob message above is
the standard path.

## Packaging into `.difypkg`

A `.difypkg` is a ZIP with `manifest.yaml` at the **root** (not nested in a folder). Two musts:

- **`zip -D`** (no directory entries). Plain `zip -r` writes `tools/`, `provider/` directory entries;
  the daemon then tries to read `tools` as a file → install error `read tools: is a directory`. The
  bundled `scripts/pack_plugin.sh` already uses `-D` and verifies `目录条目=0`.
- **No `__pycache__`/`.pyc`** in the package (the script strips them).

**Signature:** self-hosted Dify may reject unsigned local plugins. If install fails on signature, set
`FORCE_VERIFYING_SIGNATURE=false` for the `plugin_daemon` (in `docker/.env`) and restart it, then
install from local file.

## Offline (air-gapped / 内网) install

If the Dify server can't reach PyPI, bundle wheels:
```
requirements.txt:
    --no-index
    --find-links=./wheels/
    dify_plugin==0.4.1
wheels/*.whl   ← dify_plugin==0.4.1 + its full dependency closure, for the server's python+arch
```
`scripts/fetch_offline_wheels.sh <dir> <pyver> <platform>` does this. Wheels are platform-specific
(e.g. `cp312` + `manylinux2014_aarch64` for Python 3.12 on ARM64). If pip can't produce them for the
target platform, copy `wheels/` from a plugin that already installs offline on that exact server.

## Common failure → cause

| Symptom | Cause / fix |
|---|---|
| `read tools: is a directory` | zip had directory entries → repackage with `zip -D` (use `pack_plugin.sh`) |
| `init environment … failed too many times … corrupted/network` | offline server, deps not bundled → add `wheels/` + offline `requirements.txt` |
| install rejected (signature) | set `FORCE_VERIFYING_SIGNATURE=false` on plugin_daemon, restart, retry |
| downloaded file is `<hash>.bin` | used `file_name` not `filename`, and/or missing `as_attachment=true` on the URL |
