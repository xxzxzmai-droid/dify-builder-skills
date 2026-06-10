import subprocess
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class OfflinePackageTest(unittest.TestCase):
    def test_package_contains_installable_skills_and_no_git_state(self):
        result = subprocess.run(
            ["bash", str(ROOT / "scripts" / "package_offline.sh")],
            cwd=str(ROOT),
            text=True,
            capture_output=True,
            check=True,
        )
        output_paths = [Path(line.strip()) for line in result.stdout.splitlines() if line.strip()]
        self.assertEqual(len(output_paths), 2)
        package_path, latest_path = output_paths
        self.assertTrue(package_path.exists(), package_path)
        self.assertTrue(latest_path.exists(), latest_path)
        self.assertEqual(latest_path.name, "dify-builder-skills-offline-latest.zip")
        with zipfile.ZipFile(package_path) as package:
            names = package.namelist()
        joined = "\n".join(names)
        self.assertIn("/install_offline.sh", joined)
        self.assertIn("/OFFLINE_INSTALL.md", joined)
        self.assertIn("/dify-agent-builder/SKILL.md", joined)
        self.assertIn("/dify-plugin-builder/SKILL.md", joined)
        self.assertIn("/dify-agent-builder/references/compatibility.md", joined)
        self.assertNotIn("/.git/", joined)
        self.assertNotIn("__pycache__", joined)
        self.assertNotIn(".pyc", joined)
        self.assertNotIn(".difypkg", joined)


if __name__ == "__main__":
    unittest.main()
