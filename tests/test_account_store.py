import importlib
import os
import tempfile
import unittest
from pathlib import Path


class AccountStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.old_hermes_home = os.environ.get("HERMES_HOME")
        os.environ["HERMES_HOME"] = self.tmp.name

        import scripts.account_store as account_store
        self.account_store = importlib.reload(account_store)

    def tearDown(self):
        if self.old_hermes_home is None:
            os.environ.pop("HERMES_HOME", None)
        else:
            os.environ["HERMES_HOME"] = self.old_hermes_home

    def test_validate_account_alias_accepts_safe_alias(self):
        self.assertEqual(self.account_store.validate_account_alias("work-1"), "work-1")

    def test_validate_account_alias_rejects_unsafe_alias(self):
        with self.assertRaises(ValueError):
            self.account_store.validate_account_alias("../bad")

    def test_set_and_get_default_account(self):
        self.account_store.ensure_account_dir("work")
        self.account_store.set_default_account("work")
        self.assertEqual(self.account_store.get_default_account(), "work")

    def test_resolve_account_or_default_uses_default(self):
        self.account_store.ensure_account_dir("work")
        self.account_store.ensure_account_dir("personal")
        self.account_store.set_default_account("personal")
        self.assertEqual(self.account_store.resolve_account_or_default(None), "personal")

    def test_resolve_account_or_default_uses_single_account(self):
        self.account_store.ensure_account_dir("solo")
        self.assertEqual(self.account_store.resolve_account_or_default(None), "solo")

    def test_list_accounts_reads_metadata(self):
        self.account_store.ensure_account_dir("work")
        self.account_store.save_account_metadata("work", {"email": "work@example.com", "auth_status": "authenticated"})
        accounts = self.account_store.list_accounts()
        self.assertEqual(len(accounts), 1)
        self.assertEqual(accounts[0]["alias"], "work")
        self.assertEqual(accounts[0]["email"], "work@example.com")

    def test_detect_legacy_single_account(self):
        home = Path(self.tmp.name)
        (home / "google_token.json").write_text("{}")
        (home / "google_client_secret.json").write_text("{}")
        detected = self.account_store.detect_legacy_single_account()
        self.assertIn("token", detected)
        self.assertIn("client_secret", detected)


if __name__ == "__main__":
    unittest.main()
