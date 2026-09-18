import streamlit as st

from services.store_service import (
    cents_to_dollars,
    create_product,
    delete_product,
    dollars_to_cents,
    list_products,
    save_product_image,
    slugify,
    update_product,
)
from services.ui import render_chat_widget, require_admin_access


st.set_page_config(
    page_title="Admin Products",
    page_icon="📦",
    layout="wide",
)

from services.browser_auth import restore_session
restore_session()

st.sidebar.caption("This app is an educational tool, not medical advice.")



require_admin_access()

st.page_link("BMI2.py", label="← Back to Home")
st.page_link("pages/admin.py", label="← Admin")

st.title("Admin Products")
st.caption("Create, update, and delete product records.")

st.divider()

with st.expander("Create product", expanded=True):
    with st.form("create_product_form"):
        name = st.text_input("Product name")
        slug = st.text_input("Slug", placeholder="leave blank to auto-generate")
        description = st.text_area("Description")

        price_column, inventory_column, active_column = st.columns([1, 1, 1])
        with price_column:
            price = st.number_input("Price", min_value=0.0, value=0.0, step=1.0)
        with inventory_column:
            inventory = st.number_input(
                "Inventory",
                min_value=0,
                value=0,
                step=1,
            )
        with active_column:
            is_active = st.checkbox("Active", value=True)

        image = st.file_uploader(
            "Product image",
            type=["jpg", "jpeg", "png", "webp"],
            key="new_product_image",
        )

        submitted = st.form_submit_button(
            "Create product",
            use_container_width=True,
        )

    if submitted:
        if not name.strip():
            st.error("Product name is required.")
        else:
            try:
                product = create_product(
                    name=name,
                    slug=slugify(slug or name),
                    description=description,
                    price_cents=dollars_to_cents(price),
                    inventory_count=inventory,
                    image_path=save_product_image(image),
                    is_active=is_active,
                )
                st.success(f"Created {product['name']}.")
                st.rerun()
            except Exception as error:
                st.error(f"Could not create product: {error}")

st.subheader("Products")

try:
    products = list_products(include_inactive=True)
except Exception as error:
    st.error(f"Could not load products: {error}")
    render_chat_widget()
    st.stop()

if not products:
    st.info("No products have been created yet.")
else:
    st.dataframe(
        [
            {
                "Name": product["name"],
                "Slug": product["slug"],
                "Price": f"${cents_to_dollars(product['price_cents']):,.2f}",
                "Inventory": product["inventory_count"],
                "Active": product["is_active"],
            }
            for product in products
        ],
        use_container_width=True,
        hide_index=True,
    )

    for product in products:
        title = (
            f"{product['name']} · "
            f"${cents_to_dollars(product['price_cents']):,.2f}"
        )
        with st.expander(title):
            if product.get("image_path"):
                st.image(product["image_path"], width=180)

            with st.form(f"edit_product_{product['id']}"):
                edit_name = st.text_input(
                    "Product name",
                    value=product["name"],
                    key=f"name_{product['id']}",
                )
                edit_slug = st.text_input(
                    "Slug",
                    value=product["slug"],
                    key=f"slug_{product['id']}",
                )
                edit_description = st.text_area(
                    "Description",
                    value=product["description"],
                    key=f"description_{product['id']}",
                )

                price_column, inventory_column, active_column = st.columns(3)
                with price_column:
                    edit_price = st.number_input(
                        "Price",
                        min_value=0.0,
                        value=cents_to_dollars(product["price_cents"]),
                        step=1.0,
                        key=f"price_{product['id']}",
                    )
                with inventory_column:
                    edit_inventory = st.number_input(
                        "Inventory",
                        min_value=0,
                        value=product["inventory_count"],
                        step=1,
                        key=f"inventory_{product['id']}",
                    )
                with active_column:
                    edit_is_active = st.checkbox(
                        "Active",
                        value=product["is_active"],
                        key=f"active_{product['id']}",
                    )

                edit_image = st.file_uploader(
                    "Replace image",
                    type=["jpg", "jpeg", "png", "webp"],
                    key=f"image_{product['id']}",
                )

                save_button = st.form_submit_button(
                    "Save changes",
                    use_container_width=True,
                )

            if save_button:
                try:
                    update_product(
                        product_id=product["id"],
                        name=edit_name,
                        slug=edit_slug,
                        description=edit_description,
                        price_cents=dollars_to_cents(edit_price),
                        inventory_count=edit_inventory,
                        image_path=save_product_image(edit_image),
                        is_active=edit_is_active,
                    )
                    st.success("Product updated.")
                    st.rerun()
                except Exception as error:
                    st.error(f"Could not update product: {error}")

            delete_key = f"confirm_delete_{product['id']}"
            st.checkbox(
                "I understand this permanently deletes the product.",
                key=delete_key,
            )
            if st.button(
                "Delete product",
                key=f"delete_{product['id']}",
                type="secondary",
                use_container_width=True,
                disabled=not st.session_state.get(delete_key, False),
            ):
                try:
                    delete_product(product["id"])
                    st.success("Product deleted.")
                    st.rerun()
                except Exception as error:
                    st.error(f"Could not delete product: {error}")

from assistant.widget import assistant_widget
assistant_widget()
