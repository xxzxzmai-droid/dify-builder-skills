import re
from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage


class MyTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        content = str(tool_parameters.get("content") or "")
        name = re.sub(r'[\\/:*?"<>|\s]+', "_", str(tool_parameters.get("filename") or "output")).strip("_") or "output"
        if "." not in name:
            name += ".txt"
        name = name[:80]
        blob = content.encode("utf-8")
        yield self.create_text_message(f"已生成文件 {name}（{len(blob)} 字节），见下方附件。")
        # 关键:dify-api 读取的是 meta["filename"](不是 file_name)来命名下载文件。
        # 下载 URL 末尾的扩展名由 mime 猜;要让"点击下载"用正确文件名,在工作流里给 URL 加 &as_attachment=true。
        yield self.create_blob_message(
            blob=blob,
            meta={"mime_type": "application/octet-stream", "filename": name},
        )
