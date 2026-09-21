from pathlib import Path
import re

path = Path("app/src/main/java/az/budcem/premium/BudgetDb.java")
src = path.read_text(encoding="utf-8")

# payDebt has no local 'period' variable; keep its normal one-time debt label.
src = src.replace(
    'tv.put("period", period == null || period.isEmpty() ? "Borc ödənişi" : period);',
    'tv.put("period", "Borc ödənişi");'
)

# updateTransaction DOES receive 'period'; preserve Kredit ödənişi vs Borc ödənişi when editing.
pattern = r'''(public void updateTransaction\(long id, String kind, long categoryId, double amount, String period, String date, String note\) \{.*?if \(debtId > 0\) \{.*?)(v\.put\("period", "Borc ödənişi"\);)'''
replacement = lambda m: m.group(1) + 'v.put("period", period == null || period.isEmpty() ? "Borc ödənişi" : period);'
src, count = re.subn(pattern, replacement, src, count=1, flags=re.S)
if count != 1:
    raise SystemExit(f"Could not patch updateTransaction period label (found {count})")

path.write_text(src, encoding="utf-8")
print("Fixed v1.2 debt/credit transaction period handling")
