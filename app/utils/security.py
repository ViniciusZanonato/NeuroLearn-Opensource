import re
from datetime import datetime
from functools import wraps
from markupsafe import escape
from urllib.parse import urlparse
from flask import session, redirect, url_for, request

rate_limit_cache = {}


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def professor_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session or session.get('tipo') != 'professor':
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def aluno_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session or session.get('tipo') != 'aluno':
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def validar_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def sanitizar_entrada(texto):
    if not texto:
        return ""
    texto = str(texto)[:1000]
    texto = escape(texto)
    texto = re.sub(r'[<>"\';\(\)&+]', '', texto)
    return texto.strip()


def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions


def validar_url(url):
    if not url:
        return True
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ['http', 'https']:
            return False
        if parsed.hostname in ['localhost', '127.0.0.1', '0.0.0.0']:
            return False
        return True
    except Exception:
        return False


def rate_limit_key():
    ip = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
    user_id = session.get('usuario_id', 'anonymous')
    return f"{ip}:{user_id}"


def check_rate_limit(key, limit=10, window=60):
    now = datetime.now()
    for k in list(rate_limit_cache.keys()):
        if (now - rate_limit_cache[k]['last_reset']).seconds > window:
            del rate_limit_cache[k]
    if key not in rate_limit_cache:
        rate_limit_cache[key] = {'count': 1, 'last_reset': now}
        return True
    entry = rate_limit_cache[key]
    if (now - entry['last_reset']).seconds > window:
        entry['count'] = 1
        entry['last_reset'] = now
        return True
    if entry['count'] >= limit:
        return False
    entry['count'] += 1
    return True


def validar_senha(senha):
    if len(senha) < 8:
        return False, "Senha deve ter pelo menos 8 caracteres"
    if len(senha) > 128:
        return False, "Senha muito longa (máximo 128 caracteres)"
    if not re.search(r'[A-Za-z]', senha):
        return False, "Senha deve conter pelo menos uma letra"
    if not re.search(r'[0-9]', senha):
        return False, "Senha deve conter pelo menos um número"
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', senha):
        return False, "Senha deve conter pelo menos um caractere especial"
    senhas_comuns = ['12345678', 'password', 'password123', '123456789', 'qwerty123']
    if senha.lower() in senhas_comuns:
        return False, "Senha muito comum, escolha uma senha mais segura"
    return True, "Senha válida"
