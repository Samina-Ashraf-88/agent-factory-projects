import re
import shutil
import subprocess
import sys

from src import crosscheck, main as cli, verification
from src.importer import import_wallet
from src.main import analyze, run_trust_gate
from src.report_generator import build_html

from .conftest import ROOT, SAMPLE


def _html(results, **kwargs):
    results = dict(results)
    results["checks"] = run_trust_gate()
    return build_html(results, currency="CR", **kwargs)


def test_html_has_all_sections_and_values(sample_results):
    html = _html(sample_results, is_sample=True)
    for heading in ("1. Financial overview", "2. Where the money goes", "3. Forgotten subscriptions",
                    "4. Possible duplicate charges", "5. Biggest financial leak", "6. Remaining money forecast",
                    "7. Recommended actions", "8. Methodology and limitations"):
        assert heading in html
    for value in ("23,000.00", "4,050.00", "796.00", "Possible duplicate — manual verification required", "Synthetic test wallet"):
        assert value in html


def test_html_is_self_contained_and_mobile_ready(sample_results):
    html = _html(sample_results)
    assert "<script" not in html
    assert not re.search(r'(?:src|href)\s*=\s*["\']?https?:', html)
    assert "default-src 'none'" in html
    assert 'name="viewport"' in html


def test_merchant_names_are_escaped(make_csv):
    results = analyze(import_wallet([make_csv([("2026-01-05", "", "<script>alert(1)</script>", -100), ("2026-01-05", "", "<script>alert(1)</script>", -100)])]))
    assert "<script" not in _html(results).lower()


def test_real_wallet_report_never_borrows_sample_findings(make_csv):
    results = analyze(import_wallet([make_csv([("2026-01-05", "", "Cinema Tickets", -300), ("2026-01-09", "", "Tea Stall", -50)])]))
    html = _html(results)
    findings = html.split("Engine self-check")[0]
    assert "PrimeVideo" not in findings and "Foodpanda" not in findings and "Synthetic test wallet" not in findings
    assert "No charges matched on date, merchant and amount." in html
    assert "No repeating charges were found" in html


def test_account_numbers_do_not_reach_the_report(make_csv):
    results = analyze(import_wallet([make_csv([("2026-01-05", "", "Transfer from acct 1234567890123456", 500), ("2026-01-05", "", "bad row 1234567890123456", "x")])]))
    assert "1234567890123456" not in _html(results)


def test_trust_gate_passes_on_the_real_engine():
    assert verification.passed(run_trust_gate())


def test_failed_gate_stops_the_run_and_writes_nothing(monkeypatch, tmp_path, make_csv, capsys):
    bad = [{"name": "Total income", "expected": 23000, "actual": 22000, "passed": False}]
    monkeypatch.setattr(cli, "run_trust_gate", lambda: bad)
    code = cli.main(["--input", str(make_csv([("2026-01-05", "", "Cinema", -300)])), "--output-dir", str(tmp_path / "out")])
    assert code == 2
    assert not (tmp_path / "out").exists()
    assert "STOPPED" in capsys.readouterr().err


def test_check_fails_when_numbers_are_wrong(sample_results):
    tampered = dict(sample_results, income={**sample_results["income"], "total": 22999})
    assert not verification.passed(verification.run_checks(tampered))


def test_script_runs_end_to_end(tmp_path):
    out = tmp_path / "reports"
    done = subprocess.run(
        [sys.executable, str(ROOT / "my_monthly_money_check.py"), "--input", str(SAMPLE), "--opening-balance", "6000", "--output-dir", str(out)],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert done.returncode == 0, done.stderr
    assert "PASS" in done.stdout and "FAIL" not in done.stdout
    assert (out / "money_detective_report.html").exists()


def test_inspect_stops_before_analysis(tmp_path, capsys):
    assert cli.main(["--input", str(SAMPLE), "--inspect", "--output-dir", str(tmp_path / "o")]) == 0
    assert "FILE INSPECTION" in capsys.readouterr().out
    assert not (tmp_path / "o").exists()


def test_sanitized_export_has_only_safe_columns(sample_results, tmp_path):
    csv_path, summary, _ = crosscheck.export_sanitized(sample_results, tmp_path)
    assert csv_path.read_text(encoding="utf-8").splitlines()[0] == "date,merchant,amount,transaction_type,category"
    assert "ORDER 88213" not in csv_path.read_text(encoding="utf-8")
    assert summary.exists()


def test_compare_reports_agreement_and_disagreement(sample_results):
    ours = crosscheck.build_summary(sample_results)
    theirs = dict(ours, total_income=22000, largest_category=ours["largest_category"].upper())
    status = {r["item"]: r["status"] for r in crosscheck.compare(ours, theirs)}
    assert status["total_income"] == "DISAGREE"
    assert status["largest_category"] == "AGREE"
    assert status["total_expenses"] == "AGREE"
    assert status["forecast_assumptions"] == "COMPARE BY HAND"


def test_gitignore_protects_financial_files(tmp_path):
    shutil.copy(ROOT / ".gitignore", tmp_path / ".gitignore")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)

    def ignored(name):
        return subprocess.run(["git", "check-ignore", "-q", name], cwd=tmp_path).returncode == 0

    for private in ("wallet_export.csv", "private/x.xlsx", "statement.json", "money_detective_report.html",
                    "reports/money_detective_report.html", "sanitized_export/sanitized_transactions.csv", ".env"):
        assert ignored(private), private
    for shared in ("data/sample_wallet.csv", "reports/.gitkeep", "src/main.py"):
        assert not ignored(shared), shared
