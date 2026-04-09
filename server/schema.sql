CREATE DATABASE IF NOT EXISTS online_bookstore CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE online_bookstore;

CREATE TABLE IF NOT EXISTS users (
  id INT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(120) NOT NULL,
  email VARCHAR(255) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  role ENUM('admin', 'customer') NOT NULL DEFAULT 'customer',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS categories (
  id INT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(120) NOT NULL UNIQUE,
  description TEXT NULL
);

CREATE TABLE IF NOT EXISTS books (
  id INT PRIMARY KEY AUTO_INCREMENT,
  title VARCHAR(255) NOT NULL,
  author VARCHAR(255) NOT NULL,
  description TEXT NULL,
  price DECIMAL(10, 2) NOT NULL,
  stock_quantity INT NOT NULL DEFAULT 0,
  category_id INT NOT NULL,
  image_url VARCHAR(500) NULL,
  isbn VARCHAR(50) NULL UNIQUE,
  published_date DATE NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_books_category FOREIGN KEY (category_id) REFERENCES categories(id)
);

-- Repair an older books table before running seed inserts.
ALTER TABLE books ADD COLUMN IF NOT EXISTS description TEXT NULL;
ALTER TABLE books ADD COLUMN IF NOT EXISTS price DECIMAL(10, 2) NOT NULL DEFAULT 0;
ALTER TABLE books ADD COLUMN IF NOT EXISTS stock_quantity INT NOT NULL DEFAULT 0;
ALTER TABLE books ADD COLUMN IF NOT EXISTS category_id INT NULL;
ALTER TABLE books ADD COLUMN IF NOT EXISTS image_url VARCHAR(500) NULL;
ALTER TABLE books ADD COLUMN IF NOT EXISTS isbn VARCHAR(50) NULL;
ALTER TABLE books ADD COLUMN IF NOT EXISTS published_date DATE NULL;
ALTER TABLE books ADD COLUMN IF NOT EXISTS created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE books ADD COLUMN IF NOT EXISTS updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP;

CREATE TABLE IF NOT EXISTS carts (
  id INT PRIMARY KEY AUTO_INCREMENT,
  user_id INT NOT NULL UNIQUE,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_carts_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS cart_items (
  id INT PRIMARY KEY AUTO_INCREMENT,
  cart_id INT NOT NULL,
  book_id INT NOT NULL,
  quantity INT NOT NULL,
  UNIQUE KEY uq_cart_book (cart_id, book_id),
  CONSTRAINT fk_cart_items_cart FOREIGN KEY (cart_id) REFERENCES carts(id) ON DELETE CASCADE,
  CONSTRAINT fk_cart_items_book FOREIGN KEY (book_id) REFERENCES books(id)
);

CREATE TABLE IF NOT EXISTS orders (
  id INT PRIMARY KEY AUTO_INCREMENT,
  user_id INT NOT NULL,
  total_amount DECIMAL(10, 2) NOT NULL,
  status ENUM('pending', 'paid', 'shipped', 'delivered', 'cancelled') NOT NULL DEFAULT 'pending',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_orders_user FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS order_items (
  id INT PRIMARY KEY AUTO_INCREMENT,
  order_id INT NOT NULL,
  book_id INT NOT NULL,
  quantity INT NOT NULL,
  price_at_purchase DECIMAL(10, 2) NOT NULL,
  CONSTRAINT fk_order_items_order FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
  CONSTRAINT fk_order_items_book FOREIGN KEY (book_id) REFERENCES books(id)
);

CREATE TABLE IF NOT EXISTS assistant_conversations (
  id INT PRIMARY KEY AUTO_INCREMENT,
  session_id VARCHAR(255) NOT NULL,
  user_id INT NOT NULL,
  book_id INT NULL,
  quantity INT NULL,
  negotiated_unit_price DECIMAL(10, 2) NULL,
  customer_name VARCHAR(255) NULL,
  phone VARCHAR(50) NULL,
  address TEXT NULL,
  state VARCHAR(50) NOT NULL DEFAULT 'idle',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_assistant_conversation_session_user (session_id, user_id),
  CONSTRAINT fk_assistant_conversations_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT fk_assistant_conversations_book FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS assistant_order_sessions (
  id INT PRIMARY KEY AUTO_INCREMENT,
  session_id VARCHAR(255) NOT NULL,
  user_id INT NOT NULL,
  order_id INT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_assistant_session_user (session_id, user_id),
  CONSTRAINT fk_assistant_order_sessions_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT fk_assistant_order_sessions_order FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
);

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
);

CREATE TABLE IF NOT EXISTS reviews (
  id INT PRIMARY KEY AUTO_INCREMENT,
  user_id INT NOT NULL,
  book_id INT NOT NULL,
  rating INT NOT NULL CHECK (rating BETWEEN 1 AND 5),
  comment TEXT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_reviews_user_book (user_id, book_id),
  CONSTRAINT fk_reviews_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT fk_reviews_book FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS wishlist (
  id INT PRIMARY KEY AUTO_INCREMENT,
  user_id INT NOT NULL,
  book_id INT NOT NULL,
  UNIQUE KEY uq_wishlist_user_book (user_id, book_id),
  CONSTRAINT fk_wishlist_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT fk_wishlist_book FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
);

INSERT INTO categories (id, name, description) VALUES
  (1, 'Fiction', 'Stories, novels, and literary reads'),
  (2, 'Non Fiction', 'Biographies, essays, and true stories'),
  (3, 'Self Improvement', 'Habits, productivity, and personal growth'),
  (4, 'Business', 'Leadership, money, and entrepreneurship')
ON DUPLICATE KEY UPDATE name = VALUES(name), description = VALUES(description);

INSERT INTO books (id, title, author, description, price, stock_quantity, category_id, image_url, isbn, published_date) VALUES
  (1, 'The Alchemist', 'Paulo Coelho', 'A timeless novel about purpose, courage, and personal legend.', 14.00, 40, 1, 'https://images.unsplash.com/photo-1512820790803-83ca734da794', '9780062315007', '1993-05-01'),
  (2, 'Atomic Habits', 'James Clear', 'A practical guide to building habits and breaking unhelpful patterns.', 18.00, 35, 3, 'https://images.unsplash.com/photo-1516979187457-637abb4f9353', '9780735211292', '2018-10-16'),
  (3, 'Sapiens', 'Yuval Noah Harari', 'A sweeping history of humankind and how societies evolved.', 20.00, 22, 2, 'https://images.unsplash.com/photo-1495446815901-a7297e633e8d', '9780062316097', '2015-02-10'),
  (4, 'The Psychology of Money', 'Morgan Housel', 'Lessons about wealth, greed, and happiness.', 16.50, 28, 4, 'https://images.unsplash.com/photo-1528207776546-365bb710ee93', '9780857197689', '2020-09-08')
ON DUPLICATE KEY UPDATE title = VALUES(title);
