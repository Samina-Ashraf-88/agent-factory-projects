"""Private data the skill could reach. Access alone is not transmission; risk_classifier joins the two."""
from __future__ import annotations

from .models import ACCESS_ONLY, AI_PROVIDER, Severity, SkillFile
from .scanning import Rule, scan

DATA = ("private_data",)
RULES = [
    Rule("PRIV_CONVERSATION", "privacy", Severity.MEDIUM,
         r"\b(?:conversation|chat)\s+(?:history|log|transcript|contents?)\b|\bsession\s+transcript\b|\bprevious\s+messages\b",
         "Refers to your conversation content.", tags=DATA + ("conversation",), data_flow=AI_PROVIDER,
         data_at_risk="conversation content"),
    Rule("PRIV_DOCUMENTS", "privacy", Severity.MEDIUM,
         r"(?:~|\$HOME|%USERPROFILE%|\$env:USERPROFILE)[/\\](?:Documents|Desktop|Downloads|Pictures|OneDrive|Dropbox)\b"
         r"|\b(?:user'?s?|your|private|personal|confidential)\s+(?:documents?|files?|photos?)\b",
         "Refers to personal files outside the project.", tags=DATA, data_flow=ACCESS_ONLY,
         data_at_risk="personal documents"),
    Rule("PRIV_HOME_WIDE", "privacy", Severity.HIGH,
         r"(?<![\w-])(?:find|ls\s+-\w*R\w*|grep\s+-\w*r\w*|rg|tar|zip\s+-r|Get-ChildItem\s+-Recurse)\s+(?:[^\n|]{0,40}\s)?(?:(?:~|\$HOME|C:\\|%USERPROFILE%)(?:/\*?)?(?=\s|$|[|;\"'])|/(?=\s+-|\s*$|\s*[|;]))",
         "Searches or archives your whole home folder or disk, far beyond what a skill normally needs.",
         tags=DATA, data_flow=ACCESS_ONLY, data_at_risk="everything in your home folder"),
    Rule("PRIV_SOURCE_BULK", "privacy", Severity.MEDIUM,
         r"\bgit\s+(?:ls-files|archive|bundle)\b|\b(?:entire|whole|full|all)\s+(?:the\s+)?(?:repo(?:sitory)?|codebase|source\s+code|project\s+files)\b",
         "Touches the whole codebase at once.", tags=DATA, data_flow=ACCESS_ONLY, data_at_risk="source code"),
    Rule("PRIV_EMAIL", "privacy", Severity.LOW, r"\b(?:inbox|e-?mails?\s+(?:messages?|contents?|history|threads?)|gmail|outlook)\b",
         "Mentions email. A mention alone reads nothing; sending it elsewhere is escalated.",
         tags=DATA, data_flow=ACCESS_ONLY, data_at_risk="email"),
    Rule("PRIV_FINANCIAL", "privacy", Severity.LOW,
         r"\b(?:bank\s+(?:statements?|accounts?)|tax\s+returns?|credit\s+cards?|financial\s+records?|invoices?|payroll)\b",
         "Mentions financial records. A mention alone reads nothing; sending them elsewhere is escalated.",
         tags=DATA, data_flow=ACCESS_ONLY, data_at_risk="financial records"),
    Rule("PRIV_BROWSER", "privacy", Severity.HIGH,
         r"\b(?:browser\s+(?:history|cookies|profile|passwords?)|saved\s+passwords?|Chrome[/\\]User Data)\b",
         "Refers to browser data, which can include logged-in sessions.", tags=DATA, data_flow=ACCESS_ONLY,
         data_at_risk="browser data"),
    Rule("PRIV_PII", "privacy", Severity.LOW,
         r"\b(?:social\s+security|passports?|date\s+of\s+birth|home\s+address|medical\s+records?)\b",
         "Mentions personal information. A mention alone reads nothing; sending it elsewhere is escalated.",
         tags=DATA, data_flow=ACCESS_ONLY, data_at_risk="personal information"),
]


def analyze(f: SkillFile) -> list:
    return scan(f, RULES)
