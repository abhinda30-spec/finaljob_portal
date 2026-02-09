from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mail import Mail, Message
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.secret_key = 'btech_sarkari_final_2026'

# --- Configuration for Database (PostgreSQL for Render / SQLite for Local) ---
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    # Render fix: postgres:// ko postgresql:// mein badalna zaroori hai
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
else:
    # Local machine ke liye purana SQLite chalega
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# PDF Upload Folder Setup
UPLOAD_FOLDER = 'static/uploads/pdfs'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db = SQLAlchemy(app)

# --- Email Configuration ---
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'abhishekk95675@gmail.com'
app.config['MAIL_PASSWORD'] = 'gonq jqjw pita acrl' 
app.config['MAIL_DEFAULT_SENDER'] = 'abhishekk95675@gmail.com'
mail = Mail(app)

# --- Models ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(50), nullable=False)

class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    branch = db.Column(db.String(100), nullable=False)
    salary = db.Column(db.String(50), nullable=False)
    url = db.Column(db.String(200), nullable=False)
    last_date = db.Column(db.String(50), nullable=True)
    pdf_filename = db.Column(db.String(200), nullable=True)

# --- DATABASE INITIALIZATION ---
with app.app_context():
    db.create_all()

# --- Routes ---

@app.route('/')
def home():
    user = session.get('username')
    all_jobs = Job.query.all()
    return render_template('index.html', jobs=all_jobs, user=user)

@app.route('/apply/<int:job_id>')
def apply(job_id):
    if 'username' not in session:
        flash("Kindly login first to apply for jobs!", "danger")
        return redirect(url_for('login'))
    job = db.session.get(Job, job_id)
    if job:
        return redirect(job.url)
    return redirect(url_for('home'))

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    user = session.get('username')
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')
        try:
            msg = Message(subject=f"New Inquiry: {name}",
                          recipients=['abhishekk95675@gmail.com'],
                          body=f"Name: {name}\nEmail: {email}\n\nMessage:\n{message}")
            mail.send(msg)
            return "<h3>Aapka message mil gaya hai! Hum jald hi sampark karenge. <a href='/'>Back Home</a></h3>"
        except Exception as e:
            return f"<h3>Email Error: {str(e)}</h3>"
    return render_template('contact.html', user=user)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if not session.get('admin_logged_in'):
        if request.method == 'POST':
            if request.form.get('admin_password') == 'admin123':
                session['admin_logged_in'] = True
                return redirect(url_for('admin'))
            else:
                flash("Incorrect Admin Password!", "danger")
                return redirect(url_for('admin'))
        
        return '''
        <div style="text-align:center; margin-top:100px; font-family:sans-serif;">
            <h2>Admin Access</h2>
            <form method="POST">
                <input type="password" name="admin_password" placeholder="Enter Admin Password" style="padding:10px;">
                <button type="submit" style="padding:10px 20px; cursor:pointer;">Login</button>
            </form>
            <br><a href="/">Back to Home</a>
        </div>
        '''

    if request.method == 'POST':
        pdf_file = request.files.get('pdf_file')
        filename = None
        if pdf_file and pdf_file.filename != '':
            filename = secure_filename(pdf_file.filename)
            pdf_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        new_job = Job(
            title=request.form.get('title'), 
            branch=request.form.get('branch'),
            salary=request.form.get('salary'), 
            url=request.form.get('url'),
            last_date=request.form.get('last_date'),
            pdf_filename=filename
        )
        db.session.add(new_job)
        db.session.commit()
        flash("Job published successfully!", "success")
        return redirect(url_for('admin'))
    
    all_jobs = Job.query.all()
    return render_template('admin.html', jobs=all_jobs)

@app.route('/delete-job/<int:id>')
def delete_job(id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin'))
    
    job_to_delete = db.session.get(Job, id)
    if job_to_delete:
        if job_to_delete.pdf_filename:
            try:
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], job_to_delete.pdf_filename))
            except:
                pass
        db.session.delete(job_to_delete)
        db.session.commit()
        flash("Job deleted successfully!", "success")
    
    return redirect(url_for('admin'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            session['username'] = user.username
            return redirect(url_for('home'))
        else:
            flash("Wrong credentials! Kindly signup now.", "danger")
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash("Username already exists! Choose another.", "danger")
            return redirect(url_for('signup'))
        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()
        flash("Account created successfully! Please login.", "success")
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('home'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)