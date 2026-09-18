import streamlit as st

from services.store_service import (
    ORDER_STATUSES,
    cents_to_dollars,
    create_order,
    delete_order,
    dollars_to_cents,
    list_orders,
    update_order,
)
from services.ui import render_chat_widget, require_admin_access


st.set_page_config(
    page_title="Admin Orders",
    page_icon="🧾",
    layout="wide",
)

from services.browser_auth import restore_session
restore_session()

st.sidebar.caption("This app is an educational tool, not medical advice.")



require_admin_access()

st.page_link("BMI2.py", label="← Back to Home")
st.page_link("pages/admin.py", label="← Admin")

st.title("Admin Orders")
st.caption("Create, update, and delete order records.")

st.divider()

with st.expander("Create order", expanded=True):
    with st.form("create_order_form"):
        customer_name = st.text_input("Customer name")
        customer_email = st.text_input("Customer email")

        status_column, total_column = st.columns(2)
        with status_column:
            status = st.selectbox("Status", ORDER_STATUSES)
        with total_column:
            total = st.number_input(
                "Order total",
                min_value=0.0,
                value=0.0,
                step=1.0,
            )

        notes = st.text_area("Notes")

        submitted = st.form_submit_button("Create order", use_container_width=True)

    if submitted:
        if not customer_email.strip():
            st.error("Customer email is required.")
        else:
            try:
                order = create_order(
                    customer_email=customer_email,
                    customer_name=customer_name,
                    status=status,
                    total_cents=dollars_to_cents(total),
                    notes=notes,
                )
                st.success(f"Created order {order['id']}.")
                st.rerun()
            except Exception as error:
                st.error(f"Could not create order: {error}")

st.subheader("Orders")

try:
    orders = list_orders()
except Exception as error:
    st.error(f"Could not load orders: {error}")
    render_chat_widget()
    st.stop()

if not orders:
    st.info("No orders have been created yet.")
else:
    st.dataframe(
        [
            {
                "Order": order["id"],
                "Customer": order["customer_name"] or order["customer_email"],
                "Email": order["customer_email"],
                "Status": order["status"],
                "Total": f"${cents_to_dollars(order['total_cents']):,.2f}",
                "Created": order["created_at"],
            }
            for order in orders
        ],
        use_container_width=True,
        hide_index=True,
    )

    for order in orders:
        title = (
            f"{order['customer_name'] or order['customer_email']} · "
            f"{order['status']} · "
            f"${cents_to_dollars(order['total_cents']):,.2f}"
        )
        with st.expander(title):
            with st.form(f"edit_order_{order['id']}"):
                edit_customer_name = st.text_input(
                    "Customer name",
                    value=order["customer_name"],
                    key=f"name_{order['id']}",
                )
                edit_customer_email = st.text_input(
                    "Customer email",
                    value=order["customer_email"],
                    key=f"email_{order['id']}",
                )

                status_column, total_column = st.columns(2)
                with status_column:
                    edit_status = st.selectbox(
                        "Status",
                        ORDER_STATUSES,
                        index=ORDER_STATUSES.index(order["status"])
                        if order["status"] in ORDER_STATUSES
                        else 0,
                        key=f"status_{order['id']}",
                    )
                with total_column:
                    edit_total = st.number_input(
                        "Order total",
                        min_value=0.0,
                        value=cents_to_dollars(order["total_cents"]),
                        step=1.0,
                        key=f"total_{order['id']}",
                    )

                edit_notes = st.text_area(
                    "Notes",
                    value=order["notes"],
                    key=f"notes_{order['id']}",
                )

                save_button = st.form_submit_button(
                    "Save changes",
                    use_container_width=True,
                )

            if save_button:
                try:
                    update_order(
                        order_id=order["id"],
                        customer_email=edit_customer_email,
                        customer_name=edit_customer_name,
                        status=edit_status,
                        total_cents=dollars_to_cents(edit_total),
                        notes=edit_notes,
                    )
                    st.success("Order updated.")
                    st.rerun()
                except Exception as error:
                    st.error(f"Could not update order: {error}")

            delete_key = f"confirm_delete_{order['id']}"
            st.checkbox(
                "I understand this permanently deletes the order.",
                key=delete_key,
            )
            if st.button(
                "Delete order",
                key=f"delete_{order['id']}",
                type="secondary",
                use_container_width=True,
                disabled=not st.session_state.get(delete_key, False),
            ):
                try:
                    delete_order(order["id"])
                    st.success("Order deleted.")
                    st.rerun()
                except Exception as error:
                    st.error(f"Could not delete order: {error}")

from assistant.widget import assistant_widget
assistant_widget()
