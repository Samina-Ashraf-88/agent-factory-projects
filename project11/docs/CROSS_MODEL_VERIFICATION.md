# Optional: get a second opinion from another AI model

This is manual and optional. **The project never sends your data anywhere.** Sharing happens only if you
choose to paste or upload the files yourself.

Agreement between two models is not proof. The transactions and the calculations remain the source of truth.
If they disagree, find the rows behind the difference and check those.

## Steps

1. Create the local files:

   ```
   python my_monthly_money_check.py --input private\wallet.csv --export-sanitized sanitized_export
   ```

2. Open `sanitized_export\sanitized_transactions.csv` and read it. **This is exactly what would be shared:** date,
   cleaned merchant name, amount, transaction type and category. It leaves out original descriptions, references,
   balances and file names. Merchant names, dates and amounts still reveal your habits, so decide whether you
   are comfortable with that provider seeing them.

3. If you are, give that file and `second_model_prompt.txt` to a model from a different family, in a tool that can run code.

4. Save its JSON answer, for example as `sanitized_export\second_opinion.json`, then compare:

   ```
   python my_monthly_money_check.py --input private\wallet.csv --compare sanitized_export\second_opinion.json
   ```

   The result is printed and saved as `crosscheck_result.md` in the report folder.

## What is compared

| Item | Comparison |
|---|---|
| Total income, total expenses | Must match within 0.01 |
| Recurring merchants (confirmed tier) | Same set of names |
| Possible duplicates | Same date, merchant and amount |
| Largest spending category | Same name |
| Forecast assumptions | Listed for you to compare by hand |
