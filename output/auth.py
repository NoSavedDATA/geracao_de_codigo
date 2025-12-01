from flask import Blueprint, request, jsonify, current_app, g
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import jwt
import datetime
import sqlite3

auth_bp = Blueprint('auth', __name__)

DATABASE = 'database.db'
SECRET_KEY = 'your_secret_key_here' # Troque por um segredo mais seguro

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@auth_bp.before_app_request
def before_request():
    get_db()

@auth_bp.teardown_app_request
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def create_tables():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
        if not token:
            return jsonify({'message': 'Token ausente!'}), 401
        try:
            data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            db = get_db()
            cur = db.execute('SELECT * FROM users WHERE id=?', (data['id'],))
            user = cur.fetchone()
            if not user:
                return jsonify({'message': 'Usuário não encontrado.'}), 401
            g.current_user = user
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token expirado!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Token inválido!'}), 401
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = getattr(g, 'current_user', None)
        if not user or user['is_admin'] != 1:
            return jsonify({'message': 'Acesso de administrador necessário!'}), 403
        return f(*args, **kwargs)
    return decorated

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'message': 'Dados de cadastro incompletos'}), 400
    username = data['username']
    password = data['password']
    is_admin = data.get('is_admin', 0)
    hashed_password = generate_password_hash(password)
    db = get_db()
    try:
        db.execute('INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)',
                   (username, hashed_password, is_admin))
        db.commit()
        return jsonify({'message': 'Usuário cadastrado com sucesso.'}), 201
    except sqlite3.IntegrityError:
        return jsonify({'message': 'Nome de usuário já está em uso.'}), 409

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'message': 'Dados de login incompletos'}), 400
    username = data['username']
    password = data['password']

    db = get_db()
    cur = db.execute('SELECT * FROM users WHERE username=?', (username,))
    user = cur.fetchone()
    if not user or not check_password_hash(user['password'], password):
        return jsonify({'message': 'Nome de usuário ou senha incorretos.'}), 401
    token = jwt.encode({
        'id': user['id'],
        'username': user['username'],
        'is_admin': user['is_admin'],
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=12)
    }, SECRET_KEY, algorithm="HS256")
    return jsonify({'token': token})

@auth_bp.route('/me', methods=['GET'])
@token_required
def get_current_user():
    user = g.current_user
    return jsonify({'id': user['id'], 'username': user['username'], 'is_admin': bool(user['is_admin'])})

@auth_bp.route('/users', methods=['GET'])
@token_required
@admin_required
def list_users():
    db = get_db()
    cur = db.execute('SELECT id, username, is_admin FROM users')
    users = [dict(id=row['id'], username=row['username'], is_admin=bool(row['is_admin'])) for row in cur.fetchall()]
    return jsonify({'users': users})

@auth_bp.route('/users/<int:user_id>', methods=['DELETE'])
@token_required
@admin_required
def delete_user(user_id):
    db = get_db()
    # Não permite remover a si mesmo
    if g.current_user['id'] == user_id:
        return jsonify({'message': 'O administrador não pode remover a si mesmo.'}), 400
    cur = db.execute('DELETE FROM users WHERE id=?', (user_id,))
    db.commit()
    if cur.rowcount == 0:
        return jsonify({'message': 'Usuário não encontrado.'}), 404
    return jsonify({'message': 'Usuário removido com sucesso.'})

# Para inicializar o banco de dados com um admin (executar uma vez)
def create_admin_user(username, password):
    hashed_password = generate_password_hash(password)
    db = sqlite3.connect(DATABASE)
    try:
        db.execute('INSERT INTO users (username, password, is_admin) VALUES (?, ?, 1)',
                   (username, hashed_password))
        db.commit()
    except sqlite3.IntegrityError:
        pass
    db.close()

# Chame esta função apenas uma vez para criar o banco/tabelas e admin
# create_tables()
# create_admin_user('admin', 'admin123')