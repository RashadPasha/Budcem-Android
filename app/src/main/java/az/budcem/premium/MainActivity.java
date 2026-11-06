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
    private static final int CREAM = Color.rgb(9, 11, 15);
    private static final int PURPLE = Color.rgb(255, 86, 24);
    private static final int PURPLE_SOFT = Color.rgb(38, 29, 27);
    private static final int YELLOW = Color.rgb(255, 126, 0);
    private static final int YELLOW_SOFT = Color.rgb(39, 30, 23);
    private static final int INK = Color.rgb(245, 246, 248);
    private static final int MUTED = Color.rgb(151, 157, 167);
    private static final int GREEN = Color.rgb(42, 197, 112);
    private static final int RED = Color.rgb(248, 86, 82);
    private static final int WHITE = Color.rgb(21, 24, 30);
    private static final String CHANNEL_ID = "budcem_due_dates";

    private final DecimalFormat money = new DecimalFormat("#,##0.00");
    private BudgetDb db;
    private String creatingDebtType = "PERSONAL";

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
        GradientDrawable d;
        if (color == PURPLE) {
            d = new GradientDrawable(GradientDrawable.Orientation.TL_BR,
                    new int[]{Color.rgb(255, 137, 0), Color.rgb(255, 79, 24), Color.rgb(205, 42, 12)});
        } else {
            d = new GradientDrawable();
            d.setColor(color);
        }
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
        TextView brand = tv("FINANCE CONTROL", 12, PURPLE, true);
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
        nav.addView(navButton("⌂  Ana", 0, activeTab == 0, v -> showHome()));
        nav.addView(navButton("＋  Əməliyyat", 1, activeTab == 1, v -> showTransactions()));
        nav.addView(navButton("⇄  Borc", 2, activeTab == 2, v -> showDebts()));
        nav.addView(navButton("▣  Kredit", 3, activeTab == 3, v -> showCredits()));
        nav.addView(navButton("▤  Hesabat", 4, activeTab == 4, v -> showAnalysis()));
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
        TextView heroLabel = tv("BALANS  •  DEBIT CARD", 13, Color.rgb(255, 238, 224), true);
        hero.addView(heroLabel);
        TextView heroValue = tv(azn(balance), 34, WHITE, true);
        heroValue.setPadding(0, dp(5), 0, dp(8));
        hero.addView(heroValue);
        hero.addView(tv("FINANCE CONTROL     •••• 365", 12, Color.rgb(255, 241, 230), true));
        hero.addView(tv("Sərbəst: " + azn(free) + "   |   Yığım: " + azn(saved), 12, Color.rgb(255, 241, 230), false));
        hero.addView(tv("●  "+LocalDate.now().format(DateTimeFormatter.ofPattern("dd MMMM yyyy", new Locale("az","AZ"))),11,Color.rgb(255,230,210),false));
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
        LinearLayout d1 = metricCard("Verəcəyim borc", azn(payable), Color.rgb(39, 30, 34));
        LinearLayout d2 = metricCard("Alacağım", azn(receivable), Color.rgb(25, 42, 38));
        row2.addView(d1, half);
        row2.addView(d2, half2);
        body.addView(row2);

        LinearLayout monthCard = card(WHITE);
        monthCard.addView(tv("Ayın vəziyyəti", 17, INK, true));
        double ratio = monthIncome > 0 ? (monthExpense / monthIncome) * 100 : 0;
        String ratioText = monthIncome <= 0 ? "Bu ay gəlir hələ əlavə edilməyib." :
                "Gəlirin " + Math.round(ratio) + "%‑i xərclənib. " + (ratio <= 70 ? "Yaxşı tempdir." : ratio <= 95 ? "Xərcləri bir az sıx nəzarətdə saxla." : "Xərclər gəlir limitinə çox yaxındır.");
        TextView rt = tv(ratioText, 14, MUTED, false); rt.setPadding(0, dp(8), 0, 0); monthCard.addView(rt);
        body.addView(monthCard);

        LinearLayout latest = card(WHITE);
        LinearLayout latestHead = new LinearLayout(this);
        latestHead.setOrientation(LinearLayout.HORIZONTAL);
        latestHead.setGravity(Gravity.CENTER_VERTICAL);
        latestHead.addView(tv("Son əməliyyatlar", 17, INK, true), new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        TextView all = tv("Hamısına bax  ›", 12, PURPLE, true);
        all.setOnClickListener(v -> showTransactions());
        latestHead.addView(all);
        latest.addView(latestHead);
        int latestCount = 0;
        try (Cursor c = db.latestTransactions(5)) {
            while (c.moveToNext()) {
                latestCount++;
                String kind = c.getString(c.getColumnIndexOrThrow("kind"));
                String category = c.getString(c.getColumnIndexOrThrow("category"));
                String date = c.getString(c.getColumnIndexOrThrow("date"));
                double amount = c.getDouble(c.getColumnIndexOrThrow("amount"));
                LinearLayout item = new LinearLayout(this);
                item.setOrientation(LinearLayout.HORIZONTAL);
                item.setGravity(Gravity.CENTER_VERTICAL);
                item.setPadding(0, dp(12), 0, dp(10));
                TextView left = tv(category + "\n" + date, 13, INK, true);
                TextView right = tv(("INCOME".equals(kind) ? "+ " : "− ") + azn(amount), 13,
                        "INCOME".equals(kind) ? GREEN : RED, true);
                item.addView(left, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
                item.addView(right);
                latest.addView(item);
                if (latestCount < 5) {
                    View line = new View(this);
                    line.setBackgroundColor(Color.rgb(43, 47, 55));
                    latest.addView(line, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(1)));
                }
            }
        }
        if (latestCount == 0) latest.addView(tv("Hələ əməliyyat əlavə edilməyib.", 13, MUTED, false));
        body.addView(latest);

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

        render("Finance Control", body, 0);
    }

    private void showTransactions() {
        LinearLayout body=vertical();
        LinearLayout hero=card(PURPLE);
        hero.addView(tv("ƏMƏLİYYAT MƏRKƏZİ",12,Color.WHITE,true));
        hero.addView(tv("Maliyyə hərəkətini seç və ayrıca qeyd et.",16,Color.WHITE,true));
        body.addView(hero);
        String[] labels={"Gəlir yarat","Xərc et","Borc ödə","Borc yarat","Kredit ödə","Kredit yarat","Planlanan xərc yarat"};
        String[] icons={"＋","−","↘","↗","▣","＋","◷"};
        int[] colors={GREEN,RED,PURPLE,YELLOW,GREEN,PURPLE,YELLOW};
        for(int i=0;i<labels.length;i++){
            final int action=i;
            LinearLayout item=card(WHITE);
            LinearLayout row=new LinearLayout(this); row.setGravity(Gravity.CENTER_VERTICAL);
            TextView ico=tv(icons[i],25,colors[i],true); ico.setGravity(Gravity.CENTER);
            LinearLayout.LayoutParams ip=new LinearLayout.LayoutParams(dp(48),dp(48)); row.addView(ico,ip);
            TextView name=tv(labels[i],16,INK,true); name.setPadding(dp(12),0,0,0);
            row.addView(name,new LinearLayout.LayoutParams(0,ViewGroup.LayoutParams.WRAP_CONTENT,1));
            TextView arrow=tv("›",25,MUTED,true);row.addView(arrow);
            item.addView(row);
            item.setOnClickListener(v->runOperation(action));
            body.addView(item);
        }
        LinearLayout cats=card(WHITE);
        cats.addView(tv("Kateqoriyalar",16,INK,true));
        cats.addView(tv("Gəlir və xərc kateqoriyalarını ayrıca idarə et.",13,MUTED,false));
        cats.setOnClickListener(v->showCategories()); body.addView(cats);
        render("Əməliyyatlar",body,1);
    }

    private void runOperation(int action) {
        switch(action){
            case 0: showTransactionDialog("INCOME"); break;
            case 1: showTransactionDialog("EXPENSE"); break;
            case 2: showDebtPaymentPicker("PERSONAL"); break;
            case 3: creatingDebtType="PERSONAL"; showAddDebtDialog(); break;
            case 4: showDebtPaymentPicker("CREDIT"); break;
            case 5: creatingDebtType="CREDIT"; showAddDebtDialog(); break;
            case 6: showAddPlannedExpenseDialog(); break;
        }
    }

    private void showDebtPaymentPicker(String type) {
        List<Choice> choices=new ArrayList<>();
        try(Cursor c=db.debtsByType(type)){
            while(c.moveToNext()) if(c.getDouble(c.getColumnIndexOrThrow("remaining"))>0.005)
                choices.add(new Choice(c.getLong(c.getColumnIndexOrThrow("_id")),c.getString(c.getColumnIndexOrThrow("name")),c.getDouble(c.getColumnIndexOrThrow("remaining"))));
        }
        if(choices.isEmpty()){toast(type.equals("CREDIT")?"Aktiv kredit yoxdur.":"Aktiv borc yoxdur.");return;}
        Spinner sp=spinner(choices);
        LinearLayout box=vertical();box.setPadding(dp(18),dp(8),dp(18),0);box.addView(sp);
        new AlertDialog.Builder(this).setTitle(type.equals("CREDIT")?"Kredit ödə":"Borc ödə").setView(box)
          .setNegativeButton("Ləğv et",null).setPositiveButton("Davam et",(d,w)->{
            Choice c=(Choice)sp.getSelectedItem();
            if(c!=null)showPayDebtDialog(c.id,c.label,c.extra,Math.min(c.extra,c.extra));
          }).show();
    }

    private void showAddPlannedExpenseDialog(){
        LinearLayout box=vertical();box.setPadding(dp(18),dp(8),dp(18),0);
        EditText name=input("Xərcin adı",false), category=input("Kateqoriya",false), amount=input("Məbləğ",true), date=input("Son tarix (YYYY-MM-DD)",false);
        date.setText(LocalDate.now().toString());
        Spinner mandatory=spinner(List.of("Məcburi xərc","İstəyə bağlı xərc"));
        box.addView(name);box.addView(category);box.addView(amount);box.addView(date);box.addView(mandatory);
        new AlertDialog.Builder(this).setTitle("Planlanan xərc yarat").setView(box).setNegativeButton("Ləğv et",null)
          .setPositiveButton("Yadda saxla",(d,w)->{
            double a=parseAmount(amount.getText().toString());
            if(name.getText().toString().trim().isEmpty()||category.getText().toString().trim().isEmpty()||a<=0||!validDate(date.getText().toString())){toast("Məlumatları düzgün doldur.");return;}
            db.addPlannedExpense(name.getText().toString(),category.getText().toString(),a,date.getText().toString(),mandatory.getSelectedItemPosition()==0);
            showPlannedExpenses();
          }).show();
    }

    private void showPlannedExpenses(){
        LinearLayout body=vertical();
        LinearLayout top=card(PURPLE_SOFT);top.addView(tv("Açıq planlanan xərclər",15,INK,true));
        top.addView(tv(azn(db.plannedExpenseOutstanding())+" qalıq öhdəlik",22,Color.WHITE,true));
        top.addView(actionButton("+ Planlanan xərc yarat",PURPLE,Color.WHITE,v->showAddPlannedExpenseDialog()));body.addView(top);
        int count=0;
        try(Cursor c=db.plannedExpenses()){
            while(c.moveToNext()){
                count++;long id=c.getLong(c.getColumnIndexOrThrow("_id"));String name=c.getString(c.getColumnIndexOrThrow("name"));
                String cat=c.getString(c.getColumnIndexOrThrow("category"));double amount=c.getDouble(c.getColumnIndexOrThrow("amount"));
                double paid=c.getDouble(c.getColumnIndexOrThrow("paid"));String date=c.getString(c.getColumnIndexOrThrow("due_date"));
                boolean mandatory=c.getInt(c.getColumnIndexOrThrow("mandatory"))==1;
                LinearLayout item=card(WHITE);item.addView(tv(name,16,INK,true));
                item.addView(tv(cat+" • "+date+" • "+(mandatory?"Məcburi":"İstəyə bağlı"),12,MUTED,false));
                item.addView(tv("Qalıq: "+azn(Math.max(0,amount-paid)),15,paid>=amount?GREEN:RED,true));
                if(paid<amount){item.addView(actionButton("Ödənişi qeyd et",PURPLE_SOFT,PURPLE,v->{
                    EditText val=input("Ödənilən məbləğ",true);val.setText(String.format(Locale.US,"%.2f",amount-paid));
                    new AlertDialog.Builder(this).setTitle(name).setView(val).setNegativeButton("Ləğv et",null).setPositiveButton("Təsdiq",(dd,ww)->{double x=parseAmount(val.getText().toString());if(x>0){db.payPlannedExpense(id,x);showPlannedExpenses();}}).show();
                }));}
                body.addView(item);
            }
        }
        if(count==0)body.addView(tv("Hələ planlanan xərc yoxdur.",14,MUTED,false));
        render("Planlanan xərclər",body,1);
    }


    private void showTransactionHistory() {
        LinearLayout body=vertical();
        String first=LocalDate.now().withDayOfMonth(1).toString();
        String last=LocalDate.now().toString();
        LinearLayout filter=card(WHITE);
        EditText from=input("Başlanğıc tarix (YYYY-MM-DD)",false); from.setText(first);
        EditText to=input("Son tarix (YYYY-MM-DD)",false); to.setText(last);
        filter.addView(tv("Tarix aralığı",15,INK,true)); filter.addView(from); filter.addView(to);
        LinearLayout list=vertical();
        Runnable load=()->{
            list.removeAllViews();
            if(!validDate(from.getText().toString())||!validDate(to.getText().toString())||
                    from.getText().toString().compareTo(to.getText().toString())>0) {
                list.addView(tv("Tarix aralığını düzgün daxil et.",13,RED,true)); return;
            }
            int n=0;
            try(Cursor c=db.transactionsBetween(from.getText().toString(),to.getText().toString())){
                while(c.moveToNext()){
                    n++;
                    long id=c.getLong(c.getColumnIndexOrThrow("_id"));
                    String kind=c.getString(c.getColumnIndexOrThrow("kind"));
                    String category=c.getString(c.getColumnIndexOrThrow("category"));
                    String date=c.getString(c.getColumnIndexOrThrow("date"));
                    String note=c.getString(c.getColumnIndexOrThrow("note"));
                    double amount=c.getDouble(c.getColumnIndexOrThrow("amount"));
                    LinearLayout item=card(WHITE);
                    LinearLayout row=new LinearLayout(this);row.setGravity(Gravity.CENTER_VERTICAL);
                    TextView details=tv(category+" • "+date+"\\n"+(note==null?"":note),13,INK,true);
                    row.addView(details,new LinearLayout.LayoutParams(0,ViewGroup.LayoutParams.WRAP_CONTENT,1));
                    TextView value=tv(("INCOME".equals(kind)?"+ ":"− ")+azn(amount),14,"INCOME".equals(kind)?GREEN:RED,true);
                    row.addView(value);item.addView(row);
                    if(!"PAYABLE".equals(kind)&&!"RECEIVABLE".equals(kind)){
                        LinearLayout actions=new LinearLayout(this);actions.setGravity(Gravity.END);
                        actions.addView(actionButton("✎ Redaktə",PURPLE_SOFT,PURPLE,v->editTransaction(id,amount,date,note)));
                        LinearLayout.LayoutParams delp=new LinearLayout.LayoutParams(dp(100),dp(44));delp.setMargins(dp(8),0,0,0);
                        actions.addView(actionButton("⌫ Sil",Color.rgb(54,30,32),RED,v->{
                            new AlertDialog.Builder(this).setTitle("Əməliyyatı sil")
                              .setMessage("Bu əməliyyatı silmək istədiyinə əminsən?")
                              .setNegativeButton("Ləğv et",null).setPositiveButton("Sil",(dd,ww)->{db.deleteTransaction(id);load.run();}).show();
                        }),delp);
                        item.addView(actions);
                    } else item.addView(tv("Borc/kredit ödənişi — cədvəldən idarə olunur.",11,MUTED,false));
                    list.addView(item);
                }
            }
            if(n==0)list.addView(tv("Bu tarix aralığında əməliyyat yoxdur.",13,MUTED,false));
        };
        filter.addView(actionButton("Tətbiq et",PURPLE,Color.WHITE,v->load.run()));
        body.addView(filter);body.addView(list);load.run();
        render("Əməliyyat tarixçəsi",body,1);
    }

    private void editTransaction(long id,double oldAmount,String oldDate,String oldNote) {
        LinearLayout box=vertical();box.setPadding(dp(18),dp(8),dp(18),0);
        EditText amount=input("Məbləğ",true);amount.setText(String.format(Locale.US,"%.2f",oldAmount));
        EditText date=input("Tarix (YYYY-MM-DD)",false);date.setText(oldDate);
        EditText note=input("Qeyd",false);note.setText(oldNote==null?"":oldNote);
        box.addView(amount);box.addView(date);box.addView(note);
        new AlertDialog.Builder(this).setTitle("Əməliyyatı redaktə et").setView(box)
          .setNegativeButton("Ləğv et",null).setPositiveButton("Yadda saxla",(d,w)->{
            double a=parseAmount(amount.getText().toString());
            if(a<=0||!validDate(date.getText().toString())){toast("Məbləğ və tarix düzgün deyil.");return;}
            db.updateTransaction(id,a,date.getText().toString(),note.getText().toString());
            showTransactionHistory();
          }).show();
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
                pb.setProgressBackgroundTintList(ColorStateList.valueOf(Color.rgb(48,53,61)));
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

    private void showDebts() { showDebtList("PERSONAL","Şəxsi borclar"); }
    private void showCredits() { showDebtList("CREDIT","Kreditlər"); }
    private void showDebtList(String type,String title) {
        LinearLayout body=vertical();
        LinearLayout top=card(PURPLE_SOFT);
        top.addView(tv(title,18,INK,true));
        top.addView(tv("Qalıq: "+azn(type.equals("CREDIT")?sumDebtType("CREDIT"):sumDebtType("PERSONAL")),15,PURPLE,true));
        top.addView(actionButton(type.equals("CREDIT")?"+ Kredit yarat":"+ Borc yarat",PURPLE,Color.WHITE,v->{creatingDebtType=type;showAddDebtDialog();}));
        body.addView(top);
        int n=0;
        try(Cursor c=db.debtsByType(type)){
            while(c.moveToNext()){
                n++;long id=c.getLong(c.getColumnIndexOrThrow("_id"));String name=c.getString(c.getColumnIndexOrThrow("name"));
                String dir=c.getString(c.getColumnIndexOrThrow("direction"));double principal=c.getDouble(c.getColumnIndexOrThrow("principal"));
                double remaining=c.getDouble(c.getColumnIndexOrThrow("remaining"));double monthly=c.getDouble(c.getColumnIndexOrThrow("monthly"));
                String due=c.isNull(c.getColumnIndexOrThrow("next_due"))?"Bağlanıb":c.getString(c.getColumnIndexOrThrow("next_due"));
                LinearLayout item=card(WHITE);item.addView(tv(name,17,INK,true));
                item.addView(tv(("PAYABLE".equals(dir)?"ÖDƏNİLƏCƏK":"ALINACAQ")+" • "+due,12,MUTED,false));
                item.addView(tv(azn(remaining),25,INK,true));
                item.addView(tv("İlkin: "+azn(principal)+" • Aylıq: "+azn(monthly),12,MUTED,false));
                item.addView(actionButton("Ödəniş et",PURPLE,Color.WHITE,v->showPayDebtDialog(id,name,remaining,monthly)));
                item.setOnClickListener(v->showDebtScheduleDialog(id,name));body.addView(item);
            }
        }
        if(n==0)body.addView(tv(type.equals("CREDIT")?"Kredit əlavə edilməyib.":"Borc əlavə edilməyib.",14,MUTED,false));
        render(title,body,type.equals("CREDIT")?3:2);
    }
    private double sumDebtType(String type){
        double sum=0;try(Cursor c=db.debtsByType(type)){while(c.moveToNext())sum+=c.getDouble(c.getColumnIndexOrThrow("remaining"));}return sum;
    }

    private void showAnalysis() {
        LinearLayout body=vertical();
        String month=LocalDate.now().format(DateTimeFormatter.ofPattern("yyyy-MM"));
        double inc=db.sumTransactions("INCOME",month),exp=db.sumTransactions("EXPENSE",month);
        double credits=sumDebtType("CREDIT"),debts=sumDebtType("PERSONAL");
        LinearLayout hero=card(PURPLE);hero.addView(tv("HESABAT MƏRKƏZİ",12,Color.WHITE,true));
        hero.addView(tv("Xalis nəticə: "+azn(inc-exp),27,Color.WHITE,true));body.addView(hero);
        body.addView(reportCard("Gəlir hesabatı","Tarix • məbləğ • kateqoriya • qalıq balans",inc,"INCOME",month));
        body.addView(reportCard("Xərc hesabatı","Tarix • məbləğ • kateqoriya • ümumi xərc",exp,"EXPENSE",month));
        body.addView(reportStatic("Kredit hesabatı","Aktiv kredit qalığı",credits));
        body.addView(reportStatic("Borc hesabatı","Şəxsi borc və alacaq qalığı",debts));
        body.addView(reportStatic("Planlanan ödənişlər","Ödənilməmiş planlanan xərclər",db.plannedExpenseOutstanding()));
        LinearLayout details=card(WHITE);details.addView(tv("Kateqoriya üzrə xərc",16,INK,true));
        details.addView(tv(db.topExpenseCategory(month),14,RED,true));body.addView(details);
        render("Hesabatlar",body,4);
    }
    private LinearLayout reportCard(String title,String subtitle,double value,String kind,String month){
        LinearLayout c=card(WHITE);c.addView(tv(title,16,INK,true));c.addView(tv(subtitle,12,MUTED,false));
        c.addView(tv(azn(value),22,kind.equals("INCOME")?GREEN:RED,true));
        try(Cursor cur=db.monthTransactions(month)){while(cur.moveToNext()){
            if(!kind.equals(cur.getString(cur.getColumnIndexOrThrow("kind"))))continue;
            c.addView(tv(cur.getString(cur.getColumnIndexOrThrow("date"))+" • "+cur.getString(cur.getColumnIndexOrThrow("category"))+" • "+azn(cur.getDouble(cur.getColumnIndexOrThrow("amount"))),12,INK,false));
        }}
        return c;
    }
    private LinearLayout reportStatic(String title,String subtitle,double value){
        LinearLayout c=card(WHITE);c.addView(tv(title,16,INK,true));c.addView(tv(subtitle,12,MUTED,false));c.addView(tv(azn(value),22,PURPLE,true));return c;
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
        e.setBackground(outlined(WHITE, 14, Color.rgb(57,62,71)));
        if (numeric) e.setInputType(android.text.InputType.TYPE_CLASS_NUMBER | android.text.InputType.TYPE_NUMBER_FLAG_DECIMAL);
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(50)); lp.setMargins(0,dp(7),0,0); e.setLayoutParams(lp);
        return e;
    }

    private Spinner spinner(List<?> items) {
        Spinner s = new Spinner(this);
        ArrayAdapter<Object> a = new ArrayAdapter<>(this, android.R.layout.simple_spinner_dropdown_item, new ArrayList<Object>((List<Object>)items));
        s.setAdapter(a);
        s.setBackground(outlined(WHITE, 14, Color.rgb(57,62,71)));
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
        LinearLayout box=vertical();box.setPadding(dp(18),dp(8),dp(18),0);
        EditText name=input(creatingDebtType.equals("CREDIT")?"Bank / kredit adı":"Borc / şəxs adı",false);
        Spinner direction=spinner(List.of("Mən ödəyəcəyəm","Mən alacağam"));
        EditText principal=input("Ümumi məbləğ",true),monthly=input("Aylıq ödəniş",true);
        EditText first=input("İlk ödəniş tarixi (YYYY-MM-DD)",false);first.setText(LocalDate.now().plusMonths(1).toString());
        box.addView(name);box.addView(direction);box.addView(principal);box.addView(monthly);box.addView(first);
        new AlertDialog.Builder(this).setTitle(creatingDebtType.equals("CREDIT")?"Kredit yarat":"Borc yarat").setView(box).setNegativeButton("Ləğv et",null)
          .setPositiveButton("Yarat",(d,w)->{
            double p=parseAmount(principal.getText().toString()),m=parseAmount(monthly.getText().toString());
            if(name.getText().toString().trim().isEmpty()||p<=0||m<=0||!validDate(first.getText().toString())){toast("Məlumatları düzgün doldur.");return;}
            String dir=direction.getSelectedItemPosition()==0?"PAYABLE":"RECEIVABLE";
            db.addDebt(name.getText().toString(),dir,p,m,first.getText().toString(),creatingDebtType);
            scheduleAllOpen(this);if(creatingDebtType.equals("CREDIT"))showCredits();else showDebts();
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
