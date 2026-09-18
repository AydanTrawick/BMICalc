import streamlit as st

from services.ui import render_chat_widget, require_admin_access


st.set_page_config(
    page_title="Admin",
    page_icon="🛠️",
    layout="wide",
)

from services.browser_auth import restore_session
restore_session()

st.sidebar.caption("This app is an educational tool, not medical advice.")



admin_user = require_admin_access()

st.page_link("BMI2.py", label="← Back to Home")

st.title("Admin")
st.caption(f"Signed in as {admin_user['display_name']} ({admin_user['role']}).")

st.divider()

product_column, order_column = st.columns(2)

with product_column:
    st.subheader("Products")
    st.write("Create, edit, delete, and manage product images.")
    st.page_link("pages/admin/products.py", label="Open Products", icon="📦")

with order_column:
    st.subheader("Orders")
    st.write("Review, create, update, and remove orders.")
    st.page_link("pages/admin/orders.py", label="Open Orders", icon="🧾")

from assistant.widget import assistant_widget
assistant_widget()
