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
        package_path = Path(result.stdout.strip())
        self.assertTrue(package_path.exists(), package_path)
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
