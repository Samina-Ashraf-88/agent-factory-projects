"""Test utilities. Fixtures hold synthetic data only and are read, never run."""
import shutil
import tempfile
import unittest
from pathlib import Path

from src.main import run_audit

FIXTURES = Path(__file__).parent / "fixtures"
HEADER = "---\nname: probe\ndescription: A probe. Use for tests.\n---\n\n"  # the body starts on line 6


def audit_fixture(name, **kw):
    return run_audit(str(FIXTURES / name), **kw)


class TempSkillCase(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)

    def write(self, body, name="SKILL.md", header=True, encoding="utf-8"):
        path = self.dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(((HEADER if header else "") + body).encode(encoding))
        return path

    def audit(self, **kw):
        return run_audit(str(self.dir), **kw)

    def rules(self, findings):
        return {x.rule_id for x in findings}
