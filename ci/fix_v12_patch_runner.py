from pathlib import Path

path = Path("ci/app_patch_v12.py")
src = path.read_text(encoding="utf-8")

names = [
    "simple_debt_replacement",
    "extra_db",
    "home_replacement",
    "transactions_replacement",
    "transaction_dialog",
    "debts_screen",
    "analysis_replacement",
    "add_debt_credit",
    "schedule_replacement",
]

changed = 0
for name in names:
    old = name + " = '''"
    new = name + " = r'''"
    if old in src:
        src = src.replace(old, new, 1)
        changed += 1

path.write_text(src, encoding="utf-8")
print(f"Prepared v1.2 patch runner; raw replacements enabled: {changed}")
