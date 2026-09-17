from pathlib import Path
import re

MAIN = Path("app/src/main/java/az/budcem/premium/MainActivity.java")
DB = Path("app/src/main/java/az/budcem/premium/BudgetDb.java")

main = MAIN.read_text(encoding="utf-8")
db = DB.read_text(encoding="utf-8")


def replace_once(text, pattern, replacement, label):
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.S)
    if count != 1:
        raise SystemExit(f"{label}: patch target was not found exactly once (found {count})")
    return updated

# --- Database: richer transaction rows + edit/delete + one-time debts ---
db_replacement = r'''    public Cursor monthTransactions(String monthPrefix) {
        return getReadableDatabase().rawQuery(
                "SELECT t.id AS _id,t.kind,t.category_id,t.amount,t.period,t.date,t.note,t.debt_id,COALESCE(c.name,'Borc') AS category " +
                        "FROM transactions t LEFT JOIN categories c ON c.id=t.category_id " +
                        "WHERE t.date LIKE ? ORDER BY t.date DESC,t.id DESC LIMIT 100",
                new String[]{monthPrefix + "%"});
    }

    public void updateTransaction(long id, String kind, long categoryId, double amount, String period, String date, String note) {
        SQLiteDatabase database = getWritableDatabase();
        long debtId = 0;
        try (Cursor c = database.rawQuery("SELECT debt_id FROM transactions WHERE id=?", new String[]{String.valueOf(id)})) {
            if (c.moveToFirst()) debtId = c.getLong(0);
        }

        ContentValues v = new ContentValues();
        if (debtId > 0) {
            v.put("amount", Math.max(0, amount));
            v.put("period", "Borc ödənişi");
            v.put("date", date);
            v.put("note", note == null ? "" : note);
        } else {
            v.put("kind", kind);
            v.put("category_id", categoryId);
            v.put("amount", Math.max(0, amount));
            v.put("period", period);
            v.put("date", date);
            v.put("note", note == null ? "" : note);
        }
        database.update("transactions", v, "id=?", new String[]{String.valueOf(id)});
        if (debtId > 0) rebuildDebtFromTransactions(debtId);
    }

    public void deleteTransaction(long id) {
        SQLiteDatabase database = getWritableDatabase();
        long debtId = 0;
        try (Cursor c = database.rawQuery("SELECT debt_id FROM transactions WHERE id=?", new String[]{String.valueOf(id)})) {
            if (c.moveToFirst()) debtId = c.getLong(0);
        }
        database.delete("transactions", "id=?", new String[]{String.valueOf(id)});
        if (debtId > 0) rebuildDebtFromTransactions(debtId);
    }

    private void rebuildDebtFromTransactions(long debtId) {
        SQLiteDatabase database = getWritableDatabase();
        double principal = 0;
        try (Cursor c = database.rawQuery("SELECT principal FROM debts WHERE id=?", new String[]{String.valueOf(debtId)})) {
            if (!c.moveToFirst()) return;
            principal = c.getDouble(0);
        }

        database.execSQL("UPDATE debt_schedule SET paid=0,status='OPEN' WHERE debt_id=?", new Object[]{debtId});

        double paidTotal = 0;
        try (Cursor c = database.rawQuery("SELECT COALESCE(SUM(amount),0) FROM transactions WHERE debt_id=?", new String[]{String.valueOf(debtId)})) {
            if (c.moveToFirst()) paidTotal = Math.min(principal, Math.max(0, c.getDouble(0)));
        }

        double left = paidTotal;
        try (Cursor c = database.rawQuery(
                "SELECT id,amount FROM debt_schedule WHERE debt_id=? ORDER BY due_date,id",
                new String[]{String.valueOf(debtId)})) {
            while (c.moveToNext()) {
                long scheduleId = c.getLong(0);
                double scheduled = c.getDouble(1);
                double applied = Math.min(Math.max(0, scheduled), left);
                ContentValues sv = new ContentValues();
                sv.put("paid", applied);
                sv.put("status", applied + 0.005 >= scheduled ? "PAID" : applied > 0.005 ? "PARTIAL" : "OPEN");
                database.update("debt_schedule", sv, "id=?", new String[]{String.valueOf(scheduleId)});
                left = Math.max(0, left - applied);
            }
        }

        double remaining = Math.max(0, principal - paidTotal);
        String nextDue = null;
        try (Cursor c = database.rawQuery(
                "SELECT due_date FROM debt_schedule WHERE debt_id=? AND status!='PAID' ORDER BY due_date,id LIMIT 1",
                new String[]{String.valueOf(debtId)})) {
            if (c.moveToFirst()) nextDue = c.getString(0);
        }
        ContentValues dv = new ContentValues();
        dv.put("remaining", remaining);
        if (nextDue == null || remaining <= 0.005) dv.putNull("next_due"); else dv.put("next_due", nextDue);
        database.update("debts", dv, "id=?", new String[]{String.valueOf(debtId)});
    }

    public long addSimpleDebt(String name, String direction, double principal, String dueDate) {
        if (principal <= 0) return -1;
        SQLiteDatabase database = getWritableDatabase();
        database.beginTransaction();
        try {
            String created = LocalDate.now().toString();
            String due = dueDate == null ? "" : dueDate.trim();
            ContentValues v = new ContentValues();
            v.put("name", name.trim());
            v.put("direction", direction);
            v.put("principal", principal);
            v.put("remaining", principal);
            v.put("monthly", principal);
            v.put("first_due", due.isEmpty() ? created : due);
            if (due.isEmpty()) v.putNull("next_due"); else v.put("next_due", due);
            v.put("created", created);
            long debtId = database.insert("debts", null, v);

            if (!due.isEmpty()) {
                ContentValues s = new ContentValues();
                s.put("debt_id", debtId);
                s.put("due_date", due);
                s.put("amount", principal);
                s.put("paid", 0);
                s.put("status", "OPEN");
                database.insert("debt_schedule", null, s);
            }
            database.setTransactionSuccessful();
            return debtId;
        } finally {
            database.endTransaction();
        }
    }

    public String debtName(long debtId) {'''

db = replace_once(
    db,
    r'''    public Cursor monthTransactions\(String monthPrefix\) \{.*?    public String debtName\(long debtId\) \{''',
    db_replacement,
    "BudgetDb transaction/debt"
)

# --- Transactions screen: edit/delete buttons ---
transactions_replacement = r'''    private void showTransactions() {
        LinearLayout body = vertical();
        String month = LocalDate.now().format(DateTimeFormatter.ofPattern("yyyy-MM"));

        LinearLayout add = card(WHITE);
        LinearLayout r = new LinearLayout(this);
        r.setOrientation(LinearLayout.HORIZONTAL);
        r.addView(actionButton("+ Gəlir", YELLOW, INK, v -> showTransactionDialog("INCOME")), new LinearLayout.LayoutParams(0, dp(50), 1));
        LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(0, dp(50), 1); p.setMargins(dp(8),0,0,0);
        r.addView(actionButton("+ Xərc", PURPLE, WHITE, v -> showTransactionDialog("EXPENSE")), p);
        add.addView(r);
        Button cat = actionButton("Kateqoriyaları idarə et", PURPLE_SOFT, PURPLE, v -> showCategories());
        LinearLayout.LayoutParams cp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(46)); cp.setMargins(0, dp(9), 0, 0);
        add.addView(cat, cp);
        body.addView(add);

        LinearLayout summary = card(YELLOW_SOFT);
        summary.addView(tv("Bu ay", 13, MUTED, false));
        summary.addView(tv("Gəlir " + azn(db.sumTransactions("INCOME", month)) + "   •   Xərc " + azn(db.sumTransactions("EXPENSE", month)), 16, INK, true));
        body.addView(summary);

        LinearLayout list = card(WHITE);
        list.addView(tv("Əməliyyatlar", 17, INK, true));
        int n = 0;
        try (Cursor c = db.monthTransactions(month)) {
            while (c.moveToNext()) {
                n++;
                long txId = c.getLong(c.getColumnIndexOrThrow("_id"));
                String kind = c.getString(c.getColumnIndexOrThrow("kind"));
                long categoryId = c.getLong(c.getColumnIndexOrThrow("category_id"));
                double amount = c.getDouble(c.getColumnIndexOrThrow("amount"));
                String period = c.getString(c.getColumnIndexOrThrow("period"));
                String date = c.getString(c.getColumnIndexOrThrow("date"));
                String category = c.getString(c.getColumnIndexOrThrow("category"));
                String note = c.getString(c.getColumnIndexOrThrow("note"));
                long debtId = c.getLong(c.getColumnIndexOrThrow("debt_id"));

                LinearLayout item = new LinearLayout(this);
                item.setOrientation(LinearLayout.VERTICAL);
                item.setPadding(0, dp(9), 0, dp(9));

                LinearLayout rr = new LinearLayout(this);
                rr.setOrientation(LinearLayout.HORIZONTAL);
                rr.setGravity(Gravity.CENTER_VERTICAL);
                String sub = (debtId > 0 ? "Borc ödənişi" : category) + " • " + date + (note == null || note.isEmpty() ? "" : "\n" + note);
                TextView l = tv(sub, 13, INK, false);
                TextView a = tv(("INCOME".equals(kind) ? "+ " : "− ") + azn(amount), 14, "INCOME".equals(kind) ? GREEN : RED, true);
                rr.addView(l, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
                rr.addView(a);
                item.addView(rr);

                LinearLayout actions = new LinearLayout(this);
                actions.setOrientation(LinearLayout.HORIZONTAL);
                actions.setPadding(0, dp(8), 0, 0);
                Button edit = actionButton("Redaktə", PURPLE_SOFT, PURPLE,
                        v -> showEditTransactionDialog(txId, kind, categoryId, amount, period, date, note, debtId));
                Button delete = actionButton("Sil", Color.rgb(255,235,226), RED,
                        v -> confirmDeleteTransaction(txId, debtId));
                actions.addView(edit, new LinearLayout.LayoutParams(0, dp(40), 1));
                LinearLayout.LayoutParams delLp = new LinearLayout.LayoutParams(0, dp(40), 1); delLp.setMargins(dp(8),0,0,0);
                actions.addView(delete, delLp);
                item.addView(actions);
                list.addView(item);

                if (!c.isLast()) {
                    View line = new View(this);
                    line.setBackgroundColor(Color.rgb(241,239,235));
                    line.setLayoutParams(new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(1)));
                    list.addView(line);
                }
            }
        }
        if (n == 0) {
            TextView e = tv("Bu ay üçün əməliyyat yoxdur.", 13, MUTED, false);
            e.setPadding(0,dp(12),0,0);
            list.addView(e);
        }
        body.addView(list);
        render("Gəlir və xərclər", body, 1);
    }

    private void showEditTransactionDialog(long txId, String kind, long categoryId, double oldAmount,
                                           String oldPeriod, String oldDate, String oldNote, long debtId) {
        LinearLayout box = vertical();
        box.setPadding(dp(18),dp(8),dp(18),0);

        Spinner cat = null;
        if (debtId <= 0) {
            List<Choice> cats = categoryChoices(kind);
            cat = spinner(cats);
            for (int i = 0; i < cats.size(); i++) if (cats.get(i).id == categoryId) cat.setSelection(i);
            box.addView(tv("Kateqoriya",12,MUTED,true));
            box.addView(cat);
        } else {
            box.addView(tv("Borc ödənişi",13,PURPLE,true));
        }

        EditText amount = input("Məbləğ", true);
        amount.setText(String.format(Locale.US,"%.2f",oldAmount));
        EditText date = input("Tarix (istəyə bağlı — boşdursa bu gün)", false);
        date.setText(oldDate == null ? "" : oldDate);
        List<String> periods = List.of("Birdəfəlik", "Həftəlik", "Aylıq", "İllik");
        Spinner period = spinner(periods);
        int periodIndex = periods.indexOf(oldPeriod);
        if (periodIndex >= 0) period.setSelection(periodIndex);
        EditText note = input("Qeyd (istəyə bağlı)", false);
        note.setText(oldNote == null ? "" : oldNote);
        box.addView(amount);
        box.addView(date);
        if (debtId <= 0) box.addView(period);
        box.addView(note);

        final Spinner finalCat = cat;
        new AlertDialog.Builder(this)
                .setTitle("Əməliyyatı redaktə et")
                .setView(box)
                .setNegativeButton("Ləğv et", null)
                .setPositiveButton("Yadda saxla", (d,w) -> {
                    double a = parseAmount(amount.getText().toString());
                    String rawDate = date.getText().toString().trim();
                    String dt = rawDate.isEmpty() ? LocalDate.now().toString() : rawDate;
                    if (a <= 0 || !validDate(dt)) { toast("Məbləği düzgün daxil et."); return; }
                    long catId = debtId > 0 ? 0 : ((Choice)finalCat.getSelectedItem()).id;
                    String per = debtId > 0 ? "Borc ödənişi" : String.valueOf(period.getSelectedItem());
                    db.updateTransaction(txId, kind, catId, a, per, dt, note.getText().toString());
                    scheduleAllOpen(this);
                    showTransactions();
                }).show();
    }

    private void confirmDeleteTransaction(long txId, long debtId) {
        new AlertDialog.Builder(this)
                .setTitle("Əməliyyat silinsin?")
                .setMessage(debtId > 0 ? "Bu borc ödənişi silinəndə borcun qalığı avtomatik geri hesablanacaq." : "Bu əməliyyat ümumi balans və aylıq təhlildən silinəcək.")
                .setNegativeButton("Ləğv et", null)
                .setPositiveButton("Sil", (d,w) -> {
                    db.deleteTransaction(txId);
                    scheduleAllOpen(this);
                    showTransactions();
                }).show();
    }

    private void showBudgets() {'''

main = replace_once(
    main,
    r'''    private void showTransactions\(\) \{.*?    private void showBudgets\(\) \{''',
    transactions_replacement,
    "Transactions UI"
)

# --- New transaction: date no longer mandatory ---
transaction_dialog_replacement = r'''    private void showTransactionDialog(String kind) {
        LinearLayout box = vertical(); box.setPadding(dp(18),dp(8),dp(18),0);
        List<Choice> cats = categoryChoices(kind);
        if (cats.isEmpty()) { toast("Əvvəl kateqoriya yarat."); showCategories(); return; }
        Spinner cat = spinner(cats);
        EditText amount = input("Məbləğ", true);
        EditText date = input("Tarix (istəyə bağlı — boşdursa bu gün)", false);
        List<String> periods = List.of("Birdəfəlik", "Həftəlik", "Aylıq", "İllik");
        Spinner period = spinner(periods);
        EditText note = input("Qeyd (istəyə bağlı)", false);
        box.addView(tv("Kateqoriya",12,MUTED,true)); box.addView(cat); box.addView(amount); box.addView(date); box.addView(period); box.addView(note);

        Spinner obligation = null;
        Spinner debtSpinner = null;
        if ("EXPENSE".equals(kind)) {
            box.addView(tv("Öhdəlik",12,MUTED,true));
            obligation = spinner(List.of("Adi xərc", "Borc ödənişi"));
            box.addView(obligation);
            List<Choice> debts = debtChoices("PAYABLE");
            List<Choice> withNone = new ArrayList<>(); withNone.add(new Choice(0,"Borc seçilməyib")); withNone.addAll(debts);
            debtSpinner = spinner(withNone);
            box.addView(debtSpinner);
            Spinner finalDebtSpinner = debtSpinner;
            obligation.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
                @Override public void onItemSelected(AdapterView<?> parent, View view, int position, long id) { finalDebtSpinner.setVisibility(position == 1 ? View.VISIBLE : View.GONE); }
                @Override public void onNothingSelected(AdapterView<?> parent) {}
            });
            debtSpinner.setVisibility(View.GONE);
        }

        final Spinner fObligation = obligation;
        final Spinner fDebtSpinner = debtSpinner;
        new AlertDialog.Builder(this)
                .setTitle("INCOME".equals(kind) ? "Gəlir əlavə et" : "Xərc əlavə et")
                .setView(box)
                .setNegativeButton("Ləğv et", null)
                .setPositiveButton("Yadda saxla", (d,w) -> {
                    double a = parseAmount(amount.getText().toString());
                    String rawDate = date.getText().toString().trim();
                    String dt = rawDate.isEmpty() ? LocalDate.now().toString() : rawDate;
                    if (a <= 0 || !validDate(dt)) { toast("Məbləği düzgün daxil et."); return; }
                    Choice cc = (Choice)cat.getSelectedItem();
                    String per = String.valueOf(period.getSelectedItem());
                    if ("EXPENSE".equals(kind) && fObligation != null && fObligation.getSelectedItemPosition() == 1) {
                        Choice debtChoice = (Choice)fDebtSpinner.getSelectedItem();
                        if (debtChoice == null || debtChoice.id == 0) {
                            toast("Borc seçilməyib, xərc adi xərc kimi yazıldı.");
                            db.addTransaction(kind, cc.id, a, per, dt, note.getText().toString(), 0);
                        } else {
                            db.payDebt(debtChoice.id, a, dt);
                            scheduleAllOpen(this);
                        }
                    } else {
                        db.addTransaction(kind, cc.id, a, per, dt, note.getText().toString(), 0);
                    }
                    showTransactions();
                }).show();
    }

    private void showAddParentCategoryDialog() {'''

main = replace_once(
    main,
    r'''    private void showTransactionDialog\(String kind\) \{.*?    private void showAddParentCategoryDialog\(\) \{''',
    transaction_dialog_replacement,
    "Transaction dialog"
)

# --- Debts screen: one-time debt, no monthly table ---
debts_screen_replacement = r'''    private void showDebts() {
        LinearLayout body = vertical();
        LinearLayout top = card(PURPLE_SOFT);
        top.addView(tv("Borc və alacaqlar", 18, INK, true));
        top.addView(tv("Verəcəyim: " + azn(db.totalDebtRemaining("PAYABLE")) + "   •   Alacağım: " + azn(db.totalDebtRemaining("RECEIVABLE")), 13, PURPLE, true));
        Button add = actionButton("+ Birdəfəlik borc / alacaq", PURPLE, WHITE, v -> showAddDebtDialog());
        LinearLayout.LayoutParams ap = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(48)); ap.setMargins(0,dp(12),0,0); top.addView(add, ap);
        body.addView(top);

        int n = 0;
        try (Cursor c = db.debts()) {
            while (c.moveToNext()) {
                n++;
                long id = c.getLong(c.getColumnIndexOrThrow("_id"));
                String name = c.getString(c.getColumnIndexOrThrow("name"));
                String dir = c.getString(c.getColumnIndexOrThrow("direction"));
                double principal = c.getDouble(c.getColumnIndexOrThrow("principal"));
                double remaining = c.getDouble(c.getColumnIndexOrThrow("remaining"));
                double monthly = c.getDouble(c.getColumnIndexOrThrow("monthly"));
                String nextDue = c.isNull(c.getColumnIndexOrThrow("next_due")) ? "Tarix seçilməyib" : c.getString(c.getColumnIndexOrThrow("next_due"));

                LinearLayout dc = card(WHITE);
                LinearLayout titleRow = new LinearLayout(this); titleRow.setOrientation(LinearLayout.HORIZONTAL); titleRow.setGravity(Gravity.CENTER_VERTICAL);
                titleRow.addView(tv(name, 18, INK, true), new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
                TextView badge = tv("PAYABLE".equals(dir) ? "VERƏCƏYİM" : "ALACAĞIM", 10, "PAYABLE".equals(dir) ? RED : GREEN, true);
                badge.setPadding(dp(8),dp(5),dp(8),dp(5)); badge.setBackground(rounded("PAYABLE".equals(dir) ? Color.rgb(255,235,226) : Color.rgb(225,246,237), 12)); titleRow.addView(badge);
                dc.addView(titleRow);
                TextView rem = tv(azn(remaining), 25, INK, true); rem.setPadding(0,dp(8),0,0); dc.addView(rem);
                dc.addView(tv("İlkin məbləğ: " + azn(principal) + "\nÖdəniş tarixi: " + nextDue, 12, MUTED, false));
                double closed = principal > 0 ? (principal - remaining) / principal : 1;
                ProgressBar pb = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
                pb.setMax(1000);
                pb.setProgress((int)Math.max(0,Math.min(1000,closed*1000)));
                pb.setProgressTintList(ColorStateList.valueOf("PAYABLE".equals(dir) ? PURPLE : GREEN));
                LinearLayout.LayoutParams pp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(9)); pp.setMargins(0,dp(10),0,dp(10)); dc.addView(pb, pp);
                Button pay = actionButton(remaining <= 0.005 ? "Bağlanıb" : "Ödəniş et", "PAYABLE".equals(dir) ? PURPLE : GREEN, WHITE,
                        v -> showPayDebtDialog(id, name, remaining, monthly));
                pay.setEnabled(remaining > 0.005);
                dc.addView(pay, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(46)));
                body.addView(dc);
            }
        }
        if (n == 0) {
            LinearLayout e = card(WHITE);
            e.addView(tv("Birdəfəlik borc və ya alacaq yarat. Tarix əlavə etmək istəyə bağlıdır.", 14, MUTED, false));
            body.addView(e);
        }
        render("Borclarım", body, 3);
    }

    private void showAnalysis() {'''

main = replace_once(
    main,
    r'''    private void showDebts\(\) \{.*?    private void showAnalysis\(\) \{''',
    debts_screen_replacement,
    "Debts screen"
)

# --- Debt creation: single debt, optional date ---
add_debt_replacement = r'''    private void showAddDebtDialog() {
        LinearLayout box=vertical(); box.setPadding(dp(18),dp(8),dp(18),0);
        EditText name=input("Borc / şəxs / kredit adı",false);
        Spinner direction=spinner(List.of("Mən ödəyəcəyəm", "Mən alacağam"));
        EditText principal=input("Ümumi məbləğ",true);
        EditText due=input("Ödəniş tarixi (istəyə bağlı, YYYY-MM-DD)",false);
        box.addView(name); box.addView(direction); box.addView(principal); box.addView(due);
        box.addView(tv("Tarix boş qalsa borc tarixsiz yaradılacaq. Aylıq cədvəl yaradılmır.",12,MUTED,false));
        new AlertDialog.Builder(this).setTitle("Birdəfəlik borc / alacaq").setView(box).setNegativeButton("Ləğv et",null).setPositiveButton("Yarat",(d,w)->{
            double p=parseAmount(principal.getText().toString());
            String dueText=due.getText().toString().trim();
            if(name.getText().toString().trim().isEmpty()||p<=0||(!dueText.isEmpty()&&!validDate(dueText))){toast("Ad və məbləği düzgün doldur.");return;}
            String dir=direction.getSelectedItemPosition()==0?"PAYABLE":"RECEIVABLE";
            db.addSimpleDebt(name.getText().toString(),dir,p,dueText);
            scheduleAllOpen(this);
            showDebts();
        }).show();
    }

    private void showPayDebtDialog(long debtId, String name, double remaining, double monthly) {'''

main = replace_once(
    main,
    r'''    private void showAddDebtDialog\(\) \{.*?    private void showPayDebtDialog\(long debtId, String name, double remaining, double monthly\) \{''',
    add_debt_replacement,
    "Add debt dialog"
)

# --- Debt payment: payment date is optional ---
pay_debt_replacement = r'''    private void showPayDebtDialog(long debtId, String name, double remaining, double monthly) {
        if(remaining<=0.005){toast("Bu borc artıq bağlanıb.");return;}
        LinearLayout box=vertical(); box.setPadding(dp(18),dp(8),dp(18),0);
        EditText amount=input("Ödəniş məbləği",true);
        amount.setText(String.format(Locale.US,"%.2f",Math.min(remaining,monthly)));
        EditText date=input("Ödəniş tarixi (istəyə bağlı — boşdursa bu gün)",false);
        box.addView(amount);box.addView(date);
        new AlertDialog.Builder(this).setTitle(name+" — ödəniş").setView(box).setNegativeButton("Ləğv et",null).setPositiveButton("Ödə",(d,w)->{
            double a=parseAmount(amount.getText().toString());
            String rawDate=date.getText().toString().trim();
            String dt=rawDate.isEmpty()?LocalDate.now().toString():rawDate;
            if(a<=0||!validDate(dt)){toast("Məbləği düzgün daxil et.");return;}
            double paid=db.payDebt(debtId,a,dt);
            toast("Ödənildi: "+azn(paid));
            scheduleAllOpen(this);
            showDebts();
        }).show();
    }

    private void showDebtScheduleDialog(long debtId, String name) {'''

main = replace_once(
    main,
    r'''    private void showPayDebtDialog\(long debtId, String name, double remaining, double monthly\) \{.*?    private void showDebtScheduleDialog\(long debtId, String name\) \{''',
    pay_debt_replacement,
    "Pay debt dialog"
)

MAIN.write_text(main, encoding="utf-8")
DB.write_text(db, encoding="utf-8")
print("Applied Büdcəm v1.1 patch: edit/delete transactions, one-time debts, optional dates")
