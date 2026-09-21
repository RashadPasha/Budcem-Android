from pathlib import Path
import re

MAIN = Path("app/src/main/java/az/budcem/premium/MainActivity.java")
DB = Path("app/src/main/java/az/budcem/premium/BudgetDb.java")

main = MAIN.read_text(encoding="utf-8")
db = DB.read_text(encoding="utf-8")

def replace_once(text, pattern, replacement, label):
    updated, count = re.subn(pattern, lambda m: replacement, text, count=1, flags=re.S)
    if count != 1:
        raise SystemExit(f"{label}: patch target was not found exactly once (found {count})")
    return updated

def exact_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: exact target expected once, found {count}")
    return text.replace(old, new, 1)

# ---------------- DATABASE v2 ----------------
db = exact_once(
    db,
    'private static final int DB_VERSION = 1;',
    'private static final int DB_VERSION = 2;',
    'DB version'
)

db = exact_once(
    db,
    '"direction TEXT NOT NULL," +\n                "principal REAL NOT NULL," +',
    '"direction TEXT NOT NULL," +\n                "type TEXT NOT NULL DEFAULT \'SIMPLE\'," +\n                "principal REAL NOT NULL," +',
    'Debt type schema'
)

db = exact_once(
    db,
    '''        db.execSQL("CREATE TABLE debt_schedule(" +
                "id INTEGER PRIMARY KEY AUTOINCREMENT," +
                "debt_id INTEGER NOT NULL," +
                "due_date TEXT NOT NULL," +
                "amount REAL NOT NULL," +
                "paid REAL NOT NULL DEFAULT 0," +
                "status TEXT NOT NULL DEFAULT 'OPEN')");

        seed(db);''',
    '''        db.execSQL("CREATE TABLE debt_schedule(" +
                "id INTEGER PRIMARY KEY AUTOINCREMENT," +
                "debt_id INTEGER NOT NULL," +
                "due_date TEXT NOT NULL," +
                "amount REAL NOT NULL," +
                "paid REAL NOT NULL DEFAULT 0," +
                "status TEXT NOT NULL DEFAULT 'OPEN')");

        db.execSQL("CREATE TABLE pending_income(" +
                "id INTEGER PRIMARY KEY AUTOINCREMENT," +
                "category_id INTEGER NOT NULL DEFAULT 0," +
                "amount REAL NOT NULL," +
                "expected_date TEXT," +
                "note TEXT," +
                "created TEXT NOT NULL)");

        seed(db);''',
    'Pending income schema'
)

db = replace_once(
    db,
    r'''    @Override\n    public void onUpgrade\(SQLiteDatabase db, int oldVersion, int newVersion\) \{.*?    \}\n\n    private void seed''',
    '''    @Override
    public void onUpgrade(SQLiteDatabase db, int oldVersion, int newVersion) {
        if (oldVersion < 2) {
            try { db.execSQL("ALTER TABLE debts ADD COLUMN type TEXT NOT NULL DEFAULT 'SIMPLE'"); } catch (Exception ignored) {}
            db.execSQL("CREATE TABLE IF NOT EXISTS pending_income(" +
                    "id INTEGER PRIMARY KEY AUTOINCREMENT," +
                    "category_id INTEGER NOT NULL DEFAULT 0," +
                    "amount REAL NOT NULL," +
                    "expected_date TEXT," +
                    "note TEXT," +
                    "created TEXT NOT NULL)");
        }
    }

    private void seed''',
    'onUpgrade'
)

# Preserve debt/credit payment label when editing
if 'v.put("period", "Borc ödənişi");' in db:
    db = db.replace('v.put("period", "Borc ödənişi");',
                    'v.put("period", period == null || period.isEmpty() ? "Borc ödənişi" : period);', 1)

# Simple debts are explicitly marked SIMPLE and have no installment schedule.
simple_debt_replacement = '''    public long addSimpleDebt(String name, String direction, double principal, String dueDate) {
        if (principal <= 0) return -1;
        SQLiteDatabase database = getWritableDatabase();
        String created = LocalDate.now().toString();
        String due = dueDate == null ? "" : dueDate.trim();

        ContentValues v = new ContentValues();
        v.put("name", name.trim());
        v.put("direction", direction);
        v.put("type", "SIMPLE");
        v.put("principal", principal);
        v.put("remaining", principal);
        v.put("monthly", principal);
        v.put("first_due", due.isEmpty() ? created : due);
        if (due.isEmpty()) v.putNull("next_due"); else v.put("next_due", due);
        v.put("created", created);
        return database.insert("debts", null, v);
    }

    public String debtName(long debtId) {'''
db = replace_once(
    db,
    r'''    public long addSimpleDebt\(String name, String direction, double principal, String dueDate\) \{.*?    public String debtName\(long debtId\) \{''',
    simple_debt_replacement,
    'Simple debt'
)

# Debt picker in Operations must show only one-time/simple debts, never credits.
db = replace_once(
    db,
    r'''    public Cursor debtChoices\(String direction\) \{.*?    \}\n\n    public Cursor debtSchedule''',
    '''    public Cursor debtChoices(String direction) {
        return getReadableDatabase().rawQuery(
                "SELECT id AS _id,name,remaining FROM debts WHERE direction=? AND type='SIMPLE' AND remaining>0.005 ORDER BY name",
                new String[]{direction});
    }

    public Cursor debtSchedule''',
    'Simple debt choices'
)

# Upcoming notification/payment list should be credit schedule only.
db = replace_once(
    db,
    r'''    public Cursor upcomingSchedules\(int limit\) \{.*?    public Cursor allOpenSchedules\(\) \{.*?    \}\n''',
    '''    public Cursor upcomingSchedules(int limit) {
        return getReadableDatabase().rawQuery(
                "SELECT s.id AS _id,s.debt_id,s.due_date,s.amount,s.paid,s.status,d.name,d.direction " +
                        "FROM debt_schedule s JOIN debts d ON d.id=s.debt_id " +
                        "WHERE d.type='CREDIT' AND s.status!='PAID' ORDER BY s.due_date,s.id LIMIT " + Math.max(1, limit),
                null);
    }

    public Cursor allOpenSchedules() {
        return getReadableDatabase().rawQuery(
                "SELECT s.id AS _id,s.debt_id,s.due_date,s.amount,s.paid,d.name,d.direction " +
                        "FROM debt_schedule s JOIN debts d ON d.id=s.debt_id " +
                        "WHERE d.type='CREDIT' AND s.status!='PAID' ORDER BY s.due_date",
                null);
    }
''',
    'Credit schedules'
)

extra_db = '''    public long addPendingIncome(long categoryId, double amount, String expectedDate, String note) {
        if (amount <= 0) return -1;
        ContentValues v = new ContentValues();
        v.put("category_id", categoryId);
        v.put("amount", amount);
        String expected = expectedDate == null ? "" : expectedDate.trim();
        if (expected.isEmpty()) v.putNull("expected_date"); else v.put("expected_date", expected);
        v.put("note", note == null ? "" : note);
        v.put("created", LocalDate.now().toString());
        return getWritableDatabase().insert("pending_income", null, v);
    }

    public Cursor pendingIncomes() {
        return getReadableDatabase().rawQuery(
                "SELECT p.id AS _id,p.category_id,p.amount,p.expected_date,p.note,p.created," +
                        "COALESCE(c.name,'Digər gəlir') AS category " +
                        "FROM pending_income p LEFT JOIN categories c ON c.id=p.category_id " +
                        "ORDER BY CASE WHEN p.expected_date IS NULL THEN 1 ELSE 0 END,p.expected_date,p.id DESC",
                null);
    }

    public double totalPendingIncome() {
        try (Cursor c = getReadableDatabase().rawQuery("SELECT COALESCE(SUM(amount),0) FROM pending_income", null)) {
            return c.moveToFirst() ? c.getDouble(0) : 0;
        }
    }

    public double pendingIncomeForMonth(String monthPrefix) {
        try (Cursor c = getReadableDatabase().rawQuery(
                "SELECT COALESCE(SUM(amount),0) FROM pending_income WHERE expected_date LIKE ?",
                new String[]{monthPrefix + "%"})) {
            return c.moveToFirst() ? c.getDouble(0) : 0;
        }
    }

    public void updatePendingIncome(long id, long categoryId, double amount, String expectedDate, String note) {
        ContentValues v = new ContentValues();
        v.put("category_id", categoryId);
        v.put("amount", Math.max(0, amount));
        String expected = expectedDate == null ? "" : expectedDate.trim();
        if (expected.isEmpty()) v.putNull("expected_date"); else v.put("expected_date", expected);
        v.put("note", note == null ? "" : note);
        getWritableDatabase().update("pending_income", v, "id=?", new String[]{String.valueOf(id)});
    }

    public void deletePendingIncome(long id) {
        getWritableDatabase().delete("pending_income", "id=?", new String[]{String.valueOf(id)});
    }

    public boolean receivePendingIncome(long id, String receivedDate) {
        SQLiteDatabase database = getWritableDatabase();
        database.beginTransaction();
        try {
            long categoryId;
            double amount;
            String note;
            try (Cursor c = database.rawQuery(
                    "SELECT category_id,amount,note FROM pending_income WHERE id=?",
                    new String[]{String.valueOf(id)})) {
                if (!c.moveToFirst()) return false;
                categoryId = c.getLong(0);
                amount = c.getDouble(1);
                note = c.getString(2);
            }

            ContentValues t = new ContentValues();
            t.put("kind", "INCOME");
            t.put("category_id", categoryId);
            t.put("amount", amount);
            t.put("period", "Birdəfəlik");
            t.put("date", receivedDate);
            t.put("note", note == null ? "" : note);
            t.put("debt_id", 0);
            database.insert("transactions", null, t);
            database.delete("pending_income", "id=?", new String[]{String.valueOf(id)});
            database.setTransactionSuccessful();
            return true;
        } finally {
            database.endTransaction();
        }
    }

    public Cursor recentTransactions() {
        return getReadableDatabase().rawQuery(
                "SELECT t.id AS _id,t.kind,t.category_id,t.amount,t.period,t.date,t.note,t.debt_id," +
                        "COALESCE(c.name,'Borc / Kredit') AS category " +
                        "FROM transactions t LEFT JOIN categories c ON c.id=t.category_id " +
                        "ORDER BY t.date DESC,t.id DESC LIMIT 150",
                null);
    }

    public long addCredit(String name, double principal, double monthly, String firstDue) {
        if (principal <= 0 || monthly <= 0) return -1;
        SQLiteDatabase database = getWritableDatabase();
        database.beginTransaction();
        try {
            ContentValues v = new ContentValues();
            v.put("name", name.trim());
            v.put("direction", "PAYABLE");
            v.put("type", "CREDIT");
            v.put("principal", principal);
            v.put("remaining", principal);
            v.put("monthly", monthly);
            v.put("first_due", firstDue);
            v.put("next_due", firstDue);
            v.put("created", LocalDate.now().toString());
            long debtId = database.insert("debts", null, v);

            LocalDate due = LocalDate.parse(firstDue);
            double left = principal;
            int guard = 0;
            while (left > 0.005 && guard < 600) {
                double installment = Math.min(monthly, left);
                ContentValues s = new ContentValues();
                s.put("debt_id", debtId);
                s.put("due_date", due.toString());
                s.put("amount", installment);
                s.put("paid", 0);
                s.put("status", "OPEN");
                database.insert("debt_schedule", null, s);
                left -= installment;
                due = due.plusMonths(1);
                guard++;
            }
            database.setTransactionSuccessful();
            return debtId;
        } finally {
            database.endTransaction();
        }
    }

    public Cursor debtsByType(String type) {
        return getReadableDatabase().rawQuery(
                "SELECT id AS _id,name,direction,type,principal,remaining,monthly,first_due,next_due,created " +
                        "FROM debts WHERE type=? ORDER BY remaining DESC,id DESC",
                new String[]{type});
    }

    public double totalDebtRemainingByType(String type, String direction) {
        try (Cursor c = getReadableDatabase().rawQuery(
                "SELECT COALESCE(SUM(remaining),0) FROM debts WHERE type=? AND direction=?",
                new String[]{type, direction})) {
            return c.moveToFirst() ? c.getDouble(0) : 0;
        }
    }

    public double totalDebtPrincipalByType(String type, String direction) {
        try (Cursor c = getReadableDatabase().rawQuery(
                "SELECT COALESCE(SUM(principal),0) FROM debts WHERE type=? AND direction=?",
                new String[]{type, direction})) {
            return c.moveToFirst() ? c.getDouble(0) : 0;
        }
    }

    public double payCreditSchedule(long scheduleId, double requestedAmount, String date) {
        if (requestedAmount <= 0) return 0;
        SQLiteDatabase database = getWritableDatabase();
        database.beginTransaction();
        try {
            long debtId;
            double scheduled;
            double alreadyPaid;
            try (Cursor c = database.rawQuery(
                    "SELECT debt_id,amount,paid FROM debt_schedule WHERE id=?",
                    new String[]{String.valueOf(scheduleId)})) {
                if (!c.moveToFirst()) return 0;
                debtId = c.getLong(0);
                scheduled = c.getDouble(1);
                alreadyPaid = c.getDouble(2);
            }

            String debtName;
            double remaining;
            try (Cursor c = database.rawQuery(
                    "SELECT name,remaining FROM debts WHERE id=? AND type='CREDIT'",
                    new String[]{String.valueOf(debtId)})) {
                if (!c.moveToFirst()) return 0;
                debtName = c.getString(0);
                remaining = c.getDouble(1);
            }

            double rowLeft = Math.max(0, scheduled - alreadyPaid);
            double actual = Math.min(Math.min(requestedAmount, rowLeft), remaining);
            if (actual <= 0) return 0;

            double newPaid = alreadyPaid + actual;
            ContentValues sv = new ContentValues();
            sv.put("paid", newPaid);
            sv.put("status", newPaid + 0.005 >= scheduled ? "PAID" : "PARTIAL");
            database.update("debt_schedule", sv, "id=?", new String[]{String.valueOf(scheduleId)});

            double newRemaining = Math.max(0, remaining - actual);
            String nextDue = null;
            try (Cursor c = database.rawQuery(
                    "SELECT due_date FROM debt_schedule WHERE debt_id=? AND status!='PAID' ORDER BY due_date,id LIMIT 1",
                    new String[]{String.valueOf(debtId)})) {
                if (c.moveToFirst()) nextDue = c.getString(0);
            }
            ContentValues dv = new ContentValues();
            dv.put("remaining", newRemaining);
            if (nextDue == null || newRemaining <= 0.005) dv.putNull("next_due"); else dv.put("next_due", nextDue);
            database.update("debts", dv, "id=?", new String[]{String.valueOf(debtId)});

            ContentValues tv = new ContentValues();
            tv.put("kind", "EXPENSE");
            tv.put("category_id", 0);
            tv.put("amount", actual);
            tv.put("period", "Kredit ödənişi");
            tv.put("date", date);
            tv.put("note", debtName);
            tv.put("debt_id", debtId);
            database.insert("transactions", null, tv);

            database.setTransactionSuccessful();
            return actual;
        } finally {
            database.endTransaction();
        }
    }

'''
db = exact_once(db, '    public String debtName(long debtId) {', extra_db + '    public String debtName(long debtId) {', 'DB v1.2 methods')

# ---------------- HOME ----------------
home_replacement = '''    private void showHome() {
        LinearLayout body = vertical();
        String month = LocalDate.now().format(DateTimeFormatter.ofPattern("yyyy-MM"));

        double income = db.sumTransactions("INCOME", null);
        double expense = db.sumTransactions("EXPENSE", null);
        double balance = income - expense;
        double saved = db.totalBudgetSaved();
        double free = balance - saved;
        double monthIncome = db.sumTransactions("INCOME", month);
        double monthExpense = db.sumTransactions("EXPENSE", month);
        double pending = db.totalPendingIncome();
        double simpleDebt = db.totalDebtRemainingByType("SIMPLE", "PAYABLE");
        double receivable = db.totalDebtRemainingByType("SIMPLE", "RECEIVABLE");
        double credit = db.totalDebtRemainingByType("CREDIT", "PAYABLE");

        LinearLayout hero = card(PURPLE);
        hero.addView(tv("Faktiki balans", 13, Color.rgb(232, 228, 255), false));
        TextView heroValue = tv(azn(balance), 34, WHITE, true);
        heroValue.setPadding(0, dp(5), 0, dp(8));
        hero.addView(heroValue);
        hero.addView(tv("Sərbəst istifadə: " + azn(free) + "   •   Yığım: " + azn(saved), 12, Color.rgb(240, 237, 255), false));
        body.addView(hero);

        LinearLayout row1 = new LinearLayout(this);
        row1.setOrientation(LinearLayout.HORIZONTAL);
        LinearLayout.LayoutParams half = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1);
        half.setMargins(0, 0, dp(6), dp(10));
        LinearLayout.LayoutParams half2 = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1);
        half2.setMargins(dp(6), 0, 0, dp(10));
        row1.addView(metricCard("Bu ay gəlir", azn(monthIncome), YELLOW_SOFT), half);
        row1.addView(metricCard("Bu ay xərc", azn(monthExpense), PURPLE_SOFT), half2);
        body.addView(row1);

        LinearLayout pendingCard = card(Color.rgb(226, 246, 255));
        pendingCard.addView(tv("Yolda olan vəsaitlər", 13, MUTED, false));
        pendingCard.addView(tv(azn(pending), 24, INK, true));
        pendingCard.addView(tv("Bu məbləğ faktiki gəlir və balans hesablamasına daxil edilmir.", 12, MUTED, false));
        body.addView(pendingCard);

        LinearLayout row2 = new LinearLayout(this);
        row2.setOrientation(LinearLayout.HORIZONTAL);
        row2.addView(metricCard("Birdəfəlik borc", azn(simpleDebt), Color.rgb(255, 235, 226)), half);
        row2.addView(metricCard("Kredit qalığı", azn(credit), PURPLE_SOFT), half2);
        body.addView(row2);

        if (receivable > 0.005) {
            LinearLayout alacaq = card(Color.rgb(225, 246, 237));
            alacaq.addView(tv("Alacağım", 13, MUTED, false));
            alacaq.addView(tv(azn(receivable), 20, GREEN, true));
            body.addView(alacaq);
        }

        LinearLayout quick = card(WHITE);
        quick.addView(tv("Sürətli əlavə et", 17, INK, true));
        LinearLayout qrow = new LinearLayout(this);
        qrow.setOrientation(LinearLayout.HORIZONTAL);
        qrow.setPadding(0, dp(10), 0, 0);
        Button inc = actionButton("+ Gəlir", YELLOW, INK, v -> showTransactionDialog("INCOME"));
        Button exp = actionButton("+ Xərc", PURPLE_SOFT, PURPLE, v -> showTransactionDialog("EXPENSE"));
        Button debt = actionButton("+ Borc", Color.rgb(255, 235, 226), RED, v -> showAddDebtDialog());
        qrow.addView(inc, new LinearLayout.LayoutParams(0, dp(48), 1));
        LinearLayout.LayoutParams qb = new LinearLayout.LayoutParams(0, dp(48), 1); qb.setMargins(dp(7),0,dp(7),0);
        qrow.addView(exp, qb);
        qrow.addView(debt, new LinearLayout.LayoutParams(0, dp(48), 1));
        quick.addView(qrow);
        body.addView(quick);

        LinearLayout monthCard = card(WHITE);
        monthCard.addView(tv("Ayın vəziyyəti", 17, INK, true));
        double ratio = monthIncome > 0 ? (monthExpense / monthIncome) * 100 : 0;
        String ratioText = monthIncome <= 0 ? "Bu ay faktiki gəlir hələ əlavə edilməyib." :
                "Faktiki gəlirin " + Math.round(ratio) + "%-i xərclənib. " +
                        (ratio <= 70 ? "Yaxşı tempdir." : ratio <= 95 ? "Xərcləri bir az sıx nəzarətdə saxla." : "Xərclər gəlir limitinə çox yaxındır.");
        TextView rt = tv(ratioText, 14, MUTED, false); rt.setPadding(0, dp(8), 0, 0); monthCard.addView(rt);
        body.addView(monthCard);

        LinearLayout due = card(WHITE);
        due.addView(tv("Yaxın kredit ödənişləri", 17, INK, true));
        int added = 0;
        try (Cursor c = db.upcomingSchedules(5)) {
            while (c.moveToNext()) {
                String dueDate = c.getString(c.getColumnIndexOrThrow("due_date"));
                double amount = c.getDouble(c.getColumnIndexOrThrow("amount"));
                double paid = c.getDouble(c.getColumnIndexOrThrow("paid"));
                String name = c.getString(c.getColumnIndexOrThrow("name"));
                LinearLayout r = new LinearLayout(this);
                r.setOrientation(LinearLayout.HORIZONTAL);
                r.setGravity(Gravity.CENTER_VERTICAL);
                r.setPadding(0, dp(8), 0, dp(3));
                r.addView(tv(name + "\n" + dueDate, 13, INK, true), new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
                r.addView(tv("− " + azn(Math.max(0, amount - paid)), 13, RED, true));
                due.addView(r);
                added++;
            }
        }
        if (added == 0) {
            TextView none = tv("Planlaşdırılmış kredit ödənişi yoxdur.", 13, MUTED, false);
            none.setPadding(0, dp(10), 0, 0);
            due.addView(none);
        }
        body.addView(due);

        LinearLayout motivate = card(YELLOW_SOFT);
        motivate.addView(tv("Maliyyə istiqaməti", 16, INK, true));
        double totalPayable = simpleDebt + credit;
        String msg = totalPayable <= 0.005
                ? "Aktiv borc və kredit qalığı yoxdur. Faktiki müsbət qalığı yığıma yönəltmək üçün yaxşı mövqedəsən."
                : "Birdəfəlik borc və kredit qalığın birlikdə " + azn(totalPayable) + "-dir. Yolda olan vəsaiti daxil olana qədər xərclənə bilən pul kimi hesablamırıq.";
        TextView mt = tv(msg, 14, INK, false); mt.setPadding(0, dp(8), 0, 0); motivate.addView(mt);
        body.addView(motivate);

        render("Maliyyə panelim", body, 0);
    }

    private void showTransactions() {'''
main = replace_once(
    main,
    r'''    private void showHome\(\) \{.*?    private void showTransactions\(\) \{''',
    home_replacement,
    'Home'
)

# ---------------- TRANSACTIONS + PENDING ----------------
transactions_replacement = '''    private void showTransactions() {
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
        summary.addView(tv("Bu ay — yalnız faktiki", 13, MUTED, false));
        summary.addView(tv("Gəlir " + azn(db.sumTransactions("INCOME", month)) + "   •   Xərc " + azn(db.sumTransactions("EXPENSE", month)), 16, INK, true));
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
        try (Cursor c = db.recentTransactions()) {
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
                String sub = source + " • " + date + (note == null || note.isEmpty() ? "" : "\n" + note);
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

                if (!c.isLast()) {
                    View line = new View(this); line.setBackgroundColor(Color.rgb(241,239,235));
                    line.setLayoutParams(new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(1)));
                    list.addView(line);
                }
            }
        }
        if (n == 0) {
            TextView e = tv("Hələ əməliyyat yoxdur.", 13, MUTED, false); e.setPadding(0,dp(12),0,0); list.addView(e);
        }
        body.addView(list);
        render("Gəlir və xərclər", body, 1);
    }

    private void showReceivePendingDialog(long pendingId, double amount) {
        LinearLayout box = vertical(); box.setPadding(dp(18),dp(8),dp(18),0);
        box.addView(tv("Daxil olan məbləğ: " + azn(amount), 14, INK, true));
        EditText date = input("Daxilolma tarixi (boşdursa bu gün)", false);
        box.addView(date);
        new AlertDialog.Builder(this).setTitle("Vəsait daxil oldu")
                .setView(box).setNegativeButton("Ləğv et", null)
                .setPositiveButton("Gəlirə keçir", (d,w) -> {
                    String raw = date.getText().toString().trim();
                    String dt = raw.isEmpty() ? LocalDate.now().toString() : raw;
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
        EditText expected = input("Gözlənilən tarix (istəyə bağlı)", false); expected.setText(oldExpected == null ? "" : oldExpected);
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
    'Transactions v1.2'
)

# Keep the original payment period on edit (credit vs simple debt).
main = main.replace(
    'String per = debtId > 0 ? "Borc ödənişi" : String.valueOf(period.getSelectedItem());',
    'String per = debtId > 0 ? oldPeriod : String.valueOf(period.getSelectedItem());'
)

# ---------------- INCOME / EXPENSE DIALOG ----------------
transaction_dialog = '''    private void showTransactionDialog(String kind) {
        LinearLayout box = vertical(); box.setPadding(dp(18),dp(8),dp(18),0);
        List<Choice> cats = categoryChoices(kind);
        if (cats.isEmpty()) { toast("Əvvəl kateqoriya yarat."); showCategories(); return; }

        Spinner cat = spinner(cats);
        EditText amount = input("Məbləğ", true);
        EditText date = input("Tarix (istəyə bağlı — boşdursa bu gün)", false);
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
            date.setHint("Tarix / gözlənilən tarix (istəyə bağlı)");
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

                    String rawDate = date.getText().toString().trim();
                    if (!rawDate.isEmpty() && !validDate(rawDate)) { toast("Tarixi YYYY-MM-DD formatında yaz."); return; }

                    Choice cc = (Choice)cat.getSelectedItem();
                    String per = String.valueOf(period.getSelectedItem());

                    if ("INCOME".equals(kind) && fIncomeStatus != null && fIncomeStatus.getSelectedItemPosition() == 1) {
                        db.addPendingIncome(cc.id, a, rawDate, note.getText().toString());
                        toast("Yolda olan vəsait kimi ayrıldı. Faktiki gəlirə daxil edilmədi.");
                    } else {
                        String dt = rawDate.isEmpty() ? LocalDate.now().toString() : rawDate;
                        if ("EXPENSE".equals(kind) && fObligation != null && fObligation.getSelectedItemPosition() == 1) {
                            Choice debtChoice = (Choice)fDebtSpinner.getSelectedItem();
                            if (debtChoice == null || debtChoice.id == 0) {
                                toast("Borc seçilməyib.");
                                return;
                            }
                            db.payDebt(debtChoice.id, a, dt);
                        } else {
                            db.addTransaction(kind, cc.id, a, per, dt, note.getText().toString(), 0);
                        }
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
    'Transaction dialog v1.2'
)

# ---------------- BORC + KREDIT SCREEN ----------------
debts_screen = '''    private void showDebts() {
        LinearLayout body = vertical();

        LinearLayout top = card(PURPLE_SOFT);
        top.addView(tv("Borc və kreditlər", 18, INK, true));
        top.addView(tv("Birdəfəlik borc və aylıq kredit planı ayrı idarə olunur.", 13, MUTED, false));
        LinearLayout buttons = new LinearLayout(this); buttons.setOrientation(LinearLayout.HORIZONTAL);
        Button debtAdd = actionButton("+ Borc", Color.rgb(255,235,226), RED, v -> showAddDebtDialog());
        Button creditAdd = actionButton("+ Kredit", PURPLE, WHITE, v -> showAddCreditDialog());
        buttons.addView(debtAdd, new LinearLayout.LayoutParams(0,dp(48),1));
        LinearLayout.LayoutParams cp = new LinearLayout.LayoutParams(0,dp(48),1); cp.setMargins(dp(8),0,0,0);
        buttons.addView(creditAdd, cp);
        LinearLayout.LayoutParams bp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(48)); bp.setMargins(0,dp(12),0,0);
        top.addView(buttons,bp);
        body.addView(top);

        LinearLayout simpleHead = card(YELLOW_SOFT);
        simpleHead.addView(tv("Birdəfəlik borclar", 17, INK, true));
        simpleHead.addView(tv("Verəcəyim: " + azn(db.totalDebtRemainingByType("SIMPLE","PAYABLE")) +
                "   •   Alacağım: " + azn(db.totalDebtRemainingByType("SIMPLE","RECEIVABLE")), 13, MUTED, false));
        simpleHead.addView(tv("Ödəniş: Əməliyyatlar → Xərc → Borc ödənişi → şəxsi seç.", 12, PURPLE, true));
        body.addView(simpleHead);

        int simpleCount = 0;
        try (Cursor c = db.debtsByType("SIMPLE")) {
            while (c.moveToNext()) {
                simpleCount++;
                String name = c.getString(c.getColumnIndexOrThrow("name"));
                String dir = c.getString(c.getColumnIndexOrThrow("direction"));
                double principal = c.getDouble(c.getColumnIndexOrThrow("principal"));
                double remaining = c.getDouble(c.getColumnIndexOrThrow("remaining"));

                LinearLayout dc = card(WHITE);
                LinearLayout titleRow = new LinearLayout(this); titleRow.setOrientation(LinearLayout.HORIZONTAL); titleRow.setGravity(Gravity.CENTER_VERTICAL);
                titleRow.addView(tv(name,18,INK,true),new LinearLayout.LayoutParams(0,ViewGroup.LayoutParams.WRAP_CONTENT,1));
                TextView badge = tv("PAYABLE".equals(dir) ? "VERƏCƏYİM" : "ALACAĞIM",10,"PAYABLE".equals(dir)?RED:GREEN,true);
                badge.setPadding(dp(8),dp(5),dp(8),dp(5));
                badge.setBackground(rounded("PAYABLE".equals(dir)?Color.rgb(255,235,226):Color.rgb(225,246,237),12));
                titleRow.addView(badge);
                dc.addView(titleRow);
                dc.addView(tv(azn(remaining),25,INK,true));
                dc.addView(tv("İlkin: " + azn(principal) + "   •   Bağlanıb: " + azn(Math.max(0,principal-remaining)),12,MUTED,false));
                body.addView(dc);
            }
        }
        if (simpleCount == 0) {
            LinearLayout e = card(WHITE); e.addView(tv("Birdəfəlik borc yoxdur.",13,MUTED,false)); body.addView(e);
        }

        LinearLayout creditHead = card(PURPLE_SOFT);
        creditHead.addView(tv("Kreditlər", 17, INK, true));
        creditHead.addView(tv("Qalıq: " + azn(db.totalDebtRemainingByType("CREDIT","PAYABLE")), 13, PURPLE, true));
        body.addView(creditHead);

        int creditCount = 0;
        try (Cursor c = db.debtsByType("CREDIT")) {
            while (c.moveToNext()) {
                creditCount++;
                long id = c.getLong(c.getColumnIndexOrThrow("_id"));
                String name = c.getString(c.getColumnIndexOrThrow("name"));
                double principal = c.getDouble(c.getColumnIndexOrThrow("principal"));
                double remaining = c.getDouble(c.getColumnIndexOrThrow("remaining"));
                double monthly = c.getDouble(c.getColumnIndexOrThrow("monthly"));
                String nextDue = c.isNull(c.getColumnIndexOrThrow("next_due")) ? "Bağlanıb" : c.getString(c.getColumnIndexOrThrow("next_due"));

                LinearLayout cc = card(WHITE);
                cc.addView(tv(name,18,INK,true));
                cc.addView(tv(azn(remaining),25,PURPLE,true));
                cc.addView(tv("Ümumi: " + azn(principal) + "   •   Aylıq: " + azn(monthly) + "\nNövbəti ödəniş: " + nextDue,12,MUTED,false));
                double closed = principal > 0 ? (principal-remaining)/principal : 1;
                ProgressBar pb = new ProgressBar(this,null,android.R.attr.progressBarStyleHorizontal);
                pb.setMax(1000); pb.setProgress((int)Math.max(0,Math.min(1000,closed*1000)));
                pb.setProgressTintList(ColorStateList.valueOf(PURPLE));
                LinearLayout.LayoutParams pp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,dp(9)); pp.setMargins(0,dp(10),0,dp(10));
                cc.addView(pb,pp);
                Button table = actionButton("Ödəniş cədvəli",PURPLE_SOFT,PURPLE,v->showDebtScheduleDialog(id,name));
                cc.addView(table,new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,dp(46)));
                body.addView(cc);
            }
        }
        if (creditCount == 0) {
            LinearLayout e = card(WHITE); e.addView(tv("Kredit yoxdur. Yeni kredit yaradanda aylıq cədvəl avtomatik formalaşacaq.",13,MUTED,false)); body.addView(e);
        }

        render("Borclarım", body, 3);
    }

    private void showAnalysis() {'''
main = replace_once(
    main,
    r'''    private void showDebts\(\) \{.*?    private void showAnalysis\(\) \{''',
    debts_screen,
    'Debts and credits screen'
)

# ---------------- ANALYSIS ----------------
analysis_replacement = '''    private void showAnalysis() {
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

    private LinearLayout analysisLine'''
main = replace_once(
    main,
    r'''    private void showAnalysis\(\) \{.*?    private LinearLayout analysisLine''',
    analysis_replacement,
    'Analysis v1.2'
)

# ---------------- SIMPLE DEBT + CREDIT CREATION ----------------
add_debt_credit = '''    private void showAddDebtDialog() {
        LinearLayout box=vertical(); box.setPadding(dp(18),dp(8),dp(18),0);
        EditText name=input("Şəxs / borc adı",false);
        Spinner direction=spinner(List.of("Mən borcluyam", "Mənə borcludurlar"));
        EditText principal=input("Borc məbləği",true);
        box.addView(name); box.addView(direction); box.addView(principal);
        box.addView(tv("Bu birdəfəlik borcdur. Aylıq cədvəl yaradılmır.",12,MUTED,false));

        new AlertDialog.Builder(this).setTitle("Birdəfəlik borc").setView(box)
                .setNegativeButton("Ləğv et",null)
                .setPositiveButton("Yarat",(d,w)->{
                    double p=parseAmount(principal.getText().toString());
                    if(name.getText().toString().trim().isEmpty()||p<=0){toast("Ad və məbləği düzgün doldur.");return;}
                    String dir=direction.getSelectedItemPosition()==0?"PAYABLE":"RECEIVABLE";
                    db.addSimpleDebt(name.getText().toString(),dir,p,"");
                    showDebts();
                }).show();
    }

    private void showAddCreditDialog() {
        LinearLayout box=vertical(); box.setPadding(dp(18),dp(8),dp(18),0);
        EditText name=input("Kredit adı",false);
        EditText principal=input("Ümumi kredit məbləği",true);
        EditText monthly=input("Aylıq plan ödənişi",true);
        EditText first=input("İlk ödəniş tarixi (YYYY-MM-DD)",false);
        first.setText(LocalDate.now().plusMonths(1).toString());
        box.addView(name); box.addView(principal); box.addView(monthly); box.addView(first);
        box.addView(tv("Cədvəl ümumi məbləğ bitənədək ay-ay avtomatik yaradılacaq.",12,MUTED,false));

        new AlertDialog.Builder(this).setTitle("Yeni kredit").setView(box)
                .setNegativeButton("Ləğv et",null)
                .setPositiveButton("Cədvəl yarat",(d,w)->{
                    double p=parseAmount(principal.getText().toString());
                    double m=parseAmount(monthly.getText().toString());
                    String f=first.getText().toString().trim();
                    if(name.getText().toString().trim().isEmpty()||p<=0||m<=0||!validDate(f)){
                        toast("Kredit məlumatlarını düzgün doldur.");return;
                    }
                    db.addCredit(name.getText().toString(),p,m,f);
                    scheduleAllOpen(this);
                    showDebts();
                }).show();
    }

    private void showPayDebtDialog(long debtId, String name, double remaining, double monthly) {'''
main = replace_once(
    main,
    r'''    private void showAddDebtDialog\(\) \{.*?    private void showPayDebtDialog\(long debtId, String name, double remaining, double monthly\) \{''',
    add_debt_credit,
    'Debt and credit creation'
)

# ---------------- CREDIT SCHEDULE / PARTIAL PAYMENT ----------------
schedule_replacement = '''    private void showDebtScheduleDialog(long debtId, String name) {
        LinearLayout list=vertical(); list.setPadding(dp(16),dp(8),dp(16),dp(8));
        int n=0;
        try(Cursor c=db.debtSchedule(debtId)){
            while(c.moveToNext()){
                n++;
                long scheduleId=c.getLong(c.getColumnIndexOrThrow("_id"));
                String due=c.getString(c.getColumnIndexOrThrow("due_date"));
                double amount=c.getDouble(c.getColumnIndexOrThrow("amount"));
                double paid=c.getDouble(c.getColumnIndexOrThrow("paid"));
                String status=c.getString(c.getColumnIndexOrThrow("status"));
                double left=Math.max(0,amount-paid);

                LinearLayout row=vertical();
                row.setPadding(0,dp(8),0,dp(8));
                LinearLayout topRow=new LinearLayout(this); topRow.setOrientation(LinearLayout.HORIZONTAL); topRow.setGravity(Gravity.CENTER_VERTICAL);
                String st="PAID".equals(status)?"Ödənib":"PARTIAL".equals(status)?"Qismən ödənib":"Gözləyir";
                topRow.addView(tv(due+"\n"+st,13,"PAID".equals(status)?GREEN:INK,true),new LinearLayout.LayoutParams(0,ViewGroup.LayoutParams.WRAP_CONTENT,1));
                topRow.addView(tv(azn(left),13,"PAID".equals(status)?GREEN:RED,true));
                row.addView(topRow);

                if(!"PAID".equals(status) && left>0.005){
                    Button b=actionButton("Bu ay üçün ödəniş et",PURPLE_SOFT,PURPLE,
                            v->showPayCreditScheduleDialog(scheduleId,debtId,name,left));
                    LinearLayout.LayoutParams bp=new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,dp(42)); bp.setMargins(0,dp(7),0,0);
                    row.addView(b,bp);
                }
                list.addView(row);
            }
        }
        if(n==0)list.addView(tv("Kredit cədvəli boşdur.",13,MUTED,false));
        ScrollView s=new ScrollView(this);s.addView(list);
        new AlertDialog.Builder(this).setTitle(name+" — ödəniş cədvəli").setView(s)
                .setPositiveButton("Bağla",(d,w)->showDebts()).show();
    }

    private void showPayCreditScheduleDialog(long scheduleId, long debtId, String name, double left) {
        LinearLayout box=vertical(); box.setPadding(dp(18),dp(8),dp(18),0);
        EditText amount=input("Ödənilən məbləğ",true);
        amount.setText(String.format(Locale.US,"%.2f",left));
        EditText date=input("Ödəniş tarixi (boşdursa bu gün)",false);
        box.addView(tv("Bu cədvəl sətrində qalıq: "+azn(left),13,MUTED,false));
        box.addView(amount); box.addView(date);

        new AlertDialog.Builder(this).setTitle(name+" — kredit ödənişi").setView(box)
                .setNegativeButton("Ləğv et",null)
                .setPositiveButton("Ödə",(d,w)->{
                    double a=parseAmount(amount.getText().toString());
                    String raw=date.getText().toString().trim();
                    String dt=raw.isEmpty()?LocalDate.now().toString():raw;
                    if(a<=0||!validDate(dt)){toast("Məbləğ və tarixi yoxla.");return;}
                    double paid=db.payCreditSchedule(scheduleId,a,dt);
                    toast("Kredit ödənişi: "+azn(paid));
                    scheduleAllOpen(this);
                    showDebts();
                }).show();
    }

    private double parseAmount'''
main = replace_once(
    main,
    r'''    private void showDebtScheduleDialog\(long debtId, String name\) \{.*?    private double parseAmount''',
    schedule_replacement,
    'Credit schedule'
)

MAIN.write_text(main, encoding="utf-8")
DB.write_text(db, encoding="utf-8")
print("Applied Büdcəm v1.2: pending income, one-time debts, credit schedules and partial payments")
