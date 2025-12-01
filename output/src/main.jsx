import React, { useEffect, useState, createContext, useContext } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate } from 'react-router-dom';

const API_URL = 'http://localhost:5000';

// Contexto de autenticação
const AuthContext = createContext();

function useAuth() {
  return useContext(AuthContext);
}

// Provedor de autenticação
function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));

  useEffect(() => {
    if (token) {
      fetch(`${API_URL}/me`, {
        headers: { Authorization: `Bearer ${token}` }
      })
        .then(res => {
          if (!res.ok) throw new Error();
          return res.json();
        })
        .then(data => setUser(data))
        .catch(() => {
          setToken(null);
          setUser(null);
          localStorage.removeItem('token');
        });
    }
  }, [token]);

  const login = async (username, password) => {
    const res = await fetch(`${API_URL}/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    if (res.ok) {
      const data = await res.json();
      setToken(data.token);
      localStorage.setItem('token', data.token);
      return true;
    }
    return false;
  };

  const register = async (username, password) => {
    const res = await fetch(`${API_URL}/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    return res.ok;
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('token');
  };

  return (
    <AuthContext.Provider value={{ user, token, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

// Rota protegida
function PrivateRoute({ children, adminOnly = false }) {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" />;
  if (adminOnly && !user.is_admin) return <Navigate to="/" />;
  return children;
}

// Página de Login
function Login() {
  const { login } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  const handleSubmit = async e => {
    e.preventDefault();
    const ok = await login(username, password);
    if (ok) navigate('/');
    else setError('Usuário ou senha inválidos');
  };

  return (
    <div>
      <h2>Login</h2>
      <form onSubmit={handleSubmit}>
        <input placeholder="Usuário" value={username} onChange={e => setUsername(e.target.value)} />
        <input type="password" placeholder="Senha" value={password} onChange={e => setPassword(e.target.value)} />
        <button type="submit">Entrar</button>
      </form>
      {error && <div>{error}</div>}
      <a href="/register">Cadastrar</a>
    </div>
  );
}

// Página de Cadastro
function Register() {
  const { register } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [ok, setOk] = useState(null);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  const handleSubmit = async e => {
    e.preventDefault();
    const success = await register(username, password);
    if (success) {
      setOk('Cadastro realizado!');
      setTimeout(() => navigate('/login'), 1000);
    } else {
      setError('Falha no cadastro');
    }
  };

  return (
    <div>
      <h2>Cadastro</h2>
      <form onSubmit={handleSubmit}>
        <input placeholder="Usuário" value={username} onChange={e => setUsername(e.target.value)} />
        <input type="password" placeholder="Senha" value={password} onChange={e => setPassword(e.target.value)} />
        <button type="submit">Cadastrar</button>
      </form>
      {ok && <div>{ok}</div>}
      {error && <div>{error}</div>}
      <a href="/login">Voltar para login</a>
    </div>
  );
}

// Página inicial - lista usuários e chat
function Home() {
  const { user, token, logout } = useAuth();
  const [users, setUsers] = useState([]);
  const [activeUser, setActiveUser] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMsg, setNewMsg] = useState('');
  const [refresh, setRefresh] = useState(0);

  useEffect(() => {
    fetch(`${API_URL}/users`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(res => res.json())
      .then(setUsers);
  }, [token, refresh]);

  useEffect(() => {
    if (activeUser) {
      fetch(`${API_URL}/messages/${activeUser.id}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
        .then(res => res.json())
        .then(setMessages);
    } else {
      setMessages([]);
    }
  }, [activeUser, token, refresh]);

  const sendMessage = async () => {
    if (!newMsg.trim()) return;
    await fetch(`${API_URL}/messages/${activeUser.id}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`
      },
      body: JSON.stringify({ content: newMsg }),
    });
    setNewMsg('');
    setRefresh(x => x + 1);
  };

  return (
    <div>
      <h2>Bem-vindo, {user.username} <button onClick={logout}>Sair</button></h2>
      <div style={{ display: 'flex' }}>
        <div style={{ width: 200, marginRight: 30 }}>
          <h3>Usuários</h3>
          <ul>
            {users.filter(u => u.id !== user.id).map(u => (
              <li
                key={u.id}
                style={{ cursor: 'pointer', fontWeight: activeUser?.id === u.id ? 'bold' : 'normal' }}
                onClick={() => setActiveUser(u)}
              >
                {u.username}
              </li>
            ))}
          </ul>
          {user.is_admin && <a href="/admin">Painel Admin</a>}
        </div>
        <div style={{ flex: 1 }}>
          <h3>Mensagens</h3>
          {activeUser ? (
            <div>
              <div style={{ height: 300, overflowY: 'auto', border: '1px solid #ccc', padding: 8 }}>
                {messages.map((msg, i) => (
                  <div key={i} style={{ textAlign: msg.from_id === user.id ? 'right' : 'left' }}>
                    <b>{msg.from_id === user.id ? 'Eu' : activeUser.username}:</b> {msg.content}
                  </div>
                ))}
              </div>
              <div>
                <input
                  value={newMsg}
                  onChange={e => setNewMsg(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && sendMessage()}
                  placeholder="Digite a mensagem"
                  style={{ width: '80%' }}
                />
                <button onClick={sendMessage}>Enviar</button>
              </div>
            </div>
          ) : (
            <div>Selecione um usuário para conversar</div>
          )}
        </div>
      </div>
    </div>
  );
}

// Painel Administrador
function AdminPanel() {
  const { user, token, logout } = useAuth();
  const [users, setUsers] = useState([]);
  const [error, setError] = useState(null);

  const loadUsers = () => {
    fetch(`${API_URL}/users`, {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then(res => res.json())
      .then(setUsers);
  };

  useEffect(() => {
    loadUsers();
  }, [token]);

  const removeUser = async userId => {
    if (window.confirm('Deseja remover este usuário?')) {
      const res = await fetch(`${API_URL}/users/${userId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        setUsers(users.filter(u => u.id !== userId));
      } else {
        setError('Falha ao remover usuário');
      }
    }
  };

  return (
    <div>
      <h2>Painel Administrativo <button onClick={logout}>Sair</button></h2>
      {error && <div>{error}</div>}
      <h3>Usuários cadastrados</h3>
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Usuário</th>
            <th>Admin</th>
            <th>Ação</th>
          </tr>
        </thead>
        <tbody>
          {users.filter(u => u.id !== user.id).map(u => (
            <tr key={u.id}>
              <td>{u.id}</td>
              <td>{u.username}</td>
              <td>{u.is_admin ? "Sim" : "Não"}</td>
              <td>
                <button onClick={() => removeUser(u.id)}>Remover</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <a href="/">Voltar</a>
    </div>
  );
}

// App principal
export default function App() {
  return (
    <React.StrictMode>
      <AuthProvider>
        <Router>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route
              path="/admin"
              element={
                <PrivateRoute adminOnly>
                  <AdminPanel />
                </PrivateRoute>
              }
            />
            <Route
              path="/"
              element={
                <PrivateRoute>
                  <Home />
                </PrivateRoute>
              }
            />
            <Route path="*" element={<Navigate to="/" />} />
          </Routes>
        </Router>
      </AuthProvider>
    </React.StrictMode>
  );
}