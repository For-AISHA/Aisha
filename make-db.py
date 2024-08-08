import sqlite3

# Connect to SQLite database (or create it if it doesn't exist)
conn = sqlite3.connect('walmart.db')
cursor = conn.cursor()

# Create tables

# Customers table
cursor.execute('''
CREATE TABLE IF NOT EXISTS customers (
    userId INTEGER PRIMARY KEY AUTOINCREMENT,
    firstName TEXT NOT NULL,
    lastName TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    phone TEXT,
    address TEXT,
    registrationDate DATE DEFAULT (datetime('now'))
)
''')

# Complaints table
cursor.execute('''
CREATE TABLE IF NOT EXISTS complaints (
    ticketNo INTEGER PRIMARY KEY AUTOINCREMENT,
    userId INTEGER,
    issue TEXT NOT NULL,
    complaintDate DATE DEFAULT (datetime('now')),
    status TEXT DEFAULT 'Open',
    FOREIGN KEY (userId) REFERENCES customers (userId)
)
''')

# Orders table
cursor.execute('''
CREATE TABLE IF NOT EXISTS orders (
    orderId INTEGER PRIMARY KEY AUTOINCREMENT,
    userId INTEGER,
    orderDate DATE DEFAULT (datetime('now')),
    totalAmount REAL NOT NULL,
    status TEXT DEFAULT 'Pending',
    shippingAddress TEXT,
    FOREIGN KEY (userId) REFERENCES customers (userId)
)
''')

# Products table
cursor.execute('''
CREATE TABLE IF NOT EXISTS products (
    productId INTEGER PRIMARY KEY AUTOINCREMENT,
    productName TEXT NOT NULL,
    price REAL NOT NULL,
    stockQuantity INTEGER NOT NULL
)
''')

# OrderDetails table to track which products are in which orders
cursor.execute('''
CREATE TABLE IF NOT EXISTS orderDetails (
    orderDetailId INTEGER PRIMARY KEY AUTOINCREMENT,
    orderId INTEGER,
    productId INTEGER,
    quantity INTEGER NOT NULL,
    price REAL NOT NULL,
    FOREIGN KEY (orderId) REFERENCES orders (orderId),
    FOREIGN KEY (productId) REFERENCES products (productId)
)
''')

# Insert sample records into customers table
cursor.executemany('''
INSERT INTO customers (firstName, lastName, email, phone, address)
VALUES (?, ?, ?, ?, ?)
''', [
    ('Dhairya', 'Arora', 'dhairya2arora@gmail.com', '9811264318', '357, Hakikat Nagar, Delhi-110009'),
    ('Yash', 'Khattar', 'yashkhattar73@gmail.com', '8448721780', 'Gurugram, Haryana'),
    ('Mahak', 'Arora', 'aroradhairya4@gmail.com', '9811264317', '357, Hakikat Nagar, Delhi-110009')
])

# Insert sample records into complaints table
cursor.executemany('''
INSERT INTO complaints (userId, issue)
VALUES (?, ?)
''', [
    (1, 'Incorrect item received'),
    (2, 'Late delivery'),
    (3, 'Product arrived damaged')
])

# Insert sample records into orders table
cursor.executemany('''
INSERT INTO orders (userId, totalAmount, status, shippingAddress)
VALUES (?, ?, ?, ?)
''', [
    (1, 1000, 'Shipped', '357, Hakikat Nagar, Delhi-110009'),
    (2, 1200, 'Pending', 'Gurugram, Haryana'),
    (3, 1500, 'Delivered', '357, Hakikat Nagar, Delhi-110009')
])

# Insert sample records into products table
cursor.executemany('''
INSERT INTO products (productName, price, stockQuantity)
VALUES (?, ?, ?)
''', [
    ('Laptop', 70000, 10),
    ('Smartphone', 30000, 20),
    ('Headphones', 4000, 50)
])

# Insert sample records into orderDetails table
cursor.executemany('''
INSERT INTO orderDetails (orderId, productId, quantity, price)
VALUES (?, ?, ?, ?)
''', [
    (1, 1, 1, 70000),
    (1, 3, 2, 4000),
    (2, 2, 1, 30000),
    (3, 1, 1, 70000),
    (3, 2, 1, 30000)
])

# Commit and close the connection
conn.commit()
conn.close()

print("Tables created and sample records inserted successfully.")
