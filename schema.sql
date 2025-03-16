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

-- Insert some sample medicines
INSERT INTO medicines (name, description, price, stock, image_url) VALUES 
    ('Paracetamol 500mg', 'Pain reliever and fever reducer', 50.00, 100, '/static/images/medicines/paracetamol-500-mg-10-tablet-23_1.webp'),
    ('Vitamin D3 1000IU', 'Vitamin D3 supplement', 200.00, 50, '/static/images/medicines/Vitamin-D3-1000iu-Softgel-Bottle-SG-front_For Web.webp'),
    ('Metformin 500mg', 'Type 2 diabetes medication', 180.00, 75, '/static/images/medicines/metformin.webp'),
    ('Omeprazole 20mg', 'Acid reflux medication', 150.00, 60, '/static/images/medicines/Omeprazole 20mg.jpg'),
    ('Amoxicillin 500mg', 'Antibiotic', 300.00, 40, '/static/images/medicines/Amoxicillin 500mg.jpg'),
    ('Cetirizine 10mg', 'Antihistamine for allergies', 120.00, 90, '/static/images/medicines/Cetirizine 10mg.webp'),
    ('Aspirin 81mg', 'Blood thinner', 80.00, 120, '/static/images/medicines/Aspirin 81mg.jpg'),
    ('Ibuprofen 400mg', 'Pain and inflammation reliever', 90.00, 85, '/static/images/medicines/Ibuprofen 400mg.jpg');

-- Lab Tests Tables
CREATE TABLE IF NOT EXISTS lab_tests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    price REAL NOT NULL,
    category TEXT NOT NULL,
    included_tests TEXT,  -- JSON array of included tests
    features TEXT,        -- JSON array of features
    preparation TEXT,     -- Test preparation instructions
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS lab_test_bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    test_id INTEGER NOT NULL,
    booking_date DATE NOT NULL,
    booking_time TIME NOT NULL,
    collection_type TEXT NOT NULL,  -- 'home' or 'lab'
    collection_address TEXT,        -- Required for home collection
    status TEXT NOT NULL,           -- 'pending', 'completed', 'cancelled'
    payment_status TEXT NOT NULL,   -- 'pending', 'completed'
    amount REAL NOT NULL,
    report_url TEXT,               -- URL to the test report PDF
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id),
    FOREIGN KEY (test_id) REFERENCES lab_tests (id)
);

-- Health Records Tables
CREATE TABLE IF NOT EXISTS prescriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    prescription_date DATE NOT NULL,
    description TEXT,
    file_url TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS medical_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    record_date DATE NOT NULL,
    record_type TEXT NOT NULL,  -- 'report', 'vaccination', 'surgery', etc.
    description TEXT,
    file_url TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

-- Insert sample lab tests
INSERT INTO lab_tests (name, description, price, category, included_tests, features, preparation) VALUES
('Basic Health Check', 'Complete Blood Count, Liver Function, Kidney Function', 999, 'Health Packages',
 '["Complete Blood Count", "Liver Function Test", "Kidney Function Test", "Lipid Profile"]',
 '["35+ Tests Included", "Free Home Sample Collection", "Report within 24 hours"]',
 'Fast for 8-10 hours before the test'),
 
('Diabetes Check', 'HbA1c, Blood Sugar, Lipid Profile', 799, 'Health Packages',
 '["HbA1c", "Fasting Blood Sugar", "Post Prandial Blood Sugar", "Lipid Profile"]',
 '["15+ Tests Included", "Free Diet Consultation", "Report within 24 hours"]',
 'Fast for 8-10 hours before the test'),
 
('Cardiac Health', 'ECG, Lipid Profile, Cardiac Risk Markers', 1499, 'Health Packages',
 '["ECG", "Lipid Profile", "Cardiac Risk Markers", "Complete Blood Count"]',
 '["20+ Tests Included", "Free Cardiologist Consultation", "Report within 24 hours"]',
 'Fast for 12 hours before the test'),
 
('Complete Blood Count', 'Includes RBC, WBC, Platelets', 299, 'Individual Tests',
 '["RBC Count", "WBC Count", "Platelet Count", "Hemoglobin"]',
 '["Report within 24 hours", "Free Home Collection"]',
 'No special preparation required'),
 
('Thyroid Profile', 'T3, T4, TSH levels', 499, 'Individual Tests',
 '["T3", "T4", "TSH"]',
 '["Report within 24 hours", "Free Home Collection"]',
 'No special preparation required'),
 
('Vitamin D Test', '25-OH Vitamin D levels', 699, 'Individual Tests',
 '["25-OH Vitamin D"]',
 '["Report within 24 hours", "Free Home Collection"]',
 'No special preparation required'),
 
('Lipid Profile', 'Cholesterol, Triglycerides', 399, 'Individual Tests',
 '["Total Cholesterol", "Triglycerides", "HDL", "LDL"]',
 '["Report within 24 hours", "Free Home Collection"]',
 'Fast for 12 hours before the test');

-- Doctors Tables
CREATE TABLE IF NOT EXISTS doctor_specialties (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS doctors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    specialty_id INTEGER NOT NULL,
    qualification TEXT NOT NULL,
    experience INTEGER NOT NULL,  -- Years of experience
    consultation_fee REAL NOT NULL,
    about TEXT,
    image_url TEXT,
    languages TEXT,  -- JSON array of languages
    available_days TEXT,  -- JSON array of available days
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (specialty_id) REFERENCES doctor_specialties (id)
);

CREATE TABLE IF NOT EXISTS doctor_timeslots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doctor_id INTEGER NOT NULL,
    day_of_week INTEGER NOT NULL,  -- 0 (Sunday) to 6 (Saturday)
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    FOREIGN KEY (doctor_id) REFERENCES doctors (id)
);

CREATE TABLE IF NOT EXISTS doctor_appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doctor_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    appointment_date DATE NOT NULL,
    appointment_time TIME NOT NULL,
    status TEXT NOT NULL,  -- 'pending', 'confirmed', 'completed', 'cancelled'
    payment_status TEXT NOT NULL,  -- 'pending', 'completed'
    amount REAL NOT NULL,
    symptoms TEXT,
    consultation_type TEXT NOT NULL,  -- 'online', 'in-person'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (doctor_id) REFERENCES doctors (id),
    FOREIGN KEY (user_id) REFERENCES users (id)
);

-- Insert sample specialties
INSERT INTO doctor_specialties (name) VALUES
    ('General Physician'),
    ('Cardiologist'),
    ('Dermatologist'),
    ('Pediatrician'),
    ('Orthopedic'),
    ('Neurologist'),
    ('Psychiatrist'),
    ('Gynecologist'),
    ('ENT Specialist'),
    ('Dentist');

-- Insert sample doctors
INSERT INTO doctors (name, specialty_id, qualification, experience, consultation_fee, about, image_url, languages, available_days) VALUES
    ('Dr. Shivam Yadav', 1, 'MBBS, MD (Internal Medicine)', 15, 500,
     'Experienced general physician with expertise in managing chronic diseases and preventive healthcare.',
     '/static/images/doctors/doctor1.jpeg',
     '["English", "Hindi"]',
     '[0, 1, 2, 3, 4, 5]'),
    
    ('Dr. Kritika Yadav', 2, 'MBBS, MD (Cardiology), DM', 12, 1000,
     'Specialist in interventional cardiology and heart disease management.',
     '/static/images/doctors/doctor2.jpeg',
     '["English", "Hindi", "Bengali"]',
     '[1, 2, 3, 4, 5]'),
    
    ('Dr. Beuda', 3, 'MBBS, MD (Dermatology)', 8, 800,
     'Expert in treating skin conditions and cosmetic dermatology.',
     '/static/images/doctors/doctor3.jpeg',
     '["English", "Hindi", "Gujarati"]',
     '[0, 2, 4, 6]'),
    
    ('Dr. Killi', 4, 'MBBS, MD (Pediatrics)', 10, 600,
     'Specialized in child healthcare and development.',
     '/static/images/doctors/doctor4.jpeg',
     '["English", "Hindi", "Telugu"]',
     '[1, 2, 3, 4, 5]'),
    
    ('Dr. Duggu', 5, 'MBBS, MS (Orthopedics)', 20, 900,
     'Experienced in joint replacements and sports injuries.',
     '/static/images/doctors/doctor5.jpeg',
     '["English", "Hindi"]',
     '[1, 3, 5]'),
    
    ('Dr. Takkli', 6, 'MBBS, MD (Neurology), DM', 15, 1200,
     'Specialist in neurological disorders and stroke management.',
     '/static/images/doctors/doctor6.jpeg',
     '["English", "Hindi", "Tamil"]',
     '[2, 3, 4, 5]');

-- Insert sample time slots
INSERT INTO doctor_timeslots (doctor_id, day_of_week, start_time, end_time) VALUES
    (1, 1, '09:00', '13:00'),
    (1, 1, '16:00', '20:00'),
    (1, 2, '09:00', '13:00'),
    (1, 2, '16:00', '20:00'),
    (1, 3, '09:00', '13:00'),
    (1, 3, '16:00', '20:00'),
    (2, 1, '10:00', '14:00'),
    (2, 1, '15:00', '19:00'),
    (2, 3, '10:00', '14:00'),
    (2, 3, '15:00', '19:00'),
    (2, 5, '10:00', '14:00'),
    (3, 2, '11:00', '15:00'),
    (3, 2, '16:00', '20:00'),
    (3, 4, '11:00', '15:00'),
    (3, 4, '16:00', '20:00'),
    (4, 1, '09:00', '17:00'),
    (4, 3, '09:00', '17:00'),
    (4, 5, '09:00', '17:00'),
    (5, 1, '10:00', '18:00'),
    (5, 3, '10:00', '18:00'),
    (5, 5, '10:00', '18:00'),
    (6, 2, '09:00', '13:00'),
    (6, 3, '09:00', '13:00'),
    (6, 4, '14:00', '18:00'),
    (6, 5, '14:00', '18:00');
