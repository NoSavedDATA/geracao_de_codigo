import sqlite3
import hashlib
import uuid
from flask import Flask, request, jsonify, g
from functools import wraps

app = Flask(__name__)
app.config['DATABASE'] = 'chat_app.db'
app.config['ADMIN_USERNAME'] = 'admin'

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            token TEXT,
            is_admin INTEGER DEFAULT 0
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            recipient_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(sender_id) REFERENCES users(id),
            FOREIGN KEY(recipient_id) REFERENCES users(id)
        )
    """)
    db.commit()
    # Create admin user if not exist
    cur = db.execute("SELECT * FROM users WHERE username = ?", (app.config['ADMIN_USERNAME'],))
    if cur.fetchone() is None:
        admin_pass = hash_password('admin123')
        db.execute("INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, 1)", 
                   (app.config['ADMIN_USERNAME'], admin_pass))
        db.commit()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def generate_token():
    return str(uuid.uuid4())

def authenticate(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'Auth token required'}), 401
        db = get_db()
        cur = db.execute("SELECT * FROM users WHERE token = ?", (token,))
        user = cur.fetchone()
        if not user:
            return jsonify({'error': 'Invalid token'}), 403
        g.user = user
        return f(*args, **kwargs)
    return decorated

def admin_only(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not getattr(g, 'user', None) or g.user['is_admin'] == 0:
            return jsonify({'error': 'Admin only'}), 403
        return f(*args, **kwargs)
    return decorated

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({'error': 'username and password required'}), 400

    db = get_db()
    try:
        db.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)",
                   (username, hash_password(password)))
        db.commit()
        return jsonify({'message': 'User registered successfully'}), 201
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Username already exists'}), 409

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({'error': 'username and password required'}), 400

    db = get_db()
    cur = db.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cur.fetchone()
    if user and hash_password(password) == user['password_hash']:
        token = generate_token()
        db.execute("UPDATE users SET token = ? WHERE id = ?", (token, user['id']))
        db.commit()
        return jsonify({'token': token, "is_admin": bool(user['is_admin']), "user_id": user['id']}), 200
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/logout', methods=['POST'])
@authenticate
def logout():
    db = get_db()
    db.execute("UPDATE users SET token = NULL WHERE id = ?", (g.user['id'],))
    db.commit()
    return jsonify({'message': 'Logged out successfully'}), 200

@app.route('/users', methods=['GET'])
@authenticate
def list_users():
    db = get_db()
    users = db.execute("SELECT id, username, is_admin FROM users").fetchall()
    result = [{'id': u['id'], 'username': u['username'], 'is_admin': bool(u['is_admin'])} for u in users]
    return jsonify(result), 200

@app.route('/messages', methods=['POST'])
@authenticate
def send_message():
    data = request.get_json()
    recipient_id = data.get('recipient_id')
    content = data.get('content')
    if not recipient_id or not content:
        return jsonify({'error': 'recipient_id and content required'}), 400
    db = get_db()
    if recipient_id == g.user['id']:
        return jsonify({"error": "Cannot send messages to yourself."}), 400
    cur = db.execute("SELECT * FROM users WHERE id = ?", (recipient_id,))
    if not cur.fetchone():
        return jsonify({'error': 'Recipient not found'}), 404
    db.execute('INSERT INTO messages (sender_id, recipient_id, content) VALUES (?, ?, ?)',
               (g.user['id'], recipient_id, content))
    db.commit()
    return jsonify({'message': 'Message sent'}), 201

@app.route('/messages', methods=['GET'])
@authenticate
def receive_messages():
    db = get_db()
    cur = db.execute(
        """SELECT messages.id, users.username AS sender, messages.content, messages.timestamp
         FROM messages
         JOIN users ON messages.sender_id = users.id
         WHERE messages.recipient_id = ?
         ORDER BY messages.timestamp DESC""",
        (g.user['id'],)
    )
    messages = [
        {
            'id': row['id'],
            'sender': row['sender'],
            'content': row['content'],
            'timestamp': row['timestamp']
        }
        for row in cur.fetchall()
    ]
    return jsonify(messages), 200

@app.route('/users/<int:user_id>', methods=['DELETE'])
@authenticate
@admin_only
def remove_user(user_id):
    if user_id == g.user['id']:
        return jsonify({"error": "Admin cannot remove themselves."}), 400
    db = get_db()
    cur = db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cur.fetchone()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    db.execute("DELETE FROM users WHERE id = ?", (user_id,))
    db.execute("DELETE FROM messages WHERE sender_id = ? OR recipient_id = ?", (user_id, user_id))
    db.commit()
    return jsonify({'message': 'User removed'}), 200

@app.route('/admin/messages', methods=['GET'])
@authenticate
@admin_only
def admin_all_messages():
    db = get_db()
    cur = db.execute("""
        SELECT messages.id, s.username AS sender, r.username AS recipient, messages.content, messages.timestamp
        FROM messages
        JOIN users s ON messages.sender_id = s.id
        JOIN users r ON messages.recipient_id = r.id
        ORDER BY messages.timestamp DESC
    """)
    messages = [
        {
            'id': row['id'],
            'sender': row['sender'],
            'recipient': row['recipient'],
            'content': row['content'],
            'timestamp': row['timestamp']
        }
        for row in cur.fetchall()
    ]
    return jsonify(messages), 200

if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(debug=True)