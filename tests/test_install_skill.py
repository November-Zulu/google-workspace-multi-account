import importlib
import tempfile
import unittest
from pathlib import Path
from unittest import mock


class InstallSkillTests(unittest.TestCase):
    def setUp(self):
        import scripts.install_skill as install_skill
        self.install_skill = importlib.reload(install_skill)

    def test_fails_when_python_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            hermes_home = Path(tmp) / "hermes"
            missing_python = Path(tmp) / "missing-python"
            with mock.patch("sys.argv", [
                "install_skill.py",
                "--hermes-home",
                str(hermes_home),
                "--python",
                str(missing_python),
            ]):
                rc = self.install_skill.main()
                self.assertEqual(rc, 1)

    def test_main_invokes_deploy_script(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            hermes_home = root / "hermes-home"
            python_bin = root / "python"
            python_bin.write_text("#!/bin/sh\nexit 0\n")
            deploy_script = self.install_skill.PROJECT_ROOT / "scripts" / "deploy_skill.py"
            self.assertTrue(deploy_script.exists())

            with mock.patch("subprocess.run") as run_mock, mock.patch("sys.argv", [
                "install_skill.py",
                "--hermes-home",
                str(hermes_home),
                "--python",
                str(python_bin),
            ]):
                run_mock.return_value.returncode = 0
                rc = self.install_skill.main()
                self.assertEqual(rc, 0)
                self.assertTrue(run_mock.called)
                cmd = run_mock.call_args.args[0]
                self.assertIn(str(python_bin.resolve()), cmd)
                self.assertIn(str(deploy_script), cmd)


if __name__ == "__main__":
    unittest.main()
