from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf.csrf import CSRFProtect
from flask_wtf import FlaskForm
from wtforms import StringField, validators
from datetime import datetime, timedelta
from functools import wraps
import sqlite3
import os
from werkzeug.utils import secure_filename
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
csrf = CSRFProtect(app)

# Add fromjson filter
@app.template_filter('fromjson')
def fromjson_filter(value):
    try:
        return json.loads(value)
    except (ValueError, TypeError):
        return []

# Configure upload folder
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')

# Database connection
def get_db_connection():
    if os.path.exists('instance'):
        db_path = 'instance/medicare.db'
    else:
        db_path = 'medicare.db'
        
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

# User model
class User(UserMixin):
    def __init__(self, id, email, password, full_name=None, phone=None, address_line1=None, address_line2=None, city=None, state=None, pincode=None):
        self.id = id
        self.email = email
        self.password = password
        self.full_name = full_name
        self.phone = phone
        self.address_line1 = address_line1
        self.address_line2 = address_line2
        self.city = city
        self.state = state
        self.pincode = pincode
        self._items = None  

    @property
    def items(self):
        return self._items

    @items.setter
    def items(self, value):
        self._items = value

    @staticmethod
    def get(user_id):
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        conn.close()
        if user is None:
            return None
        return User(user['id'], user['email'], user['password'], user['full_name'], user['phone'], user['address_line1'], user['address_line2'], user['city'], user['state'], user['pincode'])

# Login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user_data = cursor.fetchone()
    conn.close()
    
    if user_data:
        return User(
            id=user_data[0],
            email=user_data[1],
            password=user_data[2],
            full_name=user_data[3],
            phone=user_data[4],
            address_line1=user_data[5],
            address_line2=user_data[6],
            city=user_data[7],
            state=user_data[8],
            pincode=user_data[9]
        )
    return None

# Admin required decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.email != 'admin':
            flash('You need to be admin to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

class PaymentForm(FlaskForm):
    upi_id = StringField('UPI ID', [validators.Optional(), validators.Regexp(r'^[\w\.\-]+@[\w\-]+$', message='Invalid UPI ID format')])
    card_number = StringField('Card Number', [validators.Optional(), validators.Regexp(r'^\d{4}\s\d{4}\s\d{4}\s\d{4}$', message='Invalid card number format')])
    expiry = StringField('Expiry Date', [validators.Optional(), validators.Regexp(r'^\d{2}/\d{2}$', message='Invalid expiry date format')])
    cvv = StringField('CVV', [validators.Optional(), validators.Regexp(r'^\d{3,4}$', message='Invalid CVV')])
    name = StringField('Name on Card', [validators.Optional(), validators.Length(min=3, max=50)])

@app.route('/')
def home():
    conn = get_db_connection()
    featured_medicines = conn.execute('SELECT * FROM medicines LIMIT 4').fetchall()
    conn.close()
    return render_template('home.html', featured_medicines=featured_medicines)

@app.route('/doctors')
def doctors():
    conn = get_db_connection()
    try:
        # Get specialties for filter
        specialties = conn.execute('SELECT * FROM doctor_specialties').fetchall()
        
        # Get search and filter parameters
        specialty_id = request.args.get('specialty', type=int)
        search = request.args.get('search', '').strip()
        
        # Build query
        query = '''
            SELECT 
                d.*, 
                s.name as specialty_name,
                GROUP_CONCAT(DISTINCT dt.day_of_week) as available_days_raw,
                GROUP_CONCAT(DISTINCT dt.start_time || '-' || dt.end_time) as timeslots
            FROM doctors d
            JOIN doctor_specialties s ON d.specialty_id = s.id
            LEFT JOIN doctor_timeslots dt ON d.id = dt.doctor_id
        '''
        params = []
        
        if specialty_id or search:
            query += ' WHERE 1=1'
            if specialty_id:
                query += ' AND d.specialty_id = ?'
                params.append(specialty_id)
            if search:
                query += ' AND (d.name LIKE ? OR d.about LIKE ? OR s.name LIKE ?)'
                search_param = f'%{search}%'
                params.extend([search_param, search_param, search_param])
        
        query += ' GROUP BY d.id'
        
        doctors = conn.execute(query, params).fetchall()
        
        return render_template('doctors.html', 
                             doctors=doctors,
                             specialties=specialties,
                             selected_specialty=specialty_id,
                             search=search)
                             
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        flash('Error loading doctors. Please try again.', 'error')
        return redirect(url_for('home'))
    finally:
        conn.close()

@app.route('/doctor/<int:doctor_id>')
def doctor_profile(doctor_id):
    conn = get_db_connection()
    try:
        # Get doctor details
        doctor = conn.execute('''
            SELECT 
                d.*,
                s.name as specialty_name
            FROM doctors d
            JOIN doctor_specialties s ON d.specialty_id = s.id
            WHERE d.id = ?
        ''', (doctor_id,)).fetchone()
        
        if not doctor:
            flash('Doctor not found!', 'error')
            return redirect(url_for('doctors'))
            
        # Get doctor's timeslots
        timeslots = conn.execute('''
            SELECT * FROM doctor_timeslots
            WHERE doctor_id = ?
            ORDER BY day_of_week, start_time
        ''', (doctor_id,)).fetchall()
        
        return render_template('doctor_profile.html', 
                             doctor=doctor,
                             timeslots=timeslots)
                             
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        flash('Error loading doctor profile. Please try again.', 'error')
        return redirect(url_for('doctors'))
    finally:
        conn.close()

@app.route('/book_appointment/<int:doctor_id>', methods=['GET', 'POST'])
@login_required
def book_appointment(doctor_id):
    conn = get_db_connection()
    try:
        # Get doctor details
        doctor = conn.execute('''
            SELECT 
                d.*,
                s.name as specialty_name
            FROM doctors d
            JOIN doctor_specialties s ON d.specialty_id = s.id
            WHERE d.id = ?
        ''', (doctor_id,)).fetchone()
        
        if not doctor:
            flash('Doctor not found!', 'error')
            return redirect(url_for('doctors'))
            
        if request.method == 'POST':
            # Get form data
            appointment_date = request.form.get('appointment_date')
            appointment_time = request.form.get('appointment_time')
            consultation_type = request.form.get('consultation_type')
            symptoms = request.form.get('symptoms')
            
            # Validate appointment slot availability
            existing = conn.execute('''
                SELECT id FROM doctor_appointments
                WHERE doctor_id = ? AND appointment_date = ? 
                AND appointment_time = ? AND status != 'cancelled'
            ''', (doctor_id, appointment_date, appointment_time)).fetchone()
            
            if existing:
                flash('This time slot is already booked. Please choose another.', 'error')
                return redirect(url_for('book_appointment', doctor_id=doctor_id))
            
            # Insert appointment
            cursor = conn.execute('''
                INSERT INTO doctor_appointments (
                    doctor_id, user_id, appointment_date, appointment_time,
                    status, payment_status, amount, symptoms, consultation_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                doctor_id, current_user.id, appointment_date, appointment_time,
                'pending', 'pending', doctor['consultation_fee'], symptoms, consultation_type
            ))
            appointment_id = cursor.lastrowid
            conn.commit()
            
            # Redirect to payment
            return redirect(url_for('appointment_payment', appointment_id=appointment_id))
            
        # For GET request, show booking form
        # Get doctor's timeslots
        timeslots = conn.execute('''
            SELECT * FROM doctor_timeslots
            WHERE doctor_id = ?
            ORDER BY day_of_week, start_time
        ''', (doctor_id,)).fetchall()
        
        # Get next 7 days excluding unavailable days
        available_days = json.loads(doctor['available_days'])
        next_7_days = []
        current_date = datetime.now()
        days_added = 0
        while days_added < 7:
            if current_date.weekday() in available_days:
                next_7_days.append(current_date.strftime('%Y-%m-%d'))
                days_added += 1
            current_date += timedelta(days=1)
        
        return render_template('book_appointment.html',
                             doctor=doctor,
                             timeslots=timeslots,
                             available_dates=next_7_days)
                             
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        flash('Error booking appointment. Please try again.', 'error')
        return redirect(url_for('doctors'))
    finally:
        conn.close()

@app.route('/appointment_payment/<int:appointment_id>', methods=['GET', 'POST'])
@login_required
def appointment_payment(appointment_id):
    if request.method == 'POST':
        conn = get_db_connection()
        try:
            # Update appointment payment status
            conn.execute('''
                UPDATE doctor_appointments 
                SET payment_status = 'completed',
                    status = 'confirmed'
                WHERE id = ? AND user_id = ?
            ''', (appointment_id, current_user.id))
            conn.commit()
            flash('Payment successful! Your appointment is confirmed.', 'success')
            return redirect(url_for('my_appointments'))
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            flash('Error processing payment. Please try again.', 'error')
        finally:
            conn.close()
            
    return render_template('appointment_payment.html', appointment_id=appointment_id)

@app.route('/my_appointments')
@login_required
def my_appointments():
    conn = get_db_connection()
    try:
        appointments = conn.execute('''
            SELECT 
                a.*,
                d.name as doctor_name,
                d.qualification,
                s.name as specialty_name
            FROM doctor_appointments a
            JOIN doctors d ON a.doctor_id = d.id
            JOIN doctor_specialties s ON d.specialty_id = s.id
            WHERE a.user_id = ?
            ORDER BY a.appointment_date DESC, a.appointment_time DESC
        ''', (current_user.id,)).fetchall()
        
        return render_template('my_appointments.html', appointments=appointments)
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        flash('Error loading appointments. Please try again.', 'error')
        return redirect(url_for('home'))
    finally:
        conn.close()

@app.route('/lab_tests')
def lab_tests():
    conn = get_db_connection()
    try:
        # Fetch lab test categories
        categories = conn.execute('SELECT DISTINCT category FROM lab_tests').fetchall()
        # Fetch all lab tests
        tests = conn.execute('''
            SELECT id, name, description, price, category, 
                   included_tests, features, preparation
            FROM lab_tests
            ORDER BY category, name
        ''').fetchall()
        
        # Group tests by category
        tests_by_category = {}
        for test in tests:
            category = test['category']
            if category not in tests_by_category:
                tests_by_category[category] = []
            tests_by_category[category].append(dict(test))
            
        return render_template('lab_tests.html', 
                             categories=categories,
                             tests_by_category=tests_by_category)
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        flash('Error loading lab tests. Please try again.', 'error')
        return redirect(url_for('home'))
    finally:
        conn.close()

@app.route('/health_records')
@login_required
def health_records():
    conn = get_db_connection()
    try:
        # Fetch lab test reports
        lab_reports = conn.execute('''
            SELECT 
                b.id, b.booking_date, b.report_url,
                t.name as test_name
            FROM lab_test_bookings b
            JOIN lab_tests t ON b.test_id = t.id
            WHERE b.user_id = ? AND b.report_url IS NOT NULL
            ORDER BY b.booking_date DESC
        ''', (current_user.id,)).fetchall()
        
        # Fetch prescriptions
        prescriptions = conn.execute('''
            SELECT * FROM prescriptions 
            WHERE user_id = ?
            ORDER BY prescription_date DESC
        ''', (current_user.id,)).fetchall()
        
        # Fetch medical history
        medical_history = conn.execute('''
            SELECT * FROM medical_history 
            WHERE user_id = ?
            ORDER BY record_date DESC
        ''', (current_user.id,)).fetchall()
        
        return render_template('health_records.html',
                             lab_reports=lab_reports,
                             prescriptions=prescriptions,
                             medical_history=medical_history)
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        flash('Error loading health records. Please try again.', 'error')
        return redirect(url_for('home'))
    finally:
        conn.close()

@app.route('/profile')
@login_required
def profile():
    conn = get_db_connection()
    
    try:
        # Get user's orders
        orders = conn.execute('''
            SELECT 
                o.id, o.delivery_address, o.order_date,
                o.status, o.payment_method, o.payment_status,
                SUM(oi.total_price) as total_amount
            FROM orders o
            LEFT JOIN order_items oi ON o.id = oi.order_id
            WHERE o.user_id = ?
            GROUP BY o.id
            ORDER BY o.order_date DESC
        ''', (current_user.id,)).fetchall()
        
        # Convert orders to list of dicts for modification
        orders_with_items = []
        for order in orders:
            order_dict = dict(order)
            # Get order items and convert to dicts
            items = conn.execute('''
                SELECT 
                    oi.quantity, oi.unit_price, oi.total_price,
                    m.name as medicine_name, m.description
                FROM order_items oi
                JOIN medicines m ON oi.medicine_id = m.id
                WHERE oi.order_id = ?
            ''', (order['id'],)).fetchall()
            order_dict['_items'] = [dict(item) for item in items]  
            orders_with_items.append(order_dict)
        
        return render_template('profile.html', user=current_user, orders=orders_with_items)
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        flash('Error loading profile. Please try again.', 'error')
        return redirect(url_for('home'))
        
    finally:
        conn.close()

@app.route('/medicines')
def medicines():
    conn = get_db_connection()
    search = request.args.get('search', '')
    category = request.args.get('category', '')
    
    if search and category:
        medicines = conn.execute(
            'SELECT * FROM medicines WHERE (name LIKE ? OR description LIKE ?) AND category = ?',
            (f'%{search}%', f'%{search}%', category)
        ).fetchall()
    elif search:
        medicines = conn.execute(
            'SELECT * FROM medicines WHERE name LIKE ? OR description LIKE ?',
            (f'%{search}%', f'%{search}%')
        ).fetchall()
    elif category:
        medicines = conn.execute(
            'SELECT * FROM medicines WHERE category = ?',
            (category,)
        ).fetchall()
    else:
        medicines = conn.execute('SELECT * FROM medicines').fetchall()
    
    conn.close()
    return render_template('medicines.html', medicines=medicines)

@app.route('/admin/medicines')
@admin_required
def admin_medicines():
    conn = get_db_connection()
    medicines = conn.execute('SELECT * FROM medicines').fetchall()
    conn.close()
    return render_template('admin/medicines.html', medicines=medicines)

@app.route('/admin/medicines/add', methods=['GET', 'POST'])
@admin_required
def add_medicine():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = float(request.form['price'])
        stock = int(request.form['stock'])
        category = request.form['category']
        image_url = request.form['image_url']
        
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO medicines (name, description, price, stock, category, image_url)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (name, description, price, stock, category, image_url))
        conn.commit()
        conn.close()
        
        flash('Medicine added successfully!', 'success')
        return redirect(url_for('admin_medicines'))
        
    return render_template('admin/add_medicine.html')

@app.route('/admin/medicines/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_medicine(id):
    conn = get_db_connection()
    
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = float(request.form['price'])
        stock = int(request.form['stock'])
        category = request.form['category']
        image_url = request.form['image_url']
        
        conn.execute('''
            UPDATE medicines 
            SET name = ?, description = ?, price = ?, stock = ?, category = ?, image_url = ?
            WHERE id = ?
        ''', (name, description, price, stock, category, image_url, id))
        conn.commit()
        flash('Medicine updated successfully!', 'success')
        return redirect(url_for('admin_medicines'))
    
    medicine = conn.execute('SELECT * FROM medicines WHERE id = ?', (id,)).fetchone()
    conn.close()
    
    if medicine is None:
        flash('Medicine not found!', 'error')
        return redirect(url_for('admin_medicines'))
        
    return render_template('admin/edit_medicine.html', medicine=medicine)

@app.route('/admin/medicines/delete/<int:id>')
@admin_required
def delete_medicine(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM medicines WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash('Medicine deleted successfully!', 'success')
    return redirect(url_for('admin_medicines'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            # Convert SQLite Row to dictionary
            user_dict = dict(user)
            
            user_obj = User(
                id=user_dict['id'],
                email=user_dict['email'],
                password=user_dict['password'],
                full_name=user_dict['full_name'],
                phone=user_dict.get('phone', ''),
                address_line1=user_dict.get('address_line1', ''),
                address_line2=user_dict.get('address_line2', ''),
                city=user_dict.get('city', ''),
                state=user_dict.get('state', ''),
                pincode=user_dict.get('pincode', '')
            )
            login_user(user_obj)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('medicines'))
            
        flash('Invalid email or password', 'error')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        full_name = request.form['full_name']
        
        conn = get_db_connection()
        
        if conn.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone():
            flash('Email already registered!', 'error')
            return redirect(url_for('register'))
            
        conn.execute('INSERT INTO users (email, password, full_name) VALUES (?, ?, ?)',
                    (email, generate_password_hash(password), full_name))
        conn.commit()
        conn.close()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.pop('cart', None)
    flash('Logged out successfully!', 'success')
    return redirect(url_for('home'))

@app.route('/cart')
@login_required
def cart():
    if 'cart' not in session:
        session['cart'] = {}
    
    cart_items = []
    total = 0
    conn = get_db_connection()
    
    for medicine_id, quantity in session['cart'].items():
        medicine = conn.execute('SELECT * FROM medicines WHERE id = ?', (medicine_id,)).fetchone()
        if medicine:
            item_total = medicine['price'] * quantity
            cart_items.append({
                'medicine': medicine,
                'quantity': quantity,
                'total': item_total
            })
            total += item_total
    
    conn.close()
    return render_template('cart.html', cart_items=cart_items, total=total)

@app.route('/add_to_cart/<int:medicine_id>', methods=['GET', 'POST'])
@login_required
def add_to_cart(medicine_id):
    conn = get_db_connection()
    medicine = conn.execute('SELECT * FROM medicines WHERE id = ?', (medicine_id,)).fetchone()
    conn.close()

    if medicine is None:
        flash('Medicine not found!', 'error')
        return redirect(url_for('medicines'))

    if 'cart' not in session:
        session['cart'] = {}

    cart = session['cart']
    medicine_id_str = str(medicine_id)
    
    if medicine_id_str in cart:
        if cart[medicine_id_str] < medicine['stock']:
            cart[medicine_id_str] += 1
            flash('Added another unit to cart!', 'success')
        else:
            flash('Cannot add more units - stock limit reached!', 'error')
    else:
        cart[medicine_id_str] = 1
        flash('Added to cart!', 'success')

    session['cart'] = cart
    return redirect(url_for('medicines'))

@app.route('/update_cart/<int:medicine_id>', methods=['POST'])
@login_required
def update_cart(medicine_id):
    quantity = int(request.form['quantity'])
    
    if quantity < 1:
        flash('Quantity must be at least 1', 'error')
        return redirect(url_for('cart'))
    
    conn = get_db_connection()
    medicine = conn.execute('SELECT stock FROM medicines WHERE id = ?', (medicine_id,)).fetchone()
    conn.close()
    
    if quantity > medicine['stock']:
        flash(f'Cannot add more than {medicine["stock"]} units', 'error')
        return redirect(url_for('cart'))
    
    cart = session['cart']
    cart[str(medicine_id)] = quantity
    session['cart'] = cart
    flash('Cart updated!', 'success')
    return redirect(url_for('cart'))

@app.route('/remove_from_cart/<int:medicine_id>', methods=['POST'])
@login_required
def remove_from_cart(medicine_id):
    cart = session['cart']
    cart.pop(str(medicine_id), None)
    session['cart'] = cart
    flash('Item removed from cart!', 'success')
    return redirect(url_for('cart'))

@app.route('/checkout/address', methods=['GET', 'POST'])
@login_required
def checkout_address():
    if 'cart' not in session or not session['cart']:
        flash('Your cart is empty!', 'error')
        return redirect(url_for('cart'))
        
    if request.method == 'POST':
        # Save address to session
        session['checkout_address'] = {
            'full_name': request.form.get('full_name', current_user.full_name),
            'phone': request.form.get('phone', current_user.phone),
            'address_line1': request.form.get('address_line1', current_user.address_line1),
            'address_line2': request.form.get('address_line2', current_user.address_line2 or ''),
            'city': request.form.get('city', current_user.city),
            'state': request.form.get('state', current_user.state),
            'pincode': request.form.get('pincode', current_user.pincode)
        }
        return redirect(url_for('checkout_preview'))
    
    # For GET request, pre-fill with user's saved address
    address = {
        'full_name': current_user.full_name,
        'phone': current_user.phone,
        'address_line1': current_user.address_line1,
        'address_line2': current_user.address_line2,
        'city': current_user.city,
        'state': current_user.state,
        'pincode': current_user.pincode
    }
    return render_template('checkout_address.html', address=address)

@app.route('/checkout/preview')
@login_required
def checkout_preview():
    if 'cart' not in session or not session['cart']:
        flash('Your cart is empty!', 'error')
        return redirect(url_for('cart'))
        
    if 'checkout_address' not in session:
        return redirect(url_for('checkout_address'))
        
    conn = get_db_connection()
    cart_items = []
    total = 0
    
    try:
        # Get cart items with medicine details
        for medicine_id, quantity in session['cart'].items():
            medicine = conn.execute('SELECT * FROM medicines WHERE id = ?', (medicine_id,)).fetchone()
            if medicine:
                subtotal = medicine['price'] * quantity
                cart_items.append({
                    'medicine': medicine,
                    'quantity': quantity,
                    'subtotal': subtotal
                })
                total += subtotal
                
        address = session['checkout_address']
        
        return render_template('checkout_preview.html', 
            cart_items=cart_items,
            total=total,
            address=address
        )
    except Exception as e:
        print(f"Error in checkout preview: {e}")
        flash('Error loading checkout preview. Please try again.', 'error')
        return redirect(url_for('cart'))
    finally:
        conn.close()

@app.route('/checkout/payment', methods=['GET', 'POST'])
@login_required
def checkout_payment():
    if 'cart' not in session or not session['cart']:
        flash('Your cart is empty!', 'error')
        return redirect(url_for('cart'))
        
    if 'checkout_address' not in session:
        return redirect(url_for('checkout_address'))
        
    if request.method == 'POST':
        payment_method = request.form.get('payment_method', 'cod')
        
        # Store payment method in session
        session['payment_method'] = payment_method
        
        if payment_method == 'cod':
            # For COD, directly place the order
            return redirect(url_for('place_order'))
        else:
            # For UPI and Card, redirect to payment processing
            return redirect(url_for('process_payment'))
    
    return render_template('checkout_payment.html')

@app.route('/process_payment', methods=['GET', 'POST'])
@login_required
def process_payment():
    if 'cart' not in session or not session['cart']:
        flash('Your cart is empty!', 'error')
        return redirect(url_for('cart'))
        
    if 'checkout_address' not in session:
        return redirect(url_for('checkout_address'))
        
    if 'payment_method' not in session:
        return redirect(url_for('checkout_payment'))
        
    payment_method = session.get('payment_method')
    form = PaymentForm()
    
    if request.method == 'POST' and form.validate_on_submit():
        if payment_method == 'upi' and not form.upi_id.data:
            flash('UPI ID is required', 'error')
            return render_template('process_payment.html', payment_method=payment_method, form=form)
            
        if payment_method == 'card':
            if not all([form.card_number.data, form.expiry.data, form.cvv.data, form.name.data]):
                flash('All card details are required', 'error')
                return render_template('process_payment.html', payment_method=payment_method, form=form)
        
        # Here you would integrate with actual payment gateway
        # For now, we'll simulate successful payment
        session['payment_status'] = 'completed'
        return redirect(url_for('place_order'))
    
    return render_template('process_payment.html', payment_method=payment_method, form=form)

@app.route('/place_order')
@login_required
def place_order():
    if 'cart' not in session or not session['cart']:
        flash('Your cart is empty!', 'error')
        return redirect(url_for('cart'))
        
    if 'checkout_address' not in session:
        return redirect(url_for('checkout_address'))
        
    conn = get_db_connection()
    cart = session['cart']
    address = session['checkout_address']
    
    # Format delivery address
    delivery_address = f"{address['full_name']}\n{address['phone']}\n{address['address_line1']}"
    if address.get('address_line2'):
        delivery_address += f"\n{address['address_line2']}"
    delivery_address += f"\n{address['city']}, {address['state']} - {address['pincode']}"
    
    try:
        total_amount = 0
        order_items = []
        
        # First calculate total and prepare order items
        for medicine_id, quantity in cart.items():
            medicine = conn.execute('SELECT * FROM medicines WHERE id = ?', (medicine_id,)).fetchone()
            if medicine:
                subtotal = medicine['price'] * quantity
                total_amount += subtotal
                order_items.append({
                    'medicine_id': medicine_id,
                    'quantity': quantity,
                    'unit_price': medicine['price'],
                    'total_price': subtotal
                })
        
        payment_method = session.get('payment_method', 'cod')
        payment_status = 'completed' if payment_method != 'cod' else 'pending'
        
        # Insert main order
        cursor = conn.execute('''
            INSERT INTO orders (
                user_id, total_amount, delivery_address, 
                status, payment_method, payment_status
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            current_user.id, total_amount, delivery_address,
            'pending', payment_method, payment_status
        ))
        order_id = cursor.lastrowid
        
        # Insert order items and update stock
        for item in order_items:
            # Insert order item
            conn.execute('''
                INSERT INTO order_items (
                    order_id, medicine_id, quantity, 
                    unit_price, total_price
                ) VALUES (?, ?, ?, ?, ?)
            ''', (
                order_id, item['medicine_id'], item['quantity'],
                item['unit_price'], item['total_price']
            ))
            
            # Update stock
            conn.execute('''
                UPDATE medicines 
                SET stock = stock - ? 
                WHERE id = ?
            ''', (item['quantity'], item['medicine_id']))
        
        conn.commit()
        
        # Clear checkout session data
        session.pop('cart', None)
        session.pop('checkout_address', None)
        session.pop('payment_method', None)
        session.pop('payment_status', None)
        
        flash('Order placed successfully!', 'success')
        return redirect(url_for('profile'))
        
    except sqlite3.Error as e:
        conn.rollback()
        flash('Error placing order. Please try again.', 'error')
        print(f"Database error: {e}")
        return redirect(url_for('checkout_preview'))
        
    finally:
        conn.close()

@app.route('/order_history')
@login_required
def order_history():
    conn = get_db_connection()
    orders = conn.execute('''
        SELECT 
            o.id, o.total_amount, o.delivery_address,
            o.order_date, o.status, o.payment_method, 
            o.payment_status
        FROM orders o
        WHERE o.user_id = ?
        ORDER BY o.order_date DESC
    ''', (current_user.id,)).fetchall()
    
    # Get order items for each order
    for order in orders:
        order_items = conn.execute('''
            SELECT 
                oi.quantity, oi.unit_price, oi.total_price,
                m.name as medicine_name, m.description
            FROM order_items oi
            JOIN medicines m ON oi.medicine_id = m.id
            WHERE oi.order_id = ?
        ''', (order['id'],)).fetchall()
        order['items'] = order_items
    
    conn.close()
    return render_template('order_history.html', orders=orders)

@app.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    if not request.form.get('full_name'):
        flash('Name is required', 'error')
        return redirect(url_for('profile'))
    
    try:
        conn = get_db_connection()
        conn.execute('''
            UPDATE users 
            SET full_name = ?, phone = ?
            WHERE id = ?
        ''', (
            request.form.get('full_name'),
            request.form.get('phone'),
            current_user.id
        ))
        conn.commit()
        flash('Profile updated successfully', 'success')
    except sqlite3.Error as e:
        flash('Error updating profile. Please try again.', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('profile'))

@app.route('/update_address', methods=['POST'])
@login_required
def update_address():
    required_fields = ['address_line1', 'city', 'state', 'pincode']
    if not all(request.form.get(field) for field in required_fields):
        flash('All fields except Address Line 2 are required', 'error')
        return redirect(url_for('profile'))
    
    try:
        conn = get_db_connection()
        conn.execute('''
            UPDATE users 
            SET address_line1 = ?,
                address_line2 = ?,
                city = ?,
                state = ?,
                pincode = ?
            WHERE id = ?
        ''', (
            request.form.get('address_line1'),
            request.form.get('address_line2'),
            request.form.get('city'),
            request.form.get('state'),
            request.form.get('pincode'),
            current_user.id
        ))
        conn.commit()
        flash('Address updated successfully', 'success')
    except sqlite3.Error as e:
        flash('Error updating address. Please try again.', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('profile'))

@app.route('/track_order')
def track_order():
    order_id = request.args.get('order_id')
    if not order_id:
        return render_template('track_order.html', order=None, order_id=None)
    
    try:
        conn = get_db_connection()
        # Get order details
        order = conn.execute('''
            SELECT 
                o.id, o.delivery_address, o.order_date,
                o.status, o.payment_method, o.payment_status,
                o.total_amount
            FROM orders o
            WHERE o.id = ?
        ''', (order_id,)).fetchone()
        
        if order:
            # Convert order to dictionary for modification
            order_dict = dict(order)
            
            # Get order items
            items = conn.execute('''
                SELECT 
                    oi.quantity, oi.unit_price, oi.total_price,
                    m.name as medicine_name, m.description
                FROM order_items oi
                JOIN medicines m ON oi.medicine_id = m.id
                WHERE oi.order_id = ?
            ''', (order_id,)).fetchall()
            
            # Convert items to list of dictionaries
            order_dict['items'] = [dict(item) for item in items]
            
            return render_template('track_order.html', order=order_dict, order_id=order_id)
        else:
            return render_template('track_order.html', order=None, order_id=order_id)
            
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        flash('Error tracking order. Please try again.', 'error')
        return redirect(url_for('home'))
        
    finally:
        conn.close()

@app.route('/book_lab_test/<int:test_id>', methods=['GET', 'POST'])
@login_required
def book_lab_test(test_id):
    conn = get_db_connection()
    try:
        test = conn.execute('SELECT * FROM lab_tests WHERE id = ?', (test_id,)).fetchone()
        if not test:
            flash('Lab test not found!', 'error')
            return redirect(url_for('lab_tests'))
            
        if request.method == 'POST':
            # Get form data
            booking_date = request.form.get('booking_date')
            booking_time = request.form.get('booking_time')
            collection_type = request.form.get('collection_type')
            address = request.form.get('address') if collection_type == 'home' else None
            
            # Insert booking
            cursor = conn.execute('''
                INSERT INTO lab_test_bookings (
                    user_id, test_id, booking_date, booking_time,
                    collection_type, collection_address, status,
                    payment_status, amount
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                current_user.id, test_id, booking_date, booking_time,
                collection_type, address, 'pending', 'pending', test['price']
            ))
            booking_id = cursor.lastrowid
            conn.commit()
            
            # Redirect to payment if not home collection
            if collection_type == 'lab':
                return redirect(url_for('lab_test_payment', booking_id=booking_id))
            
            flash('Lab test booked successfully!', 'success')
            return redirect(url_for('lab_test_bookings'))
            
        # For GET request, show booking form
        # Get available time slots (9 AM to 6 PM, hourly slots)
        available_dates = [(datetime.now() + timedelta(days=x)).strftime('%Y-%m-%d') 
                          for x in range(1, 8)]  # Next 7 days
        time_slots = [f"{hour:02d}:00" for hour in range(9, 18)]
        
        return render_template('book_lab_test.html', 
                             test=test,
                             available_dates=available_dates,
                             time_slots=time_slots)
                             
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        flash('Error booking lab test. Please try again.', 'error')
        return redirect(url_for('lab_tests'))
    finally:
        conn.close()

@app.route('/lab_test_bookings')
@login_required
def lab_test_bookings():
    conn = get_db_connection()
    try:
        bookings = conn.execute('''
            SELECT 
                b.id, b.booking_date, b.booking_time,
                b.collection_type, b.collection_address,
                b.status, b.payment_status, b.amount,
                b.report_url, b.created_at,
                t.name as test_name, t.description as test_description
            FROM lab_test_bookings b
            JOIN lab_tests t ON b.test_id = t.id
            WHERE b.user_id = ?
            ORDER BY b.booking_date DESC, b.booking_time DESC
        ''', (current_user.id,)).fetchall()
        
        return render_template('lab_test_bookings.html', bookings=bookings)
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        flash('Error loading bookings. Please try again.', 'error')
        return redirect(url_for('lab_tests'))
    finally:
        conn.close()

@app.route('/lab_test_payment/<int:booking_id>', methods=['GET', 'POST'])
@login_required
def lab_test_payment(booking_id):
    if request.method == 'POST':
        conn = get_db_connection()
        try:
            # Update booking payment status
            conn.execute('''
                UPDATE lab_test_bookings 
                SET payment_status = 'completed'
                WHERE id = ? AND user_id = ?
            ''', (booking_id, current_user.id))
            conn.commit()
            flash('Payment successful!', 'success')
            return redirect(url_for('lab_test_bookings'))
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            flash('Error processing payment. Please try again.', 'error')
        finally:
            conn.close()
            
    return render_template('lab_test_payment.html', booking_id=booking_id)

@app.route('/upload_health_record', methods=['POST'])
@login_required
def upload_health_record():
    record_type = request.form.get('record_type')
    record_date = request.form.get('record_date')
    description = request.form.get('description')
    
    if 'file' not in request.files:
        flash('No file uploaded', 'error')
        return redirect(url_for('health_records'))
        
    file = request.files['file']
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('health_records'))
        
    if file:
        # Save file logic here
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'health_records', filename)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        file.save(file_path)
        
        conn = get_db_connection()
        try:
            if record_type == 'prescription':
                conn.execute('''
                    INSERT INTO prescriptions (
                        user_id, prescription_date, description, file_url
                    ) VALUES (?, ?, ?, ?)
                ''', (current_user.id, record_date, description, file_path))
            else:
                conn.execute('''
                    INSERT INTO medical_history (
                        user_id, record_date, record_type, description, file_url
                    ) VALUES (?, ?, ?, ?, ?)
                ''', (current_user.id, record_date, record_type, description, file_path))
            conn.commit()
            flash('Health record uploaded successfully!', 'success')
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            flash('Error uploading health record. Please try again.', 'error')
        finally:
            conn.close()
            
    return redirect(url_for('health_records'))

if __name__ == '__main__':
    app.run(debug=True)
