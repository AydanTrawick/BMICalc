from pathlib import Path
from typing import Any
from uuid import uuid4

from services.auth_service import get_database_connection


PRODUCT_IMAGE_DIR = Path("images/products")
ORDER_STATUSES = [
    "pending",
    "paid",
    "processing",
    "shipped",
    "cancelled",
    "refunded",
]


def ensure_store_tables() -> None:
    with get_database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS firstrep_products (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    slug TEXT UNIQUE NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    price_cents INTEGER NOT NULL DEFAULT 0,
                    inventory_count INTEGER NOT NULL DEFAULT 0,
                    image_path TEXT,
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS firstrep_orders (
                    id TEXT PRIMARY KEY,
                    customer_email TEXT NOT NULL,
                    customer_name TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'pending',
                    total_cents INTEGER NOT NULL DEFAULT 0,
                    notes TEXT NOT NULL DEFAULT '',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS firstrep_order_items (
                    id TEXT PRIMARY KEY,
                    order_id TEXT NOT NULL REFERENCES firstrep_orders(id)
                        ON DELETE CASCADE,
                    product_id TEXT REFERENCES firstrep_products(id)
                        ON DELETE SET NULL,
                    product_name TEXT NOT NULL,
                    quantity INTEGER NOT NULL DEFAULT 1,
                    unit_price_cents INTEGER NOT NULL DEFAULT 0
                )
                """
            )


def cents_to_dollars(cents: int) -> float:
    return cents / 100


def dollars_to_cents(dollars: float) -> int:
    return int(round(dollars * 100))


def slugify(value: str) -> str:
    slug = "".join(
        character.lower() if character.isalnum() else "-"
        for character in value.strip()
    )
    slug = "-".join(part for part in slug.split("-") if part)
    return slug or f"product-{uuid4().hex[:8]}"


def save_product_image(uploaded_file: Any | None) -> str | None:
    if uploaded_file is None:
        return None

    PRODUCT_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    suffix = Path(uploaded_file.name).suffix.lower() or ".png"
    image_path = PRODUCT_IMAGE_DIR / f"{uuid4().hex}{suffix}"
    image_path.write_bytes(uploaded_file.getvalue())

    return str(image_path)


def list_products(include_inactive: bool = True) -> list[dict[str, Any]]:
    ensure_store_tables()

    where_clause = "" if include_inactive else "WHERE is_active = TRUE"

    with get_database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT id, name, slug, description, price_cents,
                       inventory_count, image_path, is_active,
                       created_at, updated_at
                FROM firstrep_products
                {where_clause}
                ORDER BY created_at DESC
                """
            )
            return [dict(row) for row in cursor.fetchall()]


def get_product(product_id: str) -> dict[str, Any] | None:
    ensure_store_tables()

    with get_database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, name, slug, description, price_cents,
                       inventory_count, image_path, is_active
                FROM firstrep_products
                WHERE id = %s
                """,
                (product_id,),
            )
            row = cursor.fetchone()

    return dict(row) if row else None


def create_product(
    name: str,
    slug: str,
    description: str,
    price_cents: int,
    inventory_count: int,
    image_path: str | None,
    is_active: bool,
) -> dict[str, Any]:
    ensure_store_tables()
    product_id = str(uuid4())

    with get_database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO firstrep_products (
                    id, name, slug, description, price_cents,
                    inventory_count, image_path, is_active
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, name, slug, description, price_cents,
                          inventory_count, image_path, is_active
                """,
                (
                    product_id,
                    name.strip(),
                    slugify(slug or name),
                    description.strip(),
                    price_cents,
                    inventory_count,
                    image_path,
                    is_active,
                ),
            )
            return dict(cursor.fetchone())


def update_product(
    product_id: str,
    name: str,
    slug: str,
    description: str,
    price_cents: int,
    inventory_count: int,
    image_path: str | None,
    is_active: bool,
) -> None:
    ensure_store_tables()

    with get_database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE firstrep_products
                SET name = %s,
                    slug = %s,
                    description = %s,
                    price_cents = %s,
                    inventory_count = %s,
                    image_path = COALESCE(%s, image_path),
                    is_active = %s,
                    updated_at = NOW()
                WHERE id = %s
                """,
                (
                    name.strip(),
                    slugify(slug or name),
                    description.strip(),
                    price_cents,
                    inventory_count,
                    image_path,
                    is_active,
                    product_id,
                ),
            )


def delete_product(product_id: str) -> None:
    ensure_store_tables()

    with get_database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM firstrep_products WHERE id = %s",
                (product_id,),
            )


def list_orders() -> list[dict[str, Any]]:
    ensure_store_tables()

    with get_database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, customer_email, customer_name, status, total_cents,
                       notes, created_at, updated_at
                FROM firstrep_orders
                ORDER BY created_at DESC
                """
            )
            return [dict(row) for row in cursor.fetchall()]


def create_order(
    customer_email: str,
    customer_name: str,
    status: str,
    total_cents: int,
    notes: str,
) -> dict[str, Any]:
    ensure_store_tables()
    order_id = str(uuid4())

    with get_database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO firstrep_orders (
                    id, customer_email, customer_name, status,
                    total_cents, notes
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id, customer_email, customer_name, status,
                          total_cents, notes, created_at
                """,
                (
                    order_id,
                    customer_email.strip().lower(),
                    customer_name.strip(),
                    status,
                    total_cents,
                    notes.strip(),
                ),
            )
            return dict(cursor.fetchone())


def update_order(
    order_id: str,
    customer_email: str,
    customer_name: str,
    status: str,
    total_cents: int,
    notes: str,
) -> None:
    ensure_store_tables()

    with get_database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE firstrep_orders
                SET customer_email = %s,
                    customer_name = %s,
                    status = %s,
                    total_cents = %s,
                    notes = %s,
                    updated_at = NOW()
                WHERE id = %s
                """,
                (
                    customer_email.strip().lower(),
                    customer_name.strip(),
                    status,
                    total_cents,
                    notes.strip(),
                    order_id,
                ),
            )


def delete_order(order_id: str) -> None:
    ensure_store_tables()

    with get_database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM firstrep_orders WHERE id = %s", (order_id,))
