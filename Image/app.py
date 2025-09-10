from flask import Flask, request, render_template, jsonify, redirect, url_for, session
import os
import cv2
import numpy as np
import sqlite3
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

# Initialize Flask app
app = Flask(__name__)
app.secret_key = "supersecretkey"

# Configure upload folder
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Database setup
def init_db():
    conn = sqlite3.connect('database/users.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        password TEXT NOT NULL)''')
    conn.commit()
    conn.close()

init_db()

# Load trained model
MODEL_PATH = "model/model.h5"
model = load_model(MODEL_PATH)

# Image Preprocessing Function
def preprocess_image(img_path):
    img = cv2.imread(img_path)
    img_array = np.array([cv2.resize(img, (112, 112))]).astype(np.float32) / 255.0
    img_flat = img_array.reshape(-1,768)
    return img_flat

# Home route
@app.route("/")
def index():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template("index.html")

# Login Route
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        
        conn = sqlite3.connect('database/users.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()
        
        if user and check_password_hash(user[2], password):
            session['user'] = username
            return redirect(url_for('index'))
        else:
            return "Invalid username or password!"
    
    return render_template("login.html")

# Register Route
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = generate_password_hash(request.form["password"])
        
        try:
            conn = sqlite3.connect('database/users.db')
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
            conn.close()
            return redirect(url_for('login'))
        except:
            return "Username already exists!"
    
    return render_template("register.html")

# Logout Route
@app.route("/logout")
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

# Image Upload and Prediction Route
@app.route("/upload", methods=["POST"])
def upload_image():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"})
    
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    # Preprocess and predict
    img_array = preprocess_image(filepath)
    prediction = model.predict(img_array)
    result = "Watermarked" if prediction[0][0] > 0.5 else "Not Watermarked"
    
    return render_template("result.html", filename=filename, result=result)

if __name__ == "__main__":
    app.run(debug=True)
