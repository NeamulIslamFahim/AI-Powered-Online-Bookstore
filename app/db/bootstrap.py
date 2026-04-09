from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.exc import OperationalError

from app.core.config import settings
from app.core.security import hash_password


BOOKS_REPAIR_STATEMENTS = [
    "ALTER TABLE books ADD COLUMN description TEXT NULL",
    "ALTER TABLE books ADD COLUMN price DECIMAL(10, 2) NOT NULL DEFAULT 0",
    "ALTER TABLE books ADD COLUMN stock_quantity INT NOT NULL DEFAULT 0",
    "ALTER TABLE books ADD COLUMN category_id INT NULL",
    "ALTER TABLE books ADD COLUMN image_url VARCHAR(500) NULL",
    "ALTER TABLE books ADD COLUMN isbn VARCHAR(50) NULL",
    "ALTER TABLE books ADD COLUMN published_date DATE NULL",
    "ALTER TABLE books ADD COLUMN created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP",
    "ALTER TABLE books ADD COLUMN updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP",
]

DEFAULT_CATEGORIES = [
    ("Fiction", "Stories, novels, and literary reads"),
    ("Non Fiction", "Biographies, essays, and true stories"),
    ("Self Improvement", "Habits, productivity, and personal growth"),
    ("Business", "Leadership, money, and entrepreneurship"),
]

DEFAULT_BOOKS = [
    {
        "title": "The Alchemist",
        "author": "Paulo Coelho",
        "description": "A timeless novel about purpose, courage, and personal legend.",
        "price": 14.00,
        "stock_quantity": 40,
        "category_name": "Fiction",
        "image_url": "https://images.unsplash.com/photo-1512820790803-83ca734da794",
        "isbn": "9780062315007",
        "published_date": "1993-05-01",
    },
    {
        "title": "Atomic Habits",
        "author": "James Clear",
        "description": "A practical guide to building habits and breaking unhelpful patterns.",
        "price": 18.00,
        "stock_quantity": 35,
        "category_name": "Self Improvement",
        "image_url": "https://images.unsplash.com/photo-1516979187457-637abb4f9353",
        "isbn": "9780735211292",
        "published_date": "2018-10-16",
    },
    {
        "title": "Sapiens",
        "author": "Yuval Noah Harari",
        "description": "A sweeping history of humankind and how societies evolved.",
        "price": 20.00,
        "stock_quantity": 22,
        "category_name": "Non Fiction",
        "image_url": "https://images.unsplash.com/photo-1495446815901-a7297e633e8d",
        "isbn": "9780062316097",
        "published_date": "2015-02-10",
    },
    {
        "title": "The Psychology of Money",
        "author": "Morgan Housel",
        "description": "Lessons about wealth, greed, and happiness.",
        "price": 16.50,
        "stock_quantity": 28,
        "category_name": "Business",
        "image_url": "https://images.unsplash.com/photo-1528207776546-365bb710ee93",
        "isbn": "9780857197689",
        "published_date": "2020-09-08",
    },
]

BROKEN_APP_TABLES = [
    "assistant_order_sessions",
    "assistant_conversation_items",
    "assistant_conversations",
    "wishlist",
    "reviews",
    "order_items",
    "orders",
    "cart_items",
    "carts",
    "books",
    "categories",
    "users",
]


def _is_broken_table_error(error: Exception) -> bool:
    message = str(error).lower()
    return (
        "doesn't exist in engine" in message
        or "(1932" in message
        or "tablespace for table" in message
        or "(1813" in message
    )


def _repair_broken_app_schema(connection) -> set[str]:
    connection.execute(text("SET FOREIGN_KEY_CHECKS=0"))
    try:
        for table_name in BROKEN_APP_TABLES:
            connection.execute(text(f"DROP TABLE IF EXISTS {table_name}"))
    finally:
        connection.execute(text("SET FOREIGN_KEY_CHECKS=1"))

    return {
        row[0]
        for row in connection.execute(
            text("SELECT table_name FROM information_schema.tables WHERE table_schema = DATABASE()")
        )
    }


def recreate_database(engine: Engine) -> None:
    database_url = make_url(settings.DATABASE_URL)
    database_name = database_url.database
    if not database_name:
        raise RuntimeError("DATABASE_URL must include a database name")

    admin_engine = create_engine(
        database_url.set(database="mysql"),
        pool_pre_ping=True,
        isolation_level="AUTOCOMMIT",
    )
    try:
        with admin_engine.connect() as connection:
            connection.execute(text(f"DROP DATABASE IF EXISTS `{database_name}`"))
            connection.execute(
                text(f"CREATE DATABASE `{database_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            )
    finally:
        admin_engine.dispose()


def repair_legacy_schema(engine: Engine) -> None:
    with engine.begin() as connection:
        try:
            existing_tables = {
                row[0]
                for row in connection.execute(
                    text("SELECT table_name FROM information_schema.tables WHERE table_schema = DATABASE()")
                )
            }

            critical_tables = [table_name for table_name in ["users", "categories", "books", "orders"] if table_name in existing_tables]
            for table_name in critical_tables:
                try:
                    connection.execute(text(f"SELECT 1 FROM {table_name} LIMIT 1"))
                except OperationalError as exc:
                    if _is_broken_table_error(exc):
                        existing_tables = _repair_broken_app_schema(connection)
                        break
                    raise

            if "users" in existing_tables:
                connection.execute(
                    text(
                        """
                        INSERT INTO users (name, email, password_hash, role)
                        SELECT :name, :email, :password_hash, 'admin'
                        WHERE NOT EXISTS (
                            SELECT 1 FROM users WHERE email = :email
                        )
                        """
                    ),
                    {
                        "name": settings.ADMIN_NAME,
                        "email": settings.ADMIN_EMAIL,
                        "password_hash": hash_password(settings.ADMIN_PASSWORD),
                    },
                )

            if "users" in existing_tables and "orders" in existing_tables:
                connection.execute(
                    text(
                        """
                        CREATE TABLE IF NOT EXISTS assistant_order_sessions (
                            id INT PRIMARY KEY AUTO_INCREMENT,
                            session_id VARCHAR(255) NOT NULL,
                            user_id INT NOT NULL,
                            order_id INT NOT NULL,
                            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                            UNIQUE KEY uq_assistant_session_user (session_id, user_id),
                            CONSTRAINT fk_assistant_order_sessions_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                            CONSTRAINT fk_assistant_order_sessions_order FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
                        )
                        """
                    )
                )

            if "users" in existing_tables and "books" in existing_tables:
                connection.execute(
                    text(
                        """
                        CREATE TABLE IF NOT EXISTS assistant_conversations (
                            id INT PRIMARY KEY AUTO_INCREMENT,
                            session_id VARCHAR(255) NOT NULL,
                            user_id INT NOT NULL,
                            book_id INT NULL,
                            quantity INT NULL,
                            customer_name VARCHAR(255) NULL,
                            phone VARCHAR(50) NULL,
                            address TEXT NULL,
                            state VARCHAR(50) NOT NULL DEFAULT 'idle',
                            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                            UNIQUE KEY uq_assistant_conversation_session_user (session_id, user_id),
                            CONSTRAINT fk_assistant_conversations_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                            CONSTRAINT fk_assistant_conversations_book FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE SET NULL
                        )
                        """
                    )
                )
                connection.execute(
                    text(
                        """
                        ALTER TABLE assistant_conversations
                        ADD COLUMN IF NOT EXISTS negotiated_unit_price DECIMAL(10, 2) NULL
                        """
                    )
                )
                connection.execute(
                    text(
                        """
                        CREATE TABLE IF NOT EXISTS assistant_conversation_items (
                            id INT PRIMARY KEY AUTO_INCREMENT,
                            session_id VARCHAR(255) NOT NULL,
                            user_id INT NOT NULL,
                            book_id INT NOT NULL,
                            quantity INT NULL,
                            negotiated_unit_price DECIMAL(10, 2) NULL,
                            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                            UNIQUE KEY uq_assistant_conversation_item (session_id, user_id, book_id),
                            CONSTRAINT fk_assistant_conversation_items_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                            CONSTRAINT fk_assistant_conversation_items_book FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
                        )
                        """
                    )
                )

            if "books" not in existing_tables:
                return

            existing_columns = {
                row[0]
                for row in connection.execute(
                    text("SELECT column_name FROM information_schema.columns WHERE table_schema = DATABASE() AND table_name = 'books'")
                )
            }

            statements_by_column = {
                "description": BOOKS_REPAIR_STATEMENTS[0],
                "price": BOOKS_REPAIR_STATEMENTS[1],
                "stock_quantity": BOOKS_REPAIR_STATEMENTS[2],
                "category_id": BOOKS_REPAIR_STATEMENTS[3],
                "image_url": BOOKS_REPAIR_STATEMENTS[4],
                "isbn": BOOKS_REPAIR_STATEMENTS[5],
                "published_date": BOOKS_REPAIR_STATEMENTS[6],
                "created_at": BOOKS_REPAIR_STATEMENTS[7],
                "updated_at": BOOKS_REPAIR_STATEMENTS[8],
            }

            for column_name, statement in statements_by_column.items():
                if column_name not in existing_columns:
                    connection.execute(text(statement))

            if "categories" in existing_tables:
                for name, description in DEFAULT_CATEGORIES:
                    connection.execute(
                        text(
                            """
                            INSERT INTO categories (name, description)
                            SELECT :name, :description
                            WHERE NOT EXISTS (
                                SELECT 1 FROM categories WHERE name = :name
                            )
                            """
                        ),
                        {"name": name, "description": description},
                    )

                default_category_id = connection.execute(
                    text("SELECT id FROM categories ORDER BY id ASC LIMIT 1")
                ).scalar()

                if default_category_id is not None:
                    connection.execute(
                        text(
                            """
                            UPDATE books
                            SET category_id = :category_id
                            WHERE category_id IS NULL
                               OR category_id NOT IN (SELECT id FROM categories)
                            """
                        ),
                        {"category_id": default_category_id},
                    )

                category_map = {
                    row[1]: row[0]
                    for row in connection.execute(text("SELECT id, name FROM categories"))
                }

                for book in DEFAULT_BOOKS:
                    category_id = category_map.get(book["category_name"], default_category_id)
                    connection.execute(
                        text(
                            """
                            INSERT INTO books (
                                title, author, description, price, stock_quantity,
                                category_id, image_url, isbn, published_date
                            )
                            SELECT
                                :title, :author, :description, :price, :stock_quantity,
                                :category_id, :image_url, :isbn, :published_date
                            WHERE NOT EXISTS (
                                SELECT 1 FROM books WHERE isbn = :isbn OR title = :title
                            )
                            """
                        ),
                        {
                            "title": book["title"],
                            "author": book["author"],
                            "description": book["description"],
                            "price": book["price"],
                            "stock_quantity": book["stock_quantity"],
                            "category_id": category_id,
                            "image_url": book["image_url"],
                            "isbn": book["isbn"],
                            "published_date": book["published_date"],
                        },
                    )

                    connection.execute(
                        text(
                            """
                            UPDATE books
                            SET
                                description = COALESCE(NULLIF(description, ''), :description),
                                price = CASE WHEN price IS NULL OR price <= 0 THEN :price ELSE price END,
                                stock_quantity = CASE
                                    WHEN stock_quantity IS NULL OR stock_quantity <= 0 THEN :stock_quantity
                                    ELSE stock_quantity
                                END,
                                category_id = COALESCE(category_id, :category_id),
                                image_url = COALESCE(NULLIF(image_url, ''), :image_url),
                                published_date = COALESCE(published_date, :published_date)
                            WHERE isbn = :isbn OR title = :title
                            """
                        ),
                        {
                            "title": book["title"],
                            "description": book["description"],
                            "price": book["price"],
                            "stock_quantity": book["stock_quantity"],
                            "category_id": category_id,
                            "image_url": book["image_url"],
                            "isbn": book["isbn"],
                            "published_date": book["published_date"],
                        },
                    )
        except OperationalError as exc:
            if _is_broken_table_error(exc):
                _repair_broken_app_schema(connection)
                return
            raise


def initialize_database(engine: Engine, metadata) -> None:
    try:
        repair_legacy_schema(engine)
        metadata.create_all(bind=engine)
        repair_legacy_schema(engine)
    except OperationalError as exc:
        if not _is_broken_table_error(exc):
            raise
        recreate_database(engine)
        metadata.create_all(bind=engine)
        repair_legacy_schema(engine)
