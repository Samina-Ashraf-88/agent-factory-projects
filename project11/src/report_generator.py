"""Build the private, self-contained HTML report. No scripts and no external requests."""
from __future__ import annotations

from datetime import datetime
from html import escape
from pathlib import Path

CSS = """
:root{color-scheme:light;--surface:#fcfcfb;--panel:#f4f3ef;--ink:#0b0b0b;--ink2:#52514e;--line:#dddcd5;
--bar:#2a78d6;--track:#eceae4;--warn-bg:#fdf1dc;--warn-ink:#6b4700;--good:#0a6b0a;--bad:#a82222}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){color-scheme:dark;--surface:#1a1a19;--panel:#242422;
--ink:#f0efec;--ink2:#c3c2b7;--line:#3a3a37;--bar:#3987e5;--track:#30302d;--warn-bg:#3a2d12;--warn-ink:#f2d48f;
--good:#6fce6f;--bad:#f08a8a}}
:root[data-theme="dark"]{color-scheme:dark;--surface:#1a1a19;--panel:#242422;--ink:#f0efec;--ink2:#c3c2b7;
--line:#3a3a37;--bar:#3987e5;--track:#30302d;--warn-bg:#3a2d12;--warn-ink:#f2d48f;--good:#6fce6f;--bad:#f08a8a}
*{box-sizing:border-box}
body{margin:0;background:var(--surface);color:var(--ink);font:16px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:860px;margin:0 auto;padding:32px 16px 64px}
h1{font-size:1.9rem;line-height:1.2;margin:0 0 4px}
h2{font-size:1.3rem;margin:44px 0 12px;padding-top:20px;border-top:1px solid var(--line)}
h3{font-size:1rem;margin:20px 0 6px}
p{margin:8px 0}.muted{color:var(--ink2);font-size:.92rem}
.banner{background:var(--warn-bg);color:var(--warn-ink);padding:10px 14px;border-radius:8px;margin:14px 0;font-size:.95rem}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:14px 0}
.tile{background:var(--panel);border-radius:8px;padding:12px 14px}
.tile b{display:block;font-size:1.3rem;font-variant-numeric:tabular-nums;overflow-wrap:anywhere}
.tile span{color:var(--ink2);font-size:.85rem}
.scroll{overflow-x:auto;margin:10px 0}
table{border-collapse:collapse;width:100%;font-size:.92rem}
th,td{text-align:left;padding:7px 10px 7px 0;border-bottom:1px solid var(--line);vertical-align:top}
th{color:var(--ink2);font-weight:600}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.bars{margin:14px 0}
.bar-row{display:grid;grid-template-columns:minmax(96px,150px) 1fr 74px;gap:10px;align-items:center;padding:4px 0}
.bar-row:hover{background:var(--panel)}
.bar-label{font-size:.88rem;overflow-wrap:anywhere}.bar-value{text-align:right;font-size:.85rem;font-variant-numeric:tabular-nums}
.track{height:12px;background:var(--track);border-radius:0 4px 4px 0}
.fill{display:block;height:100%;background:var(--bar);border-radius:0 4px 4px 0}
.tag{display:inline-block;font-size:.78rem;background:var(--panel);border-radius:4px;padding:1px 6px;white-space:nowrap}
.pass{color:var(--good);font-weight:600}.fail{color:var(--bad);font-weight:600}
.neg{color:var(--bad)}
li{margin:6px 0}
"""


def _e(value) -> str:
    return escape(str(value), quote=True)


def _table(headers: list[str], rows: list[list], numeric: set[int] = frozenset()) -> str:
    head = "".join(f'<th{" class=n" if i in numeric else ""} scope="col">{_e(h)}</th>' for i, h in enumerate(headers))
    body = "".join(
        "<tr>" + "".join(f'<td{" class=n" if i in numeric else ""}>{c}</td>' for i, c in enumerate(row)) + "</tr>"
        for row in rows
    )
    return f'<div class="scroll"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def _tile(label: str, value: str) -> str:
    return f'<div class="tile"><b>{_e(value)}</b><span>{_e(label)}</span></div>'


def recommended_actions(results: dict, money) -> list[str]:
    actions = []
    strong = results["duplicates"]
    if strong:
        first = strong[0]
        actions.append(f"Check the possible duplicate at {first['merchant']} on {first['date']:%d %b %Y} "
                       f"({money(first['amount'])}) against your receipts or order history. If you only made one "
                       "purchase, ask the merchant or wallet provider about it.")
    subs = [r for r in results["recurring"] if r["kind"] == "Subscription" and r["active"]]
    if subs:
        names = ", ".join(r["merchant"] for r in subs[:4])
        monthly = sum(r["amount"] for r in subs if r["cadence"] == "monthly")
        extra = f" They cost {money(monthly)} a month." if monthly else ""
        actions.append(f"Look through your active subscriptions ({names}).{extra} "
                       "Keep the ones you use; only you can tell which those are.")
    leak = results["leak"]
    if leak.get("found"):
        actions.append(f"Try cutting {leak['category'].lower()} in half (about {leak['per_week']} times a week now). "
                       f"That would free up roughly {money(leak['halving_saves_monthly'])} a month.")
    by_class = results["spending"]["by_class"]
    reducible = by_class.get("Discretionary", 0) + by_class.get("Potentially avoidable", 0)
    months = results["overview"]["months"]
    if reducible and months:
        weekly = reducible / months / 4.345
        actions.append(f"Set a weekly limit for non-essential spending. You average about {money(weekly)} a week now, "
                       f"so a limit of {money(round(weekly * 0.8, -1))} would be a modest first step.")
    actions.append(f"Keep a small amount aside for surprises, for example {money(round(results['income']['average_monthly'] * 0.05, -1))} "
                   "(about 5% of a month's income).")
    return actions[:5]


def build_html(results: dict, *, currency: str = "", is_sample: bool = False, generated: datetime | None = None) -> str:
    def money(value: float) -> str:
        text = f"{abs(value):,.2f}"
        text = f"{text} {currency}".strip()
        return f"-{text}" if value < 0 else text

    ov = results["overview"]
    income, spending = results["income"], results["spending"]
    recurring, duplicates, leak, fc = results["recurring"], results["duplicates"], results["leak"], results["forecast"]
    imp = results["import"]
    generated = generated or datetime.now()
    out: list[str] = []
    add = out.append

    add("<h1>Money Detective Report</h1>")
    add(f'<p class="muted">{_e(f"{ov["start"]:%d %b %Y} to {ov["end"]:%d %b %Y}")} · '
        f'generated {_e(f"{generated:%d %b %Y %H:%M}")} · private, stored only on this computer</p>')
    if is_sample:
        add('<div class="banner"><strong>Synthetic test wallet.</strong> These are fictional transactions in '
            'fictional Credits (CR), used to prove the engine works. They are not anyone\'s finances.</div>')

    # 1
    add("<h2>1. Financial overview</h2>")
    add('<div class="tiles">' + _tile("Total income", money(income["total"])) + _tile("Total expenses", money(spending["gross_total"]))
        + _tile("Refunds received", money(spending["refund_total"])) + _tile("Net cash flow", money(ov["net_cash_flow"]))
        + _tile("Transactions", f"{ov['count']:,}") + "</div>")
    add(f"<p>Net cash flow is income plus refunds minus expenses. Internal transfers ({money(ov['transfers_out'])} out, "
        f"{money(ov['transfers_in'])} in) are excluded because the money stayed yours.</p>")
    add("<h3>Income by source</h3>")
    add(_table(["Source", "Total", "Payments", "Rhythm"],
               [[_e(s["source"]), money(s["total"]), s["count"], _e(s["frequency"])] for s in income["sources"]], {1, 2}))
    add(f'<p class="muted">Average monthly income: {_e(money(income["average_monthly"]))}. '
        f'Average monthly spending: {_e(money(spending["average_monthly"]))}.</p>')
    if results.get("review_transfers"):
        add(f'<p><strong>Please check:</strong> {len(results["review_transfers"])} transfer(s) look like payments to or from '
            "other people, so they are counted as real spending or income: "
            + _e(", ".join(results["review_transfers"][:6])) + ".</p>")
    if imp["warnings"] or imp["invalid"] or imp["repeated"]:
        add("<h3>Import notes</h3><ul>" + "".join(f"<li>{_e(w)}</li>" for w in imp["warnings"]) + "</ul>")
        problem_rows = [[_e(r["file"]), r["row"], _e(r["reason"]), _e(r["preview"])] for r in imp["invalid"]]
        problem_rows += [[_e(r["file"]), r["row"], _e(r["reason"]), _e(r["preview"])] for r in imp["repeated"]]
        if problem_rows:
            add(_table(["File", "Row", "Not counted because", "Row content"], problem_rows[:50], {1}))

    # 2
    add("<h2>2. Where the money goes</h2>")
    if spending["categories"]:
        top_value = max(max(c["net"], 0) for c in spending["categories"]) or 1
        bars = []
        for c in spending["categories"]:
            width = 100 * max(c["net"], 0) / top_value
            tip = f"{c['category']}: {money(c['net'])}, {c['percent']}% of spending, {c['count']} charges"
            bars.append(f'<div class="bar-row" title="{_e(tip)}"><span class="bar-label">{_e(c["category"])}</span>'
                        f'<span class="track"><span class="fill" style="width:{width:.1f}%"></span></span>'
                        f'<span class="bar-value">{c["percent"]:.1f}%</span></div>')
        add(f'<div class="bars" role="img" aria-label="Share of spending by category, largest first; the table below has the same data">{"".join(bars)}</div>')
        add(_table(["Category", "Type", "Net spent", "Share", "Charges"],
                   [[_e(c["category"]), f'<span class="tag">{_e(c["spending_class"])}</span>', money(c["net"]),
                     f'{c["percent"]:.1f}%', c["count"]] for c in spending["categories"]], {2, 3, 4}))
    add("<h3>Largest single expenses</h3>")
    add(_table(["Date", "Merchant", "Amount", "Category"],
               [[f'{t["date"]:%d %b %Y}', _e(t["merchant"]), money(t["amount"]), _e(t["category"])]
                for t in spending["largest_transactions"][:5]], {2}))
    scheduled_merchants = {r["merchant"] for r in recurring}
    small_habits = [s for s in spending["small_purchases"] if s["merchant"] not in scheduled_merchants]
    if small_habits:
        add("<h3>Small purchases that repeat</h3>")
        add(_table(["Merchant", "Purchases", "Average", "Total"],
                   [[_e(s["merchant"]), s["count"], money(s["average"]), money(s["total"])] for s in small_habits[:6]], {1, 2, 3}))

    # 3
    add("<h2>3. Forgotten subscriptions and repeat charges</h2>")
    if recurring:
        add("<p>Finding a repeat charge does not mean it is unwanted. Each row shows the evidence so you can decide.</p>")
        add(_table(["Merchant", "Amount each", "Frequency", "Total paid", "Classification", "Evidence"],
                   [[f'{_e(r["merchant"])}<br><span class="muted">{_e(r["kind"])}</span>', money(r["amount"]), _e(r["cadence"]),
                     money(r["total"]), _e(r["tier"]), _e(r["evidence"])] for r in recurring], {1, 3}))
    else:
        add("<p>No repeating charges were found in this data.</p>")

    # 4
    add("<h2>4. Possible duplicate charges</h2>")
    if duplicates:
        add("<p>These are prompts to check, not accusations. Nothing has been changed, and a same-day match can be perfectly "
            "legitimate. Every one is labelled <strong>Possible duplicate — manual verification required</strong>.</p>")
        add(_table(["Date", "Merchant", "Amount", "Matches", "Evidence", "Why it was flagged"],
                   [[f'{d["date"]:%d %b %Y}', _e(d["merchant"]), money(d["amount"]), d["count"],
                     _e(d["evidence_strength"]), _e(d["explanation"])] for d in duplicates], {2, 3}))
    else:
        add("<p>No charges matched on date, merchant and amount.</p>")

    # 5
    add("<h2>5. Biggest financial leak</h2>")
    if leak.get("caveat"):
        add(f'<div class="banner"><strong>Read this with care.</strong> {_e(leak["caveat"])} '
            f'Includes: {_e(", ".join(leak["unclassified_merchants"]))}.</div>')
    if leak.get("found"):
        add(f'<p><strong>{_e(leak["category"])}: {_e(money(leak["total"]))}</strong> across {leak["count"]} charges, '
            f'about {_e(money(leak["monthly_cost"]))} a month.</p>')
        add("<ul>" + "".join(f"<li>{_e(w)}</li>" for w in leak["why"]) + "</ul>")
        add(_table(["Merchant", "Total"], [[_e(m["merchant"]), money(m["total"])] for m in leak["merchants"]], {1}))
        add(f'<p><strong>What you could consider:</strong> half as many {_e(leak["category"].lower())} purchases would free up about '
            f'{_e(money(leak["halving_saves_monthly"]))} a month. Whether that trade is worth it is your call.</p>')
    else:
        add(f"<p>{_e(leak.get('message', ''))}</p>")
    if leak["comparisons"]:
        add("<h3>How it compares</h3><ul>" + "".join(f"<li>{_e(c)}</li>" for c in leak["comparisons"]) + "</ul>")
    add("<h3>Month by month</h3>")
    add(_table(["Month", "Income", "Spending", "Difference"],
               [[_e(m["month"]), money(m["income"]), money(m["spending"]),
                 f'<span class="{"neg" if m["net"] < 0 else ""}">{money(m["net"])}</span>'] for m in leak["monthly"]], {1, 2, 3}))
    add('<p class="muted">Pocket money and bills fall on different dates, so one month in deficit is not itself a problem. '
        "The pattern across all months is what matters.</p>")

    # 6
    add("<h2>6. Remaining money forecast</h2>")
    if fc["status"] == "ok":
        add(f'<p>Next pocket money: <strong>{_e(f"{fc["next_income_date"]:%d %b %Y}")}</strong> ({_e(fc["date_source"])}), '
            f'{fc["days"]} day(s) of spending to cover. Starting balance: '
            f'<strong>{_e(money(fc["balance"])) if fc["balance"] is not None else "not known"}</strong>.</p>')
        add(f'<p class="muted">{_e(fc["balance_basis"])}</p>')
        have_balance = fc["balance"] is not None
        add(_table(["Estimate", "Expected expenses", "Known income", "Remaining" if have_balance else "Change in money", "Basis"],
                   [[f"<strong>{_e(s['name'])}</strong>", money(s["spending"]), money(s["income"]),
                     f'<strong class="{"neg" if (s["remaining"] if have_balance else s["net_change"]) < 0 else ""}">'
                     f'{money(s["remaining"] if have_balance else s["net_change"])}</strong>', _e(s["note"])]
                    for s in fc["scenarios"]], {1, 2, 3}))
        if have_balance and fc["scenarios"][1]["remaining"] < 0:
            add("<p>A negative figure means that at this pace the money would run out before the next pocket money arrives.</p>")
        scheduled = fc["scheduled_certain"] + fc["scheduled_probable"]
        if scheduled:
            add("<h3>Charges expected before then</h3>")
            add(_table(["Merchant", "Expected dates", "Total"],
                       [[_e(e["merchant"]), _e(", ".join(f"{d:%d %b}" for d in e["dates"])), money(e["total"])] for e in scheduled], {2}))
        if fc["upside_income"]:
            add("<p>Possible extra, not counted: " + _e(", ".join(f"{u['source']} ({money(u['amount'])} per payment)" for u in fc["upside_income"])) + ".</p>")
        add("<h3>Assumptions</h3><ul>" + "".join(f"<li>{_e(a)}</li>" for a in fc["assumptions"]) + "</ul>")
        add("<h3>Uncertainties</h3><ul>" + "".join(f"<li>{_e(u)}</li>" for u in fc["uncertainties"]) + "</ul>")
    else:
        add(f"<p><strong>Forecast needs one more detail.</strong> {_e(fc['message'])}</p>")

    # 7
    add("<h2>7. Recommended actions</h2><ol>")
    for action in recommended_actions(results, money):
        add(f"<li>{_e(action)}</li>")
    add("</ol>")

    # 8
    add("<h2>8. Methodology and limitations</h2>")
    add("<p>Every number here was computed by a Python program from the transaction rows. An AI did not estimate any of them.</p><ul>"
        "<li><strong>Income:</strong> all money-in rows, after setting aside refunds, adjustments and internal transfers.</li>"
        "<li><strong>Spending:</strong> money-out rows grouped into categories by keyword rules on the merchant name; refunds reduce their category.</li>"
        "<li><strong>Repeat charges:</strong> the merchant, the amounts and the days between charges are judged together. Three or more on-rhythm charges "
        "of a steady amount are confirmed; weaker patterns are labelled probable or possible.</li>"
        "<li><strong>Possible duplicates:</strong> two or more charges with the same date, merchant and amount. Times, references and matching refunds "
        "then make the evidence stronger or weaker. Nothing is ever removed or called fraud.</li>"
        "<li><strong>Forecast:</strong> charges expected before the next pocket money, plus past variable spending per day multiplied by the days left.</li></ul>")
    add("<p><strong>Limitations:</strong> keyword categories can be wrong, and unrecognized merchants fall under Other expenses. "
        "Averages only reflect the period in the file. An annual charge cannot be seen in a shorter history, and rules cannot know what you value.</p>")
    add("<h3>Engine self-check on the synthetic wallet</h3>")
    add("<p>Before this report was built, the engine had to reproduce known answers on a fictional test wallet. These confirm the calculations, not your own data.</p>")
    add(_table(["Check", "Expected", "Actual", "Result"],
               [[_e(c["name"]), _e(f'{c["expected"]:,.2f}' if isinstance(c["expected"], (int, float)) else c["expected"]),
                 _e(f'{c["actual"]:,.2f}' if isinstance(c["actual"], (int, float)) else c["actual"]),
                 f'<span class="{"pass" if c["passed"] else "fail"}">{"PASS" if c["passed"] else "FAIL"}</span>']
                for c in results["checks"]], {1, 2}))

    return ("<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            "<meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'none'; style-src 'unsafe-inline'\">"
            "<meta name=\"robots\" content=\"noindex\"><title>Money Detective Report</title>"
            f"<style>{CSS}</style></head><body><main>{''.join(out)}</main></body></html>")


def write_report(html_text: str, directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "money_detective_report.html"
    path.write_text(html_text, encoding="utf-8")
    return path
