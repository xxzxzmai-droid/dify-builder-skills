import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_DIR = ROOT / "dify-plugin-builder"
TEMPLATE_DIR = PLUGIN_DIR / "assets" / "plugin-template"


class PluginBuilderTest(unittest.TestCase):
    def test_template_packages_without_directory_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            plugin_dir = Path(tmp) / "plugin"
            package_path = Path(tmp) / "plugin.difypkg"
            shutil.copytree(TEMPLATE_DIR, plugin_dir)
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "py_compile",
                    str(plugin_dir / "main.py"),
                    str(plugin_dir / "provider" / "my_provider.py"),
                    str(plugin_dir / "tools" / "my_tool.py"),
                ],
                check=True,
            )
            subprocess.run(
                ["bash", str(PLUGIN_DIR / "scripts" / "pack_plugin.sh"), str(plugin_dir), str(package_path)],
                check=True,
                text=True,
                capture_output=True,
            )
            with zipfile.ZipFile(package_path) as package:
                names = package.namelist()
            self.assertIn("manifest.yaml", names)
            self.assertFalse([name for name in names if name.endswith("/")])
            self.assertFalse([name for name in names if "__pycache__" in name or name.endswith(".pyc")])

    def test_scaffold_cli_generates_named_plugin(self):
        with tempfile.TemporaryDirectory() as tmp:
            plugin_dir = Path(tmp) / "work_order_exporter"
            package_path = Path(tmp) / "work_order_exporter.difypkg"
            subprocess.run(
                [
                    sys.executable,
                    str(PLUGIN_DIR / "scripts" / "scaffold_plugin.py"),
                    str(plugin_dir),
                    "--name",
                    "work_order_exporter",
                    "--author",
                    "codex",
                    "--provider",
                    "work_order_provider",
                    "--tool",
                    "export_work_order",
                    "--label-zh",
                    "工单导出",
                    "--label-en",
                    "Work Order Exporter",
                    "--description-zh",
                    "把工单内容导出为可下载文件。",
                    "--description-en",
                    "Export work order content as a downloadable file.",
                    "--filename-default",
                    "work-order.txt",
                ],
                check=True,
                text=True,
                capture_output=True,
            )
            expected = [
                plugin_dir / "manifest.yaml",
                plugin_dir / "provider" / "work_order_provider.yaml",
                plugin_dir / "provider" / "work_order_provider.py",
                plugin_dir / "tools" / "export_work_order.yaml",
                plugin_dir / "tools" / "export_work_order.py",
            ]
            for path in expected:
                self.assertTrue(path.exists(), path)
            manifest = (plugin_dir / "manifest.yaml").read_text(encoding="utf-8")
            tool_yaml = (plugin_dir / "tools" / "export_work_order.yaml").read_text(encoding="utf-8")
            self.assertIn("name: work_order_exporter", manifest)
            self.assertIn("author: codex", manifest)
            self.assertIn("source: provider/work_order_provider.py", (plugin_dir / "provider" / "work_order_provider.yaml").read_text(encoding="utf-8"))
            self.assertIn("source: tools/export_work_order.py", tool_yaml)
            self.assertIn("default: work-order.txt", tool_yaml)
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "py_compile",
                    str(plugin_dir / "main.py"),
                    str(plugin_dir / "provider" / "work_order_provider.py"),
                    str(plugin_dir / "tools" / "export_work_order.py"),
                ],
                check=True,
            )
            subprocess.run(
                ["bash", str(PLUGIN_DIR / "scripts" / "pack_plugin.sh"), str(plugin_dir), str(package_path)],
                check=True,
                text=True,
                capture_output=True,
            )
            with zipfile.ZipFile(package_path) as package:
                names = package.namelist()
            self.assertIn("manifest.yaml", names)
            self.assertIn("tools/export_work_order.py", names)
            self.assertFalse([name for name in names if name.endswith("/")])


if __name__ == "__main__":
    unittest.main()
