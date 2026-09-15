package az.budcem.premium;

import android.Manifest;
import android.app.Activity;
import android.app.AlarmManager;
import android.app.AlertDialog;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.content.res.ColorStateList;
import android.database.Cursor;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.os.Build;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.AdapterView;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.ScrollView;
import android.widget.Spinner;
import android.widget.TextView;
import android.widget.Toast;

import java.text.DecimalFormat;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

public class MainActivity extends Activity {
    private static final int CREAM = Color.rgb(255, 248, 239);
    private static final int PURPLE = Color.rgb(123, 97, 255);
    private static final int PURPLE_SOFT = Color.rgb(236, 229, 255);
    private static final int YELLOW = Color.rgb(255, 201, 77);
    private static final int YELLOW_SOFT = Color.rgb(255, 244, 216);
    private static final int INK = Color.rgb(49, 46, 62);
    private static final int MUTED = Color.rgb(124, 120, 137);
    private static final int GREEN = Color.rgb(42, 153, 101);
    private static final int RED = Color.rgb(213, 76, 76);
    private static final int WHITE = Color.WHITE;
    private static final String CHANNEL_ID = "budcem_due_dates";

    private final DecimalFormat money = new DecimalFormat("#,##0.00");
    private BudgetDb db;

    static class Choice {
        long id;
        String label;
        double extra;
        Choice(long id, String label) { this(id, label, 0); }
        Choice(long id, String label, double extra) {
            this.id = id;
            this.label = label;
            this.extra = extra;
        }
        @Override public String toString() { return label; }
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        db = new BudgetDb(this);
        ensureNotificationChannel(this);
        if (Build.VERSION.SDK_INT >= 33 && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS}, 77);
        }
        scheduleAllOpen(this);
        showHome();
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }

    private GradientDrawable rounded(int color, int radius) {
        GradientDrawable d = new GradientDrawable();
        d.setColor(color);
        d.setCornerRadius(dp(radius));
        return d;
    }

    private GradientDrawable outlined(int color, int radius, int strokeColor) {
        GradientDrawable d = rounded(color, radius);
        d.setStroke(dp(1), strokeColor);
        return d;
    }

    private TextView tv(String text, float sp, int color, boolean bold) {
        TextView v = new TextView(this);
        v.setText(text);
        v.setTextSize(sp);
        v.setTextColor(color);
        v.setTypeface(Typeface.create("sans", bold ? Typeface.BOLD : Typeface.NORMAL));
        v.setLineSpacing(0, 1.08f);
        return v;
    }

    private Button actionButton(String text, int background, int foreground, View.OnClickListener listener) {
        Button b = new Button(this);
        b.setText(text);
        b.setTextColor(foreground);
        b.setTextSize(14);
        b.setAllCaps(false);
        b.setTypeface(Typeface.DEFAULT_BOLD);
        b.setBackground(rounded(background, 16));
        b.setPadding(dp(14), dp(4), dp(14), dp(4));
        b.setOnClickListener(listener);
        return b;
    }

    private LinearLayout card(int color) {
        LinearLayout c = new LinearLayout(this);
        c.setOrientation(LinearLayout.VERTICAL);
        c.setPadding(dp(18), dp(16), dp(18), dp(16));
        c.setBackground(rounded(color, 24));
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        lp.setMargins(0, 0, 0, dp(12));
        c.setLayoutParams(lp);
        return c;
    }

    private View gap(int h) {
        View v = new View(this);
        v.setLayoutParams(new LinearLayout.LayoutParams(1, dp(h)));
        return v;
    }

    private String azn(double v) {
        return money.format(v) + " ₼";
    }

    private void render(String title, LinearLayout body, int activeTab) {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(CREAM);

        LinearLayout header = new LinearLayout(this);
        header.setOrientation(LinearLayout.VERTICAL);
        header.setPadding(dp(20), dp(14), dp(20), dp(12));
        TextView brand = tv("BÜDCƏM", 12, PURPLE, true);
        brand.setLetterSpacing(0.12f);
        header.addView(brand);
        TextView h = tv(title, 25, INK, true);
        header.addView(h);
        root.addView(header);

        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        body.setPadding(dp(16), dp(6), dp(16), dp(24));
        scroll.addView(body);
        LinearLayout.LayoutParams slp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1);
        root.addView(scroll, slp);

        LinearLayout nav = new LinearLayout(this);
        nav.setOrientation(LinearLayout.HORIZONTAL);
        nav.setGravity(Gravity.CENTER);
        nav.setPadding(dp(6), dp(7), dp(6), dp(9));
        nav.setBackgroundColor(WHITE);
        nav.addView(navButton("Ana", 0, activeTab == 0, v -> showHome()));
        nav.addView(navButton("Əməliyyat", 1, activeTab == 1, v -> showTransactions()));
        nav.addView(navButton("Büdcə", 2, activeTab == 2, v -> showBudgets()));
        nav.addView(navButton("Borclar", 3, activeTab == 3, v -> showDebts()));
        nav.addView(navButton("Təhlil", 4, activeTab == 4, v -> showAnalysis()));
        root.addView(nav);
        setContentView(root);
    }

    private Button navButton(String label, int index, boolean active, View.OnClickListener click) {
        Button b = new Button(this);
        b.setText(label);
        b.setTextSize(11);
        b.setAllCaps(false);
        b.setTextColor(active ? PURPLE : MUTED);
        b.setTypeface(Typeface.DEFAULT, active ? Typeface.BOLD : Typeface.NORMAL);
        b.setBackgroundColor(Color.TRANSPARENT);
        b.setMinWidth(0);
        b.setMinimumWidth(0);
        b.setPadding(dp(2), dp(2), dp(2), dp(2));
        b.setOnClickListener(click);
        b.setLayoutParams(new LinearLayout.LayoutParams(0, dp(48), 1));
        return b;
    }

    private LinearLayout vertical() {
        LinearLayout l = new LinearLayout(this);
        l.setOrientation(LinearLayout.VERTICAL);
        return l;
    }

    private LinearLayout metricCard(String label, String value, int color) {
        LinearLayout c = new LinearLayout(this);
        c.setOrientation(LinearLayout.VERTICAL);
        c.setPadding(dp(14), dp(13), dp(14), dp(13));
        c.setBackground(rounded(color, 20));
        c.addView(tv(label, 12, MUTED, false));
        TextView val = tv(value, 17, INK, true);
        val.setPadding(0, dp(4), 0, 0);
        c.addView(val);
        return c;
    }

    private void showHome() {
        LinearLayout body = vertical();
        String month = LocalDate.now().format(DateTimeFormatter.ofPattern("yyyy-MM"));
        double income = db.sumTransactions("INCOME", null);
        double expense = db.sumTransactions("EXPENSE", null);
        double balance = income - expense;
        double saved = db.totalBudgetSaved();
        double free = balance - saved;
        double payable = db.totalDebtRemaining("PAYABLE");
        double receivable = db.totalDebtRemaining("RECEIVABLE");
        double monthIncome = db.sumTransactions("INCOME", month);
        double monthExpense = db.sumTransactions("EXPENSE", month);

        LinearLayout hero = card(PURPLE);
        TextView heroLabel = tv("Ümumi balans", 13, Color.rgb(232, 228, 255), false);
        hero.addView(heroLabel);
        TextView heroValue = tv(azn(balance), 34, WHITE, true);
        heroValue.setPadding(0, dp(5), 0, dp(8));
        hero.addView(heroValue);
        hero.addView(tv("Sərbəst istifadə: " + azn(free) + "   •   Yığım: " + azn(saved), 12, Color.rgb(240, 237, 255), false));
        body.addView(hero);

        LinearLayout row1 = new LinearLayout(this);
        row1.setOrientation(LinearLayout.HORIZONTAL);
        LinearLayout m1 = metricCard("Bu ay gəlir", azn(monthIncome), YELLOW_SOFT);
        LinearLayout m2 = metricCard("Bu ay xərc", azn(monthExpense), PURPLE_SOFT);
        LinearLayout.LayoutParams half = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1);
        half.setMargins(0, 0, dp(6), dp(10));
        row1.addView(m1, half);
        LinearLayout.LayoutParams half2 = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1);
        half2.setMargins(dp(6), 0, 0, dp(10));
        row1.addView(m2, half2);
        body.addView(row1);

        LinearLayout row2 = new LinearLayout(this);
        row2.setOrientation(LinearLayout.HORIZONTAL);
        LinearLayout d1 = metricCard("Verəcəyim borc", azn(payable), Color.rgb(255, 235, 226));
        LinearLayout d2 = metricCard("Alacağım", azn(receivable), Color.rgb(225, 246, 237));
        row2.addView(d1, half);
        row2.addView(d2, half2);
        body.addView(row2);

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
        String ratioText = monthIncome <= 0 ? "Bu ay gəlir hələ əlavə edilməyib." :
                "Gəlirin " + Math.round(ratio) + "%‑i xərclənib. " + (ratio <= 70 ? "Yaxşı tempdir." : ratio <= 95 ? "Xərcləri bir az sıx nəzarətdə saxla." : "Xərclər gəlir limitinə çox yaxındır.");
        TextView rt = tv(ratioText, 14, MUTED, false); rt.setPadding(0, dp(8), 0, 0); monthCard.addView(rt);
        body.addView(monthCard);

        LinearLayout due = card(WHITE);
        due.addView(tv("Yaxın ödənişlər", 17, INK, true));
        int added = 0;
        try (Cursor c = db.upcomingSchedules(5)) {
            while (c.moveToNext()) {
                String dueDate = c.getString(c.getColumnIndexOrThrow("due_date"));
                double amount = c.getDouble(c.getColumnIndexOrThrow("amount"));
                double paid = c.getDouble(c.getColumnIndexOrThrow("paid"));
                String name = c.getString(c.getColumnIndexOrThrow("name"));
                String direction = c.getString(c.getColumnIndexOrThrow("direction"));
                due.addView(gap(8));
                LinearLayout r = new LinearLayout(this);
                r.setOrientation(LinearLayout.HORIZONTAL);
                r.setGravity(Gravity.CENTER_VERTICAL);
                TextView left = tv(name + "\n" + dueDate, 13, INK, true);
                TextView right = tv(("PAYABLE".equals(direction) ? "− " : "+ ") + azn(Math.max(0, amount - paid)), 13, "PAYABLE".equals(direction) ? RED : GREEN, true);
                r.addView(left, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
                r.addView(right);
                due.addView(r);
                added++;
            }
        }
        if (added == 0) {
            TextView none = tv("Planlaşdırılmış ödəniş yoxdur.", 13, MUTED, false); none.setPadding(0, dp(10), 0, 0); due.addView(none);
        }
        body.addView(due);

        LinearLayout motivate = card(YELLOW_SOFT);
        motivate.addView(tv("Borcsuzluq motivasiyası", 16, INK, true));
        double principal = db.totalDebtPrincipal("PAYABLE");
        double progress = principal > 0 ? ((principal - payable) / principal) * 100 : 100;
        String msg;
        if (principal <= 0) msg = "Aktiv verəcəyin borc yoxdur. Bu üstünlüyü yığıma çevirmək üçün yaxşı zamandır.";
        else if (progress < 20) msg = "Başlanğıc mərhələsindəsən. Hər ödəniş borcun ağırlığını real olaraq azaldır.";
        else if (progress < 60) msg = "Artıq borcun təxminən " + Math.round(progress) + "%‑ni bağlamısan. Ritmi qorumaq ən böyük üstünlüyündür.";
        else if (progress < 90) msg = "Son hissəyə yaxınlaşırsan — bağlanmış hissə " + Math.round(progress) + "%‑dir. Yeni borc yaratmadan davam et.";
        else msg = "Final mərhələsidir. Borcun " + Math.round(progress) + "%‑i artıq arxada qalıb.";
        TextView mt = tv(msg, 14, INK, false); mt.setPadding(0, dp(8), 0, 0); motivate.addView(mt);
        body.addView(motivate);

        render("Maliyyə panelim", body, 0);
    }

    private void showTransactions() {
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
                String kind = c.getString(c.getColumnIndexOrThrow("kind"));
                double amount = c.getDouble(c.getColumnIndexOrThrow("amount"));
                String date = c.getString(c.getColumnIndexOrThrow("date"));
                String category = c.getString(c.getColumnIndexOrThrow("category"));
                String note = c.getString(c.getColumnIndexOrThrow("note"));
                LinearLayout rr = new LinearLayout(this);
                rr.setOrientation(LinearLayout.HORIZONTAL);
                rr.setGravity(Gravity.CENTER_VERTICAL);
                rr.setPadding(0, dp(10), 0, dp(10));
                String sub = category + " • " + date + (note == null || note.isEmpty() ? "" : "\n" + note);
                TextView l = tv(sub, 13, INK, false);
                TextView a = tv(("INCOME".equals(kind) ? "+ " : "− ") + azn(amount), 14, "INCOME".equals(kind) ? GREEN : RED, true);
                rr.addView(l, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
                rr.addView(a);
                list.addView(rr);
                if (!c.isLast()) {
                    View line = new View(this); line.setBackgroundColor(Color.rgb(241,239,235)); line.setLayoutParams(new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(1))); list.addView(line);
                }
            }
        }
        if (n == 0) { TextView e = tv("Bu ay üçün əməliyyat yoxdur.", 13, MUTED, false); e.setPadding(0,dp(12),0,0); list.addView(e); }
        body.addView(list);
        render("Gəlir və xərclər", body, 1);
    }

    private void showBudgets() {
        LinearLayout body = vertical();
        LinearLayout top = card(YELLOW_SOFT);
        top.addView(tv("Yığım büdcələri", 18, INK, true));
        top.addView(tv("Məqsəd yarat, pul ayırdıqca irəliləyişini gör.", 13, MUTED, false));
        Button add = actionButton("+ Yeni büdcə", YELLOW, INK, v -> showAddBudgetDialog());
        LinearLayout.LayoutParams ap = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(48)); ap.setMargins(0,dp(12),0,0); top.addView(add, ap);
        body.addView(top);

        int n = 0;
        try (Cursor c = db.budgets()) {
            while (c.moveToNext()) {
                n++;
                long id = c.getLong(c.getColumnIndexOrThrow("_id"));
                String name = c.getString(c.getColumnIndexOrThrow("name"));
                double target = c.getDouble(c.getColumnIndexOrThrow("target"));
                double saved = c.getDouble(c.getColumnIndexOrThrow("saved"));
                LinearLayout bc = card(WHITE);
                bc.addView(tv(name, 18, INK, true));
                bc.addView(tv(azn(saved) + " / " + azn(target), 13, MUTED, false));
                ProgressBar pb = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
                pb.setMax(1000);
                int pr = target > 0 ? (int)Math.min(1000, Math.round((saved / target) * 1000)) : 0;
                pb.setProgress(pr);
                pb.setProgressTintList(ColorStateList.valueOf(PURPLE));
                pb.setProgressBackgroundTintList(ColorStateList.valueOf(Color.rgb(237,233,229)));
                LinearLayout.LayoutParams pp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(10)); pp.setMargins(0,dp(12),0,dp(12));
                bc.addView(pb, pp);
                double pct = target > 0 ? saved * 100 / target : 0;
                bc.addView(tv(Math.round(pct) + "% tamamlanıb", 12, PURPLE, true));
                Button deposit = actionButton("Pul əlavə et", PURPLE_SOFT, PURPLE, v -> showBudgetDepositDialog(id, name));
                LinearLayout.LayoutParams bp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(46)); bp.setMargins(0,dp(10),0,0); bc.addView(deposit, bp);
                body.addView(bc);
            }
        }
        if (n == 0) {
            LinearLayout empty = card(WHITE); empty.addView(tv("Hələ büdcə yaratmamısan.", 14, MUTED, false)); body.addView(empty);
        }
        render("Büdcələrim", body, 2);
    }

    private void showDebts() {
        LinearLayout body = vertical();
        LinearLayout top = card(PURPLE_SOFT);
        top.addView(tv("Borc və alacaqlar", 18, INK, true));
        top.addView(tv("Verəcəyim: " + azn(db.totalDebtRemaining("PAYABLE")) + "   •   Alacağım: " + azn(db.totalDebtRemaining("RECEIVABLE")), 13, PURPLE, true));
        Button add = actionButton("+ Yeni borc / alacaq", PURPLE, WHITE, v -> showAddDebtDialog());
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
                String nextDue = c.isNull(c.getColumnIndexOrThrow("next_due")) ? "Bağlanıb" : c.getString(c.getColumnIndexOrThrow("next_due"));

                LinearLayout dc = card(WHITE);
                LinearLayout titleRow = new LinearLayout(this); titleRow.setOrientation(LinearLayout.HORIZONTAL); titleRow.setGravity(Gravity.CENTER_VERTICAL);
                titleRow.addView(tv(name, 18, INK, true), new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
                TextView badge = tv("PAYABLE".equals(dir) ? "VERƏCƏYİM" : "ALACAĞIM", 10, "PAYABLE".equals(dir) ? RED : GREEN, true);
                badge.setPadding(dp(8),dp(5),dp(8),dp(5)); badge.setBackground(rounded("PAYABLE".equals(dir) ? Color.rgb(255,235,226) : Color.rgb(225,246,237), 12)); titleRow.addView(badge);
                dc.addView(titleRow);
                TextView rem = tv(azn(remaining), 25, INK, true); rem.setPadding(0,dp(8),0,0); dc.addView(rem);
                dc.addView(tv("İlkin: " + azn(principal) + "   •   Aylıq: " + azn(monthly) + "\nNövbəti tarix: " + nextDue, 12, MUTED, false));
                double closed = principal > 0 ? (principal - remaining) / principal : 1;
                ProgressBar pb = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal); pb.setMax(1000); pb.setProgress((int)Math.max(0,Math.min(1000,closed*1000))); pb.setProgressTintList(ColorStateList.valueOf("PAYABLE".equals(dir) ? PURPLE : GREEN));
                LinearLayout.LayoutParams pp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(9)); pp.setMargins(0,dp(10),0,dp(10)); dc.addView(pb, pp);
                LinearLayout actions = new LinearLayout(this); actions.setOrientation(LinearLayout.HORIZONTAL);
                Button pay = actionButton("Ödəniş et", "PAYABLE".equals(dir) ? PURPLE : GREEN, WHITE, v -> showPayDebtDialog(id, name, remaining, monthly));
                Button table = actionButton("Cədvəl", PURPLE_SOFT, PURPLE, v -> showDebtScheduleDialog(id, name));
                actions.addView(pay, new LinearLayout.LayoutParams(0,dp(46),1)); LinearLayout.LayoutParams tp = new LinearLayout.LayoutParams(0,dp(46),1); tp.setMargins(dp(8),0,0,0); actions.addView(table,tp); dc.addView(actions);
                body.addView(dc);
            }
        }
        if (n == 0) { LinearLayout e = card(WHITE); e.addView(tv("Borc və alacaq əlavə etdikdə aylıq cədvəl burada görünəcək.", 14, MUTED, false)); body.addView(e); }
        render("Borclarım", body, 3);
    }

    private void showAnalysis() {
        LinearLayout body = vertical();
        String month = LocalDate.now().format(DateTimeFormatter.ofPattern("yyyy-MM"));
        double inc = db.sumTransactions("INCOME", month);
        double exp = db.sumTransactions("EXPENSE", month);
        double savedMonth = db.monthBudgetMoves(month);
        double debtPaid = db.sumDebtTransactions(month);
        double net = inc - exp;
        double savingsRate = inc > 0 ? savedMonth * 100 / inc : 0;
        double expenseRate = inc > 0 ? exp * 100 / inc : 0;
        double debtBurden = inc > 0 ? debtPaid * 100 / inc : 0;

        LinearLayout hero = card(PURPLE);
        hero.addView(tv("Aylıq maliyyə nəticəsi", 13, Color.rgb(235,231,255), false));
        hero.addView(tv(azn(net), 30, WHITE, true));
        hero.addView(tv(net >= 0 ? "Bu ay gəlir xərci qarşılayır." : "Bu ay xərc gəlirdən çoxdur.", 13, WHITE, false));
        body.addView(hero);

        LinearLayout rates = card(WHITE);
        rates.addView(tv("Əsas göstəricilər", 17, INK, true));
        rates.addView(analysisLine("Xərc / gəlir", Math.round(expenseRate) + "%", expenseRate <= 80 ? GREEN : RED));
        rates.addView(analysisLine("Yığıma ayrılan", Math.round(savingsRate) + "%", PURPLE));
        rates.addView(analysisLine("Borc ödəniş yükü", Math.round(debtBurden) + "%", debtBurden <= 30 ? GREEN : RED));
        rates.addView(analysisLine("Ən böyük xərc kateqoriyası", db.topExpenseCategory(month) + " ₼", INK));
        body.addView(rates);

        LinearLayout insight = card(YELLOW_SOFT);
        insight.addView(tv("Ağıllı ay təhlili", 17, INK, true));
        List<String> tips = new ArrayList<>();
        if (inc <= 0) tips.add("Gəliri əlavə etdikdə ayın real yük və qənaət faizləri görünəcək.");
        else {
            if (expenseRate > 100) tips.add("Xərc gəliri keçib. Növbəti ay ilk hədəf xərcləri ən azı gəlirin 90%-indən aşağı salmaqdır.");
            else if (expenseRate > 85) tips.add("Balans müsbət olsa da təhlükəsizlik payın zəifdir. Ən böyük kateqoriyada kiçik azalma ciddi fərq yarada bilər.");
            else tips.add("Xərc nisbətin idarəolunandır. Qalan hissənin bir qismini məqsəd büdcəsinə yönəltmək borc və yığım planını sürətləndirər.");
            if (debtBurden > 40) tips.add("Borc ödənişləri aylıq gəlirin böyük hissəsini tutur. Yeni öhdəlik götürməmək hazırda ən güclü qərardır.");
            if (savingsRate < 5 && net > 0) tips.add("Müsbət qalıq var, amma yığıma az yönəlib. Kiçik avtomatik hədəf belə ayın sonunda görünən nəticə yaradar.");
            if (savingsRate >= 10) tips.add("Yığım tempin yaxşıdır. Məqsəd büdcəsini davamlı saxlamaq maliyyə ehtiyatını böyüdür.");
        }
        for (String tip : tips) { TextView t = tv("• " + tip, 14, INK, false); t.setPadding(0,dp(9),0,0); insight.addView(t); }
        body.addView(insight);

        double p = db.totalDebtPrincipal("PAYABLE");
        double r = db.totalDebtRemaining("PAYABLE");
        LinearLayout debtMot = card(PURPLE_SOFT);
        debtMot.addView(tv("Borc bağlama göstəricisi", 17, INK, true));
        if (p <= 0) {
            debtMot.addView(tv("Aktiv verəcəyin borc yoxdur.", 14, GREEN, true));
        } else {
            double done = (p-r)*100/p;
            debtMot.addView(tv(Math.round(done) + "% bağlanıb", 23, PURPLE, true));
            debtMot.addView(tv("Qalıq: " + azn(r) + ". Davamlı kiçik ödənişlər də borcun müddətini qısaldır.", 13, MUTED, false));
        }
        body.addView(debtMot);
        render("Aylıq təhlil", body, 4);
    }

    private LinearLayout analysisLine(String label, String value, int color) {
        LinearLayout r = new LinearLayout(this); r.setOrientation(LinearLayout.HORIZONTAL); r.setGravity(Gravity.CENTER_VERTICAL); r.setPadding(0,dp(11),0,dp(5));
        r.addView(tv(label, 13, MUTED, false), new LinearLayout.LayoutParams(0,ViewGroup.LayoutParams.WRAP_CONTENT,1));
        r.addView(tv(value, 14, color, true));
        return r;
    }

    private void showCategories() {
        LinearLayout body = vertical();
        LinearLayout top = card(WHITE);
        top.addView(tv("Üst / alt kateqoriya", 17, INK, true));
        LinearLayout rr = new LinearLayout(this); rr.setOrientation(LinearLayout.HORIZONTAL);
        rr.addView(actionButton("+ Üst", YELLOW, INK, v -> showAddParentCategoryDialog()), new LinearLayout.LayoutParams(0,dp(46),1));
        LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(0,dp(46),1); p.setMargins(dp(8),0,0,0); rr.addView(actionButton("+ Alt", PURPLE_SOFT, PURPLE, v -> showAddChildCategoryDialog()), p);
        top.addView(rr);
        body.addView(top);

        LinearLayout list = card(WHITE);
        try (Cursor c = db.allCategories()) {
            while (c.moveToNext()) {
                String kind = c.getString(c.getColumnIndexOrThrow("kind"));
                String label = c.getString(c.getColumnIndexOrThrow("label"));
                TextView item = tv(("INCOME".equals(kind) ? "GƏLİR   " : "XƏRC   ") + label, 14, INK, false); item.setPadding(0,dp(8),0,dp(8)); list.addView(item);
            }
        }
        body.addView(list);
        render("Kateqoriyalar", body, 1);
    }

    private EditText input(String hint, boolean numeric) {
        EditText e = new EditText(this);
        e.setHint(hint);
        e.setTextColor(INK);
        e.setHintTextColor(MUTED);
        e.setTextSize(15);
        e.setSingleLine(true);
        e.setPadding(dp(13),dp(11),dp(13),dp(11));
        e.setBackground(outlined(WHITE, 14, Color.rgb(226,222,216)));
        if (numeric) e.setInputType(android.text.InputType.TYPE_CLASS_NUMBER | android.text.InputType.TYPE_NUMBER_FLAG_DECIMAL);
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(50)); lp.setMargins(0,dp(7),0,0); e.setLayoutParams(lp);
        return e;
    }

    private Spinner spinner(List<?> items) {
        Spinner s = new Spinner(this);
        ArrayAdapter<Object> a = new ArrayAdapter<>(this, android.R.layout.simple_spinner_dropdown_item, new ArrayList<Object>((List<Object>)items));
        s.setAdapter(a);
        s.setBackground(outlined(WHITE, 14, Color.rgb(226,222,216)));
        s.setPadding(dp(8),0,dp(8),0);
        s.setLayoutParams(new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(52)));
        return s;
    }

    private List<Choice> categoryChoices(String kind) {
        List<Choice> out = new ArrayList<>();
        try (Cursor c = db.categoryChoices(kind)) {
            while (c.moveToNext()) out.add(new Choice(c.getLong(c.getColumnIndexOrThrow("_id")), c.getString(c.getColumnIndexOrThrow("label"))));
        }
        return out;
    }

    private List<Choice> parentChoices(String kind) {
        List<Choice> out = new ArrayList<>();
        try (Cursor c = db.parentCategories(kind)) {
            while (c.moveToNext()) out.add(new Choice(c.getLong(c.getColumnIndexOrThrow("_id")), c.getString(c.getColumnIndexOrThrow("name"))));
        }
        return out;
    }

    private List<Choice> debtChoices(String direction) {
        List<Choice> out = new ArrayList<>();
        try (Cursor c = db.debtChoices(direction)) {
            while (c.moveToNext()) out.add(new Choice(c.getLong(c.getColumnIndexOrThrow("_id")), c.getString(c.getColumnIndexOrThrow("name")), c.getDouble(c.getColumnIndexOrThrow("remaining"))));
        }
        return out;
    }

    private void showTransactionDialog(String kind) {
        LinearLayout box = vertical(); box.setPadding(dp(18),dp(8),dp(18),0);
        List<Choice> cats = categoryChoices(kind);
        if (cats.isEmpty()) { toast("Əvvəl kateqoriya yarat."); showCategories(); return; }
        Spinner cat = spinner(cats);
        EditText amount = input("Məbləğ", true);
        EditText date = input("Tarix (YYYY-MM-DD)", false); date.setText(LocalDate.now().toString());
        List<String> periods = List.of("Birdəfəlik", "Həftəlik", "Aylıq", "İllik");
        Spinner period = spinner(periods);
        EditText note = input("Qeyd (istəyə bağlı)", false);
        box.addView(tv("Kateqoriya",12,MUTED,true)); box.addView(cat); box.addView(amount); box.addView(date); box.addView(period); box.addView(note);

        Spinner obligation = null;
        Spinner debtSpinner = null;
        List<Choice> debts = null;
        if ("EXPENSE".equals(kind)) {
            box.addView(tv("Öhdəlik",12,MUTED,true));
            obligation = spinner(List.of("Adi xərc", "Borc ödənişi"));
            box.addView(obligation);
            debts = debtChoices("PAYABLE");
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
                    if (a <= 0 || !validDate(date.getText().toString())) { toast("Məbləğ və tarixi düzgün daxil et."); return; }
                    Choice cc = (Choice)cat.getSelectedItem();
                    String per = String.valueOf(period.getSelectedItem());
                    String dt = date.getText().toString();
                    if ("EXPENSE".equals(kind) && fObligation != null && fObligation.getSelectedItemPosition() == 1) {
                        Choice debtChoice = (Choice)fDebtSpinner.getSelectedItem();
                        if (debtChoice == null || debtChoice.id == 0) { toast("Borc seçilməyib, xərc adi xərc kimi yazıldı."); db.addTransaction(kind, cc.id, a, per, dt, note.getText().toString(), 0); }
                        else { db.payDebt(debtChoice.id, a, dt); scheduleAllOpen(this); }
                    } else {
                        db.addTransaction(kind, cc.id, a, per, dt, note.getText().toString(), 0);
                    }
                    showTransactions();
                }).show();
    }

    private void showAddParentCategoryDialog() {
        LinearLayout box = vertical(); box.setPadding(dp(18),dp(8),dp(18),0);
        EditText name = input("Kateqoriya adı", false);
        Spinner kind = spinner(List.of("Xərc", "Gəlir"));
        box.addView(name); box.addView(kind);
        new AlertDialog.Builder(this).setTitle("Üst kateqoriya").setView(box).setNegativeButton("Ləğv et",null).setPositiveButton("Yarat",(d,w)->{
            if (name.getText().toString().trim().isEmpty()) { toast("Ad boş ola bilməz."); return; }
            db.addCategory(name.getText().toString(),0,kind.getSelectedItemPosition()==0?"EXPENSE":"INCOME"); showCategories();
        }).show();
    }

    private void showAddChildCategoryDialog() {
        LinearLayout box = vertical(); box.setPadding(dp(18),dp(8),dp(18),0);
        EditText name = input("Alt kateqoriya adı", false);
        Spinner kind = spinner(List.of("Xərc", "Gəlir"));
        List<Choice> parents = parentChoices("EXPENSE");
        Spinner parent = spinner(parents);
        box.addView(name); box.addView(kind); box.addView(tv("Üst kateqoriya",12,MUTED,true)); box.addView(parent);
        kind.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
            @Override public void onItemSelected(AdapterView<?> p, View v, int pos, long id) {
                List<Choice> fresh = parentChoices(pos==0?"EXPENSE":"INCOME");
                ArrayAdapter<Choice> aa = new ArrayAdapter<>(MainActivity.this, android.R.layout.simple_spinner_dropdown_item, fresh); parent.setAdapter(aa);
            }
            @Override public void onNothingSelected(AdapterView<?> p) {}
        });
        new AlertDialog.Builder(this).setTitle("Alt kateqoriya").setView(box).setNegativeButton("Ləğv et",null).setPositiveButton("Yarat",(d,w)->{
            Choice pc = (Choice)parent.getSelectedItem();
            if (pc == null || name.getText().toString().trim().isEmpty()) { toast("Ad və üst kateqoriya tələb olunur."); return; }
            db.addCategory(name.getText().toString(),pc.id,kind.getSelectedItemPosition()==0?"EXPENSE":"INCOME"); showCategories();
        }).show();
    }

    private void showAddBudgetDialog() {
        LinearLayout box = vertical(); box.setPadding(dp(18),dp(8),dp(18),0);
        EditText name = input("Məqsəd adı — məsələn Ehtiyat fondu", false);
        EditText target = input("Hədəf məbləğ", true);
        box.addView(name); box.addView(target);
        new AlertDialog.Builder(this).setTitle("Yeni büdcə").setView(box).setNegativeButton("Ləğv et",null).setPositiveButton("Yarat",(d,w)->{
            double t=parseAmount(target.getText().toString()); if(name.getText().toString().trim().isEmpty()||t<=0){toast("Ad və hədəf məbləğ tələb olunur.");return;} db.addBudget(name.getText().toString(),t); showBudgets();
        }).show();
    }

    private void showBudgetDepositDialog(long id, String name) {
        LinearLayout box = vertical(); box.setPadding(dp(18),dp(8),dp(18),0);
        EditText amount=input("Əlavə ediləcək məbləğ",true); EditText date=input("Tarix",false); date.setText(LocalDate.now().toString()); box.addView(amount); box.addView(date);
        new AlertDialog.Builder(this).setTitle(name+" — pul əlavə et").setView(box).setNegativeButton("Ləğv et",null).setPositiveButton("Əlavə et",(d,w)->{
            double a=parseAmount(amount.getText().toString()); if(a<=0||!validDate(date.getText().toString())){toast("Məbləğ və tarix düzgün deyil.");return;} db.addBudgetMoney(id,a,date.getText().toString()); showBudgets();
        }).show();
    }

    private void showAddDebtDialog() {
        LinearLayout box=vertical(); box.setPadding(dp(18),dp(8),dp(18),0);
        EditText name=input("Borc / şəxs / kredit adı",false);
        Spinner direction=spinner(List.of("Mən ödəyəcəyəm", "Mən alacağam"));
        EditText principal=input("Ümumi məbləğ",true);
        EditText monthly=input("Aylıq ödəniş",true);
        EditText first=input("İlk ödəniş tarixi (YYYY-MM-DD)",false); first.setText(LocalDate.now().plusMonths(1).toString());
        box.addView(name); box.addView(direction); box.addView(principal); box.addView(monthly); box.addView(first);
        new AlertDialog.Builder(this).setTitle("Yeni borc / alacaq").setView(box).setNegativeButton("Ləğv et",null).setPositiveButton("Cədvəl yarat",(d,w)->{
            double p=parseAmount(principal.getText().toString()); double m=parseAmount(monthly.getText().toString());
            if(name.getText().toString().trim().isEmpty()||p<=0||m<=0||!validDate(first.getText().toString())){toast("Məlumatları düzgün doldur.");return;}
            String dir=direction.getSelectedItemPosition()==0?"PAYABLE":"RECEIVABLE"; db.addDebt(name.getText().toString(),dir,p,m,first.getText().toString()); scheduleAllOpen(this); showDebts();
        }).show();
    }

    private void showPayDebtDialog(long debtId, String name, double remaining, double monthly) {
        if(remaining<=0.005){toast("Bu borc artıq bağlanıb.");return;}
        LinearLayout box=vertical(); box.setPadding(dp(18),dp(8),dp(18),0);
        EditText amount=input("Ödəniş məbləği",true); amount.setText(String.format(Locale.US,"%.2f",Math.min(remaining,monthly)));
        EditText date=input("Ödəniş tarixi",false); date.setText(LocalDate.now().toString()); box.addView(amount);box.addView(date);
        new AlertDialog.Builder(this).setTitle(name+" — ödəniş").setView(box).setNegativeButton("Ləğv et",null).setPositiveButton("Ödə",(d,w)->{
            double a=parseAmount(amount.getText().toString()); if(a<=0||!validDate(date.getText().toString())){toast("Məbləğ və tarix düzgün deyil.");return;} double paid=db.payDebt(debtId,a,date.getText().toString()); toast("Ödənildi: "+azn(paid)); scheduleAllOpen(this); showDebts();
        }).show();
    }

    private void showDebtScheduleDialog(long debtId, String name) {
        LinearLayout list=vertical(); list.setPadding(dp(16),dp(8),dp(16),dp(8));
        int n=0;
        try(Cursor c=db.debtSchedule(debtId)){
            while(c.moveToNext()){
                n++;
                String due=c.getString(c.getColumnIndexOrThrow("due_date")); double amount=c.getDouble(c.getColumnIndexOrThrow("amount")); double paid=c.getDouble(c.getColumnIndexOrThrow("paid")); String status=c.getString(c.getColumnIndexOrThrow("status"));
                LinearLayout row=new LinearLayout(this); row.setOrientation(LinearLayout.HORIZONTAL); row.setGravity(Gravity.CENTER_VERTICAL); row.setPadding(0,dp(8),0,dp(8));
                String st="PAID".equals(status)?"Ödənib":"PARTIAL".equals(status)?"Qismən":"Gözləyir";
                row.addView(tv(due+"\n"+st,13,"PAID".equals(status)?GREEN:INK,true),new LinearLayout.LayoutParams(0,ViewGroup.LayoutParams.WRAP_CONTENT,1));
                double left=Math.max(0,amount-paid); row.addView(tv(azn(left),13,"PAID".equals(status)?GREEN:RED,true));
                if(!"PAID".equals(status)){
                    Button b=actionButton("Ödə",PURPLE_SOFT,PURPLE,v->{ db.payDebt(debtId,left,LocalDate.now().toString()); scheduleAllOpen(this); toast("Ödəniş qeydə alındı."); });
                    LinearLayout.LayoutParams bp=new LinearLayout.LayoutParams(dp(76),dp(42)); bp.setMargins(dp(8),0,0,0); row.addView(b,bp);
                }
                list.addView(row);
            }
        }
        if(n==0)list.addView(tv("Cədvəl boşdur.",13,MUTED,false));
        ScrollView s=new ScrollView(this);s.addView(list);
        new AlertDialog.Builder(this).setTitle(name+" — aylıq cədvəl").setView(s).setPositiveButton("Bağla",(d,w)->showDebts()).show();
    }

    private double parseAmount(String text) {
        try { return Double.parseDouble(text.trim().replace(",", ".")); } catch (Exception e) { return 0; }
    }

    private boolean validDate(String date) {
        try { LocalDate.parse(date); return true; } catch (DateTimeParseException e) { return false; }
    }

    private void toast(String s) { Toast.makeText(this,s,Toast.LENGTH_SHORT).show(); }

    public static void ensureNotificationChannel(Context context) {
        if(Build.VERSION.SDK_INT>=26){
            NotificationManager nm=(NotificationManager)context.getSystemService(Context.NOTIFICATION_SERVICE);
            NotificationChannel ch=new NotificationChannel(CHANNEL_ID,"Büdcəm ödəniş xatırlatmaları",NotificationManager.IMPORTANCE_HIGH);
            ch.setDescription("Borc ödəniş tarixləri yaxınlaşanda xəbərdarlıq edir.");
            nm.createNotificationChannel(ch);
        }
    }

    public static void scheduleAllOpen(Context context) {
        BudgetDb db=new BudgetDb(context);
        int count=0;
        try(Cursor c=db.allOpenSchedules()){
            while(c.moveToNext() && count<180){
                long sid=c.getLong(c.getColumnIndexOrThrow("_id"));
                String due=c.getString(c.getColumnIndexOrThrow("due_date"));
                double amount=c.getDouble(c.getColumnIndexOrThrow("amount"))-c.getDouble(c.getColumnIndexOrThrow("paid"));
                String name=c.getString(c.getColumnIndexOrThrow("name"));
                scheduleReminder(context,sid,name,due,amount,3);
                scheduleReminder(context,sid,name,due,amount,0);
                count++;
            }
        } catch(Exception ignored) {}
    }

    private static void scheduleReminder(Context context,long scheduleId,String debtName,String dueDate,double amount,int daysBefore){
        try{
            LocalDate d=LocalDate.parse(dueDate).minusDays(daysBefore);
            LocalDateTime when=d.atTime(9,0);
            long trigger=when.atZone(ZoneId.systemDefault()).toInstant().toEpochMilli();
            if(trigger<=System.currentTimeMillis()) return;
            Intent i=new Intent(context,ReminderReceiver.class);
            i.putExtra("name",debtName); i.putExtra("due",dueDate); i.putExtra("amount",amount); i.putExtra("days",daysBefore);
            int request=(int)Math.min(Integer.MAX_VALUE-10,scheduleId*10+(daysBefore==0?1:2));
            PendingIntent pi=PendingIntent.getBroadcast(context,request,i,PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);
            AlarmManager am=(AlarmManager)context.getSystemService(Context.ALARM_SERVICE);
            if(Build.VERSION.SDK_INT>=23) am.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP,trigger,pi); else am.set(AlarmManager.RTC_WAKEUP,trigger,pi);
        }catch(Exception ignored){}
    }

    public static class ReminderReceiver extends BroadcastReceiver {
        @Override public void onReceive(Context context, Intent intent) {
            ensureNotificationChannel(context);
            String name=intent.getStringExtra("name"); String due=intent.getStringExtra("due"); double amount=intent.getDoubleExtra("amount",0); int days=intent.getIntExtra("days",0);
            Intent open=new Intent(context,MainActivity.class);
            PendingIntent pi=PendingIntent.getActivity(context,9000+(int)(System.currentTimeMillis()%1000),open,PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);
            String text=(days==0?"Bu gün ödəniş günüdür: ":"Ödənişə 3 gün qalıb: ")+name+" • "+String.format(Locale.US,"%.2f ₼",amount)+" • "+due;
            Notification.Builder b=Build.VERSION.SDK_INT>=26?new Notification.Builder(context,CHANNEL_ID):new Notification.Builder(context);
            b.setSmallIcon(az.budcem.premium.R.drawable.ic_launcher).setContentTitle("Büdcəm • Ödəniş xatırlatması").setContentText(text).setStyle(new Notification.BigTextStyle().bigText(text)).setAutoCancel(true).setContentIntent(pi).setPriority(Notification.PRIORITY_HIGH);
            NotificationManager nm=(NotificationManager)context.getSystemService(Context.NOTIFICATION_SERVICE);
            if(Build.VERSION.SDK_INT<33 || context.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)==PackageManager.PERMISSION_GRANTED) nm.notify((int)(System.currentTimeMillis()%100000),b.build());
        }
    }

    public static class BootReceiver extends BroadcastReceiver {
        @Override public void onReceive(Context context, Intent intent) {
            if(Intent.ACTION_BOOT_COMPLETED.equals(intent.getAction())) scheduleAllOpen(context);
        }
    }
}
