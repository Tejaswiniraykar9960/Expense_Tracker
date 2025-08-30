import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
import pandas as pd

# ---------------- App config ----------------
app = Flask(__name__)

# Secret key (use env var in prod, fallback for dev)
app.secret_key = os.environ.get("SECRET_KEY", "change_this_secret_for_dev")

# ---------------- Paths ----------------
DATA_DIR = "data"
EXPENSES_FILE = os.path.join(DATA_DIR, "expenses.xlsx")
USERS_FILE = os.path.join(DATA_DIR, "users.xlsx")

# Ensure data dir exists
os.makedirs(DATA_DIR, exist_ok=True)

# Create expenses.xlsx if missing
if not os.path.exists(EXPENSES_FILE):
    df = pd.DataFrame(columns=["Date", "Category", "Amount", "Description"])
    df.to_excel(EXPENSES_FILE, index=False, engine="openpyxl")

# Create users.xlsx with default accounts if missing
if not os.path.exists(USERS_FILE):
    users_df = pd.DataFrame([
        {"username": "hp", "password": "1234"},
        {"username": "admin", "password": "admin123"}
    ])
    users_df.to_excel(USERS_FILE, index=False, engine="openpyxl")
    print(f"Created default users in {USERS_FILE}")

# ---------------- Helpers ----------------
def read_expenses():
    """Read expenses into a DataFrame and reset index."""
    df = pd.read_excel(EXPENSES_FILE, engine="openpyxl").fillna("")
    return df.reset_index(drop=True)

def save_expenses(df):
    """Save DataFrame to Excel after resetting index."""
    df.reset_index(drop=True).to_excel(EXPENSES_FILE, index=False, engine="openpyxl")

# ---------------- Routes ----------------
@app.route('/')
def index():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        entered_username = request.form.get('username', '').strip()
        entered_password = request.form.get('password', '').strip()

        # Read users file
        users_df = pd.read_excel(USERS_FILE, engine="openpyxl").fillna("")

        # Clean both sides for comparison
        users_df['username'] = users_df['username'].astype(str).str.strip().str.lower()
        users_df['password'] = users_df['password'].astype(str).str.strip()

        if ((users_df['username'] == entered_username.lower()) &
            (users_df['password'] == entered_password)).any():
            session['user'] = entered_username
            flash("✅ Logged in", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("❌ Invalid credentials", "danger")

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    flash("Logged out", "info")
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))

    df = read_expenses()
    expenses = df.to_dict(orient='records')
    return render_template('dashboard.html', expenses=expenses)

@app.route('/add', methods=['GET', 'POST'])
def add_expense():
    if 'user' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        date = request.form.get('date', '').strip()
        category = request.form.get('category', '').strip()
        amount = request.form.get('amount', '0').strip()
        description = request.form.get('description', '').strip()

        try:
            amount_val = str(float(amount))
        except ValueError:
            flash("Please enter a valid amount.", "danger")
            return redirect(url_for('add_expense'))

        df = read_expenses()
        new_row = {"Date": date, "Category": category, "Amount": amount_val, "Description": description}
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        save_expenses(df)
        flash("✅ Expense added", "success")
        return redirect(url_for('dashboard'))

    return render_template('add.html')

@app.route('/edit/<int:index>', methods=['GET', 'POST'])
def edit_expense(index):
    if 'user' not in session:
        return redirect(url_for('login'))

    df = read_expenses()
    if index < 0 or index >= len(df):
        flash("Expense not found.", "danger")
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        date = request.form.get('date', '').strip()
        category = request.form.get('category', '').strip()
        amount = request.form.get('amount', '0').strip()
        description = request.form.get('description', '').strip()

        try:
            amount_val = str(float(amount))
        except ValueError:
            flash("Please enter a valid amount.", "danger")
            return redirect(url_for('edit_expense', index=index))

        df.loc[index] = [date, category, amount_val, description]
        save_expenses(df)
        flash("✅ Expense updated", "success")
        return redirect(url_for('dashboard'))

    expense = df.iloc[index].to_dict()
    return render_template('edit.html', expense=expense, index=index)

@app.route('/delete/<int:index>', methods=['POST'])
def delete_expense(index): 
    if 'user' not in session:
        return redirect(url_for('login'))

    df = read_expenses()
    if index < 0 or index >= len(df):
        flash("Expense not found.", "danger")
        return redirect(url_for('dashboard'))

    df = df.drop(index).reset_index(drop=True)
    save_expenses(df)
    flash("✅ Expense deleted", "success")
    return redirect(url_for('dashboard'))

# ---------------- Run ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # for Render
    app.run(host="0.0.0.0", port=port, debug=True)  # debug=True only for local

