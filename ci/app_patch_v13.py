from pathlib import Path
import re

MAIN = Path("app/src/main/java/az/budcem/premium/MainActivity.java")
DB = Path("app/src/main/java/az/budcem/premium/BudgetDb.java")

main = MAIN.read_text(encoding="utf-8")
db = DB.read_text(encoding="utf-8")

def replace_once(text, pattern, replacement, label):
    updated, count = re.subn(pattern, lambda m: replacement, text, count=1, flags=re.S)
    if count != 1:
        raise SystemExit(f"{label}: patch target expected once, found {count}")
    return updated

def exact_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: exact target expected once, found {count}")
    return text.replace(old, new, 1)

# ---------- Imports and screen state ----------
if "import android.app.DatePickerDialog;" not in main:
    main = exact_once(main, "import android.app.AlertDialog;\n", "import android.app.AlertDialog;\nimport android.app.DatePickerDialog;\n", "DatePickerDialog import")

main = exact_once(
    main,
    "    private BudgetDb db;\n",
    '''    private BudgetDb db;
    private String txFilterFrom = "";
    private String txFilterTo = "";
    private String ledgerFilterFrom = "";
    private String ledgerFilterTo = "";
''',
    "Filter state"
)

# ---------- Database query/update helpers ----------
db = replace_once(
    db,
    r'''    public Cursor allCategories\(\) \{.*?    \}\n\n    public long addTransaction''',
    r'''    public Cursor allCategories() {
        return getReadableDatabase().rawQuery(
                "SELECT c.id AS _id,c.name,c.kind,c.parent_id,CASE WHEN p.name IS NULL THEN c.name ELSE p.name || ' › ' || c.name END AS label " +
                        "FROM categories c LEFT JOIN categories p ON p.id=c.parent_id ORDER BY c.kind,c.parent_id,label",
                null);
    }

    public void updateCategory(long id, String name, long parentId, String kind) {
        ContentValues v = new ContentValues();
        v.put("name", name == null ? "" : name.trim());
        v.put("parent_id", Math.max(0, parentId));
        v.put("kind", kind);
        getWritableDatabase().update("categories", v, "id=?", new String[]{String.valueOf(id)});
    }

    public Cursor transactionsBetween(String fromDate, String toDate, boolean ascending) {
        String from = (fromDate == null || fromDate.isEmpty()) ? "0001-01-01" : fromDate;
        String to = (toDate == null || toDate.isEmpty()) ? "9999-12-31" : toDate;
        return getReadableDatabase().rawQuery(
                "SELECT t.id AS _id,t.kind,t.category_id,t.amount,t.period,t.date,t.note,t.debt_id," +
                        "COALESCE(c.name,'Borc / Kredit') AS category " +
                        "FROM transactions t LEFT JOIN categories c ON c.id=t.category_id " +
                        "WHERE t.date>=? AND t.date<=? ORDER BY t.date " + (ascending ? "ASC" : "DESC") + ",t.id " + (ascending ? "ASC" : "DESC"),
                new String[]{from, to});
    }

    public double balanceBefore(String date) {
        String d = (date == null || date.isEmpty()) ? "0001-01-01" : date;
        try (Cursor c = getReadableDatabase().rawQuery(
                "SELECT COALESCE(SUM(CASE WHEN kind='INCOME' THEN amount ELSE -amount END),0) FROM transactions WHERE date<?",
                new String[]{d})) {
            return c.moveToFirst() ? c.getDouble(0) : 0;
        }
    }

    public double sumBetween(String kind, String fromDate, String toDate) {
        String from = (fromDate == null || fromDate.isEmpty()) ? "0001-01-01" : fromDate;
        String to = (toDate == null || toDate.isEmpty()) ? "9999-12-31" : toDate;
        try (Cursor c = getReadableDatabase().rawQuery(
                "SELECT COALESCE(SUM(amount),0) FROM transactions WHERE kind=? AND date>=? AND date<=?",
                new String[]{kind, from, to})) {
            return c.moveToFirst() ? c.getDouble(0) : 0;
        }
    }

    public long addTransaction''',
    "DB category/filter helpers"
)

# ---------- Generic date picker + table helpers ----------
helpers = r'''    private EditText datePickerInput(String hint, String initial, boolean allowEmpty) {
        EditText e = input(hint, false);
        e.setFocusable(false);
        e.setClickable(true);
        e.setCursorVisible(false);
        if (initial != null && !initial.trim().isEmpty()) e.setText(initial.trim());

        e.setOnClickListener(v -> {
            LocalDate base = LocalDate.now();
            String current = e.getText().toString().trim();
            if (!current.isEmpty()) {
                try { base = LocalDate.parse(current); } catch (Exception ignored) {}
            }
            LocalDate finalBase = base;
            DatePickerDialog dlg = new DatePickerDialog(
                    this,
                    (view, year, month, day) -> e.setText(LocalDate.of(year, month + 1, day).toString()),
                    finalBase.getYear(), finalBase.getMonthValue() - 1, finalBase.getDayOfMonth()
            );
            if (allowEmpty) {
                dlg.setButton(DatePickerDialog.BUTTON_NEUTRAL, "Tarixi sil", (dialog, which) -> e.setText(""));
            }
            dlg.show();
        });
        return e;
    }

    private TextView tableCell(String text, int widthDp, boolean header, int color) {
        TextView v = tv(text, header ? 12 : 12, color, header);
        v.setGravity(Gravity.CENTER_VERTICAL);
        v.setPadding(dp(9), dp(9), dp(9), dp(9));
        v.setBackground(outlined(header ? PURPLE_SOFT : WHITE, 8, Color.rgb(230,226,220)));
        v.setLayoutParams(new LinearLayout.LayoutParams(dp(widthDp), ViewGroup.LayoutParams.WRAP_CONTENT));
        return v;
    }

    private LinearLayout tableRow() {
        LinearLayout r = new LinearLayout(this);
        r.setOrientation(LinearLayout.HORIZONTAL);
        r.setGravity(Gravity.CENTER_VERTICAL);
        return r;
    }

    private android.widget.HorizontalScrollView horizontalTable(LinearLayout table) {
        android.widget.HorizontalScrollView hs = new android.widget.HorizontalScrollView(this);
        hs.setFillViewport(false);
        hs.addView(table);
        return hs;
    }

'''
main = exact_once(main, "    private EditText input(String hint, boolean numeric) {", helpers + "    private EditText input(String hint, boolean numeric) {", "UI helpers")

# ---------- Category editing ----------
categories_replacement = r'''    private void showCategories() {
        LinearLayout body = vertical();
        LinearLayout top = card(WHITE);
        top.addView(tv("Üst / alt kateqoriya", 17, INK, true));
        top.addView(tv("Kateqoriyaya toxunmadan da sağdakı Redaktə düyməsi ilə adını, növünü və üst kateqoriyasını dəyişə bilərsən.", 12, MUTED, false));
        LinearLayout rr = new LinearLayout(this); rr.setOrientation(LinearLayout.HORIZONTAL);
        rr.setPadding(0, dp(10), 0, 0);
        rr.addView(actionButton("+ Üst", YELLOW, INK, v -> showAddParentCategoryDialog()), new LinearLayout.LayoutParams(0,dp(46),1));
        LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(0,dp(46),1); p.setMargins(dp(8),0,0,0);
        rr.addView(actionButton("+ Alt", PURPLE_SOFT, PURPLE, v -> showAddChildCategoryDialog()), p);
        top.addView(rr);
        body.addView(top);

        LinearLayout list = card(WHITE);
        list.addView(tv("Kateqoriyalar", 17, INK, true));
        try (Cursor c = db.allCategories()) {
            while (c.moveToNext()) {
                long id = c.getLong(c.getColumnIndexOrThrow("_id"));
                String rawName = c.getString(c.getColumnIndexOrThrow("name"));
                String kind = c.getString(c.getColumnIndexOrThrow("kind"));
                long parentId = c.getLong(c.getColumnIndexOrThrow("parent_id"));
                String label = c.getString(c.getColumnIndexOrThrow("label"));

                LinearLayout row = new LinearLayout(this);
                row.setOrientation(LinearLayout.HORIZONTAL);
                row.setGravity(Gravity.CENTER_VERTICAL);
                row.setPadding(0, dp(7), 0, dp(7));

                String kindLabel = "INCOME".equals(kind) ? "GƏLİR" : "XƏRC";
                TextView item = tv(kindLabel + "   " + label, 14, INK, false);
                row.addView(item, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));

                Button edit = actionButton("Redaktə", PURPLE_SOFT, PURPLE,
                        v -> showEditCategoryDialog(id, rawName, kind, parentId));
                row.addView(edit, new LinearLayout.LayoutParams(dp(100), dp(40)));
                list.addView(row);
            }
        }
        body.addView(list);
        render("Kateqoriyalar", body, 1);
    }

    private void showEditCategoryDialog(long id, String oldName, String oldKind, long oldParentId) {
        LinearLayout box = vertical();
        box.setPadding(dp(18),dp(8),dp(18),0);

        EditText name = input("Kateqoriya adı", false);
        name.setText(oldName);
        Spinner kind = spinner(List.of("Xərc", "Gəlir"));
        kind.setSelection("INCOME".equals(oldKind) ? 1 : 0);

        List<Choice> initialParents = editableParentChoices(oldKind, id);
        Spinner parent = spinner(initialParents);
        for (int i=0;i<initialParents.size();i++) {
            if (initialParents.get(i).id == oldParentId) parent.setSelection(i);
        }

        kind.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
            @Override public void onItemSelected(AdapterView<?> p, View v, int pos, long ignored) {
                String k = pos == 0 ? "EXPENSE" : "INCOME";
                List<Choice> fresh = editableParentChoices(k, id);
                ArrayAdapter<Choice> aa = new ArrayAdapter<>(MainActivity.this, android.R.layout.simple_spinner_dropdown_item, fresh);
                parent.setAdapter(aa);
                for (int i=0;i<fresh.size();i++) if (fresh.get(i).id == oldParentId) parent.setSelection(i);
            }
            @Override public void onNothingSelected(AdapterView<?> p) {}
        });

        box.addView(name);
        box.addView(tv("Növ",12,MUTED,true)); box.addView(kind);
        box.addView(tv("Üst kateqoriya",12,MUTED,true)); box.addView(parent);

        new AlertDialog.Builder(this)
                .setTitle("Kateqoriyanı redaktə et")
                .setView(box)
                .setNegativeButton("Ləğv et", null)
                .setPositiveButton("Yadda saxla", (d,w) -> {
                    String n = name.getText().toString().trim();
                    Choice pc = (Choice) parent.getSelectedItem();
                    if (n.isEmpty() || pc == null) { toast("Kateqoriya adı boş ola bilməz."); return; }
                    String k = kind.getSelectedItemPosition() == 0 ? "EXPENSE" : "INCOME";
                    db.updateCategory(id, n, pc.id, k);
                    showCategories();
                }).show();
    }

    private List<Choice> editableParentChoices(String kind, long categoryId) {
        List<Choice> out = new ArrayList<>();
        out.add(new Choice(0, "Üst kateqoriya yoxdur"));
        for (Choice c : parentChoices(kind)) if (c.id != categoryId) out.add(c);
        return out;
    }

    private EditText input(String hint, boolean numeric) {'''
main = replace_once(
    main,
    r'''    private void showCategories\(\) \{.*?    private EditText input\(String hint, boolean numeric\) \{''',
    categories_replacement,
    "Categories edit UI"
)

# Reinsert helpers lost because category block replacement consumes up to input.
main = exact_once(main, "    private EditText input(String hint, boolean numeric) {", helpers + "    private EditText input(String hint, boolean numeric) {", "Restore UI helpers after categories")

# ---------- Transactions with date filter and pending income ----------
transactions_replacement = r'''    private void showTransactions() {
        LinearLayout body = vertical();

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

        LinearLayout filter = card(WHITE);
        filter.addView(tv("Tarix filtri", 17, INK, true));
        filter.addView(tv("Başlanğıc və son tarixi seç. Hər ikisi boşdursa bütün əməliyyatlar göstərilir.", 12, MUTED, false));

        EditText from = datePickerInput("Başlanğıc tarix", txFilterFrom, true);
        EditText to = datePickerInput("Son tarix", txFilterTo, true);
        filter.addView(from);
        filter.addView(to);

        LinearLayout fr = new LinearLayout(this); fr.setOrientation(LinearLayout.HORIZONTAL); fr.setPadding(0,dp(8),0,0);
        Button apply = actionButton("Filtri tətbiq et", PURPLE, WHITE, v -> {
            String f = from.getText().toString().trim();
            String t = to.getText().toString().trim();
            if ((!f.isEmpty() && !validDate(f)) || (!t.isEmpty() && !validDate(t)) || (!f.isEmpty() && !t.isEmpty() && f.compareTo(t) > 0)) {
                toast("Tarix aralığını yoxla."); return;
            }
            txFilterFrom = f;
            txFilterTo = t;
            showTransactions();
        });
        Button clear = actionButton("Təmizlə", PURPLE_SOFT, PURPLE, v -> {
            txFilterFrom = "";
            txFilterTo = "";
            showTransactions();
        });
        fr.addView(apply,new LinearLayout.LayoutParams(0,dp(44),1));
        LinearLayout.LayoutParams clp=new LinearLayout.LayoutParams(0,dp(44),1); clp.setMargins(dp(8),0,0,0); fr.addView(clear,clp);
        filter.addView(fr);
        body.addView(filter);

        String reportFrom = txFilterFrom.isEmpty() ? "0001-01-01" : txFilterFrom;
        String reportTo = txFilterTo.isEmpty() ? "9999-12-31" : txFilterTo;
        double filterIncome = db.sumBetween("INCOME", reportFrom, reportTo);
        double filterExpense = db.sumBetween("EXPENSE", reportFrom, reportTo);

        LinearLayout summary = card(YELLOW_SOFT);
        summary.addView(tv(txFilterFrom.isEmpty() && txFilterTo.isEmpty() ? "Seçilmiş bütün dövr" : "Seçilmiş tarix aralığı", 13, MUTED, false));
        summary.addView(tv("Gəlir " + azn(filterIncome) + "   •   Xərc " + azn(filterExpense) + "   •   Fərq " + azn(filterIncome-filterExpense), 15, INK, true));
        body.addView(summary);

        LinearLayout pending = card(Color.rgb(226,246,255));
        pending.addView(tv("Yolda olan vəsaitlər", 17, INK, true));
        pending.addView(tv("Cəmi: " + azn(db.totalPendingIncome()) + " — faktiki gəlirə daxil deyil", 12, MUTED, false));
        int pendingCount = 0;
        try (Cursor c = db.pendingIncomes()) {
            while (c.moveToNext()) {
                pendingCount++;
                long id = c.getLong(c.getColumnIndexOrThrow("_id"));
                long categoryId = c.getLong(c.getColumnIndexOrThrow("category_id"));
                double amount = c.getDouble(c.getColumnIndexOrThrow("amount"));
                String expected = c.isNull(c.getColumnIndexOrThrow("expected_date")) ? "" : c.getString(c.getColumnIndexOrThrow("expected_date"));
                String note = c.getString(c.getColumnIndexOrThrow("note"));
                String category = c.getString(c.getColumnIndexOrThrow("category"));

                LinearLayout item = vertical();
                item.setPadding(0, dp(10), 0, dp(8));
                LinearLayout rr = new LinearLayout(this);
                rr.setOrientation(LinearLayout.HORIZONTAL);
                rr.setGravity(Gravity.CENTER_VERTICAL);
                String info = category + (expected.isEmpty() ? " • tarix yoxdur" : " • gözlənilir: " + expected) +
                        (note == null || note.isEmpty() ? "" : "\n" + note);
                rr.addView(tv(info, 13, INK, false), new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
                rr.addView(tv("+ " + azn(amount), 14, PURPLE, true));
                item.addView(rr);

                LinearLayout actions = new LinearLayout(this);
                actions.setOrientation(LinearLayout.HORIZONTAL);
                actions.setPadding(0, dp(7), 0, 0);
                Button receive = actionButton("Daxil oldu", GREEN, WHITE, v -> showReceivePendingDialog(id, amount));
                Button edit = actionButton("Redaktə", PURPLE_SOFT, PURPLE, v -> showEditPendingIncomeDialog(id, categoryId, amount, expected, note));
                Button del = actionButton("Sil", Color.rgb(255,235,226), RED, v -> confirmDeletePendingIncome(id));
                actions.addView(receive, new LinearLayout.LayoutParams(0, dp(40), 1));
                LinearLayout.LayoutParams ep = new LinearLayout.LayoutParams(0, dp(40), 1); ep.setMargins(dp(6),0,dp(6),0);
                actions.addView(edit, ep);
                actions.addView(del, new LinearLayout.LayoutParams(0, dp(40), 1));
                item.addView(actions);
                pending.addView(item);
            }
        }
        if (pendingCount == 0) {
            TextView e = tv("Yolda olan vəsait yoxdur.", 13, MUTED, false); e.setPadding(0,dp(10),0,0); pending.addView(e);
        }
        body.addView(pending);

        LinearLayout list = card(WHITE);
        list.addView(tv("Əməliyyatlar", 17, INK, true));
        int n = 0;
        try (Cursor c = db.transactionsBetween(reportFrom, reportTo, false)) {
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

                LinearLayout item = vertical();
                item.setPadding(0, dp(9), 0, dp(9));
                LinearLayout rr = new LinearLayout(this);
                rr.setOrientation(LinearLayout.HORIZONTAL);
                rr.setGravity(Gravity.CENTER_VERTICAL);
                String source = debtId > 0 ? ("Kredit ödənişi".equals(period) ? "Kredit ödənişi" : "Borc ödənişi") : category;
                String sub = date + " • " + source + (note == null || note.isEmpty() ? "" : "\n" + note);
                rr.addView(tv(sub, 13, INK, false), new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
                rr.addView(tv(("INCOME".equals(kind) ? "+ " : "− ") + azn(amount), 14, "INCOME".equals(kind) ? GREEN : RED, true));
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
            }
        }
        if (n == 0) {
            TextView e = tv("Bu tarix aralığında əməliyyat yoxdur.", 13, MUTED, false); e.setPadding(0,dp(12),0,0); list.addView(e);
        }
        body.addView(list);
        render("Gəlir və xərclər", body, 1);
    }

    private void showReceivePendingDialog(long pendingId, double amount) {
        LinearLayout box = vertical(); box.setPadding(dp(18),dp(8),dp(18),0);
        box.addView(tv("Daxil olan məbləğ: " + azn(amount), 14, INK, true));
        EditText date = datePickerInput("Daxilolma tarixi", LocalDate.now().toString(), false);
        box.addView(date);
        new AlertDialog.Builder(this).setTitle("Vəsait daxil oldu")
                .setView(box).setNegativeButton("Ləğv et", null)
                .setPositiveButton("Gəlirə keçir", (d,w) -> {
                    String dt = date.getText().toString().trim();
                    if (!validDate(dt)) { toast("Tarix düzgün deyil."); return; }
                    if (db.receivePendingIncome(pendingId, dt)) toast("Vəsait faktiki gəlirə keçirildi.");
                    showTransactions();
                }).show();
    }

    private void showEditPendingIncomeDialog(long id, long categoryId, double oldAmount, String oldExpected, String oldNote) {
        LinearLayout box = vertical(); box.setPadding(dp(18),dp(8),dp(18),0);
        List<Choice> cats = categoryChoices("INCOME");
        Spinner cat = spinner(cats);
        for (int i=0;i<cats.size();i++) if (cats.get(i).id == categoryId) cat.setSelection(i);
        EditText amount = input("Məbləğ", true); amount.setText(String.format(Locale.US,"%.2f",oldAmount));
        EditText expected = datePickerInput("Gözlənilən tarix", oldExpected, true);
        EditText note = input("Qeyd", false); note.setText(oldNote == null ? "" : oldNote);
        box.addView(tv("Kateqoriya",12,MUTED,true)); box.addView(cat); box.addView(amount); box.addView(expected); box.addView(note);
        new AlertDialog.Builder(this).setTitle("Yolda olan vəsaiti redaktə et").setView(box)
                .setNegativeButton("Ləğv et",null)
                .setPositiveButton("Yadda saxla",(d,w)->{
                    double a=parseAmount(amount.getText().toString());
                    String ex=expected.getText().toString().trim();
                    if(a<=0||(!ex.isEmpty()&&!validDate(ex))){toast("Məbləğ və tarixi yoxla.");return;}
                    Choice cc=(Choice)cat.getSelectedItem();
                    db.updatePendingIncome(id,cc.id,a,ex,note.getText().toString());
                    showTransactions();
                }).show();
    }

    private void confirmDeletePendingIncome(long id) {
        new AlertDialog.Builder(this).setTitle("Yolda olan vəsait silinsin?")
                .setMessage("Bu məbləğ faktiki gəlir olmadığı üçün balansdan heç nə çıxılmayacaq.")
                .setNegativeButton("Ləğv et",null)
                .setPositiveButton("Sil",(d,w)->{db.deletePendingIncome(id);showTransactions();}).show();
    }

    private void showEditTransactionDialog(long txId, String kind, long categoryId, double oldAmount,
'''
main = replace_once(
    main,
    r'''    private void showTransactions\(\) \{.*?    private void showEditTransactionDialog\(long txId, String kind, long categoryId, double oldAmount,\n''',
    transactions_replacement,
    "Transactions date filter"
)

# Make edit transaction date selectable.
main = exact_once(
    main,
    '        EditText date = input("Tarix (istəyə bağlı — boşdursa bu gün)", false);\n        date.setText(oldDate == null ? "" : oldDate);',
    '        EditText date = datePickerInput("Tarix", oldDate == null ? LocalDate.now().toString() : oldDate, false);',
    "Edit transaction date picker"
)

# ---------- New transaction uses date picker ----------
transaction_dialog = r'''    private void showTransactionDialog(String kind) {
        LinearLayout box = vertical(); box.setPadding(dp(18),dp(8),dp(18),0);
        List<Choice> cats = categoryChoices(kind);
        if (cats.isEmpty()) { toast("Əvvəl kateqoriya yarat."); showCategories(); return; }

        Spinner cat = spinner(cats);
        EditText amount = input("Məbləğ", true);
        EditText date = datePickerInput("Tarix", LocalDate.now().toString(), false);
        List<String> periods = List.of("Birdəfəlik", "Həftəlik", "Aylıq", "İllik");
        Spinner period = spinner(periods);
        EditText note = input("Qeyd (istəyə bağlı)", false);

        box.addView(tv("Kateqoriya",12,MUTED,true));
        box.addView(cat);
        box.addView(amount);

        Spinner incomeStatus = null;
        Spinner obligation = null;
        Spinner debtSpinner = null;

        if ("INCOME".equals(kind)) {
            box.addView(tv("Vəsaitin statusu",12,MUTED,true));
            incomeStatus = spinner(List.of("Daxil olub", "Yolda olan vəsait"));
            box.addView(incomeStatus);
        }

        box.addView(date);
        box.addView(period);
        box.addView(note);

        if ("EXPENSE".equals(kind)) {
            box.addView(tv("Xərc növü",12,MUTED,true));
            obligation = spinner(List.of("Adi xərc", "Borc ödənişi"));
            box.addView(obligation);

            List<Choice> debts = debtChoices("PAYABLE");
            List<Choice> withNone = new ArrayList<>();
            withNone.add(new Choice(0,"Borc seç"));
            withNone.addAll(debts);
            debtSpinner = spinner(withNone);
            box.addView(debtSpinner);

            Spinner finalDebtSpinner = debtSpinner;
            obligation.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
                @Override public void onItemSelected(AdapterView<?> parent, View view, int position, long id) {
                    finalDebtSpinner.setVisibility(position == 1 ? View.VISIBLE : View.GONE);
                }
                @Override public void onNothingSelected(AdapterView<?> parent) {}
            });
            debtSpinner.setVisibility(View.GONE);
        }

        final Spinner fIncomeStatus = incomeStatus;
        final Spinner fObligation = obligation;
        final Spinner fDebtSpinner = debtSpinner;

        new AlertDialog.Builder(this)
                .setTitle("INCOME".equals(kind) ? "Gəlir əlavə et" : "Xərc əlavə et")
                .setView(box)
                .setNegativeButton("Ləğv et", null)
                .setPositiveButton("Yadda saxla", (d,w) -> {
                    double a = parseAmount(amount.getText().toString());
                    if (a <= 0) { toast("Məbləği düzgün daxil et."); return; }

                    String selectedDate = date.getText().toString().trim();
                    if (!validDate(selectedDate)) { toast("Tarixi seç."); return; }

                    Choice cc = (Choice)cat.getSelectedItem();
                    String per = String.valueOf(period.getSelectedItem());

                    if ("INCOME".equals(kind) && fIncomeStatus != null && fIncomeStatus.getSelectedItemPosition() == 1) {
                        db.addPendingIncome(cc.id, a, selectedDate, note.getText().toString());
                        toast("Yolda olan vəsait kimi ayrıldı. Faktiki gəlirə daxil edilmədi.");
                    } else if ("EXPENSE".equals(kind) && fObligation != null && fObligation.getSelectedItemPosition() == 1) {
                        Choice debtChoice = (Choice)fDebtSpinner.getSelectedItem();
                        if (debtChoice == null || debtChoice.id == 0) { toast("Borc seçilməyib."); return; }
                        db.payDebt(debtChoice.id, a, selectedDate);
                    } else {
                        db.addTransaction(kind, cc.id, a, per, selectedDate, note.getText().toString(), 0);
                    }
                    scheduleAllOpen(this);
                    showTransactions();
                }).show();
    }

    private void showAddParentCategoryDialog() {'''
main = replace_once(
    main,
    r'''    private void showTransactionDialog\(String kind\) \{.*?    private void showAddParentCategoryDialog\(\) \{''',
    transaction_dialog,
    "Transaction date picker"
)

# Budget movement date selection.
main = exact_once(
    main,
    '        EditText amount=input("Əlavə ediləcək məbləğ",true); EditText date=input("Tarix",false); date.setText(LocalDate.now().toString()); box.addView(amount); box.addView(date);',
    '        EditText amount=input("Əlavə ediləcək məbləğ",true); EditText date=datePickerInput("Tarix",LocalDate.now().toString(),false); box.addView(amount); box.addView(date);',
    "Budget date picker"
)

# Credit first due date and credit payment date selection.
main = exact_once(
    main,
    '        EditText first=input("İlk ödəniş tarixi (YYYY-MM-DD)",false);\n        first.setText(LocalDate.now().plusMonths(1).toString());',
    '        EditText first=datePickerInput("İlk ödəniş tarixi",LocalDate.now().plusMonths(1).toString(),false);',
    "Credit first due date"
)
main = exact_once(
    main,
    '        EditText date=input("Ödəniş tarixi (boşdursa bu gün)",false);',
    '        EditText date=datePickerInput("Ödəniş tarixi",LocalDate.now().toString(),false);',
    "Credit payment date"
)

# ---------- Debt and credit tables ----------
debts_replacement = r'''    private void showDebts() {
        LinearLayout body = vertical();

        LinearLayout top = card(PURPLE_SOFT);
        top.addView(tv("Borc və kreditlər", 18, INK, true));
        top.addView(tv("Birdəfəlik borc və aylıq kredit planı ayrı cədvəllərdə göstərilir.", 13, MUTED, false));
        LinearLayout buttons = new LinearLayout(this); buttons.setOrientation(LinearLayout.HORIZONTAL);
        Button debtAdd = actionButton("+ Borc", Color.rgb(255,235,226), RED, v -> showAddDebtDialog());
        Button creditAdd = actionButton("+ Kredit", PURPLE, WHITE, v -> showAddCreditDialog());
        buttons.addView(debtAdd, new LinearLayout.LayoutParams(0,dp(48),1));
        LinearLayout.LayoutParams cp = new LinearLayout.LayoutParams(0,dp(48),1); cp.setMargins(dp(8),0,0,0);
        buttons.addView(creditAdd, cp);
        LinearLayout.LayoutParams bp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(48)); bp.setMargins(0,dp(12),0,0);
        top.addView(buttons,bp);
        body.addView(top);

        LinearLayout simpleCard = card(WHITE);
        simpleCard.addView(tv("Birdəfəlik borclar", 17, INK, true));
        simpleCard.addView(tv("Verəcəyim: " + azn(db.totalDebtRemainingByType("SIMPLE","PAYABLE")) +
                "   •   Alacağım: " + azn(db.totalDebtRemainingByType("SIMPLE","RECEIVABLE")), 13, MUTED, false));
        simpleCard.addView(tv("Ödəniş: Əməliyyatlar → Xərc → Borc ödənişi → şəxsi seç.", 12, PURPLE, true));

        LinearLayout simpleTable = vertical();
        LinearLayout sh = tableRow();
        sh.addView(tableCell("Ad",150,true,INK));
        sh.addView(tableCell("Növ",105,true,INK));
        sh.addView(tableCell("İlkin",105,true,INK));
        sh.addView(tableCell("Ödənib",105,true,INK));
        sh.addView(tableCell("Qalıq",105,true,INK));
        simpleTable.addView(sh);

        int simpleCount=0;
        try(Cursor c=db.debtsByType("SIMPLE")){
            while(c.moveToNext()){
                simpleCount++;
                String name=c.getString(c.getColumnIndexOrThrow("name"));
                String dir=c.getString(c.getColumnIndexOrThrow("direction"));
                double principal=c.getDouble(c.getColumnIndexOrThrow("principal"));
                double remaining=c.getDouble(c.getColumnIndexOrThrow("remaining"));
                LinearLayout tr=tableRow();
                tr.addView(tableCell(name,150,false,INK));
                tr.addView(tableCell("PAYABLE".equals(dir)?"Verəcəyim":"Alacağım",105,false,"PAYABLE".equals(dir)?RED:GREEN));
                tr.addView(tableCell(azn(principal),105,false,INK));
                tr.addView(tableCell(azn(Math.max(0,principal-remaining)),105,false,GREEN));
                tr.addView(tableCell(azn(remaining),105,false,remaining>0.005?RED:GREEN));
                simpleTable.addView(tr);
            }
        }
        if(simpleCount==0){
            LinearLayout tr=tableRow(); tr.addView(tableCell("Birdəfəlik borc yoxdur.",570,false,MUTED)); simpleTable.addView(tr);
        }
        simpleCard.addView(horizontalTable(simpleTable));
        body.addView(simpleCard);

        LinearLayout creditCard = card(WHITE);
        creditCard.addView(tv("Kreditlər",17,INK,true));
        creditCard.addView(tv("Kredit qalığı: " + azn(db.totalDebtRemainingByType("CREDIT","PAYABLE")),13,PURPLE,true));
        creditCard.addView(tv("Kredit sətrinə toxunaraq aylıq ödəniş cədvəlini aç.",12,MUTED,false));

        LinearLayout creditTable=vertical();
        LinearLayout ch=tableRow();
        ch.addView(tableCell("Kredit",150,true,INK));
        ch.addView(tableCell("Ümumi",105,true,INK));
        ch.addView(tableCell("Aylıq",105,true,INK));
        ch.addView(tableCell("Qalıq",105,true,INK));
        ch.addView(tableCell("Növbəti tarix",125,true,INK));
        creditTable.addView(ch);

        int creditCount=0;
        try(Cursor c=db.debtsByType("CREDIT")){
            while(c.moveToNext()){
                creditCount++;
                long id=c.getLong(c.getColumnIndexOrThrow("_id"));
                String name=c.getString(c.getColumnIndexOrThrow("name"));
                double principal=c.getDouble(c.getColumnIndexOrThrow("principal"));
                double remaining=c.getDouble(c.getColumnIndexOrThrow("remaining"));
                double monthly=c.getDouble(c.getColumnIndexOrThrow("monthly"));
                String nextDue=c.isNull(c.getColumnIndexOrThrow("next_due"))?"Bağlanıb":c.getString(c.getColumnIndexOrThrow("next_due"));

                LinearLayout tr=tableRow();
                tr.setOnClickListener(v->showDebtScheduleDialog(id,name));
                tr.addView(tableCell(name,150,false,PURPLE));
                tr.addView(tableCell(azn(principal),105,false,INK));
                tr.addView(tableCell(azn(monthly),105,false,INK));
                tr.addView(tableCell(azn(remaining),105,false,remaining>0.005?RED:GREEN));
                tr.addView(tableCell(nextDue,125,false,MUTED));
                creditTable.addView(tr);
            }
        }
        if(creditCount==0){
            LinearLayout tr=tableRow(); tr.addView(tableCell("Kredit yoxdur.",590,false,MUTED)); creditTable.addView(tr);
        }
        creditCard.addView(horizontalTable(creditTable));
        body.addView(creditCard);

        render("Borclarım", body, 3);
    }

    private void showAnalysis() {'''
main = replace_once(
    main,
    r'''    private void showDebts\(\) \{.*?    private void showAnalysis\(\) \{''',
    debts_replacement,
    "Debt/credit tables"
)

# ---------- Analysis + CR/DR ledger report ----------
analysis_replacement = r'''    private void showAnalysis() {
        LinearLayout body = vertical();
        String month = LocalDate.now().format(DateTimeFormatter.ofPattern("yyyy-MM"));
        double inc = db.sumTransactions("INCOME", month);
        double exp = db.sumTransactions("EXPENSE", month);
        double pendingTotal = db.totalPendingIncome();
        double pendingMonth = db.pendingIncomeForMonth(month);
        double savedMonth = db.monthBudgetMoves(month);
        double debtPaid = db.sumDebtTransactions(month);
        double net = inc - exp;
        double savingsRate = inc > 0 ? savedMonth * 100 / inc : 0;
        double expenseRate = inc > 0 ? exp * 100 / inc : 0;
        double debtBurden = inc > 0 ? debtPaid * 100 / inc : 0;

        LinearLayout report = card(WHITE);
        report.addView(tv("CR / DR Balans hesabatı",17,INK,true));
        report.addView(tv("Gəlir = CR, Xərc = DR. Hər əməliyyatdan sonra qalan balansı gör.",12,MUTED,false));
        Button openLedger = actionButton("CR / DR hesabatını aç", PURPLE, WHITE, v -> {
            if (ledgerFilterFrom.isEmpty()) ledgerFilterFrom = LocalDate.now().withDayOfMonth(1).toString();
            if (ledgerFilterTo.isEmpty()) ledgerFilterTo = LocalDate.now().toString();
            showLedgerReport();
        });
        LinearLayout.LayoutParams rlp=new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,dp(46)); rlp.setMargins(0,dp(10),0,0);
        report.addView(openLedger,rlp);
        body.addView(report);

        LinearLayout hero = card(PURPLE);
        hero.addView(tv("Aylıq faktiki nəticə", 13, Color.rgb(235,231,255), false));
        hero.addView(tv(azn(net), 30, WHITE, true));
        hero.addView(tv("Yolda olan vəsait bu nəticəyə daxil deyil.", 13, WHITE, false));
        body.addView(hero);

        LinearLayout pendingCard = card(Color.rgb(226,246,255));
        pendingCard.addView(tv("Yolda olan vəsaitlər",17,INK,true));
        pendingCard.addView(tv("Cəmi " + azn(pendingTotal) + "   •   Bu aya gözlənilən " + azn(pendingMonth),14,PURPLE,true));
        pendingCard.addView(tv("Potensial məbləğdir; daxil olana qədər gəlir hesab edilmir.",12,MUTED,false));
        body.addView(pendingCard);

        LinearLayout rates = card(WHITE);
        rates.addView(tv("Əsas göstəricilər", 17, INK, true));
        rates.addView(analysisLine("Xərc / faktiki gəlir", Math.round(expenseRate) + "%", expenseRate <= 80 ? GREEN : RED));
        rates.addView(analysisLine("Yığıma ayrılan", Math.round(savingsRate) + "%", PURPLE));
        rates.addView(analysisLine("Borc + kredit ödəniş yükü", Math.round(debtBurden) + "%", debtBurden <= 30 ? GREEN : RED));
        rates.addView(analysisLine("Ən böyük xərc kateqoriyası", db.topExpenseCategory(month) + " ₼", INK));
        body.addView(rates);

        LinearLayout insight = card(YELLOW_SOFT);
        insight.addView(tv("Ağıllı ay təhlili", 17, INK, true));
        List<String> tips = new ArrayList<>();
        if (inc <= 0) tips.add("Faktiki gəlir əlavə etdikdə ayın real yük və qənaət faizləri görünəcək.");
        else {
            if (expenseRate > 100) tips.add("Xərc faktiki gəliri keçib. Yolda olan vəsaiti gələnə qədər bu fərqi bağlanmış hesab etmirik.");
            else if (expenseRate > 85) tips.add("Balans müsbət olsa da təhlükəsizlik payı zəifdir. Ən böyük xərc kateqoriyasını izləmək faydalıdır.");
            else tips.add("Faktiki xərc nisbəti idarəolunandır. Yolda olan vəsait gəldikdə onu ayrıca qərarla yığım və ya borca yönəldə bilərsən.");
            if (debtBurden > 40) tips.add("Borc və kredit ödənişləri aylıq gəlirin böyük hissəsini tutur.");
            if (savingsRate >= 10) tips.add("Yığım tempin yaxşıdır.");
        }
        for (String tip : tips) {
            TextView t = tv("• " + tip, 14, INK, false); t.setPadding(0,dp(9),0,0); insight.addView(t);
        }
        body.addView(insight);

        LinearLayout debtMot = card(PURPLE_SOFT);
        double simple = db.totalDebtRemainingByType("SIMPLE","PAYABLE");
        double credit = db.totalDebtRemainingByType("CREDIT","PAYABLE");
        debtMot.addView(tv("Öhdəlik qalığı",17,INK,true));
        debtMot.addView(tv("Birdəfəlik borc: " + azn(simple) + "\nKredit: " + azn(credit),14,PURPLE,true));
        body.addView(debtMot);

        render("Aylıq təhlil", body, 4);
    }

    private void showLedgerReport() {
        LinearLayout body = vertical();

        LinearLayout filter = card(WHITE);
        filter.addView(tv("CR / DR Balans hesabatı",18,INK,true));
        filter.addView(tv("CR = Gəlir   •   DR = Xərc",12,MUTED,false));

        EditText from = datePickerInput("Başlanğıc tarix", ledgerFilterFrom, false);
        EditText to = datePickerInput("Son tarix", ledgerFilterTo, false);
        filter.addView(from); filter.addView(to);

        LinearLayout actions=new LinearLayout(this); actions.setOrientation(LinearLayout.HORIZONTAL); actions.setPadding(0,dp(8),0,0);
        Button apply=actionButton("Hesabatı yenilə",PURPLE,WHITE,v->{
            String f=from.getText().toString().trim();
            String t=to.getText().toString().trim();
            if(!validDate(f)||!validDate(t)||f.compareTo(t)>0){toast("Tarix aralığını yoxla.");return;}
            ledgerFilterFrom=f; ledgerFilterTo=t; showLedgerReport();
        });
        Button back=actionButton("Təhlilə qayıt",PURPLE_SOFT,PURPLE,v->showAnalysis());
        actions.addView(apply,new LinearLayout.LayoutParams(0,dp(44),1));
        LinearLayout.LayoutParams blp=new LinearLayout.LayoutParams(0,dp(44),1); blp.setMargins(dp(8),0,0,0); actions.addView(back,blp);
        filter.addView(actions);
        body.addView(filter);

        String fromDate=ledgerFilterFrom;
        String toDate=ledgerFilterTo;
        double opening=db.balanceBefore(fromDate);
        double cr=db.sumBetween("INCOME",fromDate,toDate);
        double dr=db.sumBetween("EXPENSE",fromDate,toDate);
        double closing=opening+cr-dr;

        LinearLayout summary=card(YELLOW_SOFT);
        summary.addView(tv("Açılış balansı: "+azn(opening),13,MUTED,false));
        summary.addView(tv("CR (Gəlir): "+azn(cr)+"   •   DR (Xərc): "+azn(dr),15,INK,true));
        summary.addView(tv("Bağlanış balansı: "+azn(closing),20,closing>=0?GREEN:RED,true));
        body.addView(summary);

        LinearLayout card=card(WHITE);
        card.addView(tv("Balans hərəkətləri",17,INK,true));
        LinearLayout table=vertical();
        LinearLayout h=tableRow();
        h.addView(tableCell("Tarix",105,true,INK));
        h.addView(tableCell("Açıqlama",170,true,INK));
        h.addView(tableCell("DR",105,true,INK));
        h.addView(tableCell("CR",105,true,INK));
        h.addView(tableCell("Balans",115,true,INK));
        table.addView(h);

        double running=opening;
        int n=0;
        try(Cursor c=db.transactionsBetween(fromDate,toDate,true)){
            while(c.moveToNext()){
                n++;
                String kind=c.getString(c.getColumnIndexOrThrow("kind"));
                double amount=c.getDouble(c.getColumnIndexOrThrow("amount"));
                String date=c.getString(c.getColumnIndexOrThrow("date"));
                String category=c.getString(c.getColumnIndexOrThrow("category"));
                String note=c.getString(c.getColumnIndexOrThrow("note"));
                String period=c.getString(c.getColumnIndexOrThrow("period"));
                long debtId=c.getLong(c.getColumnIndexOrThrow("debt_id"));

                if("INCOME".equals(kind)) running+=amount; else running-=amount;
                String desc=debtId>0 ? ("Kredit ödənişi".equals(period)?"Kredit ödənişi":"Borc ödənişi") : category;
                if(note!=null&&!note.isEmpty()) desc += " • "+note;

                LinearLayout tr=tableRow();
                tr.addView(tableCell(date,105,false,MUTED));
                tr.addView(tableCell(desc,170,false,INK));
                tr.addView(tableCell("EXPENSE".equals(kind)?azn(amount):"—",105,false,"EXPENSE".equals(kind)?RED:MUTED));
                tr.addView(tableCell("INCOME".equals(kind)?azn(amount):"—",105,false,"INCOME".equals(kind)?GREEN:MUTED));
                tr.addView(tableCell(azn(running),115,false,running>=0?INK:RED));
                table.addView(tr);
            }
        }
        if(n==0){
            LinearLayout tr=tableRow(); tr.addView(tableCell("Bu aralıqda əməliyyat yoxdur.",600,false,MUTED)); table.addView(tr);
        }
        card.addView(horizontalTable(table));
        body.addView(card);

        render("CR / DR hesabatı",body,4);
    }

    private LinearLayout analysisLine'''
main = replace_once(
    main,
    r'''    private void showAnalysis\(\) \{.*?    private LinearLayout analysisLine''',
    analysis_replacement,
    "Analysis + ledger"
)

MAIN.write_text(main, encoding="utf-8")
DB.write_text(db, encoding="utf-8")
print("Applied Büdcəm v1.3: CR/DR ledger, date pickers, category editing, tables and date filters")
