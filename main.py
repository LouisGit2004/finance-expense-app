import streamlit as st
import pandas as pd
import plotly.express as px
import json
import os

from streamlit import column_config

# Page setup
st.set_page_config(page_title="Simple Finance Expense App", page_icon="💰", layout="wide")

# File for storing categories
category_file = "categories.json"

# Initialize categories in session state
if "categories" not in st.session_state:
    st.session_state.categories = {"Uncategorized": []}

# Load categories from file if it exists
if os.path.exists(category_file):
    with open(category_file, "r") as f:
        st.session_state.categories = json.load(f)

# Save categories to file
def save_categories():
    with open(category_file, "w") as f:
        json.dump(st.session_state.categories, f)

# Categorize transactions based on keywords
def categorize_transactions(df):
    df["Category"] = "Uncategorized"
    for category, keywords in st.session_state.categories.items():
        if category == "Uncategorized" or not keywords:
            continue
        lowered_keywords = [kw.lower().strip() for kw in keywords]
        for idx, row in df.iterrows():
            details = row["Details"].lower().strip()
            if details in lowered_keywords:
                df.at[idx, "Category"] = category
    return df

# Load and clean transaction data
def load_transactions(file):
    try:
        df = pd.read_csv(file)
        df.columns = [col.strip() for col in df.columns]
        df["Amount"] = df["Amount"].str.replace(",", "").astype(float)
        df["Date"] = pd.to_datetime(df["Date"], format="%d %b %Y")
        return categorize_transactions(df)
    except Exception as e:
        st.error(f"Error processing file: {str(e)}")
        return None

# Add keyword to category
def add_keyword_to_category(category, keyword):
    keyword = keyword.strip()
    if category not in st.session_state.categories:
        st.session_state.categories[category] = []
    if keyword and keyword not in st.session_state.categories[category]:
        st.session_state.categories[category].append(keyword)
        save_categories()
        return True
    return False

# Main app logic
def main():
    st.title("💰 Simple Finance Expense App")

    uploaded_file = st.file_uploader("Upload your transactions CSV", type=["csv"])
    if uploaded_file:
        df = load_transactions(uploaded_file)
        if df is not None:
            debits_df = df[df["Debit/Credit"] == "Debit"].copy()
            credits_df = df[df["Debit/Credit"] == "Credit"].copy()
            st.session_state.debits_df = debits_df.copy()

            tab1, tab2 = st.tabs(["Expenses (Debits)", "Payments (Credits)"])

            # Tab 1: Expenses
            with tab1:
                st.subheader("Manage Categories")
                new_category = st.text_input("New Category Name")
                if st.button("Add Category") and new_category:
                    if new_category not in st.session_state.categories:
                        st.session_state.categories[new_category] = []
                        save_categories()
                        st.rerun()

                st.subheader("Your Expenses")
                edited_df = st.data_editor(
                    st.session_state.debits_df[["Date", "Details", "Amount", "Category"]],
                    column_config={
                        "Date": st.column_config.DateColumn(label="Date", format="DD/MM/YYYY"),
                        "Amount": st.column_config.NumberColumn(label="Amount", format="%.2f GBP"),
                        "Category": st.column_config.SelectboxColumn(
                            label="Category",
                            options=list(st.session_state.categories.keys())
                        )
                    },
                    hide_index=True,
                    use_container_width=True,
                    key="category_editor"
                )

                if st.button("Apply Changes", type="primary"):
                    for idx, row in edited_df.iterrows():
                        new_cat = row["Category"]
                        if new_cat != st.session_state.debits_df.at[idx, "Category"]:
                            details = row["Details"]
                            st.session_state.debits_df.at[idx, "Category"] = new_cat
                            add_keyword_to_category(new_cat, details)

                st.subheader("Expense Summary")
                category_totals = st.session_state.debits_df.groupby("Category")["Amount"].sum().reset_index()
                category_totals = category_totals.sort_values("Amount", ascending=False)

                st.dataframe(
                    category_totals,
                    column_config={
                        "Amount": st.column_config.NumberColumn(label="Amount", format="%.2f GBP")
                    },
                    use_container_width=True,
                    hide_index=True,
                )

                fig = px.pie(
                    category_totals,
                    values="Amount",
                    names="Category",
                    title="Expense by Category",
                )
                st.plotly_chart(fig, use_container_width=True)

            # Tab 2: Payments
            with tab2:
                st.subheader("Payments Summary")
                total_payments = credits_df["Amount"].sum()
                st.metric("Total Payments", f"{total_payments:,.2f} GBP")
                st.dataframe(credits_df, use_container_width=True)

# Run the app
main()
