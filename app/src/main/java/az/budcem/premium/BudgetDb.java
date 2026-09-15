package az.budcem.premium;

import android.content.ContentValues;
import android.content.Context;
import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;
import android.database.sqlite.SQLiteOpenHelper;

import java.time.LocalDate;
import java.util.Locale;

public class BudgetDb extends SQLiteOpenHelper {
    private static final String DB_NAME = "budcem.db";
    private static final int DB_VERSION = 1;

    public BudgetDb(Context context) {
        super(context, DB_NAME, null, DB_VERSION);
    }

    @Override
    public void onCreate(SQLiteDatabase db) {
        db.execSQL("CREATE TABLE categories(" +
                "id INTEGER PRIMARY KEY AUTOINCREMENT," +
                "name TEXT NOT NULL," +
                "parent_id INTEGER NOT NULL DEFAULT 0," +
                "kind TEXT NOT NULL DEFAULT 'BOTH')");

        db.execSQL("CREATE TABLE transactions(" +
                "id INTEGER PRIMARY KEY AUTOINCREMENT," +
                "kind TEXT NOT NULL," +
                "category_id INTEGER NOT NULL DEFAULT 0," +
                "amount REAL NOT NULL," +
                "period TEXT," +
                "date TEXT NOT NULL," +
                "note TEXT," +
                "debt_id INTEGER NOT NULL DEFAULT 0)");

        db.execSQL("CREATE TABLE budgets(" +
                "id INTEGER PRIMARY KEY AUTOINCREMENT," +
                "name TEXT NOT NULL," +
                "target REAL NOT NULL DEFAULT 0," +
                "saved REAL NOT NULL DEFAULT 0," +
                "created TEXT NOT NULL)");

        db.execSQL("CREATE TABLE budget_moves(" +
                "id INTEGER PRIMARY KEY AUTOINCREMENT," +
                "budget_id INTEGER NOT NULL," +
                "amount REAL NOT NULL," +
                "date TEXT NOT NULL)");

        db.execSQL("CREATE TABLE debts(" +
                "id INTEGER PRIMARY KEY AUTOINCREMENT," +
                "name TEXT NOT NULL," +
                "direction TEXT NOT NULL," +
                "principal REAL NOT NULL," +
                "remaining REAL NOT NULL," +
                "monthly REAL NOT NULL," +
                "first_due TEXT NOT NULL," +
                "next_due TEXT," +
                "created TEXT NOT NULL)");

        db.execSQL("CREATE TABLE debt_schedule(" +
                "id INTEGER PRIMARY KEY AUTOINCREMENT," +
                "debt_id INTEGER NOT NULL," +
                "due_date TEXT NOT NULL," +
                "amount REAL NOT NULL," +
                "paid REAL NOT NULL DEFAULT 0," +
                "status TEXT NOT NULL DEFAULT 'OPEN')");

        seed(db);
    }

    @Override
    public void onUpgrade(SQLiteDatabase db, int oldVersion, int newVersion) {
        // v1
    }

    private void seed(SQLiteDatabase db) {
        addSeed(db, "Əmək haqqı", "INCOME");
        addSeed(db, "Freelance", "INCOME");
        addSeed(db, "Digər gəlir", "INCOME");
        addSeed(db, "Ev", "EXPENSE");
        addSeed(db, "Qida", "EXPENSE");
        addSeed(db, "Nəqliyyat", "EXPENSE");
        addSeed(db, "Uşaq", "EXPENSE");
        addSeed(db, "Kreditlər", "EXPENSE");
        addSeed(db, "Digər xərc", "EXPENSE");
    }

    private void addSeed(SQLiteDatabase db, String name, String kind) {
        ContentValues v = new ContentValues();
        v.put("name", name);
        v.put("kind", kind);
        v.put("parent_id", 0);
        db.insert("categories", null, v);
    }

    public long addCategory(String name, long parentId, String kind) {
        ContentValues v = new ContentValues();
        v.put("name", name.trim());
        v.put("parent_id", parentId);
        v.put("kind", kind);
        return getWritableDatabase().insert("categories", null, v);
    }

    public Cursor categoryChoices(String kind) {
        return getReadableDatabase().rawQuery(
                "SELECT c.id AS _id, CASE WHEN p.name IS NULL THEN c.name ELSE p.name || ' › ' || c.name END AS label " +
                        "FROM categories c LEFT JOIN categories p ON p.id=c.parent_id " +
                        "WHERE c.kind=? OR c.kind='BOTH' ORDER BY c.parent_id, label",
                new String[]{kind});
    }

    public Cursor parentCategories(String kind) {
        return getReadableDatabase().rawQuery(
                "SELECT id AS _id,name FROM categories WHERE parent_id=0 AND (kind=? OR kind='BOTH') ORDER BY name",
                new String[]{kind});
    }

    public Cursor allCategories() {
        return getReadableDatabase().rawQuery(
                "SELECT c.id AS _id,c.kind,c.parent_id,CASE WHEN p.name IS NULL THEN c.name ELSE p.name || ' › ' || c.name END AS label " +
                        "FROM categories c LEFT JOIN categories p ON p.id=c.parent_id ORDER BY c.kind,c.parent_id,label",
                null);
    }

    public long addTransaction(String kind, long categoryId, double amount, String period, String date, String note, long debtId) {
        ContentValues v = new ContentValues();
        v.put("kind", kind);
        v.put("category_id", categoryId);
        v.put("amount", amount);
        v.put("period", period);
        v.put("date", date);
        v.put("note", note == null ? "" : note);
        v.put("debt_id", debtId);
        return getWritableDatabase().insert("transactions", null, v);
    }

    public long addBudget(String name, double target) {
        ContentValues v = new ContentValues();
        v.put("name", name.trim());
        v.put("target", Math.max(target, 0));
        v.put("saved", 0);
        v.put("created", LocalDate.now().toString());
        return getWritableDatabase().insert("budgets", null, v);
    }

    public void addBudgetMoney(long budgetId, double amount, String date) {
        if (amount <= 0) return;
        SQLiteDatabase db = getWritableDatabase();
        db.beginTransaction();
        try {
            db.execSQL("UPDATE budgets SET saved=saved+? WHERE id=?", new Object[]{amount, budgetId});
            ContentValues v = new ContentValues();
            v.put("budget_id", budgetId);
            v.put("amount", amount);
            v.put("date", date);
            db.insert("budget_moves", null, v);
            db.setTransactionSuccessful();
        } finally {
            db.endTransaction();
        }
    }

    public Cursor budgets() {
        return getReadableDatabase().rawQuery("SELECT id AS _id,name,target,saved,created FROM budgets ORDER BY id DESC", null);
    }

    public long addDebt(String name, String direction, double principal, double monthly, String firstDue) {
        if (principal <= 0) return -1;
        if (monthly <= 0) monthly = principal;

        SQLiteDatabase db = getWritableDatabase();
        db.beginTransaction();
        long debtId;
        try {
            ContentValues v = new ContentValues();
            v.put("name", name.trim());
            v.put("direction", direction);
            v.put("principal", principal);
            v.put("remaining", principal);
            v.put("monthly", monthly);
            v.put("first_due", firstDue);
            v.put("next_due", firstDue);
            v.put("created", LocalDate.now().toString());
            debtId = db.insert("debts", null, v);

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
                db.insert("debt_schedule", null, s);
                left -= installment;
                due = due.plusMonths(1);
                guard++;
            }
            db.setTransactionSuccessful();
        } finally {
            db.endTransaction();
        }
        return debtId;
    }

    public double payDebt(long debtId, double requestedAmount, String date) {
        if (requestedAmount <= 0) return 0;
        SQLiteDatabase db = getWritableDatabase();
        db.beginTransaction();
        double actual = 0;
        String direction = "PAYABLE";
        String debtName = "Borc";
        try {
            double remaining = 0;
            try (Cursor c = db.rawQuery("SELECT name,direction,remaining FROM debts WHERE id=?", new String[]{String.valueOf(debtId)})) {
                if (!c.moveToFirst()) return 0;
                debtName = c.getString(0);
                direction = c.getString(1);
                remaining = c.getDouble(2);
            }
            actual = Math.min(requestedAmount, remaining);
            double left = actual;

            try (Cursor c = db.rawQuery(
                    "SELECT id,amount,paid FROM debt_schedule WHERE debt_id=? AND status!='PAID' ORDER BY due_date,id",
                    new String[]{String.valueOf(debtId)})) {
                while (c.moveToNext() && left > 0.005) {
                    long scheduleId = c.getLong(0);
                    double amount = c.getDouble(1);
                    double paid = c.getDouble(2);
                    double need = Math.max(0, amount - paid);
                    double take = Math.min(need, left);
                    double newPaid = paid + take;
                    ContentValues sv = new ContentValues();
                    sv.put("paid", newPaid);
                    sv.put("status", newPaid + 0.005 >= amount ? "PAID" : "PARTIAL");
                    db.update("debt_schedule", sv, "id=?", new String[]{String.valueOf(scheduleId)});
                    left -= take;
                }
            }

            double newRemaining = Math.max(0, remaining - actual);
            String nextDue = null;
            try (Cursor c = db.rawQuery(
                    "SELECT due_date FROM debt_schedule WHERE debt_id=? AND status!='PAID' ORDER BY due_date,id LIMIT 1",
                    new String[]{String.valueOf(debtId)})) {
                if (c.moveToFirst()) nextDue = c.getString(0);
            }
            ContentValues dv = new ContentValues();
            dv.put("remaining", newRemaining);
            if (nextDue == null) dv.putNull("next_due"); else dv.put("next_due", nextDue);
            db.update("debts", dv, "id=?", new String[]{String.valueOf(debtId)});

            ContentValues tv = new ContentValues();
            tv.put("kind", "PAYABLE".equals(direction) ? "EXPENSE" : "INCOME");
            tv.put("category_id", 0);
            tv.put("amount", actual);
            tv.put("period", "Borc ödənişi");
            tv.put("date", date);
            tv.put("note", debtName);
            tv.put("debt_id", debtId);
            db.insert("transactions", null, tv);

            db.setTransactionSuccessful();
        } finally {
            db.endTransaction();
        }
        return actual;
    }

    public Cursor debts() {
        return getReadableDatabase().rawQuery(
                "SELECT id AS _id,name,direction,principal,remaining,monthly,first_due,next_due,created FROM debts ORDER BY remaining DESC,id DESC",
                null);
    }

    public Cursor debtChoices(String direction) {
        return getReadableDatabase().rawQuery(
                "SELECT id AS _id,name,remaining FROM debts WHERE direction=? AND remaining>0.005 ORDER BY name",
                new String[]{direction});
    }

    public Cursor debtSchedule(long debtId) {
        return getReadableDatabase().rawQuery(
                "SELECT s.id AS _id,s.due_date,s.amount,s.paid,s.status,d.name,d.direction " +
                        "FROM debt_schedule s JOIN debts d ON d.id=s.debt_id WHERE s.debt_id=? ORDER BY s.due_date,s.id",
                new String[]{String.valueOf(debtId)});
    }

    public Cursor upcomingSchedules(int limit) {
        return getReadableDatabase().rawQuery(
                "SELECT s.id AS _id,s.debt_id,s.due_date,s.amount,s.paid,s.status,d.name,d.direction " +
                        "FROM debt_schedule s JOIN debts d ON d.id=s.debt_id " +
                        "WHERE s.status!='PAID' ORDER BY s.due_date,s.id LIMIT " + Math.max(1, limit),
                null);
    }

    public Cursor allOpenSchedules() {
        return getReadableDatabase().rawQuery(
                "SELECT s.id AS _id,s.debt_id,s.due_date,s.amount,s.paid,d.name,d.direction " +
                        "FROM debt_schedule s JOIN debts d ON d.id=s.debt_id WHERE s.status!='PAID' ORDER BY s.due_date",
                null);
    }

    public double sumTransactions(String kind, String monthPrefix) {
        String sql = "SELECT COALESCE(SUM(amount),0) FROM transactions WHERE kind=?";
        String[] args;
        if (monthPrefix != null) {
            sql += " AND date LIKE ?";
            args = new String[]{kind, monthPrefix + "%"};
        } else {
            args = new String[]{kind};
        }
        try (Cursor c = getReadableDatabase().rawQuery(sql, args)) {
            return c.moveToFirst() ? c.getDouble(0) : 0;
        }
    }

    public double sumDebtTransactions(String monthPrefix) {
        try (Cursor c = getReadableDatabase().rawQuery(
                "SELECT COALESCE(SUM(amount),0) FROM transactions WHERE debt_id>0 AND date LIKE ?",
                new String[]{monthPrefix + "%"})) {
            return c.moveToFirst() ? c.getDouble(0) : 0;
        }
    }

    public double totalBudgetSaved() {
        try (Cursor c = getReadableDatabase().rawQuery("SELECT COALESCE(SUM(saved),0) FROM budgets", null)) {
            return c.moveToFirst() ? c.getDouble(0) : 0;
        }
    }

    public double monthBudgetMoves(String monthPrefix) {
        try (Cursor c = getReadableDatabase().rawQuery(
                "SELECT COALESCE(SUM(amount),0) FROM budget_moves WHERE date LIKE ?",
                new String[]{monthPrefix + "%"})) {
            return c.moveToFirst() ? c.getDouble(0) : 0;
        }
    }

    public double totalDebtRemaining(String direction) {
        try (Cursor c = getReadableDatabase().rawQuery(
                "SELECT COALESCE(SUM(remaining),0) FROM debts WHERE direction=?",
                new String[]{direction})) {
            return c.moveToFirst() ? c.getDouble(0) : 0;
        }
    }

    public double totalDebtPrincipal(String direction) {
        try (Cursor c = getReadableDatabase().rawQuery(
                "SELECT COALESCE(SUM(principal),0) FROM debts WHERE direction=?",
                new String[]{direction})) {
            return c.moveToFirst() ? c.getDouble(0) : 0;
        }
    }

    public String topExpenseCategory(String monthPrefix) {
        try (Cursor c = getReadableDatabase().rawQuery(
                "SELECT COALESCE(cat.name,'Digər') AS n,COALESCE(SUM(t.amount),0) AS s " +
                        "FROM transactions t LEFT JOIN categories cat ON cat.id=t.category_id " +
                        "WHERE t.kind='EXPENSE' AND t.date LIKE ? GROUP BY cat.name ORDER BY s DESC LIMIT 1",
                new String[]{monthPrefix + "%"})) {
            if (c.moveToFirst()) return c.getString(0) + " • " + String.format(Locale.US, "%.2f", c.getDouble(1));
            return "Məlumat yoxdur";
        }
    }

    public Cursor monthTransactions(String monthPrefix) {
        return getReadableDatabase().rawQuery(
                "SELECT t.id AS _id,t.kind,t.amount,t.period,t.date,t.note,COALESCE(c.name,'Borc') AS category " +
                        "FROM transactions t LEFT JOIN categories c ON c.id=t.category_id " +
                        "WHERE t.date LIKE ? ORDER BY t.date DESC,t.id DESC LIMIT 100",
                new String[]{monthPrefix + "%"});
    }

    public String debtName(long debtId) {
        try (Cursor c = getReadableDatabase().rawQuery("SELECT name FROM debts WHERE id=?", new String[]{String.valueOf(debtId)})) {
            return c.moveToFirst() ? c.getString(0) : "Borc";
        }
    }
}
