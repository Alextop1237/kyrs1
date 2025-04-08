from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_bcrypt import Bcrypt
from psycopg2 import connect, Error
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)
bcrypt = Bcrypt(app)




@app.route('/ultimate_test')
def ultimate_test():
    # 1. Тестовые данные (в обход БД)
    test_data = [
        (1, "Концерт Queen", "2023-12-20", "19:00", 2500),
        (2, "Балет Лебединое озеро", "2023-12-22", "18:30", 1800)
    ]
    
    # 2. Генерируем HTML напрямую
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Ultimate Test</title></head>
    <body>
        <h1>Тест шаблонизатора</h1>
        <div id="events">
    """
    
    for event in test_data:
        html += f"""
        <div style="border:1px solid #ccc; padding:10px; margin:10px;">
            <h3>{event[1]}</h3>
            <p>Дата: {event[2]} в {event[3]}</p>
            <p>Цена: {event[4]} руб.</p>
        </div>
        """
    
    html += "</div></body></html>"
    
    return html




@app.route('/fixed')
def fixed():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Максимально простой запрос
        cur.execute("SELECT id, name FROM measure LIMIT 10")
        events = cur.fetchall()
        
        # Генерируем HTML напрямую
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Тест отображения</title>
            <style>
                body { font-family: Arial; padding: 20px; }
                .event { padding: 10px; margin: 5px; background: #f0f0f0; }
            </style>
        </head>
        <body>
            <h1>Тестовое отображение мероприятий</h1>
            <div id="events">
        """
        
        if not events:
            html += "<p>Нет мероприятий в базе</p>"
        else:
            for event in events:
                html += f'<div class="event">{event[0]}: {event[1]}</div>'
        
        html += """
            </div>
            <p>Проверка завершена. Данные из БД отображаются.</p>
        </body>
        </html>
        """
        
        return html
        
    except Exception as e:
        return f"Ошибка: {str(e)}"
    finally:
        if conn:
            conn.close()


# Database connection
def get_db_connection():
    try:
        conn = connect(
            dbname="measures",
            user="postgres",
            password="student",
            host="localhost",
            port="5432"
        )
        return conn
    except Error as e:
        print(f"Error connecting to PostgreSQL: {e}")
        return None

# Home page
@app.route('/')
def index():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Упрощенный запрос для теста
        cur.execute("""
            SELECT id, name, date, time, price 
            FROM measure 
            WHERE date >= CURRENT_DATE
            ORDER BY date
            LIMIT 10
        """)
        measures = cur.fetchall()
        
        # Дебаг вывод
        print("Мероприятия из БД:", measures)
        
        return render_template('index.html', 
                            measures=measures,
                            show_events=True)  # Добавляем флаг для шаблона
        
    except Exception as e:
        print("Ошибка:", e)
        return render_template('index.html', 
                            measures=[],
                            show_events=False)
    finally:
        if conn:
            conn.close()


# User registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        mail = request.form['mail']
        login = request.form['login']
        password = request.form['password']
        name = request.form['name']
        
        conn = get_db_connection()
        if not conn:
            flash('Database connection error', 'danger')
            return redirect(url_for('register'))
        
        try:
            cur = conn.cursor()
            
            # Check if user exists
            cur.execute("SELECT id FROM users WHERE mail = %s OR login = %s", (mail, login))
            if cur.fetchone():
                flash('User with this email or login already exists', 'danger')
                return redirect(url_for('register'))
            
            # Get user role (default is 'user')
            cur.execute("SELECT id FROM roles WHERE user_role = 'user'")
            role_id = cur.fetchone()[0]
            
            # Hash password
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
            
            # Insert new user
            cur.execute("""
                INSERT INTO users (role_id, mail, login, password, name)
                VALUES (%s, %s, %s, %s, %s)
            """, (role_id, mail, login, hashed_password, name))
            conn.commit()
            
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
            
        except Error as e:
            conn.rollback()
            print(f"Error during registration: {e}")
            flash('Registration failed. Please try again.', 'danger')
            return redirect(url_for('register'))
        finally:
            if conn:
                conn.close()
    
    return render_template('register.html')

# User login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login = request.form['login']
        password = request.form['password']
        
        conn = get_db_connection()
        if not conn:
            flash('Database connection error', 'danger')
            return redirect(url_for('login'))
        
        try:
            cur = conn.cursor()
            
            # Get user data
            cur.execute("""
                SELECT u.id, u.password, r.user_role, u.name 
                FROM users u 
                JOIN roles r ON u.role_id = r.id 
                WHERE u.login = %s
            """, (login,))
            user_data = cur.fetchone()
            
            if user_data and bcrypt.check_password_hash(user_data[1], password):
                session['user_id'] = user_data[0]
                session['user_role'] = user_data[2]
                session['user_name'] = user_data[3]
                flash('Login successful!', 'success')
                return redirect(url_for('index'))
            else:
                flash('Invalid login or password', 'danger')
                return redirect(url_for('login'))
                
        except Error as e:
            print(f"Error during login: {e}")
            flash('Login failed. Please try again.', 'danger')
            return redirect(url_for('login'))
        finally:
            if conn:
                conn.close()
    
    return render_template('login.html')

# User logout
@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

# List all measures
@app.route('/measures')
def list_measures():
    conn = get_db_connection()
    if not conn:
        flash('Database connection error', 'danger')
        return redirect(url_for('index'))
    
    try:
        cur = conn.cursor()
        
        # Get all measures with area names
        cur.execute("""
            SELECT m.id, m.name, m.date, m.time, m.length, m.price, a.name as area_name 
            FROM measure m 
            JOIN area a ON m.area_id = a.id 
            WHERE m.date >= CURRENT_DATE 
            ORDER BY m.date, m.time
        """)
        measures = cur.fetchall()
        
        return render_template('measures.html', measures=measures)
    except Error as e:
        print(f"Error fetching measures: {e}")
        flash('Error fetching measures', 'danger')
        return redirect(url_for('index'))
    finally:
        if conn:
            conn.close()

# Measure details and ticket purchase
@app.route('/measure/<int:measure_id>', methods=['GET', 'POST'])
def measure_detail(measure_id):
    if 'user_id' not in session:
        flash('Please log in to purchase tickets', 'warning')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    if not conn:
        flash('Database connection error', 'danger')
        return redirect(url_for('list_measures'))
    
    try:
        cur = conn.cursor()
        
        # Get measure details
        cur.execute("""
            SELECT m.id, m.name, m.date, m.time, m.length, m.price, a.name as area_name, a.id as area_id 
            FROM measure m 
            JOIN area a ON m.area_id = a.id 
            WHERE m.id = %s
        """, (measure_id,))
        measure = cur.fetchone()
        
        if not measure:
            flash('Measure not found', 'danger')
            return redirect(url_for('list_measures'))
        
        # Get topology for the area
        cur.execute("""
            SELECT row, placecount 
            FROM topology 
            WHERE area_id = %s 
            ORDER BY row
        """, (measure[7],))
        topology = cur.fetchall()
        
        # Get sold tickets
        cur.execute("""
            SELECT row, place 
            FROM ticket 
            WHERE measure_id = %s
        """, (measure_id,))
        sold_tickets = cur.fetchall()
        sold_tickets = {(t[0], t[1]) for t in sold_tickets}
        
        if request.method == 'POST':
            row = int(request.form['row'])
            place = int(request.form['place'])
            
            # Check if seat is available
            if (row, place) in sold_tickets:
                flash('This seat is already taken', 'danger')
                return redirect(url_for('measure_detail', measure_id=measure_id))
            
            # Check if seat exists in topology
            valid_seat = False
            for topo_row in topology:
                if topo_row[0] == row and 1 <= place <= topo_row[1]:
                    valid_seat = True
                    break
            
            if not valid_seat:
                flash('Invalid seat selection', 'danger')
                return redirect(url_for('measure_detail', measure_id=measure_id))
            
            # Calculate ticket price (could add premium for certain rows)
            ticket_price = measure[5]  # Base price
            
            # Insert ticket
            cur.execute("""
                INSERT INTO ticket (measure_id, row, place, price)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            """, (measure_id, row, place, ticket_price))
            ticket_id = cur.fetchone()[0]
            
            # Update user's ticket
            cur.execute("""
                UPDATE users 
                SET ticket_id = %s 
                WHERE id = %s
            """, (ticket_id, session['user_id']))
            
            conn.commit()
            
            flash(f'Ticket purchased successfully for row {row}, seat {place}!', 'success')
            return redirect(url_for('my_tickets'))
        
        return render_template('measure_detail.html', measure=measure, topology=topology, sold_tickets=sold_tickets)
    
    except Error as e:
        conn.rollback()
        print(f"Error during ticket purchase: {e}")
        flash('Ticket purchase failed. Please try again.', 'danger')
        return redirect(url_for('measure_detail', measure_id=measure_id))
    finally:
        if conn:
            conn.close()

# User's tickets
@app.route('/my_tickets')
def my_tickets():
    if 'user_id' not in session:
        flash('Please log in to view your tickets', 'warning')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    if not conn:
        flash('Database connection error', 'danger')
        return redirect(url_for('index'))
    
    try:
        cur = conn.cursor()
        
        # Get user's tickets
        cur.execute("""
            SELECT t.id, m.name, m.date, m.time, a.name as area_name, t.row, t.place, t.price 
            FROM ticket t 
            JOIN measure m ON t.measure_id = m.id 
            JOIN area a ON m.area_id = a.id 
            JOIN users u ON u.ticket_id = t.id 
            WHERE u.id = %s
        """, (session['user_id'],))
        tickets = cur.fetchall()
        
        return render_template('my_tickets.html', tickets=tickets)
    except Error as e:
        print(f"Error fetching tickets: {e}")
        flash('Error fetching your tickets', 'danger')
        return redirect(url_for('index'))
    finally:
        if conn:
            conn.close()

# Admin dashboard
@app.route('/admin/dashboard')
def admin_dashboard():
    if 'user_id' not in session or session['user_role'] not in ['admin', 'measure admin']:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    if not conn:
        flash('Database connection error', 'danger')
        return redirect(url_for('index'))
    
    try:
        cur = conn.cursor()
        
        # Get measures count
        cur.execute("SELECT COUNT(*) FROM measure")
        measures_count = cur.fetchone()[0]
        
        # Get users count
        cur.execute("SELECT COUNT(*) FROM users")
        users_count = cur.fetchone()[0]
        
        # Get tickets count
        cur.execute("SELECT COUNT(*) FROM ticket")
        tickets_count = cur.fetchone()[0]
        
        # Get recent measures
        cur.execute("""
            SELECT m.id, m.name, m.date, a.name 
            FROM measure m 
            JOIN area a ON m.area_id = a.id 
            ORDER BY m.date DESC 
            LIMIT 5
        """)
        recent_measures = cur.fetchall()
        
        return render_template('admin/dashboard.html', 
                            measures_count=measures_count,
                            users_count=users_count,
                            tickets_count=tickets_count,
                            recent_measures=recent_measures)
    except Error as e:
        print(f"Error in admin dashboard: {e}")
        flash('Error loading dashboard', 'danger')
        return redirect(url_for('index'))
    finally:
        if conn:
            conn.close()

# Add new measure (admin only)
@app.route('/admin/add_measure', methods=['GET', 'POST'])
def add_measure():
    if 'user_id' not in session or session['user_role'] not in ['admin', 'measure admin']:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    if not conn:
        flash('Database connection error', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    try:
        cur = conn.cursor()
        
        # Get all areas for dropdown
        cur.execute("SELECT id, name FROM area")
        areas = cur.fetchall()
        
        if request.method == 'POST':
            name = request.form['name']
            area_id = int(request.form['area_id'])
            date_str = request.form['date']
            time = request.form['time']
            length = float(request.form['length'])
            price = float(request.form['price'])
            
            # Convert date string to date object
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            # Insert new measure
            cur.execute("""
                INSERT INTO measure (area_id, name, date, time, length, price)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (area_id, name, date, time, length, price))
            conn.commit()
            
            flash('Measure added successfully!', 'success')
            return redirect(url_for('admin_dashboard'))
        
        return render_template('admin/add_measure.html', areas=areas)
    except Error as e:
        conn.rollback()
        print(f"Error adding measure: {e}")
        flash('Error adding measure', 'danger')
        return redirect(url_for('admin_dashboard'))
    finally:
        if conn:
            conn.close()

# Add new area (admin only)
@app.route('/admin/add_area', methods=['GET', 'POST'])
def add_area():
    if 'user_id' not in session or session['user_role'] != 'admin':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        name = request.form['name']
        
        conn = get_db_connection()
        if not conn:
            flash('Database connection error', 'danger')
            return redirect(url_for('admin_dashboard'))
        
        try:
            cur = conn.cursor()
            
            # Insert new area
            cur.execute("INSERT INTO area (name) VALUES (%s) RETURNING id", (name,))
            area_id = cur.fetchone()[0]
            
            # Add topology rows
            rows = int(request.form['rows'])
            for row in range(1, rows + 1):
                places = int(request.form[f'places_row_{row}'])
                cur.execute("""
                    INSERT INTO topology (area_id, row, placecount)
                    VALUES (%s, %s, %s)
                """, (area_id, row, places))
            
            conn.commit()
            
            flash('Area added successfully!', 'success')
            return redirect(url_for('admin_dashboard'))
        except Error as e:
            conn.rollback()
            print(f"Error adding area: {e}")
            flash('Error adding area', 'danger')
            return redirect(url_for('admin_dashboard'))
        finally:
            if conn:
                conn.close()
    
    return render_template('admin/add_area.html')

if __name__ == '__main__':
    app.run(debug=True)