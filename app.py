from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename  
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
    
DB_NAME = 'database.db'

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE,
                        password TEXT
                    )''')
        c.execute('''CREATE TABLE IF NOT EXISTS medicines (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT,
                        quantity INTEGER,
                        price REAL,
                        image TEXT,
                        user_id INTEGER
                    )''')

init_db()

# ------------------ ROUTES ------------------
@app.route('/')
def home():
    if 'user_id' in session:
        return redirect('/dashboard')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'], method='pbkdf2:sha256')

        try:
            with sqlite3.connect(DB_NAME) as conn:
                c = conn.cursor()
                c.execute(
                    "INSERT INTO users (username, password) VALUES (?, ?)",
                    (username, password)
                )
            flash("Ro‘yxatdan o‘tish muvaffaqiyatli! Kirishingiz mumkin.", "success")
            return redirect('/')
        except sqlite3.IntegrityError:
            flash("Foydalanuvchi mavjud!", "danger")
            return redirect('/register')

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        with sqlite3.connect(DB_NAME) as conn:
            c = conn.cursor()
            user = c.execute(
                "SELECT * FROM users WHERE username=?",
                (username,)
            ).fetchone()

            if user and check_password_hash(user[2], password):
                session['user_id'] = user[0]
                session['username'] = user[1]
                return redirect('/dashboard')

        flash("Login yoki parol noto‘g‘ri!", "danger")
        return redirect('/login')  # ❌ '/' emas '/login' bo'lishi kerak

    # GET so‘rovi bo‘lsa sahifa render qilinsin
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/')

    search = request.args.get('search', '')

    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()

        if search:
            medicines = c.execute(
                "SELECT * FROM medicines WHERE user_id=? AND name LIKE ?",
                (session['user_id'], f"%{search}%")
            ).fetchall()
        else:
            medicines = c.execute(
                "SELECT * FROM medicines WHERE user_id=?",
                (session['user_id'],)
            ).fetchall()

    return render_template('dashboard.html', medicines=medicines)

@app.route('/add', methods=['POST'])
def add_medicine():
    name = request.form['name']
    quantity = request.form['quantity']
    price = request.form['price']

    # 👇 BU YANGI QISM (rasm olish)
    file = request.files['image']

    filename = ''
    if file and file.filename != '' and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    else:
        filename = ''


    # 👇 databasega saqlash
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO medicines (name, quantity, price, image, user_id) VALUES (?, ?, ?, ?, ?)",
            (name, quantity, price, filename, session['user_id'])
        )

    return redirect('/dashboard')

@app.route('/delete/<int:id>', methods=['POST'])
def delete_medicine(id):
    if 'user_id' not in session:
        return redirect('/')

    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute(
            "DELETE FROM medicines WHERE id=? AND user_id=?",
            (id, session['user_id'])
        )

    return redirect('/dashboard')
@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect('/')


@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_medicine(id):
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()

        if request.method == 'POST':
            name = request.form['name']
            quantity = request.form['quantity']
            price = request.form['price']

            file = request.files.get('image')

            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)   # ✅ SHU YER HAM
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

                c.execute("""
                    UPDATE medicines
                    SET name=?, quantity=?, price=?, image=?
                    WHERE id=? AND user_id=?
                """, (name, quantity, price, filename, id))
            else:
                filename = ''
                c.execute("""
                    UPDATE medicines
                    SET name=?, quantity=?, price=?
                    WHERE id=? AND user_id=?
                """, (name, quantity, price, id))

            return redirect('/dashboard')

        medicine = c.execute(
            "SELECT * FROM medicines WHERE id=?",
            (id,)
        ).fetchone()

    return render_template('edit.html', medicine=medicine)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)