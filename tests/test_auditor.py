"""Tests for dashlane-auditor. Run with: python3 -m unittest discover tests

Nothing here touches a real vault or the network: dcli is replaced by a fake
executable serving a fixture, and HaveIBeenPwned calls are stubbed.
"""

import hashlib
import importlib.machinery
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "dashlane-auditor"


def load_module():
    loader = importlib.machinery.SourceFileLoader("dashlane_auditor", str(SCRIPT))
    spec = importlib.util.spec_from_loader("dashlane_auditor", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


da = load_module()
sys.path.insert(0, str(ROOT))
import assist  # noqa: E402

DAY = 86400


def cred(id, password, url, login="you@example.com", strength=90,
         changed_days=30, used_days=1, uses=10):
    now = time.time()
    return {
        "id": id,
        "title": url.split("//")[-1],
        "url": url,
        "email": login,
        "password": password,
        "strength": str(strength),
        "modificationDatetime": str(int(now - changed_days * DAY)),
        "lastUse": str(int(now - used_days * DAY)) if used_days is not None else None,
        "numberUse": str(uses),
    }


FIXTURE = [
    cred("1", "Str0ng&Unique-1", "https://github.com"),
    cred("2", "shared-pass-123", "https://google.com", strength=70),
    cred("3", "shared-pass-123", "https://reddit.com", strength=70, used_days=5),
    cred("4", "qwerty12", "https://amazon.com", strength=10),
    cred("5", "Old&Strong-but-fine", "https://dropbox.com", changed_days=900),
    cred("6", "dead-weak", "https://netflix.com", strength=5,
         used_days=1000, changed_days=1500),
    cred("7", "app-only", "android://abc@com.example.app"),
]


class PureFunctionTests(unittest.TestCase):
    def test_parse_timestamp_handles_strings_millis_and_blanks(self):
        self.assertIsNone(da.parse_timestamp(None))
        self.assertIsNone(da.parse_timestamp("0"))
        self.assertIsNone(da.parse_timestamp("not a number"))
        self.assertEqual(da.parse_timestamp("1700000000").year, 2023)
        self.assertEqual(da.parse_timestamp(1700000000000).year, 2023)

    def test_strength_prefers_dashlane_score(self):
        self.assertEqual(da.password_strength_issues("x", 90), [])
        self.assertEqual(da.password_strength_issues("x", 40), ["Dashlane strength 40/100"])

    def test_strength_heuristic_without_score(self):
        self.assertEqual(da.password_strength_issues("Abcdefgh1234!", None), [])
        issues = da.password_strength_issues("abc", None)
        self.assertIn("short (3 chars)", issues)
        self.assertIn("low complexity", issues)

    def test_site_url_keeps_only_web_origins(self):
        self.assertEqual(da.site_url("github.com/settings"), "https://github.com")
        self.assertEqual(da.site_url("http://example.com:8080/x?y=1"), "http://example.com:8080")
        self.assertIsNone(da.site_url("android://abc@com.example.app"))
        self.assertIsNone(da.site_url(""))

    def test_domain_of_strips_www(self):
        self.assertEqual(da.domain_of("https://www.GitHub.com/login"), "github.com")

    def test_md_cell_escapes_pipes_and_newlines(self):
        self.assertEqual(da.md_cell("a|b\nc"), "a\\|b c")

    def test_change_password_url_prefers_sites_db(self):
        db = {"github.com": "https://github.com/settings/security"}
        self.assertEqual(da.change_password_url("https://www.github.com/x", db),
                         "https://github.com/settings/security")


class AnalyzeTests(unittest.TestCase):
    def setUp(self):
        self.rows = {r["id"]: r for r in da.analyze(FIXTURE, 365, 730, check_breaches=False)}

    def test_flags_reused_and_weak_but_not_strong(self):
        self.assertFalse(self.rows["1"]["flagged"])
        self.assertTrue(self.rows["2"]["reused"] and self.rows["2"]["flagged"])
        self.assertTrue(self.rows["3"]["reused"])
        self.assertTrue(self.rows["4"]["weak"] and self.rows["4"]["flagged"])

    def test_stale_alone_is_not_flagged(self):
        self.assertTrue(self.rows["5"]["stale"])
        self.assertFalse(self.rows["5"]["flagged"])

    def test_dead_accounts_are_not_in_rotation_queue(self):
        self.assertTrue(self.rows["6"]["dead"])
        self.assertFalse(self.rows["6"]["flagged"])

    def test_rows_never_contain_passwords(self):
        blob = json.dumps(list(self.rows.values()), default=str)
        for c in FIXTURE:
            self.assertNotIn(c["password"], blob)

    def test_only_filter_and_rotation_order(self):
        rows = list(self.rows.values())
        self.assertEqual({r["id"] for r in da.apply_only_filter(rows, "weak")}, {"4"})
        self.assertEqual({r["id"] for r in da.apply_only_filter(rows, "reused")}, {"2", "3"})
        ordered = [r["id"] for r in da.rotation_order(da.apply_only_filter(rows, None))]
        self.assertEqual(ordered[-1], "3")  # used 5 days ago, others yesterday


class BreachCheckTests(unittest.TestCase):
    def test_matches_suffixes_locally_and_sends_only_prefixes(self):
        sha1 = hashlib.sha1(b"hunter2").hexdigest().upper()
        requested = []

        class Resp(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        def fake_urlopen(req, timeout):
            requested.append(req.full_url)
            body = f"{sha1[5:]}:42\r\nFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF:1\r\n"
            return Resp(body.encode())

        with mock.patch.object(da.urllib.request, "urlopen", fake_urlopen), \
                mock.patch("sys.stderr", io.StringIO()):
            counts = da.fetch_breach_counts({sha1})
        self.assertEqual(counts, {sha1: 42})
        self.assertEqual(requested, [f"https://api.pwnedpasswords.com/range/{sha1[:5]}"])

    def test_returns_none_when_service_unreachable(self):
        with mock.patch.object(da.urllib.request, "urlopen", side_effect=OSError), \
                mock.patch("sys.stderr", io.StringIO()):
            self.assertIsNone(da.fetch_breach_counts({"A" * 40}))


class SaveNewPasswordTests(unittest.TestCase):
    row = {"id": "2", "title": "google.com", "login": "you@example.com"}

    def run_flow(self, answers, vault_passwords):
        out = io.StringIO()
        with mock.patch("builtins.input", side_effect=answers), \
                mock.patch.object(da, "copy_to_clipboard", return_value=True) as clip, \
                mock.patch.object(da, "fetch_password_by_id",
                                  side_effect=vault_passwords) as fetch, \
                redirect_stdout(out):
            result = da.save_new_password(self.row, "N3w-Secret!")
        return result, out.getvalue(), clip, fetch

    def test_waits_until_vault_matches(self):
        result, out, clip, fetch = self.run_flow(["", ""], ["old", "N3w-Secret!"])
        self.assertTrue(result)
        self.assertEqual(fetch.call_count, 2)
        fetch.assert_called_with("2", sync=True)
        clip.assert_called_with("")  # clipboard cleared at the end
        self.assertNotIn("N3w-Secret!", out)

    def test_skip_warns_and_returns_false(self):
        result, out, _, fetch = self.run_flow(["skip"], [])
        self.assertFalse(result)
        self.assertIn("NOT in your vault", out)
        fetch.assert_not_called()

    def test_password_only_shown_on_request(self):
        _, out, _, _ = self.run_flow(["show", ""], ["N3w-Secret!"])
        self.assertIn("new password: N3w-Secret!", out)


class AssistTests(unittest.TestCase):
    def test_host_allowed(self):
        url = "https://myaccount.google.com/security"
        self.assertTrue(assist.host_allowed("https://accounts.google.com/x", url, "google.com"))
        self.assertTrue(assist.host_allowed(url, url, "google.com"))
        self.assertTrue(assist.host_allowed("https://account.microsoft.com/",
                                            "https://account.microsoft.com/security",
                                            "live.com"))
        self.assertFalse(assist.host_allowed("https://evil-google.com/", url, "google.com"))
        self.assertFalse(assist.host_allowed("https://example.org/", url, "google.com"))
        self.assertFalse(assist.host_allowed("about:blank", url, "google.com"))

    def test_generated_passwords_are_strong(self):
        for _ in range(20):
            pw = assist.generate_password()
            self.assertEqual(len(pw), 24)
            self.assertEqual(da.password_strength_issues(pw, None), [])


class AuditEndToEndTests(unittest.TestCase):
    """Run the real CLI against a fake dcli."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        tmp = Path(self.tmp.name)
        (tmp / "vault.json").write_text(json.dumps(FIXTURE))
        fake = tmp / "dcli"
        fake.write_text(
            f"#!{sys.executable}\n"
            "import sys\n"
            f"sys.stdout.write(open({str(tmp / 'vault.json')!r}).read())\n"
        )
        fake.chmod(0o755)
        self.env = dict(os.environ, PATH=f"{tmp}{os.pathsep}{os.environ['PATH']}",
                        HOME=str(tmp))

    def tearDown(self):
        self.tmp.cleanup()

    def audit(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "audit", "--no-breach-check", *args],
            cwd=self.tmp.name, env=self.env, capture_output=True, text=True, check=True,
        )

    def test_markdown_report(self):
        self.audit()
        report = (Path(self.tmp.name) / "dashlane-audit.md").read_text()
        self.assertIn("Credentials scanned: **7**", report)
        self.assertIn("Needing rotation: **3**", report)
        self.assertIn("[open](https://myaccount.google.com/security)", report)
        for c in FIXTURE:
            self.assertNotIn(c["password"], report)

    def test_json_report_respects_output_path(self):
        self.audit("--format", "json", "-o", "custom.txt")
        payload = json.loads((Path(self.tmp.name) / "custom.txt").read_text())
        self.assertEqual(payload["summary"]["credentials_scanned"], 7)
        self.assertEqual(payload["summary"]["likely_dead"], 1)
        self.assertEqual({r["id"] for r in payload["flagged"]}, {"2", "3", "4"})
        self.assertFalse((Path(self.tmp.name) / "dashlane-audit.json").exists())


if __name__ == "__main__":
    unittest.main()
