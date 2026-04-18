import importlib
import tempfile
import unittest
from pathlib import Path


class DeploySkillTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.project = self.root / "project"
        self.dest = self.root / "dest"
        (self.project / "references").mkdir(parents=True)
        (self.project / "scripts").mkdir(parents=True)
        (self.project / "scripts" / "__pycache__").mkdir(parents=True)

        (self.project / "SKILL.md").write_text("skill")
        (self.project / "references" / "usage.md").write_text("usage")
        (self.project / "scripts" / "tool.py").write_text("print('ok')")
        (self.project / "scripts" / "__pycache__" / "tool.cpython-311.pyc").write_bytes(b"x")

        import scripts.deploy_skill as deploy_skill
        self.deploy_skill = importlib.reload(deploy_skill)
        self.deploy_skill.PROJECT_ROOT = self.project

    def test_deploy_copies_expected_files(self):
        copied = self.deploy_skill.deploy(self.dest)
        self.assertIn("SKILL.md", copied)
        self.assertIn("references", copied)
        self.assertIn("scripts", copied)
        self.assertTrue((self.dest / "SKILL.md").exists())
        self.assertTrue((self.dest / "references" / "usage.md").exists())
        self.assertTrue((self.dest / "scripts" / "tool.py").exists())

    def test_deploy_excludes_pyc_cache(self):
        self.deploy_skill.deploy(self.dest)
        self.assertFalse((self.dest / "scripts" / "__pycache__").exists())


if __name__ == "__main__":
    unittest.main()
