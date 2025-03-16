import sqlite3
import os
from werkzeug.security import generate_password_hash

def init_db():
    # Make sure we're in the right directory
    if os.path.exists('instance'):
        db_path = 'instance/medicare.db'
    else:
        db_path = 'medicare.db'

    # Remove existing database if it exists
    if os.path.exists(db_path):
        os.remove(db_path)

    # Create instance directory if it doesn't exist
    os.makedirs('instance', exist_ok=True)

    # Connect to database
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row

    # Create tables
    connection.executescript('''
        DROP TABLE IF EXISTS users;
        DROP TABLE IF EXISTS medicines;
        DROP TABLE IF EXISTS orders;
        DROP TABLE IF EXISTS order_items;

        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            full_name TEXT NOT NULL,
            phone TEXT,
            address_line1 TEXT,
            address_line2 TEXT,
            city TEXT,
            state TEXT,
            pincode TEXT,
            is_admin INTEGER DEFAULT 0
        );

        CREATE TABLE medicines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            stock INTEGER NOT NULL,
            image_url TEXT
        );

        CREATE TABLE orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            total_amount REAL NOT NULL,
            delivery_address TEXT NOT NULL,
            order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'pending',
            payment_method TEXT DEFAULT 'cod',
            payment_status TEXT DEFAULT 'pending',
            FOREIGN KEY (user_id) REFERENCES users (id)
        );

        CREATE TABLE order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            medicine_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            total_price REAL NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders (id),
            FOREIGN KEY (medicine_id) REFERENCES medicines (id)
        );
    ''')

    # Insert sample medicines
    medicines = [
        ('Paracetamol 500mg', 'Pain reliever and fever reducer', 50.00, 100, 'https://i.ibb.co/7ry9Xtg/medicine1.jpg'),
        ('Vitamin D3 1000IU', 'Vitamin D3 supplement', 200.00, 50, 'https://i.ibb.co/9hLGrXy/medicine2.jpg'),
        ('Metformin 500mg', 'Type 2 diabetes medication', 180.00, 75, 'https://i.ibb.co/0MKW4bd/medicine3.jpg'),
        ('Omeprazole 20mg', 'Acid reflux medication', 150.00, 60, 'https://i.ibb.co/FX1kMF9/medicine4.jpg'),
        ('Amoxicillin 500mg', 'Antibiotic', 300.00, 40, 'https://i.ibb.co/QJVPy2B/medicine5.jpg'),
        ('Cetirizine 10mg', 'Antihistamine for allergies', 120.00, 90, 'https://i.ibb.co/zfM6LZ5/medicine6.jpg'),
        ('Aspirin 81mg', 'Blood thinner', 80.00, 120, 'https://i.ibb.co/RYxkTvM/medicine7.jpg'),
        ('Ibuprofen 400mg', 'Pain and inflammation reliever', 90.00, 85, 'https://i.ibb.co/WzVJCZ7/medicine8.jpg')
    ]

    connection.executemany('''
        INSERT INTO medicines (name, description, price, stock, image_url)
        VALUES (?, ?, ?, ?, ?)
    ''', medicines)

    # Insert admin user
    connection.execute('''
        INSERT INTO users (email, password, full_name, phone, address_line1, city, state, pincode, is_admin)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        'admin123@gmail.com',
        generate_password_hash('admin123'),
        'Admin User',
        '1234567890',
        '123 Main St',
        'Mumbai',
        'Maharashtra',
        '400001',
        1
    ))

    # Insert demo user
    connection.execute('''
        INSERT INTO users (email, password, full_name, phone, address_line1, city, state, pincode)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        'demo@example.com',
        generate_password_hash('password123'),
        'Demo User',
        '1234567890',
        '123 Main St',
        'Mumbai',
        'Maharashtra',
        '400001'
    ))

    connection.commit()
    print("Database initialized successfully!")
    connection.close()

if __name__ == '__main__':
    init_db()
