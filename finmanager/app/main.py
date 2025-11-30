import asyncio
import datetime
import time
import sys
import os

# Add project root to sys.path to allow imports from core
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
import pandas as pd

from core.domain import Transaction
from core.frp import Event, StateEventBus, check_budget_handler, on_transaction_added
from core.lazy import iter_transactions, lazy_top_categories
from core.memo import forecast_expenses
from core.recursion import flatten_categories, sum_expenses_recursive
from core.service import BudgetService, ReportService
from core.transforms import (
    by_amount_range,
    by_category,
    check_budget,
    load_seed,
    validate_transaction,
)
from core.auth import verify_credentials, get_user_role, get_user_accounts
from core.state_utils import update_account_balance, update_transaction, delete_transaction, create_transaction

# Configuration
st.set_page_config(page_title="Financial Manager", layout="wide", page_icon="💸")

# --- Helper to load CSS ---
def load_css(file_name):
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# Load custom CSS
css_path = os.path.join(os.path.dirname(__file__), 'assets', 'style.css')
if os.path.exists(css_path):
    load_css(css_path)

# --- Authentication ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.role = None

if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        with st.container(border=True):
            st.title("Financial Manager")
            st.write("Please log in to access your financial dashboard.")
            with st.form("login_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submit = st.form_submit_button("Login", use_container_width=True)

                if submit:
                    if verify_credentials(username, password):
                        st.session_state.logged_in = True
                        st.session_state.username = username
                        st.session_state.role = get_user_role(username)
                        st.success("Logged in successfully!")
                        st.rerun()
                    else:
                        st.error("Invalid username or password")
    st.stop()

# Sidebar Logout
st.sidebar.title("FinManager 💸")
st.sidebar.markdown("---")
st.sidebar.write(f"Logged in as: **{st.session_state.username}** ({st.session_state.role})")
if st.sidebar.button("Logout", key="logout_btn"):
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.role = None
    st.rerun()

st.sidebar.markdown("---")

# Load Data (Simulated Global State for now, usually would be in session state)
if "state" not in st.session_state:
    accs, cats, trans, buds = load_seed("data/seed.json")
    st.session_state.state = {
        "accounts": accs,
        "categories": cats,
        "transactions": trans,
        "budgets": buds,
        "alerts": [],
    }

    # Init Event Bus
    bus = StateEventBus()
    bus.subscribe("TRANSACTION_ADDED", on_transaction_added)
    bus.subscribe("TRANSACTION_ADDED", check_budget_handler)
    st.session_state.bus = bus

state = st.session_state.state

# Filter Data based on User Role
allowed_accounts = get_user_accounts(st.session_state.username)

if allowed_accounts is None:
    # Admin sees all
    accounts = state["accounts"]
    transactions = state["transactions"]
else:
    # User sees only their accounts
    accounts = tuple(a for a in state["accounts"] if a.id in allowed_accounts)
    transactions = tuple(t for t in state["transactions"] if t.account_id in allowed_accounts)

categories = state["categories"]
budgets = state["budgets"] # Budgets might need filtering too but for now shared or all visible
alerts = state["alerts"]

# Sidebar Menu
# If Admin, show special "Manage Users"
menu_options = [
    "Overview",
    "Data",
    "Functional Core",
    "Pipelines",
    "Async/FRP",
    "Reports",
    "Tests",
    "About",
]
if st.session_state.role == "admin":
    menu_options.insert(1, "Manage Users")

menu = st.sidebar.radio("Navigation", menu_options)

def metric_card(label, value, col):
    col.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

if menu == "Overview":
    st.title("Overview")
    st.markdown("### Dashboard Summary")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        metric_card("Accounts", len(accounts), col1)
    with col2:
        metric_card("Categories", len(categories), col2)
    with col3:
        metric_card("Transactions", len(transactions), col3)
    with col4:
        total_balance = sum(a.balance for a in accounts)
        metric_card("Total Balance", f"${total_balance}", col4)

    st.markdown("---")

    col_acc, col_chart = st.columns([1, 2])

    with col_acc:
        st.subheader("Your Accounts")
        if accounts:
            acc_df = pd.DataFrame([{"Name": a.name, "ID": a.id, "Balance": a.balance, "Currency": a.currency} for a in accounts])
            st.dataframe(
                acc_df,
                column_config={
                    "Balance": st.column_config.NumberColumn(format="$%d")
                },
                hide_index=True,
                use_container_width=True
            )
        else:
            st.info("No accounts found.")

    with col_chart:
        # --- New: Expense by Category Chart ---
        st.subheader("Expense by Category")
        # Prepare data for chart
        if transactions:
            df_trans = pd.DataFrame([t.__dict__ for t in transactions])
            
            # Join with categories to get names
            cat_map = {c.id: c.name for c in categories}
            df_trans['category_name'] = df_trans['cat_id'].map(cat_map)
            
            df_expenses = df_trans[df_trans['amount'] < 0].copy()
            if not df_expenses.empty:
                df_expenses['abs_amount'] = df_expenses['amount'].abs()
                chart_data = df_expenses.groupby('category_name')['abs_amount'].sum()
                st.bar_chart(chart_data, color="#00ADB5")
            else:
                st.info("No expenses found to chart.")

    st.markdown("---")
    st.subheader("Recent Transactions")
    
    if transactions:
        df_all_trans = pd.DataFrame([t.__dict__ for t in transactions])
        st.dataframe(
            df_all_trans,
            column_config={
                "id": st.column_config.TextColumn("ID", disabled=True),
                "amount": st.column_config.NumberColumn("Amount", format="$%d"),
                "ts": st.column_config.DatetimeColumn("Date", format="D MMM YYYY, h:mm a"),
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.write("No transactions found.")
    
elif menu == "Manage Users":
    st.title("Admin: Manage Users")
    if st.session_state.role != "admin":
        st.error("Access Denied")
        st.stop()

    with st.container(border=True):
        # Select User to Manage
        target_user = st.selectbox("Select User", ["user1", "user2"])
        target_acc_ids = get_user_accounts(target_user)
        
        st.subheader(f"Managing: {target_user}")

        # Tabs for better organization
        admin_tab1, admin_tab2, admin_tab3 = st.tabs(["Manage Accounts", "Edit Transactions", "Create Transaction"])
        
        target_accounts = [a for a in state["accounts"] if a.id in target_acc_ids]

        # 1. Manage Accounts (Balance)
        with admin_tab1:
            st.write("### Account Balances")
            for acc in target_accounts:
                with st.expander(f"Account: {acc.name} ({acc.id})"):
                    col_bal1, col_bal2 = st.columns([3, 1])
                    new_bal = col_bal1.number_input(f"Balance for {acc.id}", value=acc.balance, key=f"bal_{acc.id}")
                    if col_bal2.button(f"Update", key=f"btn_{acc.id}"):
                        st.session_state.state = update_account_balance(st.session_state.state, acc.id, new_bal)
                        st.success("Balance Updated")
                        st.rerun()

        # 2. Manage Transactions
        target_trans = [t for t in state["transactions"] if t.account_id in target_acc_ids]
        
        with admin_tab2:
            st.write("### Edit Transactions")
            st.dataframe(pd.DataFrame([t.__dict__ for t in target_trans]), hide_index=True, use_container_width=True)
            
            st.divider()
            st.write("#### Modify Transaction")
            
            if target_trans:
                t_id_to_edit = st.selectbox("Select Transaction ID", [t.id for t in target_trans])
                if t_id_to_edit:
                    curr_t = next(t for t in target_trans if t.id == t_id_to_edit)
                    
                    with st.form("edit_trans_form"):
                        edit_amt = st.number_input("Amount", value=curr_t.amount, key="edit_amt")
                        edit_note = st.text_input("Note", value=curr_t.note, key="edit_note")
                        
                        c1, c2 = st.columns(2)
                        with c1:
                            update_submitted = st.form_submit_button("Update Transaction", use_container_width=True)
                        with c2:
                            delete_submitted = st.form_submit_button("Delete Transaction", type="primary", use_container_width=True)

                        if update_submitted:
                            st.session_state.state = update_transaction(st.session_state.state, t_id_to_edit, {"amount": edit_amt, "note": edit_note})
                            st.success("Transaction Updated")
                            st.rerun()
                        
                        if delete_submitted:
                            st.session_state.state = delete_transaction(st.session_state.state, t_id_to_edit)
                            st.success("Transaction Deleted")
                            st.rerun()
            else:
                st.info("No transactions to edit.")

        with admin_tab3:
            st.write("### Create New Transaction")
            with st.form("create_trans_form"):
                new_acc_id = st.selectbox("Account", [a.id for a in target_accounts])
                new_amt = st.number_input("Amount", 0)
                new_note = st.text_input("Note", placeholder="Transaction Note")
                create_submitted = st.form_submit_button("Create Transaction", use_container_width=True)
                
                if create_submitted:
                    # Generate ID
                    import uuid
                    new_id = f"tx_{len(state['transactions'])}_{uuid.uuid4().hex[:4]}"
                    # Default category general
                    new_t = Transaction(new_id, new_acc_id, "cat_general", int(new_amt), datetime.datetime.now().isoformat(), new_note)
                    st.session_state.state = create_transaction(st.session_state.state, new_t)
                    st.success("Transaction Created")
                    st.rerun()

elif menu == "Data":
    st.title("Data Inspection")
    
    with st.container(border=True):
        tab1, tab2, tab3, tab4 = st.tabs(["Transactions", "Accounts", "Categories", "Budgets"])
        
        with tab1:
            st.subheader("Transactions")
            if transactions:
                df = pd.DataFrame([t.__dict__ for t in transactions])
                
                # Interactive Filters
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    f_acc = st.multiselect("Filter by Account", options=list(set(df['account_id'])))
                with col_f2:
                    # Need category names map
                    cat_map = {c.id: c.name for c in categories}
                    df['category_name'] = df['cat_id'].map(cat_map)
                    f_cat = st.multiselect("Filter by Category", options=list(set(df['category_name'])))
                
                if f_acc:
                    df = df[df['account_id'].isin(f_acc)]
                if f_cat:
                    df = df[df['category_name'].isin(f_cat)]
                
                st.data_editor(
                    df,
                    column_config={
                        "amount": st.column_config.NumberColumn(
                            "Amount",
                            help="The amount of the transaction",
                            format="$%d",
                        ),
                        "category_name": st.column_config.TextColumn("Category"),
                    },
                    disabled=True,
                    hide_index=True,
                    use_container_width=True
                )
            else:
                st.info("No transactions available.")

        with tab2:
            st.subheader("Accounts")
            st.dataframe(pd.DataFrame([a.__dict__ for a in accounts]), hide_index=True, use_container_width=True)

        with tab3:
            st.subheader("Categories")
            st.dataframe(pd.DataFrame([c.__dict__ for c in categories]), hide_index=True, use_container_width=True)

        with tab4:
            st.subheader("Budgets")
            st.dataframe(pd.DataFrame([b.__dict__ for b in budgets]), hide_index=True, use_container_width=True)

elif menu == "About":
    st.title("About")
    with st.container(border=True):
        st.write("Financial Manager Project")
        st.write("Team: 2-3 Students")
        st.write("Stack: Python 3.11+, Streamlit, Pytest")

elif menu == "Functional Core":
    st.title("Functional Core")
    
    with st.container(border=True):
        st.subheader("Filter Closures")

        # Filter Controls
        with st.expander("Filters", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                selected_cat = st.selectbox(
                    "Category", ["All"] + [c.name for c in categories]
                )
            with col2:
                min_amt = st.number_input("Min Amount (Abs)", 0, 10000, 0)
                max_amt = st.number_input("Max Amount (Abs)", 0, 100000, 10000)

        # Apply Filters
        filtered_trans = transactions

        if selected_cat != "All":
            cat_id = next(c.id for c in categories if c.name == selected_cat)
            filtered_trans = tuple(filter(by_category(cat_id), filtered_trans))

        filtered_trans = tuple(filter(by_amount_range(min_amt, max_amt), filtered_trans))

        st.write(f"Filtered Transactions: {len(filtered_trans)}")
        st.dataframe(filtered_trans, use_container_width=True)

    with st.container(border=True):
        st.subheader("Transaction Validation (Either/Maybe)")
        with st.form("validate_tx"):
            c1, c2, c3 = st.columns(3)
            with c1:
                # Prepare options with an invalid one for testing validation
                acc_options = [a.id for a in accounts] + ["invalid_acc"]
                v_acc = st.selectbox("Account ID", acc_options)
            with c2:
                cat_options = [c.id for c in categories] + ["invalid_cat"]
                v_cat = st.selectbox("Category ID", cat_options)
            with c3:
                v_amt = st.number_input("Amount", step=100)
            
            submitted = st.form_submit_button("Validate", use_container_width=True)

            if submitted:
                # Create a dummy transaction
                t_cand = Transaction("new", v_acc, v_cat, int(v_amt), "2023-01-01", "cand")

                result = validate_transaction(t_cand, accounts, categories)

                if result.is_right():
                    st.success("Transaction is Valid!")

                    # Check budgets if valid
                    # Simple check against all budgets
                    for b in budgets:
                        res_b = check_budget(b, transactions + (t_cand,))
                        if res_b.is_left():
                            st.warning(
                                f"Budget Alert: {res_b.unwrap()['error']} (Limit: {res_b.unwrap()['limit']}, Spent: {res_b.unwrap()['spent']})"
                            )
                        else:
                            pass  # Budget ok
                else:
                    st.error(f"Validation Failed: {result.unwrap()['error']}")

elif menu == "Pipelines":
    st.title("Pipelines & Recursion")

    with st.container(border=True):
        st.subheader("Lazy Top Categories")

        k = st.slider("Top K", 1, 10, 3)

        if st.button("Compute Top K (Lazy)"):
            # Create an iterator
            tx_iter = iter_transactions(transactions)

            # Compute
            top_k = list(lazy_top_categories(tx_iter, categories, k))

            st.write("Top Categories by Expense:")
            for name, amount in top_k:
                st.write(f"**{name}**: {amount}")

    st.divider()

    with st.container(border=True):
        st.subheader("Recursive Expense Report")

        # Select root category
        root_cats = [c for c in categories if c.parent_id is None]
        selected_root = st.selectbox("Select Root Category", [c.name for c in root_cats])

        if selected_root:
            root_id = next(c.id for c in root_cats if c.name == selected_root)

            # Flatten
            flat_cats = flatten_categories(categories, root_id)
            st.write(f"Flattened Hierarchy for {selected_root}:")
            st.write(" > ".join([c.name for c in flat_cats]))

            # Recursive Sum
            total_expenses = sum_expenses_recursive(categories, transactions, root_id)
            st.metric(f"Total Expenses for {selected_root} (Tree)", f"{total_expenses}")

elif menu == "Async/FRP":
    st.title("Async / FRP")
    
    with st.container(border=True):
        st.subheader("Event Bus Simulation")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### Add Transaction (Event)")
            with st.form("event_tx"):
                amt = st.number_input("Amount", -1000, 1000, value=0)
                cat = st.selectbox("Category", [c.name for c in categories])
                sub = st.form_submit_button("Publish TRANSACTION_ADDED", use_container_width=True)

                if sub:
                    cat_id = next(c.id for c in categories if c.name == cat)
                    # Pick random account
                    acc_id = accounts[0].id

                    new_t = Transaction(
                        id=f"tx_evt_{len(transactions)}",
                        account_id=acc_id,
                        cat_id=cat_id,
                        amount=amt,
                        ts=datetime.datetime.now().isoformat(),
                        note="Event TX",
                    )

                    evt = Event(
                        id=f"evt_{len(transactions)}",
                        ts=datetime.datetime.now().isoformat(),
                        name="TRANSACTION_ADDED",
                        payload={"transaction": new_t},
                    )

                    # Publish and Update State
                    st.session_state.state = st.session_state.bus.publish(
                        evt, st.session_state.state
                    )
                    st.success("Event Published!")
                    st.rerun()

        with col2:
            st.markdown("### Live Alerts")
            if alerts:
                for a in alerts:
                    st.error(a)
            else:
                st.info("No alerts yet.")

        st.subheader("Live State Monitor")
        st.write(f"Total Transactions: {len(transactions)}")
        st.write("Accounts Balance (Updated via Event):")
        for a in accounts:
            st.write(f"{a.name}: {a.balance}")

    with st.container(border=True):
        st.subheader("Async Aggregation (Lab 8)")

        if st.button("Run Full Async Report (End-to-End)"):
            rs = ReportService({})
            months = sorted(list(set(t.ts[:7] for t in transactions)))
            
            async def run_full_scenario():
                task1 = rs.expenses_by_month(transactions, months)
                task2 = rs.balance_forecast(accounts, transactions)
             
                return await asyncio.gather(task1, task2)

            try:
                # Безопасный запуск асинхронности в Streamlit
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Замеряем время 
                start_t = time.perf_counter()
                expenses_res, forecast_res = loop.run_until_complete(run_full_scenario())
                end_t = time.perf_counter()
                
                loop.close()

                st.success(f"Calculated in {end_t - start_t:.4f}s")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("Expenses by Month")
                    st.bar_chart(expenses_res, color="#00ADB5")
                
                with col2:
                    st.subheader("Balance Forecast")
                    
                    # Transform to DataFrame
                    forecast_data = []
                    acc_map = {a.id: a.name for a in accounts}
                    
                    for acc_id, bal in forecast_res.items():
                        forecast_data.append({
                            "Account": acc_map.get(acc_id, acc_id),
                            "Projected Balance": bal
                        })
                    
                    if forecast_data:
                        st.dataframe(
                            pd.DataFrame(forecast_data),
                            column_config={
                                "Projected Balance": st.column_config.NumberColumn(
                                    "Projected Balance",
                                    format="$%d"
                                )
                            },
                            hide_index=True,
                            use_container_width=True
                        )
                    else:
                        st.info("No forecast data available.")

            except Exception as e:
                st.error(f"Async Error: {e}")


elif menu == "Reports":
    st.title("Reports")

    # Lab 7 Services
    st.subheader("Services & Composition")

    bs = BudgetService([], [])
    rs = ReportService({})

    with st.container(border=True):
        tab1, tab2 = st.tabs(["Budget Report", "Category Report"])

        with tab1:
            st.write("### Budget vs Actuals")
            if st.button("Generate Budget Report"):
                report = bs.monthly_report(budgets, transactions)
                
                # Enrich report with category names and format for display
                report_data = []
                
                # Create lookups
                cat_map = {c.id: c.name for c in categories}
                budget_map = {b.id: b for b in budgets}
                
                for b_id, data in report.items():
                    budget = budget_map.get(b_id)
                    cat_name = "Unknown"
                    period = "Unknown"
                    
                    if budget:
                        cat_name = cat_map.get(budget.cat_id, budget.cat_id)
                        period = budget.period
                    
                    report_data.append({
                        "Budget ID": b_id,
                        "Category": cat_name,
                        "Period": period,
                        "Limit": data.get("limit", 0),
                        "Spent": data.get("spent", 0),
                        "Status": data.get("status", "UNKNOWN")
                    })
                
                if report_data:
                    df_rep = pd.DataFrame(report_data)
                    
                    # Highlight OVER status? 
                    # Streamlit dataframe allows styling, but simple column config helps too.
                    
                    st.dataframe(
                        df_rep,
                        column_config={
                            "Limit": st.column_config.NumberColumn(format="$%d"),
                            "Spent": st.column_config.NumberColumn(format="$%d"),
                        },
                        hide_index=True,
                        use_container_width=True
                    )
                else:
                    st.info("No budget data available.")

        with tab2:
            st.write("### Expense Trend by Category")
            c_name = st.selectbox("Category", [c.name for c in categories], key="rep_cat")
            if st.button("Generate Category Report"):
                cid = next(c.id for c in categories if c.name == c_name)
                rep = rs.category_report(cid, transactions)
                
                # Display metrics instead of JSON
                col_m1, col_m2 = st.columns(2)
                with col_m1:
                    metric_card("Total Expense", f"${rep['total_expense']}", col_m1)
                with col_m2:
                    metric_card("Transaction Count", rep['transaction_count'], col_m2)

    st.divider()

    with st.container(border=True):
        st.subheader("Forecast (Cached)")

        col_fc1, col_fc2 = st.columns(2)
        with col_fc1:
            cat_name = st.selectbox(
                "Category for Forecast", [c.name for c in categories], key="fc_cat"
            )
            periods = st.slider("Periods to forecast", 1, 12, 3)
        
        with col_fc2:
            st.write("Click below to forecast expenses using historical data.")

        if st.button("Calculate Forecast"):
            cat_id = next(c.id for c in categories if c.name == cat_name)

            # Measure time
            start = time.perf_counter()
            prediction = forecast_expenses(cat_id, transactions, periods)
            end = time.perf_counter()

            elapsed_ms = (end - start) * 1000

            metric_card("Forecasted Expense", f"${prediction}", st)
            st.caption(f"Calculation time: {elapsed_ms:.2f} ms")
            
            # Visualize Forecast vs History (Mock visualization since forecast returns a single number)
            # We can show a bar with "Average History" and "Forecast"
            st.bar_chart({"Forecast": prediction}, color="#00ADB5")
            
            st.info(
                "Try clicking again to see the cache effect (time should drop close to 0)."
            )

elif menu == "Tests":
    st.title("Tests")
    with st.container(border=True):
        st.write("This section displays information about the project's test suite.")
        st.info("Tests are implemented using `pytest`.")
        
        st.markdown("""
        ### Available Test Modules:
        - `tests/test_lab1.py`: Domain & Transforms
        - `tests/test_lab2.py`: Recursion & Filters
        - `tests/test_lab3.py`: Memoization
        - `tests/test_lab4.py`: Validation (Maybe/Either)
        - `tests/test_lab5.py`: Lazy Evaluation
        - `tests/test_lab6.py`: FRP / Event Bus
        - `tests/test_lab7.py`: Composition & Services
        - `tests/test_lab8.py`: Async
        
        Run `pytest` in the console to execute them.
        """)

else:
    st.info(f"Section {menu} is under construction.")
