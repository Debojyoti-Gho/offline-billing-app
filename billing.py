import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# Database Setup
conn = sqlite3.connect('store_billing.db', check_same_thread=False)
c = conn.cursor()

# Create Tables
c.execute('''CREATE TABLE IF NOT EXISTS products (
                product_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                price REAL NOT NULL,
                stock INTEGER NOT NULL)''')

c.execute('''CREATE TABLE IF NOT EXISTS transactions (
                transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER,
                quantity INTEGER,
                total_price REAL,
                transaction_type TEXT,
                date TEXT,
                FOREIGN KEY (product_id) REFERENCES products (product_id))''')

conn.commit()

# App Layout
st.title("Offline Store Billing App")

menu = ["Add Product", "View Products", "Billing", "View Transactions", "Exchange/Return"]
choice = st.sidebar.selectbox("Menu", menu)

if choice == "Add Product":
    st.subheader("Add New Product")

    with st.form("add_product_form"):
        name = st.text_input("Product Name")
        price = st.number_input("Product Price", min_value=0.01, step=0.01)
        stock = st.number_input("Stock Quantity", min_value=1, step=1)
        submit = st.form_submit_button("Add Product")

        if submit:
            if name and price > 0 and stock > 0:
                c.execute("INSERT INTO products (name, price, stock) VALUES (?, ?, ?)", (name, price, stock))
                conn.commit()
                st.success(f"Product '{name}' added successfully!")
            else:
                st.error("Please fill all fields correctly.")

elif choice == "View Products":
    st.subheader("Product List")
    products = pd.read_sql_query("SELECT * FROM products", conn)
    st.dataframe(products)

elif choice == "Billing":
    st.subheader("Billing Section")

    with st.form("billing_form"):
        product_id = st.number_input("Product ID", min_value=1, step=1)
        quantity = st.number_input("Quantity", min_value=1, step=1)
        submit = st.form_submit_button("Generate Bill")

        if submit:
            product = c.execute("SELECT * FROM products WHERE product_id = ?", (product_id,)).fetchone()

            if product:
                name, price, stock = product[1], product[2], product[3]

                if stock >= quantity:
                    total_price = quantity * price
                    c.execute("UPDATE products SET stock = stock - ? WHERE product_id = ?", (quantity, product_id))
                    c.execute("INSERT INTO transactions (product_id, quantity, total_price, transaction_type, date) VALUES (?, ?, ?, ?, ?)",
                              (product_id, quantity, total_price, 'Sale', datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                    conn.commit()

                    st.success(f"Bill Generated: {name} x {quantity} = \u20B9{total_price:.2f}")
                else:
                    st.error(f"Insufficient stock for {name}. Available: {stock}")
            else:
                st.error("Product not found.")

elif choice == "View Transactions":
    st.subheader("Transaction History")
    transactions = pd.read_sql_query("SELECT * FROM transactions", conn)
    st.dataframe(transactions)

elif choice == "Exchange/Return":
    st.subheader("Exchange/Return Section")

    with st.form("exchange_return_form"):
        transaction_id = st.number_input("Transaction ID", min_value=1, step=1)
        new_quantity = st.number_input("Quantity to Return/Exchange", min_value=1, step=1)
        transaction_type = st.selectbox("Type", ["Return", "Exchange"])
        submit = st.form_submit_button("Process")

        if submit:
            transaction = c.execute("SELECT * FROM transactions WHERE transaction_id = ?", (transaction_id,)).fetchone()

            if transaction:
                product_id, original_quantity, original_price, _, date = transaction[1], transaction[2], transaction[3], transaction[4], transaction[5]

                if transaction_type == "Return":
                    c.execute("UPDATE products SET stock = stock + ? WHERE product_id = ?", (new_quantity, product_id))
                    c.execute("INSERT INTO transactions (product_id, quantity, total_price, transaction_type, date) VALUES (?, ?, ?, ?, ?)",
                              (product_id, -new_quantity, -(original_price / original_quantity) * new_quantity, 'Return', datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                    conn.commit()
                    st.success(f"Return Processed: \u20B9{-(original_price / original_quantity) * new_quantity:.2f} refunded.")

                elif transaction_type == "Exchange":
                    product = c.execute("SELECT * FROM products WHERE product_id = ?", (product_id,)).fetchone()
                    if product:
                        name, price, stock = product[1], product[2], product[3]

                        if stock >= new_quantity:
                            c.execute("UPDATE products SET stock = stock + ? WHERE product_id = ?", (original_quantity, product_id))
                            c.execute("UPDATE products SET stock = stock - ? WHERE product_id = ?", (new_quantity, product_id))
                            c.execute("INSERT INTO transactions (product_id, quantity, total_price, transaction_type, date) VALUES (?, ?, ?, ?, ?)",
                                      (product_id, new_quantity, price * new_quantity, 'Exchange', datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                            conn.commit()
                            st.success(f"Exchange Processed: New Quantity = {new_quantity}, Total = \u20B9{price * new_quantity:.2f}")
                        else:
                            st.error(f"Insufficient stock for exchange. Available: {stock}")
                    else:
                        st.error("Product not found for exchange.")
            else:
                st.error("Transaction not found.")

st.sidebar.info("Ensure your database file ('store_billing.db') is kept safe for offline use.")
