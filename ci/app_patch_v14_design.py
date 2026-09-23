from pathlib import Path
import re

MAIN = Path("app/src/main/java/az/budcem/premium/MainActivity.java")
main = MAIN.read_text(encoding="utf-8")

def replace_once(text, pattern, replacement, label):
    updated, count = re.subn(pattern, lambda m: replacement, text, count=1, flags=re.S)
    if count == 1:
        return updated

    marker_patterns = {
        "Premium shell": (r"private\s+void\s+render\s*\(", r"private\s+LinearLayout\s+vertical\s*\(\s*\)\s*\{"),
        "Dashboard": (r"private\s+void\s+showHome\s*\(\s*\)\s*\{", r"private\s+void\s+showTransactions\s*\(\s*\)\s*\{"),
        "Transactions / income / create": (r"private\s+void\s+showTransactions\s*\(\s*\)\s*\{", r"private\s+void\s+showReceivePendingDialog\s*\(long\s+pendingId,\s*double\s+amount\)\s*\{"),
        "Separated debt/credit/reports/more": (r"private\s+void\s+showDebts\s*\(\s*\)\s*\{", r"private\s+void\s+showAnalysis\s*\(\s*\)\s*\{"),
    }
    if label in marker_patterns:
        start_re, end_re = marker_patterns[label]
        sm = re.search(start_re, text)
        em = re.search(end_re, text[sm.end():] if sm else "")
        if sm and em:
            end_abs_start = sm.end() + em.start()
            end_abs_end = sm.end() + em.end()
            line_start = text.rfind("\n", 0, sm.start()) + 1
            return text[:line_start] + replacement + text[end_abs_end:]

    raise SystemExit(f"{label}: expected once, found {count}; render={text.find('render(')}, vertical={text.find('vertical(')}")

def exact_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected once, found {count}")
    return text.replace(old, new, 1)

# Premium blue / white palette.
replacements = {
    "private static final int CREAM = Color.rgb(255, 248, 239);":
        "private static final int CREAM = Color.rgb(246, 249, 253);",
    "private static final int PURPLE = Color.rgb(123, 97, 255);":
        "private static final int PURPLE = Color.rgb(29, 78, 216);",
    "private static final int PURPLE_SOFT = Color.rgb(236, 229, 255);":
        "private static final int PURPLE_SOFT = Color.rgb(232, 240, 255);",
    "private static final int YELLOW = Color.rgb(255, 201, 77);":
        "private static final int YELLOW = Color.rgb(56, 189, 248);",
    "private static final int YELLOW_SOFT = Color.rgb(255, 244, 216);":
        "private static final int YELLOW_SOFT = Color.rgb(236, 248, 255);",
    "private static final int INK = Color.rgb(49, 46, 62);":
        "private static final int INK = Color.rgb(15, 23, 42);",
    "private static final int MUTED = Color.rgb(124, 120, 137);":
        "private static final int MUTED = Color.rgb(100, 116, 139);",
    "private static final int GREEN = Color.rgb(42, 153, 101);":
        "private static final int GREEN = Color.rgb(16, 185, 129);",
    "private static final int RED = Color.rgb(213, 76, 76);":
        "private static final int RED = Color.rgb(239, 68, 68);",
}
for old, new in replacements.items():
    if old in main:
        main = main.replace(old, new, 1)

# Modern shell + simplified navigation.
shell = r'''    private void render(String title, LinearLayout body, int activeTab) {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(CREAM);

        LinearLayout header = new LinearLayout(this);
        header.setOrientation(LinearLayout.VERTICAL);
        header.setPadding(dp(18), dp(14), dp(18), dp(10));

        LinearLayout brandRow = new LinearLayout(this);
        brandRow.setOrientation(LinearLayout.HORIZONTAL);
        brandRow.setGravity(Gravity.CENTER_VERTICAL);
        TextView brand = tv("Büdcəm", 25, INK, true);
        brandRow.addView(brand, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));

        TextView badge = tv("PREMIUM", 10, PURPLE, true);
        badge.setPadding(dp(9), dp(5), dp(9), dp(5));
        badge.setBackground(rounded(PURPLE_SOFT, 14));
        brandRow.addView(badge);
        header.addView(brandRow);

        TextView subtitle = tv(title, 12, MUTED, false);
        subtitle.setPadding(0, dp(3), 0, 0);
        header.addView(subtitle);
        root.addView(header);

        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        body.setPadding(dp(14), dp(4), dp(14), dp(28));
        scroll.addView(body);
        root.addView(scroll, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1));

        LinearLayout navWrap = new LinearLayout(this);
        navWrap.setOrientation(LinearLayout.VERTICAL);
        navWrap.setPadding(dp(8), dp(5), dp(8), dp(8));
        navWrap.setBackgroundColor(WHITE);

        LinearLayout nav = new LinearLayout(this);
        nav.setOrientation(LinearLayout.HORIZONTAL);
        nav.setGravity(Gravity.CENTER);
        nav.addView(navButton("Ana", "⌂", activeTab == 0, v -> showHome()));
        nav.addView(navButton("Əməliyyat", "⇄", activeTab == 1, v -> showTransactions()));
        nav.addView(navButton("Əlavə et", "+", activeTab == 2, v -> showCreateTransaction()));
        nav.addView(navButton("Hesabat", "▥", activeTab == 3, v -> showReports()));
        nav.addView(navButton("Daha", "•••", activeTab == 4, v -> showMore()));
        navWrap.addView(nav);
        root.addView(navWrap);
        setContentView(root);
    }

    private LinearLayout navButton(String label, String icon, boolean active, View.OnClickListener click) {
        LinearLayout item = new LinearLayout(this);
        item.setOrientation(LinearLayout.VERTICAL);
        item.setGravity(Gravity.CENTER);
        item.setPadding(dp(3), dp(5), dp(3), dp(4));
        item.setBackground(active ? rounded(PURPLE_SOFT, 18) : rounded(Color.TRANSPARENT, 18));

        TextView iconView = tv(icon, "+".equals(icon) ? 24 : 19, active ? PURPLE : MUTED, true);
        iconView.setGravity(Gravity.CENTER);
        item.addView(iconView, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(28)));

        TextView labelView = tv(label, 10, active ? PURPLE : MUTED, active);
        labelView.setGravity(Gravity.CENTER);
        labelView.setSingleLine(true);
        item.addView(labelView, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(20)));

        item.setOnClickListener(click);
        item.setLayoutParams(new LinearLayout.LayoutParams(0, dp(58), 1));
        return item;
    }

    private LinearLayout dashboardMetric(String label, String value, int accent) {
        LinearLayout c = new LinearLayout(this);
        c.setOrientation(LinearLayout.VERTICAL);
        c.setPadding(dp(14), dp(13), dp(14), dp(13));
        c.setBackground(outlined(WHITE, 20, Color.rgb(226, 232, 240)));
        TextView dot = tv("●  " + label, 11, accent, true);
        c.addView(dot);
        TextView valueView = tv(value, 18, INK, true);
        valueView.setPadding(0, dp(6), 0, 0);
        c.addView(valueView);
        return c;
    }

    private LinearLayout menuTile(String icon, String title, String subtitle, View.OnClickListener click) {
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setGravity(Gravity.CENTER_VERTICAL);
        row.setPadding(dp(14), dp(12), dp(14), dp(12));
        row.setBackground(outlined(WHITE, 18, Color.rgb(226, 232, 240)));

        TextView iv = tv(icon, 21, PURPLE, true);
        iv.setGravity(Gravity.CENTER);
        iv.setBackground(rounded(PURPLE_SOFT, 14));
        iv.setPadding(dp(9), dp(7), dp(9), dp(7));
        row.addView(iv);

        LinearLayout text = vertical();
        text.setPadding(dp(12),0,0,0);
        text.addView(tv(title, 14, INK, true));
        text.addView(tv(subtitle, 11, MUTED, false));
        row.addView(text, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));

        row.addView(tv("›", 24, MUTED, false));
        row.setOnClickListener(click);
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        lp.setMargins(0,0,0,dp(8));
        row.setLayoutParams(lp);
        return row;
    }

    private Button filterChip(String text, boolean active, View.OnClickListener click) {
        Button b = new Button(this);
        b.setText(text);
        b.setAllCaps(false);
        b.setTextSize(11);
        b.setTypeface(Typeface.DEFAULT, active ? Typeface.BOLD : Typeface.NORMAL);
        b.setTextColor(active ? WHITE : PURPLE);
        b.setBackground(rounded(active ? PURPLE : PURPLE_SOFT, 16));
        b.setPadding(dp(10), 0, dp(10), 0);
        b.setOnClickListener(click);
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(0, dp(38), 1);
        lp.setMargins(dp(3), 0, dp(3), 0);
        b.setLayoutParams(lp);
        return b;
    }

    private LinearLayout vertical() {'''
main = replace_once(
    main,
    r'''    private void render\(String title, LinearLayout body, int activeTab\) \{.*?    private LinearLayout vertical\(\) \{''',
    shell,
    "Premium shell"
)

# Cleaner home dashboard.
home = r'''    private void showHome() {
        LinearLayout body = vertical();
        String month = LocalDate.now().format(DateTimeFormatter.ofPattern("yyyy-MM"));

        double income = db.sumTransactions("INCOME", null);
        double expense = db.sumTransactions("EXPENSE", null);
        double balance = income - expense;
        double monthIncome = db.sumTransactions("INCOME", month);
        double monthExpense = db.sumTransactions("EXPENSE", month);
        double pending = db.totalPendingIncome();
        double saved = db.totalBudgetSaved();
        double debt = db.totalDebtRemainingByType("SIMPLE","PAYABLE");
        double credit = db.totalDebtRemainingByType("CREDIT","PAYABLE");

        LinearLayout hero = card(PURPLE);
        hero.setPadding(dp(20),dp(20),dp(20),dp(20));
        hero.addView(tv("Faktiki balans", 12, Color.rgb(219,234,254), false));
        TextView total = tv(azn(balance), 33, WHITE, true);
        total.setPadding(0,dp(4),0,dp(7));
        hero.addView(total);
        hero.addView(tv("Gəlir " + azn(income) + "   •   Xərc " + azn(expense), 12, Color.rgb(219,234,254), false));
        body.addView(hero);

        LinearLayout row1 = new LinearLayout(this); row1.setOrientation(LinearLayout.HORIZONTAL);
        LinearLayout.LayoutParams l = new LinearLayout.LayoutParams(0,ViewGroup.LayoutParams.WRAP_CONTENT,1); l.setMargins(0,0,dp(5),dp(10));
        LinearLayout.LayoutParams r = new LinearLayout.LayoutParams(0,ViewGroup.LayoutParams.WRAP_CONTENT,1); r.setMargins(dp(5),0,0,dp(10));
        row1.addView(dashboardMetric("Bu ay gəlir", azn(monthIncome), GREEN), l);
        row1.addView(dashboardMetric("Bu ay xərc", azn(monthExpense), RED), r);
        body.addView(row1);

        LinearLayout row2 = new LinearLayout(this); row2.setOrientation(LinearLayout.HORIZONTAL);
        row2.addView(dashboardMetric("Yolda", azn(pending), YELLOW), l);
        row2.addView(dashboardMetric("Yığım", azn(saved), PURPLE), r);
        body.addView(row2);

        LinearLayout row3 = new LinearLayout(this); row3.setOrientation(LinearLayout.HORIZONTAL);
        row3.addView(dashboardMetric("Borc", azn(debt), RED), l);
        row3.addView(dashboardMetric("Kredit", azn(credit), PURPLE), r);
        body.addView(row3);

        LinearLayout quick = card(WHITE);
        quick.addView(tv("Sürətli keçidlər",16,INK,true));
        TextView qsub = tv("Ən çox istifadə etdiyin bölmələr",11,MUTED,false); qsub.setPadding(0,dp(2),0,dp(10)); quick.addView(qsub);
        quick.addView(menuTile("+", "Yeni əməliyyat", "Gəlir, xərc və ödəniş əlavə et", v -> showCreateTransaction()));
        quick.addView(menuTile("₼", "Gəlirlər", "Faktiki və yolda olan vəsaitlər", v -> showIncome()));
        quick.addView(menuTile("▤", "Borc və kredit", "Öhdəlikləri ayrıca idarə et", v -> showDebts()));
        quick.addView(menuTile("▥", "Hesabatlar", "Balans və maliyyə hesabatlarına bax", v -> showReports()));
        body.addView(quick);

        LinearLayout recent = card(WHITE);
        recent.addView(tv("Son əməliyyatlar",16,INK,true));
        int count=0;
        try(Cursor c=db.transactionsBetween("0001-01-01","9999-12-31",false)){
            while(c.moveToNext() && count<5){
                count++;
                String kind=c.getString(c.getColumnIndexOrThrow("kind"));
                double amount=c.getDouble(c.getColumnIndexOrThrow("amount"));
                String date=c.getString(c.getColumnIndexOrThrow("date"));
                String category=c.getString(c.getColumnIndexOrThrow("category"));
                String period=c.getString(c.getColumnIndexOrThrow("period"));
                long debtId=c.getLong(c.getColumnIndexOrThrow("debt_id"));
                String source=debtId>0?("Kredit ödənişi".equals(period)?"Kredit ödənişi":"Borc ödənişi"):category;

                LinearLayout rr=new LinearLayout(this); rr.setOrientation(LinearLayout.HORIZONTAL); rr.setGravity(Gravity.CENTER_VERTICAL); rr.setPadding(0,dp(9),0,dp(9));
                LinearLayout left=vertical();
                left.addView(tv(source,13,INK,true));
                left.addView(tv(date,11,MUTED,false));
                rr.addView(left,new LinearLayout.LayoutParams(0,ViewGroup.LayoutParams.WRAP_CONTENT,1));
                rr.addView(tv(("INCOME".equals(kind)?"+ ":"− ")+azn(amount),14,"INCOME".equals(kind)?GREEN:RED,true));
                recent.addView(rr);
            }
        }
        if(count==0) recent.addView(tv("Hələ əməliyyat yoxdur.",12,MUTED,false));
        body.addView(recent);

        render("Maliyyə dashboard", body, 0);
    }

    private void showTransactions() {'''
main = replace_once(main, r'''    private void showHome\(\) \{.*?    private void showTransactions\(\) \{''', home, "Dashboard")

# Transactions list, income page, create page.
transactions = r'''    private void showTransactions() {
        LinearLayout body = vertical();

        LinearLayout top = card(WHITE);
        top.addView(tv("Əməliyyatlar",18,INK,true));
        top.addView(tv("Tarixə görə süz, redaktə et və ya sil.",12,MUTED,false));

        LinearLayout preset1=new LinearLayout(this); preset1.setOrientation(LinearLayout.HORIZONTAL); preset1.setPadding(0,dp(10),0,dp(6));
        preset1.addView(filterChip("Bu gün",false,v->{
            String d=LocalDate.now().toString(); txFilterFrom=d; txFilterTo=d; showTransactions();
        }));
        preset1.addView(filterChip("Bu həftə",false,v->{
            LocalDate now=LocalDate.now(); LocalDate start=now.minusDays(now.getDayOfWeek().getValue()-1);
            txFilterFrom=start.toString(); txFilterTo=now.toString(); showTransactions();
        }));
        preset1.addView(filterChip("Bu ay",false,v->{
            LocalDate now=LocalDate.now(); txFilterFrom=now.withDayOfMonth(1).toString(); txFilterTo=now.toString(); showTransactions();
        }));
        preset1.addView(filterChip("Hamısı",txFilterFrom.isEmpty()&&txFilterTo.isEmpty(),v->{
            txFilterFrom=""; txFilterTo=""; showTransactions();
        }));
        top.addView(preset1);

        LinearLayout dates=new LinearLayout(this); dates.setOrientation(LinearLayout.HORIZONTAL);
        EditText from=datePickerInput("Başlanğıc",txFilterFrom,true);
        EditText to=datePickerInput("Son",txFilterTo,true);
        from.setLayoutParams(new LinearLayout.LayoutParams(0,dp(48),1));
        LinearLayout.LayoutParams tlp=new LinearLayout.LayoutParams(0,dp(48),1); tlp.setMargins(dp(8),0,0,0); to.setLayoutParams(tlp);
        dates.addView(from); dates.addView(to);
        top.addView(dates);

        LinearLayout filterActions=new LinearLayout(this); filterActions.setOrientation(LinearLayout.HORIZONTAL); filterActions.setPadding(0,dp(8),0,0);
        Button apply=actionButton("Tətbiq et",PURPLE,WHITE,v->{
            String f=from.getText().toString().trim(); String t=to.getText().toString().trim();
            if((!f.isEmpty()&&!validDate(f))||(!t.isEmpty()&&!validDate(t))||(!f.isEmpty()&&!t.isEmpty()&&f.compareTo(t)>0)){toast("Tarix aralığını yoxla.");return;}
            txFilterFrom=f; txFilterTo=t; showTransactions();
        });
        Button add=actionButton("+ Yeni",PURPLE_SOFT,PURPLE,v->showCreateTransaction());
        filterActions.addView(apply,new LinearLayout.LayoutParams(0,dp(44),1));
        LinearLayout.LayoutParams alp=new LinearLayout.LayoutParams(0,dp(44),1); alp.setMargins(dp(8),0,0,0); filterActions.addView(add,alp);
        top.addView(filterActions);
        body.addView(top);

        String f=txFilterFrom.isEmpty()?"0001-01-01":txFilterFrom;
        String t=txFilterTo.isEmpty()?"9999-12-31":txFilterTo;
        double inc=db.sumBetween("INCOME",f,t);
        double exp=db.sumBetween("EXPENSE",f,t);

        LinearLayout mini = new LinearLayout(this); mini.setOrientation(LinearLayout.HORIZONTAL);
        LinearLayout.LayoutParams ml=new LinearLayout.LayoutParams(0,ViewGroup.LayoutParams.WRAP_CONTENT,1); ml.setMargins(0,0,dp(5),dp(10));
        LinearLayout.LayoutParams mr=new LinearLayout.LayoutParams(0,ViewGroup.LayoutParams.WRAP_CONTENT,1); mr.setMargins(dp(5),0,0,dp(10));
        mini.addView(dashboardMetric("Gəlir",azn(inc),GREEN),ml);
        mini.addView(dashboardMetric("Xərc",azn(exp),RED),mr);
        body.addView(mini);

        int n=0;
        try(Cursor c=db.transactionsBetween(f,t,false)){
            while(c.moveToNext()){
                n++;
                long txId=c.getLong(c.getColumnIndexOrThrow("_id"));
                String kind=c.getString(c.getColumnIndexOrThrow("kind"));
                long categoryId=c.getLong(c.getColumnIndexOrThrow("category_id"));
                double amount=c.getDouble(c.getColumnIndexOrThrow("amount"));
                String period=c.getString(c.getColumnIndexOrThrow("period"));
                String date=c.getString(c.getColumnIndexOrThrow("date"));
                String category=c.getString(c.getColumnIndexOrThrow("category"));
                String note=c.getString(c.getColumnIndexOrThrow("note"));
                long debtId=c.getLong(c.getColumnIndexOrThrow("debt_id"));
                String source=debtId>0?("Kredit ödənişi".equals(period)?"Kredit ödənişi":"Borc ödənişi"):category;

                LinearLayout item=card(WHITE);
                LinearLayout row=new LinearLayout(this); row.setOrientation(LinearLayout.HORIZONTAL); row.setGravity(Gravity.CENTER_VERTICAL);
                TextView badge=tv("INCOME".equals(kind)?"CR":"DR",10,"INCOME".equals(kind)?GREEN:RED,true);
                badge.setPadding(dp(8),dp(5),dp(8),dp(5)); badge.setBackground(rounded("INCOME".equals(kind)?Color.rgb(220,252,231):Color.rgb(254,226,226),12));
                row.addView(badge);

                LinearLayout info=vertical(); info.setPadding(dp(10),0,0,0);
                info.addView(tv(source,14,INK,true));
                info.addView(tv(date+(note==null||note.isEmpty()?"":" • "+note),11,MUTED,false));
                row.addView(info,new LinearLayout.LayoutParams(0,ViewGroup.LayoutParams.WRAP_CONTENT,1));
                row.addView(tv(("INCOME".equals(kind)?"+ ":"− ")+azn(amount),15,"INCOME".equals(kind)?GREEN:RED,true));
                item.addView(row);

                LinearLayout actions=new LinearLayout(this); actions.setOrientation(LinearLayout.HORIZONTAL); actions.setPadding(0,dp(10),0,0);
                Button edit=actionButton("Redaktə",PURPLE_SOFT,PURPLE,v->showEditTransactionDialog(txId,kind,categoryId,amount,period,date,note,debtId));
                Button del=actionButton("Sil",Color.rgb(254,242,242),RED,v->confirmDeleteTransaction(txId,debtId));
                actions.addView(edit,new LinearLayout.LayoutParams(0,dp(40),1));
                LinearLayout.LayoutParams dlp=new LinearLayout.LayoutParams(0,dp(40),1); dlp.setMargins(dp(8),0,0,0); actions.addView(del,dlp);
                item.addView(actions);
                body.addView(item);
            }
        }
        if(n==0){
            LinearLayout empty=card(WHITE); empty.addView(tv("Bu tarix aralığında əməliyyat yoxdur.",13,MUTED,false)); body.addView(empty);
        }

        render("Əməliyyat tarixçəsi", body, 1);
    }

    private void showIncome() {
        LinearLayout body=vertical();
        String month=LocalDate.now().format(DateTimeFormatter.ofPattern("yyyy-MM"));

        LinearLayout hero=card(PURPLE);
        hero.addView(tv("Bu ay faktiki gəlir",12,Color.rgb(219,234,254),false));
        hero.addView(tv(azn(db.sumTransactions("INCOME",month)),28,WHITE,true));
        hero.addView(tv("Yolda olan vəsait: "+azn(db.totalPendingIncome()),12,Color.rgb(219,234,254),false));
        body.addView(hero);

        LinearLayout action=card(WHITE);
        action.addView(menuTile("+","Gəlir əlavə et","Faktiki və ya yolda olan gəlir yarat",v->showTransactionDialog("INCOME")));
        body.addView(action);

        LinearLayout pending=card(WHITE);
        pending.addView(tv("Yolda olan vəsaitlər",16,INK,true));
        int pc=0;
        try(Cursor c=db.pendingIncomes()){
            while(c.moveToNext()){
                pc++;
                long id=c.getLong(c.getColumnIndexOrThrow("_id"));
                long categoryId=c.getLong(c.getColumnIndexOrThrow("category_id"));
                double amount=c.getDouble(c.getColumnIndexOrThrow("amount"));
                String expected=c.isNull(c.getColumnIndexOrThrow("expected_date"))?"":c.getString(c.getColumnIndexOrThrow("expected_date"));
                String note=c.getString(c.getColumnIndexOrThrow("note"));
                String category=c.getString(c.getColumnIndexOrThrow("category"));

                LinearLayout item=vertical(); item.setPadding(0,dp(10),0,dp(8));
                LinearLayout rr=new LinearLayout(this); rr.setOrientation(LinearLayout.HORIZONTAL); rr.setGravity(Gravity.CENTER_VERTICAL);
                LinearLayout left=vertical();
                left.addView(tv(category,13,INK,true));
                left.addView(tv(expected.isEmpty()?"Tarix seçilməyib":"Gözlənilir: "+expected,11,MUTED,false));
                rr.addView(left,new LinearLayout.LayoutParams(0,ViewGroup.LayoutParams.WRAP_CONTENT,1));
                rr.addView(tv(azn(amount),14,PURPLE,true));
                item.addView(rr);

                LinearLayout ac=new LinearLayout(this); ac.setOrientation(LinearLayout.HORIZONTAL); ac.setPadding(0,dp(7),0,0);
                Button receive=actionButton("Daxil oldu",GREEN,WHITE,v->showReceivePendingDialog(id,amount));
                Button edit=actionButton("Redaktə",PURPLE_SOFT,PURPLE,v->showEditPendingIncomeDialog(id,categoryId,amount,expected,note));
                ac.addView(receive,new LinearLayout.LayoutParams(0,dp(38),1));
                LinearLayout.LayoutParams ep=new LinearLayout.LayoutParams(0,dp(38),1); ep.setMargins(dp(7),0,0,0); ac.addView(edit,ep);
                item.addView(ac); pending.addView(item);
            }
        }
        if(pc==0) pending.addView(tv("Yolda olan vəsait yoxdur.",12,MUTED,false));
        body.addView(pending);

        LinearLayout recent=card(WHITE);
        recent.addView(tv("Son gəlirlər",16,INK,true));
        int n=0;
        try(Cursor c=db.transactionsBetween("0001-01-01","9999-12-31",false)){
            while(c.moveToNext()&&n<12){
                if(!"INCOME".equals(c.getString(c.getColumnIndexOrThrow("kind")))) continue;
                n++;
                String category=c.getString(c.getColumnIndexOrThrow("category"));
                String date=c.getString(c.getColumnIndexOrThrow("date"));
                double amount=c.getDouble(c.getColumnIndexOrThrow("amount"));
                LinearLayout rr=new LinearLayout(this); rr.setOrientation(LinearLayout.HORIZONTAL); rr.setGravity(Gravity.CENTER_VERTICAL); rr.setPadding(0,dp(8),0,dp(8));
                LinearLayout left=vertical(); left.addView(tv(category,13,INK,true)); left.addView(tv(date,11,MUTED,false));
                rr.addView(left,new LinearLayout.LayoutParams(0,ViewGroup.LayoutParams.WRAP_CONTENT,1));
                rr.addView(tv("+ "+azn(amount),14,GREEN,true)); recent.addView(rr);
            }
        }
        if(n==0) recent.addView(tv("Gəlir əməliyyatı yoxdur.",12,MUTED,false));
        body.addView(recent);
        render("Gəlirlər", body, 4);
    }

    private void showCreateTransaction() {
        LinearLayout body=vertical();

        LinearLayout intro=card(PURPLE);
        intro.addView(tv("Yeni əməliyyat",22,WHITE,true));
        intro.addView(tv("Nə əlavə etmək istəyirsən?",12,Color.rgb(219,234,254),false));
        body.addView(intro);

        body.addView(menuTile("+","Gəlir əlavə et","Faktiki və ya yolda olan vəsait",v->showTransactionDialog("INCOME")));
        body.addView(menuTile("−","Xərc əlavə et","İstənilən tarixə xərc yaz",v->showTransactionDialog("EXPENSE")));
        body.addView(menuTile("↘","Borc ödənişi","Xərc yaradarkən Borc ödənişi seç",v->showTransactionDialog("EXPENSE")));
        body.addView(menuTile("₼","Kredit ödənişi","Kredit cədvəlindən qismən və ya tam ödə",v->showCredits()));
        body.addView(menuTile("▤","Yeni borc","Birdəfəlik borc / alacaq yarat",v->showAddDebtDialog()));
        body.addView(menuTile("▥","Yeni kredit","Aylıq ödəniş cədvəli yarat",v->showAddCreditDialog()));

        render("Əməliyyat yarat", body, 2);
    }

    private void showReceivePendingDialog(long pendingId, double amount) {'''
main = replace_once(
    main,
    r'''    private void showTransactions\(\) \{.*?    private void showReceivePendingDialog\(long pendingId, double amount\) \{''',
    transactions,
    "Transactions / income / create"
)

# Separate debt, credit, reports and more pages.
pages = r'''    private void showDebts() {
        LinearLayout body=vertical();

        LinearLayout hero=card(PURPLE);
        hero.addView(tv("Birdəfəlik borclar",12,Color.rgb(219,234,254),false));
        hero.addView(tv(azn(db.totalDebtRemainingByType("SIMPLE","PAYABLE")),28,WHITE,true));
        hero.addView(tv("Alacağım: "+azn(db.totalDebtRemainingByType("SIMPLE","RECEIVABLE")),12,Color.rgb(219,234,254),false));
        body.addView(hero);

        LinearLayout add=card(WHITE);
        add.addView(menuTile("+","Yeni borc / alacaq","Şəxs və məbləği əlavə et",v->showAddDebtDialog()));
        body.addView(add);

        int n=0;
        try(Cursor c=db.debtsByType("SIMPLE")){
            while(c.moveToNext()){
                n++;
                String name=c.getString(c.getColumnIndexOrThrow("name"));
                String dir=c.getString(c.getColumnIndexOrThrow("direction"));
                double principal=c.getDouble(c.getColumnIndexOrThrow("principal"));
                double remaining=c.getDouble(c.getColumnIndexOrThrow("remaining"));
                double paid=Math.max(0,principal-remaining);

                LinearLayout item=card(WHITE);
                LinearLayout tr=new LinearLayout(this); tr.setOrientation(LinearLayout.HORIZONTAL); tr.setGravity(Gravity.CENTER_VERTICAL);
                LinearLayout left=vertical();
                left.addView(tv(name,16,INK,true));
                left.addView(tv("PAYABLE".equals(dir)?"Mən borcluyam":"Mənə borcludurlar",11,"PAYABLE".equals(dir)?RED:GREEN,true));
                tr.addView(left,new LinearLayout.LayoutParams(0,ViewGroup.LayoutParams.WRAP_CONTENT,1));
                tr.addView(tv(azn(remaining),18,remaining>0.005?PURPLE:GREEN,true));
                item.addView(tr);

                ProgressBar pb=new ProgressBar(this,null,android.R.attr.progressBarStyleHorizontal);
                pb.setMax(1000);
                pb.setProgress((int)(principal<=0?1000:Math.max(0,Math.min(1000,paid/principal*1000))));
                pb.setProgressTintList(ColorStateList.valueOf(PURPLE));
                LinearLayout.LayoutParams pp=new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,dp(7)); pp.setMargins(0,dp(11),0,dp(8)); item.addView(pb,pp);

                item.addView(tv("İlkin "+azn(principal)+"   •   Ödənib "+azn(paid),11,MUTED,false));
                body.addView(item);
            }
        }
        if(n==0){ LinearLayout e=card(WHITE); e.addView(tv("Aktiv birdəfəlik borc yoxdur.",13,MUTED,false)); body.addView(e); }

        render("Borclar", body, 4);
    }

    private void showCredits() {
        LinearLayout body=vertical();

        LinearLayout hero=card(PURPLE);
        hero.addView(tv("Kredit qalığı",12,Color.rgb(219,234,254),false));
        hero.addView(tv(azn(db.totalDebtRemainingByType("CREDIT","PAYABLE")),28,WHITE,true));
        hero.addView(tv("Aylıq cədvəllər və qismən ödənişlər",12,Color.rgb(219,234,254),false));
        body.addView(hero);

        LinearLayout add=card(WHITE);
        add.addView(menuTile("+","Yeni kredit","Ümumi məbləğ və aylıq ödəniş planı",v->showAddCreditDialog()));
        body.addView(add);

        int n=0;
        try(Cursor c=db.debtsByType("CREDIT")){
            while(c.moveToNext()){
                n++;
                long id=c.getLong(c.getColumnIndexOrThrow("_id"));
                String name=c.getString(c.getColumnIndexOrThrow("name"));
                double principal=c.getDouble(c.getColumnIndexOrThrow("principal"));
                double remaining=c.getDouble(c.getColumnIndexOrThrow("remaining"));
                double monthly=c.getDouble(c.getColumnIndexOrThrow("monthly"));
                String nextDue=c.isNull(c.getColumnIndexOrThrow("next_due"))?"Bağlanıb":c.getString(c.getColumnIndexOrThrow("next_due"));
                double paid=Math.max(0,principal-remaining);

                LinearLayout item=card(WHITE);
                item.addView(tv(name,16,INK,true));

                LinearLayout stats=new LinearLayout(this); stats.setOrientation(LinearLayout.HORIZONTAL); stats.setPadding(0,dp(9),0,dp(8));
                LinearLayout s1=vertical(); s1.addView(tv("Qalıq",10,MUTED,false)); s1.addView(tv(azn(remaining),15,PURPLE,true));
                LinearLayout s2=vertical(); s2.addView(tv("Aylıq",10,MUTED,false)); s2.addView(tv(azn(monthly),15,INK,true));
                LinearLayout s3=vertical(); s3.addView(tv("Növbəti",10,MUTED,false)); s3.addView(tv(nextDue,12,INK,true));
                stats.addView(s1,new LinearLayout.LayoutParams(0,ViewGroup.LayoutParams.WRAP_CONTENT,1));
                stats.addView(s2,new LinearLayout.LayoutParams(0,ViewGroup.LayoutParams.WRAP_CONTENT,1));
                stats.addView(s3,new LinearLayout.LayoutParams(0,ViewGroup.LayoutParams.WRAP_CONTENT,1));
                item.addView(stats);

                ProgressBar pb=new ProgressBar(this,null,android.R.attr.progressBarStyleHorizontal);
                pb.setMax(1000); pb.setProgress((int)(principal<=0?1000:Math.max(0,Math.min(1000,paid/principal*1000))));
                pb.setProgressTintList(ColorStateList.valueOf(PURPLE));
                LinearLayout.LayoutParams pp=new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,dp(7)); pp.setMargins(0,dp(4),0,dp(10)); item.addView(pb,pp);

                Button table=actionButton("Ödəniş cədvəli",PURPLE_SOFT,PURPLE,v->showDebtScheduleDialog(id,name));
                item.addView(table,new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,dp(42)));
                body.addView(item);
            }
        }
        if(n==0){ LinearLayout e=card(WHITE); e.addView(tv("Aktiv kredit yoxdur.",13,MUTED,false)); body.addView(e); }

        render("Kreditlər", body, 4);
    }

    private void showReports() {
        LinearLayout body=vertical();
        String month=LocalDate.now().format(DateTimeFormatter.ofPattern("yyyy-MM"));

        LinearLayout hero=card(PURPLE);
        hero.addView(tv("Hesabat mərkəzi",22,WHITE,true));
        hero.addView(tv("Bütün maliyyə hesabatların bir yerdə",12,Color.rgb(219,234,254),false));
        body.addView(hero);

        double inc=db.sumTransactions("INCOME",month);
        double exp=db.sumTransactions("EXPENSE",month);

        LinearLayout row=new LinearLayout(this); row.setOrientation(LinearLayout.HORIZONTAL);
        LinearLayout.LayoutParams l=new LinearLayout.LayoutParams(0,ViewGroup.LayoutParams.WRAP_CONTENT,1); l.setMargins(0,0,dp(5),dp(10));
        LinearLayout.LayoutParams r=new LinearLayout.LayoutParams(0,ViewGroup.LayoutParams.WRAP_CONTENT,1); r.setMargins(dp(5),0,0,dp(10));
        row.addView(dashboardMetric("Bu ay CR",azn(inc),GREEN),l);
        row.addView(dashboardMetric("Bu ay DR",azn(exp),RED),r);
        body.addView(row);

        body.addView(menuTile("⇄","CR / DR balans hesabatı","Açılış, gəlir, xərc və hərəkətli balans",v->{
            ledgerFilterFrom=LocalDate.now().withDayOfMonth(1).toString();
            ledgerFilterTo=LocalDate.now().toString();
            showLedgerReport();
        }));
        body.addView(menuTile("↗","Gəlir hesabatı","Faktiki və yolda olan gəlirlərə bax",v->showIncome()));
        body.addView(menuTile("▤","Borc hesabatı","Birdəfəlik borc və alacaqlar",v->showDebts()));
        body.addView(menuTile("₼","Kredit hesabatı","Kredit qalıqları və ödəniş cədvəlləri",v->showCredits()));
        body.addView(menuTile("◎","Büdcə vəziyyəti","Yığım məqsədləri və progress",v->showBudgets()));
        body.addView(menuTile("✦","Aylıq təhlil","Xərc yükü, qənaət və maliyyə insight-ları",v->showAnalysis()));

        render("Hesabatlar",body,3);
    }

    private void showMore() {
        LinearLayout body=vertical();

        LinearLayout intro=card(WHITE);
        intro.addView(tv("Bölmələr",18,INK,true));
        intro.addView(tv("Proqramın bütün imkanlarına buradan rahat keç.",12,MUTED,false));
        body.addView(intro);

        body.addView(menuTile("₼","Gəlirlər","Faktiki və yolda olan vəsaitlər",v->showIncome()));
        body.addView(menuTile("▤","Borclar","Birdəfəlik borc və alacaqlar",v->showDebts()));
        body.addView(menuTile("▥","Kreditlər","Aylıq kredit planları",v->showCredits()));
        body.addView(menuTile("◎","Büdcə","Yığım məqsədləri",v->showBudgets()));
        body.addView(menuTile("≡","Kateqoriyalar","Gəlir və xərc kateqoriyalarını idarə et",v->showCategories()));
        body.addView(menuTile("✦","Təhlil","Aylıq maliyyə təhlili",v->showAnalysis()));

        render("Daha çox",body,4);
    }

    private void showAnalysis() {'''
main = replace_once(
    main,
    r'''    private void showDebts\(\) \{.*?    private void showAnalysis\(\) \{''',
    pages,
    "Separated debt/credit/reports/more"
)

# Sub-pages should highlight "Daha", ledger highlights Reports.
def patch_render_index(text, signature_pattern, next_signature_pattern, old_call_pattern, new_call):
    pattern = rf'''({signature_pattern}.*?){next_signature_pattern}'''
    m = re.search(pattern, text, flags=re.S)
    if not m:
        return text
    block = m.group(1)
    updated = re.sub(old_call_pattern, new_call, block)
    if updated == block:
        return text
    return text[:m.start(1)] + updated + text[m.end(1):]

main = patch_render_index(
    main,
    r'''    private void showBudgets\(\) \{''',
    r'''    private void showCategories\(\) \{''',
    r'''render\(([^;]+), body, 2\);''',
    r'''render(\1, body, 4);'''
)
main = patch_render_index(
    main,
    r'''    private void showCategories\(\) \{''',
    r'''    private void showEditCategoryDialog''',
    r'''render\(([^;]+), body, 1\);''',
    r'''render(\1, body, 4);'''
)
main = patch_render_index(
    main,
    r'''    private void showAnalysis\(\) \{''',
    r'''    private void showLedgerReport''',
    r'''render\(([^;]+), body, 4\);''',
    r'''render(\1, body, 4);'''
)
main = patch_render_index(
    main,
    r'''    private void showLedgerReport\(\) \{''',
    r'''    private LinearLayout analysisLine''',
    r'''render\(([^;]+),body,4\);''',
    r'''render(\1,body,3);'''
)

MAIN.write_text(main, encoding="utf-8")
print("Applied Büdcəm v1.4 premium blue-white redesign")
