import os
import unittest

from src.main import run_audit
from src.models import Severity
from src.skill_loader import load_skill, parse_frontmatter
from tests.helpers import TempSkillCase


class Loading(TempSkillCase):
    def test_frontmatter(self):
        values, where, closed = parse_frontmatter(["---", "name: x", "description: >", "  long", "  text", "---", "body"])
        self.assertTrue(closed)
        self.assertEqual(values["description"], "long text")
        self.assertEqual(where["name"], 2)

    def test_finds_nested_and_hidden_files(self):
        self.write("hi")
        self.write("x = 1", "scripts/deep/tool.py", header=False)
        self.write("A=1", ".hidden/.env", header=False)
        rels = {f.rel for f in load_skill(str(self.dir)).files}
        self.assertLessEqual({"SKILL.md", "scripts/deep/tool.py", ".hidden/.env"}, rels)

    def test_missing_path_raises(self):
        with self.assertRaises(FileNotFoundError):
            load_skill(str(self.dir / "nope"))

    def test_plugin_surfaces_in_scope_for_a_skill(self):
        self.write('{"name": "p"}', ".claude-plugin/plugin.json", header=False)
        self.write('{"s": {"command": "npx", "args": ["some-server"]}}', ".mcp.json", header=False)
        self.write('{"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "./x.sh"}]}]}}', "hooks/hooks.json", header=False)
        self.write("hi", "skills/a/SKILL.md")
        self.write("other", "skills/b/SKILL.md")
        rules = self.rules(run_audit(str(self.dir / "skills" / "a"))[2])
        self.assertIn("MCP_LOCAL", rules)
        self.assertIn("HOOK_COMMAND", rules)
        self.assertEqual(load_skill(str(self.dir / "skills" / "a")).out_of_scope, ["b"])

    def test_binary_executable_blocks_clean(self):
        self.write("Hello.")
        (self.dir / "tool.bin").write_bytes(b"MZ\x00\x00" + b"\x00" * 50)
        _, _, findings, verdict, _ = self.audit()
        self.assertIn("BIN_EXECUTABLE", self.rules(findings))
        self.assertNotIn("CLEAN", verdict)

    def test_disguised_image(self):
        self.write("Hello.")
        (self.dir / "logo.png").write_bytes(b"MZ\x00\x00" + b"\x00" * 50)
        self.assertTrue(any(x.severity >= Severity.HIGH for x in self.audit()[2]))

    def test_real_image_does_not_block_clean(self):
        self.write("Hello.")
        (self.dir / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 50)
        self.assertIn("CLEAN", self.audit()[3])

    def test_utf16_is_still_scanned(self):
        self.write("rm -rf ~\n", encoding="utf-16")
        self.assertIn("DES_WIPE_HOME", self.rules(self.audit()[2]))

    @unittest.skipUnless(hasattr(os, "symlink"), "no symlink support")
    def test_symlink_recorded_not_followed(self):
        self.write("Hello.")
        secret = self.dir.parent / f"{self.dir.name}_secret.txt"
        secret.write_text("rm -rf ~")
        self.addCleanup(lambda: secret.unlink(missing_ok=True))
        try:
            os.symlink(secret, self.dir / "link.txt")
        except OSError:
            self.skipTest("symlinks need privileges here")
        rules = self.rules(self.audit()[2])
        self.assertIn("LOAD_SYMLINK", rules)
        self.assertNotIn("DES_WIPE_HOME", rules)


class SourceVerification(TempSkillCase):
    def _git(self, sha, origin="https://github.com/acme/skills.git"):
        (self.dir / ".git").mkdir()
        (self.dir / ".git" / "HEAD").write_text(sha + "\n")
        (self.dir / ".git" / "config").write_text(f'[remote "origin"]\n\turl = {origin}\n')

    def _catalog(self, sha, url="https://github.com/acme/skills.git"):
        path = self.dir.parent / f"{self.dir.name}_cat.json"
        path.write_text('{"name": "m", "plugins": [{"name": "probe", "author": {"name": "Acme"}, '
                        f'"source": {{"url": "{url}", "sha": "{sha}"}}}}]}}')
        self.addCleanup(lambda: path.unlink(missing_ok=True))
        return str(path)

    def test_matches_catalog(self):
        self.write("Hello.")
        self._git("a" * 40)
        info = self.audit(marketplace_file=self._catalog("a" * 40), plugin_name="probe")[1]
        self.assertEqual(info.status, "MATCHES CATALOG")
        self.assertIn("Acme", info.publisher)

    def test_wrong_commit_is_a_finding(self):
        self.write("Hello.")
        self._git("a" * 40)
        _, info, findings, verdict, _ = self.audit(marketplace_file=self._catalog("b" * 40), plugin_name="probe")
        self.assertEqual(info.status, "MISMATCH")
        self.assertIn("SRC_MISMATCH", self.rules(findings))
        self.assertNotIn("CLEAN", verdict)

    def test_wrong_repository_is_a_finding(self):
        self.write("Hello.")
        self._git("a" * 40, origin="https://github.com/evil/skills.git")
        info = self.audit(marketplace_file=self._catalog("a" * 40), plugin_name="probe")[1]
        self.assertEqual(info.status, "MISMATCH")

    def test_claims_alone_stay_unverified(self):
        self.write("Hello.")
        self.assertEqual(self.audit(publisher="Acme", source="https://x.example.com")[1].status, "UNVERIFIED")
