from flask import Blueprint, request, jsonify, session
from functools import wraps
import sqlite3
import hashlib

admin_bp = Blueprint('admin', __name__)

DB_PATH = 'database.db'


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('is_admin') != True:
            return jsonify({'error': 'Acesso restrito'}), 403
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/admin/login', methods=['POST'])
def admin_login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({'error': 'Preencha todos os campos.'}), 400

    conn = get_db_connection()
    admin = conn.execute(
        'SELECT * FROM users WHERE username = ? AND is_admin = 1', (username,)
    ).fetchone()
    conn.close()

    if admin and admin['password'] == hash_password(password):
        session['user_id'] = admin['id']
        session['is_admin'] = True
        return jsonify({'message': 'Login de admin realizado com sucesso.'}), 200
    return jsonify({'error': 'Credenciais de administrador inválidas.'}), 401


@admin_bp.route('/admin/logout', methods=['POST'])
@admin_required
def admin_logout():
    session.clear()
    return jsonify({'message': 'Logout de admin realizado com sucesso.'}), 200


@admin_bp.route('/admin/users', methods=['GET'])
@admin_required
def list_users():
    conn = get_db_connection()
    users = conn.execute(
        'SELECT id, username, is_admin FROM users'
    ).fetchall()
    conn.close()
    users_list = [
        {'id': user['id'], 'username': user['username'], 'is_admin': bool(user['is_admin'])}
        for user in users
    ]
    return jsonify({'users': users_list}), 200


@admin_bp.route('/admin/remove_user/<int:user_id>', methods=['DELETE'])
@admin_required
def remove_user(user_id):
    # Previne remoção do próprio admin
    if user_id == session.get('user_id'):
        return jsonify({'error': 'Não é possível remover o próprio administrador.'}), 400

    conn = get_db_connection()
    user = conn.execute(
        'SELECT * FROM users WHERE id = ?', (user_id,)
    ).fetchone()
    if not user:
        conn.close()
        return jsonify({'error': 'Usuário não encontrado.'}), 404

    conn.execute('DELETE FROM messages WHERE sender_id = ? OR receiver_id = ?', (user_id, user_id))
    conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Usuário removido com sucesso.'}), 200