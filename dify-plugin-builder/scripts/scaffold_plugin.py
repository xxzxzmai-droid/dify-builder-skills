#!/usr/bin/env python3
"""Create a named Dify tool plugin from the bundled template.

The script is intentionally small and stdlib-only. It performs the fragile,
repeatable edits (manifest identity, provider/tool file names, source paths and
Python class names) while leaving custom business logic to the agent/user.
"""
import argparse
import re
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = ROOT / "assets" / "plugin-template"


def snake(value, fallback):
    text = re.sub(r"[^a-zA-Z0-9_]+", "_", str(value or "")).strip("_").lower()
    text = re.sub(r"_+", "_", text)
    return text or fallback


def class_name(value, suffix):
    parts = [part for part in snake(value, suffix).split("_") if part]
    name = "".join(part.capitalize() for part in parts)
    if not name or not name[0].isalpha():
        name = suffix + name
    if not name.endswith(suffix):
        name += suffix
    return name


def yaml_scalar(value):
    text = str(value or "")
    if re.fullmatch(r"[A-Za-z0-9_./:@+-]+", text):
        return text
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def write(path, text):
    path.write_text(text, encoding="utf-8")


def manifest_yaml(args, provider_file):
    return f"""version: 0.0.1
type: plugin
author: {args.author}
name: {args.name}
label:
  en_US: {yaml_scalar(args.label_en)}
  zh_Hans: {yaml_scalar(args.label_zh)}
description:
  en_US: {yaml_scalar(args.description_en)}
  zh_Hans: {yaml_scalar(args.description_zh)}
icon: icon.svg
resource:
  memory: 268435456
  permission:
    tool:
      enabled: true
plugins:
  tools:
    - provider/{provider_file}.yaml
meta:
  version: 0.0.1
  arch:
    - amd64
    - arm64
  runner:
    language: python
    version: "3.12"
    entrypoint: main
created_at: 2026-01-01T00:00:00+08:00
privacy: PRIVACY.md
verified: false
"""


def provider_yaml(args, provider_file, tool_file):
    return f"""identity:
  author: {args.author}
  name: {provider_file}
  label:
    en_US: {yaml_scalar(args.label_en)}
    zh_Hans: {yaml_scalar(args.label_zh)}
  description:
    en_US: {yaml_scalar(args.description_en)}
    zh_Hans: {yaml_scalar(args.description_zh)}
  icon: icon.svg
tools:
  - tools/{tool_file}.yaml
extra:
  python:
    source: provider/{provider_file}.py
"""


def provider_py(provider_class):
    return f"""from typing import Any

from dify_plugin import ToolProvider
from dify_plugin.errors.tool import ToolProviderCredentialValidationError


class {provider_class}(ToolProvider):
    def _validate_credentials(self, credentials: dict[str, Any]) -> None:
        # Pure-compute tools do not need credentials. Add validation here when a tool needs an API key.
        try:
            return
        except Exception as e:
            raise ToolProviderCredentialValidationError(str(e))
"""


def tool_yaml(args, tool_file):
    return f"""identity:
  name: {tool_file}
  author: {args.author}
  label:
    en_US: {yaml_scalar(args.label_en)}
    zh_Hans: {yaml_scalar(args.label_zh)}
description:
  human:
    en_US: {yaml_scalar(args.description_en)}
    zh_Hans: {yaml_scalar(args.description_zh)}
  llm: {yaml_scalar(args.llm_description)}
parameters:
  - name: content
    type: string
    required: true
    label: {{en_US: Content, zh_Hans: 内容}}
    human_description: {{en_US: The content to process., zh_Hans: 要处理的内容。}}
    llm_description: The full text content to process.
    form: llm
  - name: filename
    type: string
    required: false
    default: {yaml_scalar(args.filename_default)}
    label: {{en_US: File name, zh_Hans: 文件名}}
    human_description: {{en_US: Output file name with extension., zh_Hans: 输出文件名，需包含扩展名。}}
    llm_description: Desired output file name, for example report.yml
    form: llm
extra:
  python:
    source: tools/{tool_file}.py
"""


def tool_py(args, tool_class):
    if args.mode == "text":
        invoke = """        content = str(tool_parameters.get("content") or "")
        yield self.create_text_message(content)
"""
    elif args.mode == "json":
        invoke = """        content = str(tool_parameters.get("content") or "")
        yield self.create_json_message({"content": content, "length": len(content)})
"""
    else:
        invoke = """        content = str(tool_parameters.get("content") or "")
        name = re.sub(r'[\\\\/:*?"<>|\\s]+', "_", str(tool_parameters.get("filename") or "output")).strip("_") or "output"
        if "." not in name:
            name += ".txt"
        name = name[:80]
        blob = content.encode("utf-8")
        yield self.create_text_message(f"已生成文件 {name}（{len(blob)} 字节），见下方附件。")
        yield self.create_blob_message(
            blob=blob,
            meta={"mime_type": "application/octet-stream", "filename": name},
        )
"""
    imports = "import re\n" if args.mode == "downloadable-file" else ""
    return f"""{imports}from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage


class {tool_class}(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
{invoke}"""


def parse_args(argv):
    parser = argparse.ArgumentParser(description="Scaffold a named Dify tool plugin from the template.")
    parser.add_argument("output_dir", help="Directory to create")
    parser.add_argument("--name", required=True, help="Plugin package name, lowercase snake_case")
    parser.add_argument("--author", required=True, help="Lowercase author id, [a-z0-9_]")
    parser.add_argument("--provider", help="Provider name, defaults to <name>_provider")
    parser.add_argument("--tool", help="Tool name, defaults to <name>_tool")
    parser.add_argument("--label-zh", required=True, help="Chinese label")
    parser.add_argument("--label-en", required=True, help="English label")
    parser.add_argument("--description-zh", required=True, help="Chinese description")
    parser.add_argument("--description-en", required=True, help="English description")
    parser.add_argument("--llm-description", help="LLM-facing tool description")
    parser.add_argument("--filename-default", default="output.txt", help="Default output filename")
    parser.add_argument(
        "--mode",
        choices=["downloadable-file", "text", "json"],
        default="downloadable-file",
        help="Starter tool behavior",
    )
    parser.add_argument("--overwrite", action="store_true", help="Replace output_dir if it already exists")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv or sys.argv[1:])
    args.name = snake(args.name, "my_plugin")
    args.author = snake(args.author, "yourname")
    args.provider = snake(args.provider, f"{args.name}_provider")
    args.tool = snake(args.tool, f"{args.name}_tool")
    args.llm_description = args.llm_description or args.description_en

    if not re.fullmatch(r"[a-z0-9_]+", args.author):
        print("author must match [a-z0-9_]", file=sys.stderr)
        return 2

    output_dir = Path(args.output_dir).resolve()
    if output_dir.exists():
        if not args.overwrite:
            print(f"output directory already exists: {output_dir}", file=sys.stderr)
            return 2
        shutil.rmtree(output_dir)
    shutil.copytree(TEMPLATE_DIR, output_dir)

    provider_dir = output_dir / "provider"
    tools_dir = output_dir / "tools"
    provider_file = args.provider
    tool_file = args.tool

    for stale in [provider_dir / "my_provider.yaml", provider_dir / "my_provider.py", tools_dir / "my_tool.yaml", tools_dir / "my_tool.py"]:
        if stale.exists():
            stale.unlink()

    write(output_dir / "manifest.yaml", manifest_yaml(args, provider_file))
    write(provider_dir / f"{provider_file}.yaml", provider_yaml(args, provider_file, tool_file))
    write(provider_dir / f"{provider_file}.py", provider_py(class_name(provider_file, "Provider")))
    write(tools_dir / f"{tool_file}.yaml", tool_yaml(args, tool_file))
    write(tools_dir / f"{tool_file}.py", tool_py(args, class_name(tool_file, "Tool")))

    print(f"created {output_dir}")
    print(f"provider_id: {args.author}/{args.name}/{provider_file}")
    print(f"tool_name: {tool_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
