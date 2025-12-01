# Gere código python com os seguintes requisitos:
# 1. O sistema deve possuir back-end em python, e front-end em node.js
# 2. O sistema deve realizar cadastro de usuários.
# 3. O banco de dados deve ser local.
# 4. O sistema deve gerenciar a troca de mensagem entre os usuários
# 5. O sistema deve possuir um administrador que possa remover usuários

import sqlite3
from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS
app = Flask(__name__)
CORS(app)
DATABASE = 'chat_app.db'
ADMIN_PASSWORD = 'admin123'  # Senha do administrador (deve ser alterada para produção)
def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  password TEXT NOT NULL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS messages
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  sender_id INTEGER,
                  receiver_id INTEGER,
                  message TEXT,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY(sender_id) REFERENCES users(id),
                  FOREIGN KEY(receiver_id) REFERENCES users(id))''')
    conn.commit()
    conn.close()
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data['username']
    password = generate_password_hash(data['password'])
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        return jsonify({'message': 'User registered successfully!'}), 201
    except sqlite3.IntegrityError:
        return jsonify({'message': 'Username already exists!'}), 409
    finally:
        conn.close()
# faça uma função de login que retorne um token de autenticação
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data['username']
    password = data['password']
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT id, password FROM users WHERE username = ?", (username,))
    user = c.fetchone()
    conn.close()
    if user and check_password_hash(user[1], password):
        token = generate_token()
        return jsonify({'message': 'Login successful!', 'token': token, 'user_id': user[0]}), 200
    else:
        return jsonify({'message': 'Invalid credentials!'}), 401
@app.route('/send_message', methods=['POST'])
def send_message():
    data = request.get_json()
    sender_id = data['sender_id']
    receiver_id = data['receiver_id']
    message = data['message']
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("INSERT INTO messages (sender_id, receiver_id, message) VALUES (?, ?, ?)",
              (sender_id, receiver_id, message))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Message sent successfully!'}), 201
@app.route('/get_messages', methods=['GET'])
def get_messages():
    user_id = request.args.get('user_id')
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT sender_id, receiver_id, message, timestamp FROM messages WHERE receiver_id = ?", (user_id,))
    messages = c.fetchall()
    conn.close()
    return jsonify({'messages': messages}), 200
@app.route('/remove_user', methods=['DELETE'])
def remove_user():
    data = request.get_json()
    admin_password = data['admin_password']
    user_id = data['user_id']
    if admin_password != ADMIN_PASSWORD:
        return jsonify({'message': 'Unauthorized!'}), 401
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'User removed successfully!'}), 200
if __name__ == '__main__':
    init_db()
    app.run(debug=True)
