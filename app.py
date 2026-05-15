from flask import Flask, render_template, request, jsonify, session, redirect, url_for, abort
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import requests
import json
import os
import re
import secrets
import hashlib
from functools import wraps
from markupsafe import escape
from urllib.parse import urlparse
from dotenv import load_dotenv

# Carregar variáveis do arquivo .env
load_dotenv()

# Importar o filtro de relatório
from filtro_relatorio_neurodivergencia import FiltroRelatorioNeurodivergencia, filtrar_relatorio_json

# Funções de segurança e validação
def login_required(f):
    """Decorator para exigir login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def professor_required(f):
    """Decorator para exigir perfil de professor"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session or session.get('tipo') != 'professor':
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def aluno_required(f):
    """Decorator para exigir perfil de aluno"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session or session.get('tipo') != 'aluno':
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def validar_email(email):
    """Valida formato de email"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def sanitizar_entrada(texto):
    """Sanitiza entrada de texto"""
    if not texto:
        return ""
    # Converter para string e limitar tamanho
    texto = str(texto)[:1000]  # Limitar a 1000 caracteres
    # Remove scripts e tags perigosas
    texto = escape(texto)
    # Remove caracteres especiais perigosos
    texto = re.sub(r'[<>"\';\(\)&+]', '', texto)
    return texto.strip()

def allowed_file(filename):
    """Verifica se o arquivo tem extensão permitida"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validar_url(url):
    """Valida se a URL é segura"""
    if not url:
        return True
    try:
        parsed = urlparse(url)
        # Permitir apenas HTTP e HTTPS
        if parsed.scheme not in ['http', 'https']:
            return False
        # Bloquear URLs locais em produção
        if parsed.hostname in ['localhost', '127.0.0.1', '0.0.0.0']:
            return False
        return True
    except:
        return False

def rate_limit_key():
    """Gera chave para rate limiting baseada no IP e usuário"""
    ip = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
    user_id = session.get('usuario_id', 'anonymous')
    return f"{ip}:{user_id}"

# Cache simples para rate limiting
rate_limit_cache = {}

def check_rate_limit(key, limit=10, window=60):
    """Verifica rate limiting simples"""
    now = datetime.now()
    
    # Limpar entradas antigas
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
    """Valida força da senha"""
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
    # Verificar se não é uma senha comum
    senhas_comuns = ['12345678', 'password', 'password123', '123456789', 'qwerty123']
    if senha.lower() in senhas_comuns:
        return False, "Senha muito comum, escolha uma senha mais segura"
    return True, "Senha válida"

app = Flask(__name__)
# Configurações de segurança - usar variáveis de ambiente em produção
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sistema_educacional.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configurações de segurança adicionais
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file upload
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
# Permitir HTTP em desenvolvimento - ALTERAR PARA True EM PRODUÇÃO
app.config['SESSION_COOKIE_SECURE'] = False  # Permitir HTTP em desenvolvimento
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent XSS
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF protection
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=2)  # Session timeout

# Extensões permitidas para upload
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'ppt', 'pptx'}

db = SQLAlchemy(app)

# Configuracao de IA.
# Padrao: Ollama local para evitar envio de dados sensiveis de alunos a terceiros.
AI_PROVIDER = os.environ.get('AI_PROVIDER', 'ollama').strip().lower()
OLLAMA_BASE_URL = os.environ.get('OLLAMA_BASE_URL', 'http://127.0.0.1:11434').rstrip('/')
OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL', 'gemma3:12b')
OLLAMA_TIMEOUT = int(os.environ.get('OLLAMA_TIMEOUT', '180'))
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
GEMINI_URL = os.environ.get(
    'GEMINI_URL',
    'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent'
)

if AI_PROVIDER == 'ollama':
    print(f"IA configurada para Ollama local: {OLLAMA_MODEL} em {OLLAMA_BASE_URL}")
elif AI_PROVIDER == 'gemini' and not GEMINI_API_KEY:
    print("AVISO: AI_PROVIDER=gemini, mas GEMINI_API_KEY nao configurada. Funcionalidades de IA serao limitadas.")

# Modelos do Banco de Dados
class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    senha_hash = db.Column(db.String(100), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)  # 'professor' ou 'aluno'
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)

class Aluno(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    email_escola = db.Column(db.String(100))  # ID da escola ou email escolar
    serie_ano = db.Column(db.String(20), nullable=False)
    professor_responsavel = db.Column(db.String(100), nullable=False)
    idade = db.Column(db.Integer, nullable=False)
    questionario_completo = db.Column(db.Boolean, default=False)
    perfil_gerado = db.Column(db.Boolean, default=False)
    observacoes = db.Column(db.Text)
    usuario = db.relationship('Usuario', backref=db.backref('aluno_perfil', uselist=False))

class Professor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    disciplina = db.Column(db.String(100))
    formacao = db.Column(db.String(200))
    usuario = db.relationship('Usuario', backref=db.backref('professor_perfil', uselist=False))

class Atividade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    tipo = db.Column(db.String(50), nullable=False)  # 'logica', 'memoria', 'criatividade', etc.
    professor_id = db.Column(db.Integer, db.ForeignKey('professor.id'), nullable=False)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    data_limite = db.Column(db.DateTime)  # Data limite para entrega
    arquivo_anexo = db.Column(db.String(200))  # Nome do arquivo anexado
    arquivo_original = db.Column(db.String(200))  # Nome original do arquivo
    pontuacao_maxima = db.Column(db.Integer, default=100)
    instrucoes_especiais = db.Column(db.Text)  # Instruções adicionais
    professor = db.relationship('Professor', backref='atividades')

class RespostaAluno(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey('aluno.id'), nullable=False)
    atividade_id = db.Column(db.Integer, db.ForeignKey('atividade.id'), nullable=False)
    resposta = db.Column(db.Text, nullable=False)
    tempo_resposta = db.Column(db.Integer)  # em segundos
    data_envio = db.Column(db.DateTime, default=datetime.utcnow)
    aluno = db.relationship('Aluno', backref='respostas')
    atividade = db.relationship('Atividade', backref='respostas')

class AnaliseIA(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey('aluno.id'), nullable=False)
    tipo_analise = db.Column(db.String(100), nullable=False)
    resultado = db.Column(db.Text, nullable=False)
    confianca = db.Column(db.Float)  # 0-1
    data_analise = db.Column(db.DateTime, default=datetime.utcnow)
    aluno = db.relationship('Aluno', backref='analises')

# Novos modelos para NeuroLearn
class QuestionarioNeuroLearn(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey('aluno.id'), nullable=False)
    bloco = db.Column(db.Integer, nullable=False)  # 1-7 (blocos temáticos)
    questao = db.Column(db.Integer, nullable=False)  # 1-67
    resposta = db.Column(db.Integer, nullable=False)  # 1-5 (escala)
    data_resposta = db.Column(db.DateTime, default=datetime.utcnow)
    aluno = db.relationship('Aluno', backref='questionario_respostas')

class PerfilAprendizagem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey('aluno.id'), nullable=False, unique=True)
    perfil_geral = db.Column(db.Text)
    potenciais_expressivos = db.Column(db.Text)
    potenciais_cognitivos = db.Column(db.Text)
    indicios_neurodivergencias = db.Column(db.Text)
    recomendacoes_professores = db.Column(db.Text)
    reforco_motivacional = db.Column(db.Text)
    tipo_perfil = db.Column(db.String(100))  # para filtros do professor
    data_geracao = db.Column(db.DateTime, default=datetime.utcnow)
    aluno = db.relationship('Aluno', backref=db.backref('perfil_aprendizagem', uselist=False))

# Novos modelos para as funcionalidades adicionais

class TestePerfiliCognitivo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey('aluno.id'), nullable=False)
    tipo_teste = db.Column(db.String(50), nullable=False)  # visual, auditivo, sinestesico, logico
    pontuacao = db.Column(db.Integer, nullable=False)
    tempo_resposta = db.Column(db.Integer)  # em segundos
    data_teste = db.Column(db.DateTime, default=datetime.utcnow)
    resultados_detalhados = db.Column(db.Text)  # JSON com detalhes
    aluno = db.relationship('Aluno', backref='testes_cognitivos')

class TrilhaAprendizado(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), nullable=False)
    descricao = db.Column(db.Text)
    tipo_conteudo = db.Column(db.String(50), nullable=False)  # audio, texto, jogo, video
    nivel_dificuldade = db.Column(db.String(20), nullable=False)  # facil, medio, dificil
    area_conhecimento = db.Column(db.String(100), nullable=False)  # matematica, portugues, ciencias, etc
    perfil_alvo = db.Column(db.String(100))  # tipo de perfil mais adequado
    duracao_estimada = db.Column(db.Integer)  # em minutos
    url_conteudo = db.Column(db.String(500))
    arquivo_conteudo = db.Column(db.String(200))
    ativo = db.Column(db.Boolean, default=True)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)

class ProgressoTrilha(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey('aluno.id'), nullable=False)
    trilha_id = db.Column(db.Integer, db.ForeignKey('trilha_aprendizado.id'), nullable=False)
    progresso = db.Column(db.Float, default=0.0)  # 0.0 a 100.0
    tempo_gasto = db.Column(db.Integer, default=0)  # em minutos
    data_inicio = db.Column(db.DateTime, default=datetime.utcnow)
    data_conclusao = db.Column(db.DateTime)
    feedback_aluno = db.Column(db.Text)
    dificuldade_percebida = db.Column(db.Integer)  # 1-5
    aluno = db.relationship('Aluno', backref='progressos_trilha')
    trilha = db.relationship('TrilhaAprendizado', backref='progressos')

class CronogramaEstudo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey('aluno.id'), nullable=False)
    data_inicio = db.Column(db.Date, nullable=False)
    data_fim = db.Column(db.Date, nullable=False)
    objetivo = db.Column(db.String(200), nullable=False)
    horas_por_dia = db.Column(db.Float, nullable=False)
    dias_semana = db.Column(db.String(20), nullable=False)  # "1,2,3,4,5" para seg-sex
    horario_preferido = db.Column(db.String(20))  # "manha", "tarde", "noite"
    tempo_pausa = db.Column(db.Integer, default=10)  # minutos de pausa
    tempo_sessao = db.Column(db.Integer, default=25)  # minutos por sessão (pomodoro)
    lembretes_ativos = db.Column(db.Boolean, default=True)
    ativo = db.Column(db.Boolean, default=True)
    aluno = db.relationship('Aluno', backref='cronogramas')

class SessaoEstudo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cronograma_id = db.Column(db.Integer, db.ForeignKey('cronograma_estudo.id'), nullable=False)
    data_sessao = db.Column(db.DateTime, nullable=False)
    duracao_planejada = db.Column(db.Integer, nullable=False)  # minutos
    duracao_real = db.Column(db.Integer)  # minutos
    realizada = db.Column(db.Boolean, default=False)
    feedback = db.Column(db.Text)
    nivel_concentracao = db.Column(db.Integer)  # 1-5
    trilha_estudada = db.Column(db.Integer, db.ForeignKey('trilha_aprendizado.id'))
    cronograma = db.relationship('CronogramaEstudo', backref='sessoes')
    trilha = db.relationship('TrilhaAprendizado', backref='sessoes_estudo')

class BibliotecaConteudo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    descricao = db.Column(db.Text)
    tipo = db.Column(db.String(50), nullable=False)  # podcast, video, jogo
    categoria = db.Column(db.String(100), nullable=False)  # matematica, portugues, ciencias, historia, etc
    nivel_ensino = db.Column(db.String(20))  # fundamental1, fundamental2, medio
    url_conteudo = db.Column(db.String(500))
    arquivo_conteudo = db.Column(db.String(200))
    tem_legenda = db.Column(db.Boolean, default=False)
    tem_libras = db.Column(db.Boolean, default=False)
    tem_transcricao = db.Column(db.String(500))  # arquivo de transcrição
    duracao = db.Column(db.Integer)  # em minutos
    classificacao_etaria = db.Column(db.String(10))  # livre, 10, 12, 14, 16, 18
    tags = db.Column(db.String(500))  # tags separadas por vírgula
    ativo = db.Column(db.Boolean, default=True)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)

class MonitoramentoComportamento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey('aluno.id'), nullable=False)
    data_acao = db.Column(db.DateTime, default=datetime.utcnow)
    tipo_acao = db.Column(db.String(50), nullable=False)  # login, logout, inicio_atividade, fim_atividade, pausa, erro, acerto
    contexto = db.Column(db.String(100))  # qual atividade, trilha, etc
    tempo_gasto = db.Column(db.Integer)  # em segundos
    dispositivo = db.Column(db.String(50))  # mobile, desktop, tablet
    resultado = db.Column(db.String(20))  # sucesso, erro, incompleto
    detalhes = db.Column(db.Text)  # informações adicionais em JSON
    aluno = db.relationship('Aluno', backref='monitoramentos')

class ConfiguracaoAcessibilidade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False, unique=True)
    modo_escuro = db.Column(db.Boolean, default=False)
    alto_contraste = db.Column(db.Boolean, default=False)
    tamanho_fonte = db.Column(db.String(20), default='normal')  # pequeno, normal, grande, muito-grande
    audio_leitura = db.Column(db.Boolean, default=False)
    velocidade_audio = db.Column(db.Float, default=1.0)  # 0.5 a 2.0
    navegacao_simplificada = db.Column(db.Boolean, default=False)
    reducao_animacoes = db.Column(db.Boolean, default=False)
    notificacoes_visuais = db.Column(db.Boolean, default=True)
    notificacoes_sonoras = db.Column(db.Boolean, default=True)
    cores_personalizadas = db.Column(db.String(500))  # JSON com cores customizadas
    usuario = db.relationship('Usuario', backref=db.backref('config_acessibilidade', uselist=False))

class InteracaoAssistente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    mensagem_usuario = db.Column(db.Text, nullable=False)
    resposta_assistente = db.Column(db.Text, nullable=False)
    contexto = db.Column(db.String(100))  # dashboard, atividade, cronograma, etc
    satisfacao_resposta = db.Column(db.Integer)  # 1-5, avaliação do usuário
    data_interacao = db.Column(db.DateTime, default=datetime.utcnow)
    resolveu_duvida = db.Column(db.Boolean)
    usuario = db.relationship('Usuario', backref='interacoes_assistente')

IA_SYSTEM_PROMPT = """
Voce e um assistente pedagogico local do NeuroLearn.
Regras obrigatorias:
- Nunca produza diagnostico medico, clinico ou laudo.
- Trate TDAH, TEA, dislexia, superdotacao e termos similares como hipoteses pedagogicas ou indicadores observacionais.
- Recomende revisao humana por professor, coordenacao pedagogica e profissionais qualificados quando necessario.
- Nao invente dados sobre o aluno.
- Priorize privacidade, linguagem cuidadosa, LGPD e acoes pedagogicas praticas.
- Responda em portugues do Brasil.
""".strip()

def _prompt_com_guardrails(prompt):
    return f"{IA_SYSTEM_PROMPT}\n\nContexto e tarefa:\n{prompt}"

def consultar_ollama(prompt):
    data = {
        'model': OLLAMA_MODEL,
        'prompt': _prompt_com_guardrails(prompt),
        'stream': False,
        'options': {
            'temperature': 0.2,
            'top_p': 0.9,
            'num_ctx': 8192
        }
    }

    try:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json=data,
            timeout=OLLAMA_TIMEOUT
        )
        if response.status_code == 200:
            return response.json().get('response', '').strip()
        return f"Erro no Ollama local: HTTP {response.status_code}"
    except requests.exceptions.ConnectionError:
        return (
            "IA local indisponivel: o Ollama nao esta rodando em "
            f"{OLLAMA_BASE_URL}. Inicie o Ollama e garanta que o modelo {OLLAMA_MODEL} esteja instalado."
        )
    except Exception as e:
        return f"Erro no Ollama local: {str(e)}"

def consultar_gemini(prompt):
    if not GEMINI_API_KEY:
        return "IA externa desativada: GEMINI_API_KEY nao configurada."

    data = {
        "contents": [
            {
                "parts": [
                    {"text": _prompt_com_guardrails(prompt)}
                ]
            }
        ]
    }

    try:
        response = requests.post(
            f"{GEMINI_URL}?key={GEMINI_API_KEY}",
            headers={'Content-Type': 'application/json'},
            json=data,
            timeout=60
        )

        if response.status_code == 200:
            result = response.json()
            return result['candidates'][0]['content']['parts'][0]['text']
        return f"Erro na API Gemini: {response.status_code}"
    except Exception as e:
        return f"Erro na API Gemini: {str(e)}"

def consultar_ia(prompt):
    if AI_PROVIDER == 'gemini':
        return consultar_gemini(prompt)
    return consultar_ollama(prompt)

# Rotas principais
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        senha = request.form['senha']
        tipo = request.form['tipo']
        
        # Verificar se o email já existe
        if Usuario.query.filter_by(email=email).first():
            return jsonify({'erro': 'Email já cadastrado'}), 400
        
        # Criar novo usuário
        novo_usuario = Usuario(
            nome=nome,
            email=email,
            senha_hash=generate_password_hash(senha),
            tipo=tipo
        )
        
        db.session.add(novo_usuario)
        db.session.commit()
        
        # Criar perfil específico
        if tipo == 'aluno':
            aluno = Aluno(
                usuario_id=novo_usuario.id,
                email_escola=request.form.get('email_escola'),
                serie_ano=request.form.get('serie_ano'),
                professor_responsavel=request.form.get('professor_responsavel'),
                idade=int(request.form.get('idade'))
            )
            db.session.add(aluno)
        else:
            professor = Professor(
                usuario_id=novo_usuario.id,
                disciplina=request.form.get('disciplina'),
                formacao=request.form.get('formacao')
            )
            db.session.add(professor)
        
        db.session.commit()
        
        # Auto-login: set session for the newly registered user
        session['usuario_id'] = novo_usuario.id
        session['tipo'] = novo_usuario.tipo
        
        return jsonify({'sucesso': 'Usuário registrado com sucesso'})
    
    return render_template('registro.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']
        
        usuario = Usuario.query.filter_by(email=email).first()
        
        if usuario and check_password_hash(usuario.senha_hash, senha):
            session['usuario_id'] = usuario.id
            session['tipo'] = usuario.tipo

            if usuario.tipo == 'aluno':
                aluno = Aluno.query.filter_by(usuario_id=usuario.id).first()
                if aluno:
                    registrar_monitoramento(aluno.id, 'login', 'sistema')
            
            if usuario.tipo == 'professor':
                return redirect(url_for('dashboard_professor'))
            else:
                return redirect(url_for('dashboard_aluno'))
        else:
            return jsonify({'erro': 'Credenciais inválidas'}), 401
    
    return render_template('login.html')

@app.route('/dashboard-professor')
def dashboard_professor():
    if 'usuario_id' not in session or session['tipo'] != 'professor':
        return redirect(url_for('login'))
    
    professor = Professor.query.filter_by(usuario_id=session['usuario_id']).first()
    atividades = Atividade.query.filter_by(professor_id=professor.id).all()
    
    return render_template('dashboard_professor.html', atividades=atividades)

@app.route('/dashboard-aluno')
def dashboard_aluno():
    if 'usuario_id' not in session or session['tipo'] != 'aluno':
        return redirect(url_for('login'))
    
    aluno = Aluno.query.filter_by(usuario_id=session['usuario_id']).first()
    
    # Se não completou o questionário, redireciona para o questionário
    if not aluno.questionario_completo:
        return redirect(url_for('questionario_neurolearn'))
    
    atividades = Atividade.query.all()
    # IMPORTANTE: Alunos NÃO veem seus próprios perfis completos
    # Apenas status se foi gerado ou não
    perfil_status = {
        'gerado': aluno.perfil_gerado,
        'data_geracao': None
    }
    
    if aluno.perfil_gerado:
        perfil = PerfilAprendizagem.query.filter_by(aluno_id=aluno.id).first()
        if perfil:
            perfil_status['data_geracao'] = perfil.data_geracao
    
    return render_template('dashboard_aluno.html', atividades=atividades, perfil_status=perfil_status)

@app.route('/criar-atividade', methods=['GET', 'POST'])
def criar_atividade():
    if 'usuario_id' not in session or session['tipo'] != 'professor':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        professor = Professor.query.filter_by(usuario_id=session['usuario_id']).first()
        
        # Processamento da data limite
        data_limite = None
        if request.form.get('data_limite'):
            from datetime import datetime
            data_limite = datetime.strptime(request.form['data_limite'], '%Y-%m-%dT%H:%M')
        
        # Processamento do arquivo anexo
        arquivo_anexo = None
        arquivo_original = None
        if 'arquivo' in request.files:
            arquivo = request.files['arquivo']
            if arquivo and arquivo.filename != '':
                import os
                from werkzeug.utils import secure_filename
                
                # Criar diretório de uploads se não existir
                upload_folder = os.path.join(app.root_path, 'static', 'uploads')
                os.makedirs(upload_folder, exist_ok=True)
                
                # Salvar arquivo com nome seguro
                arquivo_original = arquivo.filename
                nome_arquivo = f"atividade_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{secure_filename(arquivo.filename)}"
                arquivo_anexo = nome_arquivo
                arquivo.save(os.path.join(upload_folder, nome_arquivo))
        
        atividade = Atividade(
            titulo=request.form['titulo'],
            descricao=request.form['descricao'],
            tipo=request.form['tipo'],
            professor_id=professor.id,
            data_limite=data_limite,
            arquivo_anexo=arquivo_anexo,
            arquivo_original=arquivo_original,
            pontuacao_maxima=int(request.form.get('pontuacao_maxima', 100)),
            instrucoes_especiais=request.form.get('instrucoes_especiais', '')
        )
        
        db.session.add(atividade)
        db.session.commit()
        
        return redirect(url_for('dashboard_professor'))
    
    return render_template('criar_atividade.html')

@app.route('/responder-atividade/<int:atividade_id>', methods=['GET', 'POST'])
def responder_atividade(atividade_id):
    if 'usuario_id' not in session or session['tipo'] != 'aluno':
        return redirect(url_for('login'))
    
    atividade = Atividade.query.get_or_404(atividade_id)
    aluno = Aluno.query.filter_by(usuario_id=session['usuario_id']).first()
    
    if request.method == 'POST':
        resposta = RespostaAluno(
            aluno_id=aluno.id,
            atividade_id=atividade_id,
            resposta=request.form['resposta'],
            tempo_resposta=request.form.get('tempo_resposta', 0)
        )
        
        db.session.add(resposta)
        db.session.commit()
        
        # Analisar resposta com IA
        analisar_resposta_ia(aluno.id, resposta.id)
        
        return redirect(url_for('dashboard_aluno'))
    
    return render_template('responder_atividade.html', atividade=atividade)

def analisar_resposta_ia(aluno_id, resposta_id):
    """Análise da resposta do aluno usando IA para identificar padrões de neurodivergência"""
    aluno = Aluno.query.get(aluno_id)
    resposta = RespostaAluno.query.get(resposta_id)
    
    # Coletar todas as respostas do aluno
    todas_respostas = RespostaAluno.query.filter_by(aluno_id=aluno_id).all()
    
    # Construir prompt para análise baseado em Ontopsicologia
    prompt = f"""
    Você é um especialista em Psicologia Educacional e Ontopsicologia (Antonio Meneghetti). 
    Analise as respostas de um aluno para identificar possíveis neurodivergências e padrões de aprendizagem.
    
    Dados do Aluno:
    - Série: {aluno.serie_ano}
    
    Última Resposta:
    - Atividade: {resposta.atividade.titulo} (Tipo: {resposta.atividade.tipo})
    - Resposta: {resposta.resposta}
    - Tempo de resposta: {resposta.tempo_resposta} segundos
    
    Histórico de Respostas (últimas 5):
    """
    
    # Adicionar histórico de respostas
    for r in todas_respostas[-5:]:
        prompt += f"\n- {r.atividade.titulo}: {r.resposta[:100]}..."
    
    prompt += """
    
    Com base na Ontopsicologia de Antonio Meneghetti, que enfatiza:
    1. A análise do Em Si ôntico individual
    2. Padrões de comportamento e resposta
    3. Potencial criativo e lógico
    4. Identificação de neurodivergências como TDAH, Autismo, Dislexia, Superdotação
    
    Forneça uma análise estruturada:
    1. Padrões identificados
    2. Possíveis neurodivergências (se houver)
    3. Estratégias pedagógicas recomendadas
    4. Nível de confiança da análise (0-100%)
    
    Responda em formato JSON.
    """
    
    try:
        resultado_ia = consultar_ia(prompt)
        
        # Salvar análise no banco
        analise = AnaliseIA(
            aluno_id=aluno_id,
            tipo_analise='neurodivergencia',
            resultado=resultado_ia,
            confianca=0.8  # Placeholder
        )
        
        db.session.add(analise)
        db.session.commit()
        
    except Exception as e:
        print(f"Erro na análise IA: {e}")

@app.route('/relatorio-aluno/<int:aluno_id>')
def relatorio_aluno(aluno_id):
    if 'usuario_id' not in session or session['tipo'] != 'professor':
        return redirect(url_for('login'))
    
    aluno = Aluno.query.get_or_404(aluno_id)
    analises = AnaliseIA.query.filter_by(aluno_id=aluno_id).all()
    respostas = RespostaAluno.query.filter_by(aluno_id=aluno_id).all()
    
    return render_template('relatorio_aluno.html', 
                         aluno=aluno, 
                         analises=analises, 
                         respostas=respostas)

@app.route('/alunos')
def listar_alunos():
    if 'usuario_id' not in session or session['tipo'] != 'professor':
        return redirect(url_for('login'))
    
    alunos = Aluno.query.all()
    return render_template('listar_alunos.html', alunos=alunos)

# Rotas específicas do NeuroLearn
@app.route('/questionario-neurolearn')
def questionario_neurolearn():
    if 'usuario_id' not in session or session['tipo'] != 'aluno':
        return redirect(url_for('login'))
    
    aluno = Aluno.query.filter_by(usuario_id=session['usuario_id']).first()
    
    # Verificar se já completou o questionário
    if aluno.questionario_completo:
        return redirect(url_for('dashboard_aluno'))
    
    # Definir as 67 questões do Forma Mentis NeuroLearn organizadas em 7 blocos
    questoes = {
        1: {
            'titulo': 'Percepção e Processamento Sensorial',
            'questoes': [
                'Me incomodo facilmente com ruídos altos ou sons repetitivos',
                'Prefiro ambientes com pouca luminosidade',
                'Sinto desconforto com certas texturas de roupas ou materiais',
                'Preciso de mais tempo para processar informações visuais complexas',
                'Tenho facilidade para perceber detalhes que outros não notam',
                'Me sinto sobrecarregado em ambientes com muitos estímulos',
                'Prefiro atividades que envolvem um sentido por vez',
                'Tenho dificuldade para filtrar ruídos de fundo',
                'Sou sensível a cheiros fortes',
                'Preciso de pausas frequentes durante atividades intensas'
            ]
        },
        2: {
            'titulo': 'Atenção e Foco',
            'questoes': [
                'Tenho dificuldade para manter atenção em tarefas longas',
                'Me distraio facilmente com pensamentos ou estímulos externos',
                'Consigo me concentrar intensamente quando algo me interessa',
                'Tenho dificuldade para alternar entre diferentes atividades',
                'Preciso de lembretes constantes para completar tarefas',
                'Me perco facilmente em devaneios ou pensamentos',
                'Tenho dificuldade para prestar atenção em instruções faladas',
                'Consigo trabalhar melhor em ambientes silenciosos',
                'Tenho tendência a procrastinar tarefas importantes',
                'Me sinto mais produtivo em determinados horários do dia'
            ]
        },
        3: {
            'titulo': 'Comunicação e Expressão',
            'questoes': [
                'Prefiro me comunicar por escrito ao invés de falar',
                'Tenho dificuldade para expressar meus pensamentos verbalmente',
                'Uso gestos e expressões corporais para me comunicar',
                'Tenho facilidade para entender metáforas e linguagem figurada',
                'Prefiro conversas individuais ao invés de grupos',
                'Tenho dificuldade para iniciar conversas com pessoas desconhecidas',
                'Consigo me expressar melhor através de arte ou criatividade',
                'Tenho tendência a ser muito direto ao falar',
                'Gosto de explicar coisas com detalhes e exemplos',
                'Tenho dificuldade para entender ironia ou sarcasmo'
            ]
        },
        4: {
            'titulo': 'Organização e Planejamento',
            'questoes': [
                'Tenho dificuldade para organizar meus materiais e espaços',
                'Prefiro seguir rotinas e padrões estabelecidos',
                'Tenho facilidade para criar sistemas de organização',
                'Me sinto ansioso quando minha rotina é alterada',
                'Tenho dificuldade para estimar tempo necessário para tarefas',
                'Preciso de listas e lembretes para me organizar',
                'Gosto de planejar atividades com antecedência',
                'Tenho dificuldade para priorizar tarefas importantes',
                'Prefiro ambientes organizados e limpos',
                'Tenho facilidade para seguir instruções passo a passo'
            ]
        },
        5: {
            'titulo': 'Aprendizagem e Memória',
            'questoes': [
                'Aprendo melhor através de exemplos visuais',
                'Tenho facilidade para memorizar informações que me interessam',
                'Preciso repetir informações várias vezes para memorizar',
                'Aprendo melhor fazendo ao invés de apenas ouvindo',
                'Tenho dificuldade para lembrar sequências ou ordens',
                'Consigo fazer conexões entre conceitos aparentemente diferentes',
                'Prefiro aprender no meu próprio ritmo',
                'Tenho facilidade para lembrar detalhes específicos',
                'Aprendo melhor quando posso relacionar com experiências pessoais',
                'Tenho dificuldade com tarefas que exigem memorização mecânica'
            ]
        },
        6: {
            'titulo': 'Interação Social e Emocional',
            'questoes': [
                'Prefiro atividades individuais ao invés de em grupo',
                'Tenho dificuldade para interpretar expressões faciais',
                'Me sinto confortável em situações sociais familiares',
                'Tenho poucos amigos próximos, mas relacionamentos profundos',
                'Tenho dificuldade para entender regras sociais não escritas',
                'Me sinto ansioso em situações sociais novas',
                'Gosto de ajudar outros com seus problemas',
                'Tenho facilidade para perceber quando alguém está triste',
                'Prefiro ouvir ao invés de falar em conversas',
                'Me sinto mais confortável com pessoas que compartilham meus interesses'
            ]
        },
        7: {
            'titulo': 'Criatividade e Resolução de Problemas',
            'questoes': [
                'Gosto de encontrar soluções originais para problemas',
                'Tenho facilidade para pensar "fora da caixa"',
                'Prefiro atividades que envolvem criatividade e imaginação',
                'Tenho interesse em áreas específicas de conhecimento',
                'Gosto de questionar regras e convenções estabelecidas',
                'Tenho facilidade para ver padrões e conexões',
                'Prefiro trabalhar em projetos que me desafiam intelectualmente',
                'Tenho tendência a ser perfeccionista em trabalhos criativos',
                'Gosto de explorar diferentes perspectivas sobre um tema',
                'Tenho facilidade para gerar muitas ideias rapidamente'
            ]
        }
    }
    
    return render_template('questionario_neurolearn.html', questoes=questoes)

@app.route('/salvar-questionario', methods=['POST'])
def salvar_questionario():
    # Debug: verificar sessão
    print(f"DEBUG - Session data: {dict(session)}")
    print(f"DEBUG - Session keys: {list(session.keys())}")
    
    if 'usuario_id' not in session or session['tipo'] != 'aluno':
        print(f"DEBUG - Falha na autenticação: usuario_id={'usuario_id' in session}, tipo={session.get('tipo')}")
        return jsonify({'erro': 'Usuário não autenticado'}), 401
    
    aluno = Aluno.query.filter_by(usuario_id=session['usuario_id']).first()
    data = request.get_json()
    
    try:
        # Limpar respostas anteriores se existirem
        QuestionarioNeuroLearn.query.filter_by(aluno_id=aluno.id).delete()
        
        # Salvar novas respostas
        for questao_id, resposta in data['respostas'].items():
            # Determinar o bloco baseado no ID da questão
            bloco = ((int(questao_id) - 1) // 10) + 1
            
            questionario = QuestionarioNeuroLearn(
                aluno_id=aluno.id,
                bloco=bloco,
                questao=int(questao_id),
                resposta=int(resposta)
            )
            db.session.add(questionario)
        
        # Marcar questionário como completo
        aluno.questionario_completo = True
        db.session.commit()
        
        # Gerar perfil de aprendizagem com IA
        gerar_perfil_aprendizagem(aluno.id)
        
        return jsonify({'sucesso': 'Questionário salvo com sucesso'})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 500

def gerar_perfil_aprendizagem(aluno_id):
    """Gera o perfil de aprendizagem usando IA baseado no questionário NeuroLearn"""
    aluno = Aluno.query.get(aluno_id)
    respostas = QuestionarioNeuroLearn.query.filter_by(aluno_id=aluno_id).all()
    
    # Organizar respostas por bloco
    respostas_por_bloco = {}
    for i in range(1, 8):
        respostas_por_bloco[i] = []
    
    for resposta in respostas:
        respostas_por_bloco[resposta.bloco].append(resposta.resposta)
    
    # Criar um perfil básico primeiro (sem dependência da IA)
    perfil_data = gerar_perfil_basico(aluno, respostas_por_bloco)
    
    try:
        # Tentar usar a IA para enriquecer o perfil
        prompt = f"""
        Você é um especialista em Psicologia Educacional e análise de perfis de aprendizagem. Analise as respostas do questionário NeuroLearn e gere um perfil focado e objetivo.
        
        Dados do Aluno:
        - Nome: {aluno.usuario.nome}
        - Série: {aluno.serie_ano}
        - Idade: {aluno.idade} anos
        
        Respostas por Bloco (escala 1-5 onde 1=Discordo Totalmente, 5=Concordo Totalmente):
        Bloco 1 - Percepção Sensorial: {respostas_por_bloco[1]}
        Bloco 2 - Atenção e Foco: {respostas_por_bloco[2]}
        Bloco 3 - Comunicação: {respostas_por_bloco[3]}
        Bloco 4 - Organização: {respostas_por_bloco[4]}
        Bloco 5 - Aprendizagem: {respostas_por_bloco[5]}
        Bloco 6 - Interação Social: {respostas_por_bloco[6]}
        Bloco 7 - Criatividade: {respostas_por_bloco[7]}
        
        Responda em formato JSON válido com as chaves: perfil_geral, potenciais_expressivos, potenciais_cognitivos, indicios_neurodivergencias, recomendacoes_professores, reforco_motivacional, tipo_perfil
        """
        
        resultado_ia = consultar_ia(prompt)
        
        # Tentar parsear como JSON
        import json
        try:
            # Limpar markdown se presente
            resultado_limpo = resultado_ia.strip()
            if resultado_limpo.startswith('```json'):
                resultado_limpo = resultado_limpo[7:]
            if resultado_limpo.endswith('```'):
                resultado_limpo = resultado_limpo[:-3]
            resultado_limpo = resultado_limpo.strip()
            
            perfil_ia = json.loads(resultado_limpo)
            # Atualizar com dados da IA se válidos
            for key, value in perfil_ia.items():
                if value and len(str(value).strip()) > 0:
                    perfil_data[key] = value
        except Exception as e:
            print(f"Erro ao processar resposta da IA: {e}, usando perfil básico")
        
    except Exception as e:
        print(f"Erro ao consultar IA: {e}, usando perfil básico")
    
    # Garantir que todos os dados são strings válidas antes de salvar
    def garantir_string(valor):
        """Converte qualquer valor para string segura para o banco de dados"""
        if valor is None:
            return ''
        elif isinstance(valor, list):
            # Se for lista, converter para string separada por quebras de linha
            return '\n'.join(str(item) for item in valor)
        elif isinstance(valor, dict):
            # Se for dict, converter para formato legível
            return '\n'.join(f"{k}: {v}" for k, v in valor.items())
        else:
            return str(valor)
    
    # Salvar ou atualizar perfil (sempre)
    try:
        perfil_existente = PerfilAprendizagem.query.filter_by(aluno_id=aluno_id).first()
        if perfil_existente:
            perfil_existente.perfil_geral = garantir_string(perfil_data.get('perfil_geral', ''))
            perfil_existente.potenciais_expressivos = garantir_string(perfil_data.get('potenciais_expressivos', ''))
            perfil_existente.potenciais_cognitivos = garantir_string(perfil_data.get('potenciais_cognitivos', ''))
            perfil_existente.indicios_neurodivergencias = garantir_string(perfil_data.get('indicios_neurodivergencias', ''))
            perfil_existente.recomendacoes_professores = garantir_string(perfil_data.get('recomendacoes_professores', ''))
            perfil_existente.reforco_motivacional = garantir_string(perfil_data.get('reforco_motivacional', ''))
            perfil_existente.tipo_perfil = garantir_string(perfil_data.get('tipo_perfil', ''))
            perfil_existente.data_geracao = datetime.utcnow()
        else:
            perfil = PerfilAprendizagem(
                aluno_id=aluno_id,
                perfil_geral=garantir_string(perfil_data.get('perfil_geral', '')),
                potenciais_expressivos=garantir_string(perfil_data.get('potenciais_expressivos', '')),
                potenciais_cognitivos=garantir_string(perfil_data.get('potenciais_cognitivos', '')),
                indicios_neurodivergencias=garantir_string(perfil_data.get('indicios_neurodivergencias', '')),
                recomendacoes_professores=garantir_string(perfil_data.get('recomendacoes_professores', '')),
                reforco_motivacional=garantir_string(perfil_data.get('reforco_motivacional', '')),
                tipo_perfil=garantir_string(perfil_data.get('tipo_perfil', ''))
            )
            db.session.add(perfil)
        
        # Marcar perfil como gerado
        aluno.perfil_gerado = True
        db.session.commit()
        
    except Exception as e:
        print(f"Erro ao salvar perfil: {e}")
        db.session.rollback()

def analisar_consistencia_respostas(aluno_id):
    """Analisa a consistência das respostas para detectar possíveis mentiras"""
    respostas = QuestionarioNeuroLearn.query.filter_by(aluno_id=aluno_id).all()
    
    if len(respostas) < 60:  # Questionário incompleto
        return {
            'nivel_confianca': 0.5,
            'inconsistencias': ['Questionário incompleto'],
            'recomendacao': 'Completar questionário'
        }
    
    # Organizar respostas por bloco
    respostas_por_bloco = {}
    for i in range(1, 8):
        respostas_por_bloco[i] = []
    
    for resposta in respostas:
        respostas_por_bloco[resposta.bloco].append(resposta.resposta)
    
    # Calcular médias e variâncias
    medias = {}
    variancias = {}
    inconsistencias = []
    
    for bloco, valores in respostas_por_bloco.items():
        if valores:
            medias[bloco] = sum(valores) / len(valores)
            variancia = sum((x - medias[bloco]) ** 2 for x in valores) / len(valores)
            variancias[bloco] = variancia
    
    # Detectar inconsistências
    # 1. Variância muito alta (respostas muito dispersas)
    alta_variancia = [bloco for bloco, var in variancias.items() if var > 2.5]
    if alta_variancia:
        inconsistencias.append(f"Alta variabilidade nos blocos: {', '.join(map(str, alta_variancia))}")
    
    # 2. Padrões contraditórios entre blocos relacionados
    # Atenção vs Organização (devem ser correlacionados)
    if abs(medias.get(2, 3) - medias.get(4, 3)) > 2.0:
        inconsistencias.append("Contradição entre Atenção e Organização")
    
    # Comunicação vs Social (devem ser correlacionados)
    if abs(medias.get(3, 3) - medias.get(6, 3)) > 2.0:
        inconsistencias.append("Contradição entre Comunicação e Interação Social")
    
    # 3. Respostas extremas demais (muitos 1s ou 5s)
    todas_respostas = [r.resposta for r in respostas]
    extremas = sum(1 for r in todas_respostas if r in [1, 5])
    porcentagem_extremas = extremas / len(todas_respostas)
    
    if porcentagem_extremas > 0.7:
        inconsistencias.append("Excesso de respostas extremas (muito polarizadas)")
    
    # 4. Padrões de resposta repetitivos
    sequencias_iguais = 0
    for i in range(len(todas_respostas) - 4):
        if len(set(todas_respostas[i:i+5])) == 1:  # 5 respostas iguais em sequência
            sequencias_iguais += 1
    
    if sequencias_iguais > 3:
        inconsistencias.append("Padrões repetitivos detectados (possível falta de atenção)")
    
    # Calcular nível de confiança
    num_inconsistencias = len(inconsistencias)
    if num_inconsistencias == 0:
        nivel_confianca = 0.95
        recomendacao = "Perfil altamente confiável"
    elif num_inconsistencias == 1:
        nivel_confianca = 0.8
        recomendacao = "Perfil confiável com pequenas ressalvas"
    elif num_inconsistencias == 2:
        nivel_confianca = 0.6
        recomendacao = "Validar com observação comportamental"
    else:
        nivel_confianca = 0.3
        recomendacao = "ATENÇÃO: Reaplicar questionário com supervisão"
    
    return {
        'nivel_confianca': nivel_confianca,
        'inconsistencias': inconsistencias,
        'recomendacao': recomendacao,
        'num_inconsistencias': num_inconsistencias
    }

def gerar_analise_teste_aleatorio(aluno_id):
    """Gera dados de análise aleatórios para testar a funcionalidade da IA"""
    import random
    
    # Simular diferentes níveis de confiança para teste
    cenarios = [
        {
            'nivel_confianca': random.uniform(0.85, 0.95),
            'inconsistencias': [],
            'recomendacao': 'Perfil altamente confiável - Respostas consistentes e autênticas',
            'detalhes': 'Análise positiva: O padrão de respostas indica sinceridade e atenção ao questionário.'
        },
        {
            'nivel_confianca': random.uniform(0.75, 0.84), 
            'inconsistencias': ['Pequena variabilidade no bloco de Atenção'],
            'recomendacao': 'Perfil confiável com pequenas ressalvas',
            'detalhes': 'O aluno demonstrou consistência geral, com ligeiras flutuações em questões de atenção.'
        },
        {
            'nivel_confianca': random.uniform(0.55, 0.74),
            'inconsistencias': ['Contradição entre Comunicação e Interação Social', 'Algumas respostas extremas'],
            'recomendacao': 'Validar com observação comportamental',
            'detalhes': 'Detectadas algumas inconsistências que sugerem necessidade de validação adicional.'
        },
        {
            'nivel_confianca': random.uniform(0.25, 0.54),
            'inconsistencias': ['Padrões repetitivos detectados', 'Alta variabilidade', 'Excesso de respostas extremas'],
            'recomendacao': 'ATENÇÃO: Reaplicar questionário com supervisão',
            'detalhes': 'Múltiplas inconsistências detectadas. Recomenda-se nova aplicação sob supervisão.'
        }
    ]
    
    # Escolher cenário aleatório
    cenario = random.choice(cenarios)
    cenario['num_inconsistencias'] = len(cenario['inconsistencias'])
    
    return cenario


def gerar_perfil_basico(aluno, respostas_por_bloco):
    """Gera um perfil básico baseado nas respostas sem depender da IA"""
    
    # Calcular médias por bloco
    medias = {}
    for bloco, respostas in respostas_por_bloco.items():
        if respostas:
            medias[bloco] = sum(respostas) / len(respostas)
        else:
            medias[bloco] = 2.5
    
    # Identificar pontos fortes (média >= 4) e desafios (média <= 2)
    pontos_fortes = []
    desafios = []
    
    blocos_nomes = {
        1: 'Percepção Sensorial',
        2: 'Atenção e Foco', 
        3: 'Comunicação',
        4: 'Organização',
        5: 'Aprendizagem',
        6: 'Interação Social',
        7: 'Criatividade'
    }
    
    for bloco, media in medias.items():
        if media >= 4.0:
            pontos_fortes.append(blocos_nomes[bloco])
        elif media <= 2.0:
            desafios.append(blocos_nomes[bloco])
    
    # Definir tipo de perfil baseado nos pontos fortes
    if 'Criatividade' in pontos_fortes and 'Aprendizagem' in pontos_fortes:
        tipo_perfil = 'Pensador Criativo'
    elif 'Organização' in pontos_fortes and 'Atenção e Foco' in pontos_fortes:
        tipo_perfil = 'Organizador Metódico'
    elif 'Comunicação' in pontos_fortes and 'Interação Social' in pontos_fortes:
        tipo_perfil = 'Comunicador Social'
    elif 'Percepção Sensorial' in pontos_fortes:
        tipo_perfil = 'Observador Detalhista'
    else:
        tipo_perfil = 'Perfil Equilibrado'
    
    return {
        'perfil_geral': f"O aluno {aluno.usuario.nome} apresenta um perfil de aprendizagem com características marcantes em {', '.join(pontos_fortes) if pontos_fortes else 'múltiplas áreas'}. Seus pontos fortes incluem {', '.join(pontos_fortes) if pontos_fortes else 'habilidades diversificadas'}, o que indica um potencial significativo para o desenvolvimento acadêmico.",
        'potenciais_expressivos': f"O aluno demonstra facilidade para se expressar através de {', '.join(pontos_fortes[:2]) if len(pontos_fortes) >= 2 else 'diferentes modalidades'}. Recomenda-se oferecer oportunidades variadas de expressão para maximizar seu potencial comunicativo.",
        'potenciais_cognitivos': f"As áreas de maior destaque cognitivo são {', '.join(pontos_fortes) if pontos_fortes else 'equilibradas entre diferentes domínios'}. O aluno apresenta um perfil que favorece aprendizagens que envolvam essas competências.",
        'indicios_neurodivergencias': "As respostas indicam um perfil neurotípico com características individuais de aprendizagem que devem ser consideradas no planejamento pedagógico.",
        'recomendacoes_professores': f"1. Valorizar os pontos fortes em {', '.join(pontos_fortes[:3]) if pontos_fortes else 'múltiplas áreas'}. 2. Oferecer atividades diversificadas. 3. Respeitar o ritmo individual de aprendizagem. 4. Promover autoconfiança através de feedbacks positivos.",
        'reforco_motivacional': f"Você tem talentos únicos e especiais! Continue explorando suas habilidades em {', '.join(pontos_fortes[:2]) if len(pontos_fortes) >= 2 else 'diferentes áreas'} e sempre acredite no seu potencial!",
        'tipo_perfil': tipo_perfil
    }

@app.route('/perfil-aprendizagem')
def perfil_aprendizagem():
    # Redirecionar alunos para dashboard - perfil só acessível por professores
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    if session['tipo'] == 'aluno':
        return redirect(url_for('dashboard_aluno'))
    elif session['tipo'] == 'professor':
        return redirect(url_for('painel_professor'))
    else:
        return redirect(url_for('login'))

@app.route('/painel-professor')
def painel_professor():
    if 'usuario_id' not in session or session['tipo'] != 'professor':
        return redirect(url_for('login'))
    
    # Filtros
    tipo_filtro = request.args.get('tipo_perfil', '')
    
    # Buscar alunos com seus perfis
    query = db.session.query(Aluno, PerfilAprendizagem).join(
        PerfilAprendizagem, Aluno.id == PerfilAprendizagem.aluno_id, isouter=True
    ).join(Usuario, Aluno.usuario_id == Usuario.id)
    
    if tipo_filtro:
        query = query.filter(PerfilAprendizagem.tipo_perfil.like(f'%{tipo_filtro}%'))
    
    alunos_perfis = query.all()
    
    # Buscar tipos de perfil únicos para o filtro
    tipos_perfil = db.session.query(PerfilAprendizagem.tipo_perfil).distinct().all()
    tipos_perfil = [t[0] for t in tipos_perfil if t[0]]
    
    return render_template('painel_professor.html', 
                         alunos_perfis=alunos_perfis, 
                         tipos_perfil=tipos_perfil,
                         tipo_filtro=tipo_filtro)

@app.route('/visualizar-perfil/<int:aluno_id>')
def visualizar_perfil(aluno_id):
    if 'usuario_id' not in session or session['tipo'] != 'professor':
        return redirect(url_for('login'))
    
    aluno = Aluno.query.get_or_404(aluno_id)
    perfil = PerfilAprendizagem.query.filter_by(aluno_id=aluno_id).first()
    
    # Aplicar filtro de formatação para melhorar a apresentação
    perfil_formatado = None
    if perfil:
        filtro = FiltroRelatorioNeurodivergencia()
        
        # Criar estrutura de dados para o filtro
        dados_perfil = {
            'perfil_geral': perfil.perfil_geral or '',
            'potenciais_expressivos': perfil.potenciais_expressivos or '',
            'potenciais_cognitivos': perfil.potenciais_cognitivos or '',
            'indicios_neurodivergencias': perfil.indicios_neurodivergencias or '',
            'recomendacoes_professores': perfil.recomendacoes_professores or '',
            'reforco_motivacional': perfil.reforco_motivacional or '',
            'tipo_perfil': perfil.tipo_perfil or ''
        }
        
        # Aplicar formatação específica para as recomendações
        perfil_formatado = {
            'perfil_geral': filtro._formatar_texto(dados_perfil['perfil_geral']),
            'potenciais_expressivos': filtro._formatar_texto(dados_perfil['potenciais_expressivos']),
            'potenciais_cognitivos': filtro._formatar_texto(dados_perfil['potenciais_cognitivos']),
            'indicios_neurodivergencias': filtro._formatar_texto(dados_perfil['indicios_neurodivergencias']),
            'recomendacoes_professores': filtro._formatar_lista_estrategias(dados_perfil['recomendacoes_professores']),
            'reforco_motivacional': filtro._formatar_texto(dados_perfil['reforco_motivacional']),
            'tipo_perfil': filtro._obter_tipo_perfil_formatado(dados_perfil['tipo_perfil'])
        }
    
    return render_template('visualizar_perfil.html', aluno=aluno, perfil=perfil, perfil_formatado=perfil_formatado)

@app.route('/perfil-aluno/<int:aluno_id>')
def perfil_aluno_simples(aluno_id):
    """Perfil simplificado do aluno para o professor"""
    if 'usuario_id' not in session or session['tipo'] != 'professor':
        return redirect(url_for('login'))
    
    aluno = Aluno.query.get_or_404(aluno_id)
    perfil = PerfilAprendizagem.query.filter_by(aluno_id=aluno_id).first()
    
    return render_template('perfil_aluno_simples.html', aluno=aluno, perfil=perfil)

@app.route('/ver-respostas-questionario/<int:aluno_id>')
def ver_respostas_questionario(aluno_id):
    """Visualizar todas as respostas do questionário do aluno"""
    if 'usuario_id' not in session or session['tipo'] != 'professor':
        return redirect(url_for('login'))
    
    aluno = Aluno.query.get_or_404(aluno_id)
    respostas = QuestionarioNeuroLearn.query.filter_by(aluno_id=aluno_id).all()
    
    # Organizar respostas por bloco
    respostas_por_bloco = {}
    respostas_dict = {}
    estatisticas = {}
    
    for i in range(1, 8):
        respostas_por_bloco[i] = []
    
    for resposta in respostas:
        respostas_por_bloco[resposta.bloco].append(resposta)
        respostas_dict[resposta.questao] = resposta.resposta
        
        # Contar estatísticas
        if resposta.resposta in estatisticas:
            estatisticas[resposta.resposta] += 1
        else:
            estatisticas[resposta.resposta] = 1
    
    # Definir blocos e questões (mesmo do questionário)
    blocos_info = {
        1: {
            'titulo': 'Percepção e Processamento Sensorial',
            'questoes': [
                'Me incomodo facilmente com ruídos altos ou sons repetitivos durante as aulas',
                'Prefiro ambientes de estudo com pouca luminosidade',
                'Sinto desconforto com certas texturas de uniformes ou materiais escolares',
                'Preciso de mais tempo para processar informações visuais complexas no quadro',
                'Tenho facilidade para perceber detalhes que outros colegas não notam',
                'Me sinto sobrecarregado em ambientes escolares com muitos estímulos',
                'Prefiro atividades que envolvem um sentido por vez (só visual ou só auditivo)',
                'Tenho dificuldade para filtrar ruídos de fundo durante explicações',
                'Sou sensível a cheiros fortes no ambiente escolar',
                'Preciso de pausas frequentes durante atividades de estudo intensas'
            ]
        },
        2: {
            'titulo': 'Atenção e Foco',
            'questoes': [
                'Tenho dificuldade para manter atenção em aulas expositivas longas',
                'Me distraio facilmente com pensamentos ou estímulos externos durante os estudos',
                'Consigo me concentrar intensamente quando uma matéria me interessa muito',
                'Tenho dificuldade para alternar entre diferentes disciplinas ou atividades',
                'Preciso de lembretes constantes para completar tarefas e trabalhos',
                'Me perco facilmente em devaneios durante as aulas',
                'Tenho dificuldade para prestar atenção em instruções faladas pelos professores',
                'Consigo trabalhar melhor em ambientes silenciosos, como biblioteca',
                'Tenho tendência a procrastinar estudos e trabalhos importantes',
                'Me sinto mais produtivo para estudar em determinados horários do dia'
            ]
        },
        3: {
            'titulo': 'Comunicação e Expressão',
            'questoes': [
                'Prefiro me comunicar por escrito ao invés de participar oralmente',
                'Tenho dificuldade para expressar meus pensamentos verbalmente em sala',
                'Uso gestos e expressões corporais para me comunicar melhor',
                'Tenho facilidade para entender metáforas e linguagem figurada nas matérias',
                'Prefiro conversas individuais com professores ao invés de participar em grupos',
                'Tenho dificuldade para iniciar conversas com colegas desconhecidos',
                'Consigo me expressar melhor através de arte, desenhos ou projetos criativos',
                'Tenho tendência a ser muito direto ao falar, sem "rodeios"',
                'Gosto de explicar coisas com detalhes e exemplos práticos',
                'Tenho dificuldade para entender ironia ou sarcasmo de colegas'
            ]
        },
        4: {
            'titulo': 'Organização e Planejamento',
            'questoes': [
                'Tenho dificuldade para organizar meus materiais escolares e espaços de estudo',
                'Prefiro seguir rotinas de estudo e horários estabelecidos',
                'Tenho facilidade para criar sistemas de organização para minhas matérias',
                'Me sinto ansioso quando minha rotina escolar é alterada',
                'Tenho dificuldade para estimar tempo necessário para fazer trabalhos',
                'Preciso de listas e lembretes para me organizar nos estudos',
                'Gosto de planejar projetos e apresentações com antecedência',
                'Tenho dificuldade para priorizar tarefas mais importantes',
                'Prefiro ambientes de estudo organizados e limpos',
                'Tenho facilidade para seguir instruções passo a passo de trabalhos'
            ]
        },
        5: {
            'titulo': 'Aprendizagem e Memória',
            'questoes': [
                'Aprendo melhor através de exemplos visuais, gráficos e diagramas',
                'Tenho facilidade para memorizar informações sobre assuntos que me interessam',
                'Preciso repetir informações várias vezes para conseguir memorizar',
                'Aprendo melhor fazendo experimentos ao invés de apenas ouvindo teoria',
                'Tenho dificuldade para lembrar sequências ou ordens em matérias como História',
                'Consigo fazer conexões entre conceitos de diferentes matérias',
                'Prefiro aprender no meu próprio ritmo ao invés do ritmo da turma',
                'Tenho facilidade para lembrar detalhes específicos de aulas passadas',
                'Aprendo melhor quando posso relacionar com experiências pessoais',
                'Tenho dificuldade com matérias que exigem memorização mecânica'
            ]
        },
        6: {
            'titulo': 'Interação Social e Emocional',
            'questoes': [
                'Prefiro fazer trabalhos individuais ao invés de trabalhos em grupo',
                'Tenho dificuldade para interpretar expressões faciais de colegas e professores',
                'Me sinto confortável em situações sociais familiares na escola',
                'Tenho poucos amigos próximos, mas relacionamentos profundos',
                'Tenho dificuldade para entender "regras sociais" não escritas da escola',
                'Me sinto ansioso em situações sociais novas, como apresentações',
                'Gosto de ajudar outros colegas com dificuldades nos estudos',
                'Tenho facilidade para perceber quando um colega está triste ou preocupado',
                'Prefiro ouvir ao invés de falar em discussões de grupo',
                'Me sinto mais confortável com pessoas que compartilham meus interesses'
            ]
        },
        7: {
            'titulo': 'Criatividade e Resolução de Problemas',
            'questoes': [
                'Gosto de encontrar soluções originais para problemas de matemática e ciências',
                'Tenho facilidade para pensar "fora da caixa" em projetos escolares',
                'Prefiro atividades que envolvem criatividade e imaginação',
                'Tenho interesse muito específico e aprofundado em certas áreas de conhecimento',
                'Gosto de questionar regras e métodos convencionais de ensino',
                'Tenho facilidade para ver padrões e conexões em diferentes matérias',
                'Prefiro trabalhar em projetos que me desafiam intelectualmente',
                'Tenho tendência a ser perfeccionista em trabalhos criativos',
                'Gosto de explorar diferentes perspectivas sobre um mesmo tema',
                'Tenho facilidade para gerar muitas ideias rapidamente para projetos'
            ]
        }
    }
    
    return render_template('ver_respostas_questionario.html', 
                         aluno=aluno, 
                         respostas=respostas,
                         respostas_por_bloco=respostas_por_bloco,
                         respostas_dict=respostas_dict,
                         estatisticas=estatisticas,
                         blocos_info=blocos_info)

@app.route('/analisar-consistencia/<int:aluno_id>')
def analisar_consistencia(aluno_id):
    """Endpoint para análise de consistência das respostas - SOMENTE PROFESSOR"""
    if 'usuario_id' not in session or session['tipo'] != 'professor':
        return jsonify({'erro': 'Acesso negado - Apenas professores'}), 403
    
    aluno = Aluno.query.get_or_404(aluno_id)
    
    # Para teste, usar análise aleatória que simula diferentes cenários
    # Em produção, usar: analise = analisar_consistencia_respostas(aluno_id)
    analise = gerar_analise_teste_aleatorio(aluno_id)
    
    return jsonify(analise)

@app.route('/relatorio-detalhado/<int:aluno_id>')
def relatorio_detalhado(aluno_id):
    """Relatório detalhado e formatado de neurodivergência - SOMENTE PROFESSOR"""
    if 'usuario_id' not in session or session['tipo'] != 'professor':
        return redirect(url_for('login'))
    
    aluno = Aluno.query.get_or_404(aluno_id)
    perfil = PerfilAprendizagem.query.filter_by(aluno_id=aluno_id).first()
    
    if not perfil:
        return jsonify({'erro': 'Perfil não encontrado'}), 404
    
    # Criar estrutura JSON do perfil
    perfil_json = {
        'perfil_geral': perfil.perfil_geral,
        'potenciais_expressivos': perfil.potenciais_expressivos,
        'potenciais_cognitivos': perfil.potenciais_cognitivos,
        'indicios_neurodivergencias': perfil.indicios_neurodivergencias,
        'recomendacoes_professores': perfil.recomendacoes_professores,
        'reforco_motivacional': perfil.reforco_motivacional,
        'tipo_perfil': perfil.tipo_perfil
    }
    
    # Aplicar filtro para melhorar a apresentação
    filtro = FiltroRelatorioNeurodivergencia()
    relatorio_formatado = filtro.formatar_relatorio_detalhado(
        perfil_json, 
        aluno.usuario.nome, 
        aluno.serie_ano
    )
    
    return render_template('relatorio_detalhado.html', 
                         aluno=aluno,
                         perfil=perfil,
                         relatorio_formatado=relatorio_formatado)

# ===== NOVAS FUNCIONALIDADES =====

# 1. TESTE DE PERFIL COGNITIVO
@app.route('/teste-perfil-cognitivo')
def teste_perfil_cognitivo():
    if 'usuario_id' not in session or session['tipo'] != 'aluno':
        return redirect(url_for('login'))
    
    aluno = Aluno.query.filter_by(usuario_id=session['usuario_id']).first()
    return render_template('teste_perfil_cognitivo.html', aluno=aluno)

@app.route('/executar-teste-cognitivo', methods=['POST'])
def executar_teste_cognitivo():
    if 'usuario_id' not in session or session['tipo'] != 'aluno':
        return jsonify({'erro': 'Usuário não autenticado'}), 401
    
    aluno = Aluno.query.filter_by(usuario_id=session['usuario_id']).first()
    data = request.get_json()
    
    # Salvar resultado do teste
    teste = TestePerfiliCognitivo(
        aluno_id=aluno.id,
        tipo_teste=data['tipo_teste'],
        pontuacao=data['pontuacao'],
        tempo_resposta=data['tempo_resposta'],
        resultados_detalhados=json.dumps(data['detalhes'])
    )
    
    db.session.add(teste)
    db.session.commit()
    
    return jsonify({'sucesso': 'Teste salvo com sucesso', 'teste_id': teste.id})

# 2. TRILHAS PERSONALIZADAS DE APRENDIZADO
@app.route('/trilhas-aprendizado')
def trilhas_aprendizado():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    if session['tipo'] == 'aluno':
        aluno = Aluno.query.filter_by(usuario_id=session['usuario_id']).first()
        perfil = PerfilAprendizagem.query.filter_by(aluno_id=aluno.id).first()
        
        # Buscar trilhas adequadas ao perfil do aluno
        trilhas = TrilhaAprendizado.query.filter(
            TrilhaAprendizado.ativo == True
        ).all()
        
        # Se tem perfil, filtrar por adequação
        if perfil and perfil.tipo_perfil:
            trilhas_recomendadas = TrilhaAprendizado.query.filter(
                TrilhaAprendizado.perfil_alvo.like(f'%{perfil.tipo_perfil}%'),
                TrilhaAprendizado.ativo == True
            ).all()
        else:
            trilhas_recomendadas = []
        
        return render_template('trilhas_aluno.html', 
                             trilhas=trilhas, 
                             trilhas_recomendadas=trilhas_recomendadas,
                             aluno=aluno)
    else:
        # Professor pode gerenciar trilhas
        trilhas = TrilhaAprendizado.query.all()
        return render_template('trilhas_professor.html', trilhas=trilhas)

@app.route('/criar-trilha', methods=['GET', 'POST'])
def criar_trilha():
    if 'usuario_id' not in session or session['tipo'] != 'professor':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        trilha = TrilhaAprendizado(
            nome=request.form['nome'],
            descricao=request.form['descricao'],
            tipo_conteudo=request.form['tipo_conteudo'],
            nivel_dificuldade=request.form['nivel_dificuldade'],
            area_conhecimento=request.form['area_conhecimento'],
            perfil_alvo=request.form.get('perfil_alvo', ''),
            duracao_estimada=int(request.form.get('duracao_estimada', 0)),
            url_conteudo=request.form.get('url_conteudo', ''),
            arquivo_conteudo=request.form.get('arquivo_conteudo', '')
        )
        
        db.session.add(trilha)
        db.session.commit()
        
        return redirect(url_for('trilhas_aprendizado'))
    
    return render_template('criar_trilha.html')

@app.route('/iniciar-trilha/<int:trilha_id>')
def iniciar_trilha(trilha_id):
    if 'usuario_id' not in session or session['tipo'] != 'aluno':
        return redirect(url_for('login'))
    
    aluno = Aluno.query.filter_by(usuario_id=session['usuario_id']).first()
    trilha = TrilhaAprendizado.query.get_or_404(trilha_id)
    
    # Verificar se já existe progresso
    progresso = ProgressoTrilha.query.filter_by(
        aluno_id=aluno.id, trilha_id=trilha_id
    ).first()
    
    if not progresso:
        progresso = ProgressoTrilha(
            aluno_id=aluno.id,
            trilha_id=trilha_id,
            progresso=0.0
        )
        db.session.add(progresso)
        db.session.commit()
    
    # Registrar monitoramento
    registrar_monitoramento(aluno.id, 'inicio_trilha', f'trilha_{trilha_id}')
    
    return render_template('executar_trilha.html', trilha=trilha, progresso=progresso)

@app.route('/atualizar-progresso-trilha', methods=['POST'])
def atualizar_progresso_trilha():
    if 'usuario_id' not in session or session['tipo'] != 'aluno':
        return jsonify({'erro': 'Usuário não autenticado'}), 401
    
    aluno = Aluno.query.filter_by(usuario_id=session['usuario_id']).first()
    data = request.get_json()
    
    progresso = ProgressoTrilha.query.filter_by(
        aluno_id=aluno.id, trilha_id=data['trilha_id']
    ).first()
    
    if progresso:
        progresso.progresso = data['progresso']
        progresso.tempo_gasto += data.get('tempo_adicional', 0)
        
        if data['progresso'] >= 100.0:
            progresso.data_conclusao = datetime.utcnow()
        
        db.session.commit()
        
        # Registrar monitoramento
        registrar_monitoramento(aluno.id, 'progresso_trilha', 
                               f"trilha_{data['trilha_id']}", 
                               tempo_gasto=data.get('tempo_adicional', 0))
    
    return jsonify({'sucesso': 'Progresso atualizado'})

# 3. CRONOGRAMA DE ESTUDOS ADAPTADO
@app.route('/cronograma-estudos')
def cronograma_estudos():
    if 'usuario_id' not in session or session['tipo'] != 'aluno':
        return redirect(url_for('login'))
    
    aluno = Aluno.query.filter_by(usuario_id=session['usuario_id']).first()
    cronogramas = CronogramaEstudo.query.filter_by(
        aluno_id=aluno.id, ativo=True
    ).all()
    
    return render_template('cronograma_estudos.html', cronogramas=cronogramas, aluno=aluno)

@app.route('/criar-cronograma', methods=['GET', 'POST'])
def criar_cronograma():
    if 'usuario_id' not in session or session['tipo'] != 'aluno':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        aluno = Aluno.query.filter_by(usuario_id=session['usuario_id']).first()
        
        cronograma = CronogramaEstudo(
            aluno_id=aluno.id,
            data_inicio=datetime.strptime(request.form['data_inicio'], '%Y-%m-%d').date(),
            data_fim=datetime.strptime(request.form['data_fim'], '%Y-%m-%d').date(),
            objetivo=request.form['objetivo'],
            horas_por_dia=float(request.form['horas_por_dia']),
            dias_semana=request.form['dias_semana'],
            horario_preferido=request.form['horario_preferido'],
            tempo_pausa=int(request.form.get('tempo_pausa', 10)),
            tempo_sessao=int(request.form.get('tempo_sessao', 25)),
            lembretes_ativos=bool(request.form.get('lembretes_ativos'))
        )
        
        db.session.add(cronograma)
        db.session.commit()
        
        # Gerar sessões de estudo
        gerar_sessoes_estudo(cronograma.id)
        
        return redirect(url_for('cronograma_estudos'))
    
    return render_template('criar_cronograma.html')

def gerar_sessoes_estudo(cronograma_id):
    """Gera sessões de estudo baseadas no cronograma"""
    cronograma = CronogramaEstudo.query.get(cronograma_id)
    if not cronograma:
        return
    
    from datetime import timedelta
    
    data_atual = cronograma.data_inicio
    dias_semana_lista = [int(d) for d in cronograma.dias_semana.split(',')]
    
    while data_atual <= cronograma.data_fim:
        # Verificar se é um dia de estudo (1=segunda, 7=domingo)
        dia_semana = data_atual.weekday() + 1
        
        if dia_semana in dias_semana_lista:
            # Calcular número de sessões por dia
            num_sessoes = int((cronograma.horas_por_dia * 60) / cronograma.tempo_sessao)
            
            for i in range(num_sessoes):
                # Definir horário baseado na preferência
                if cronograma.horario_preferido == 'manha':
                    hora_inicio = 8 + (i * ((cronograma.tempo_sessao + cronograma.tempo_pausa) / 60))
                elif cronograma.horario_preferido == 'tarde':
                    hora_inicio = 14 + (i * ((cronograma.tempo_sessao + cronograma.tempo_pausa) / 60))
                else:  # noite
                    hora_inicio = 19 + (i * ((cronograma.tempo_sessao + cronograma.tempo_pausa) / 60))
                
                hora = int(hora_inicio)
                minuto = int((hora_inicio - hora) * 60)
                
                data_sessao = datetime.combine(data_atual, datetime.min.time().replace(hour=hora, minute=minuto))
                
                sessao = SessaoEstudo(
                    cronograma_id=cronograma_id,
                    data_sessao=data_sessao,
                    duracao_planejada=cronograma.tempo_sessao
                )
                
                db.session.add(sessao)
        
        data_atual += timedelta(days=1)
    
    db.session.commit()

@app.route('/sessoes-hoje')
def sessoes_hoje():
    if 'usuario_id' not in session or session['tipo'] != 'aluno':
        return jsonify({'erro': 'Usuário não autenticado'}), 401
    
    aluno = Aluno.query.filter_by(usuario_id=session['usuario_id']).first()
    hoje = datetime.now().date()
    
    sessoes = db.session.query(SessaoEstudo).join(CronogramaEstudo).filter(
        CronogramaEstudo.aluno_id == aluno.id,
        db.func.date(SessaoEstudo.data_sessao) == hoje
    ).all()
    
    sessoes_data = []
    for sessao in sessoes:
        sessoes_data.append({
            'id': sessao.id,
            'horario': sessao.data_sessao.strftime('%H:%M'),
            'duracao': sessao.duracao_planejada,
            'realizada': sessao.realizada,
            'objetivo': sessao.cronograma.objetivo
        })
    
    return jsonify({'sessoes': sessoes_data})

@app.route('/marcar-sessao-realizada/<int:sessao_id>', methods=['POST'])
def marcar_sessao_realizada(sessao_id):
    if 'usuario_id' not in session or session['tipo'] != 'aluno':
        return jsonify({'erro': 'Usuário não autenticado'}), 401
    
    sessao = SessaoEstudo.query.get_or_404(sessao_id)
    data = request.get_json()
    
    sessao.realizada = True
    sessao.duracao_real = data.get('duracao_real', sessao.duracao_planejada)
    sessao.feedback = data.get('feedback', '')
    sessao.nivel_concentracao = data.get('nivel_concentracao')
    
    db.session.commit()
    
    # Registrar monitoramento
    aluno = Aluno.query.join(CronogramaEstudo).filter(
        CronogramaEstudo.id == sessao.cronograma_id
    ).first()
    
    registrar_monitoramento(aluno.id, 'sessao_estudo', 'cronograma',
                          tempo_gasto=sessao.duracao_real * 60)
    
    return jsonify({'sucesso': 'Sessão marcada como realizada'})

# 4. PAINEL DE PROGRESSO
@app.route('/painel-progresso')
def painel_progresso():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    if session['tipo'] == 'aluno':
        aluno = Aluno.query.filter_by(usuario_id=session['usuario_id']).first()
        return render_template('painel_progresso_aluno.html', aluno=aluno)
    elif session['tipo'] == 'professor':
        # Dashboard para professores verem todos os alunos
        alunos = Aluno.query.all()
        return render_template('painel_progresso_professor.html', alunos=alunos)
    else:
        return redirect(url_for('login'))

@app.route('/dados-progresso-aluno/<int:aluno_id>')
def dados_progresso_aluno(aluno_id):
    if 'usuario_id' not in session:
        return jsonify({'erro': 'Usuário não autenticado'}), 401
    
    # Verificar permissão
    if session['tipo'] == 'aluno':
        aluno_session = Aluno.query.filter_by(usuario_id=session['usuario_id']).first()
        if aluno_session.id != aluno_id:
            return jsonify({'erro': 'Acesso negado'}), 403
    elif session['tipo'] != 'professor':
        return jsonify({'erro': 'Acesso negado'}), 403
    
    aluno = Aluno.query.get_or_404(aluno_id)
    
    # Estatísticas gerais
    total_trilhas = ProgressoTrilha.query.filter_by(aluno_id=aluno_id).count()
    trilhas_concluidas = ProgressoTrilha.query.filter_by(
        aluno_id=aluno_id
    ).filter(ProgressoTrilha.progresso >= 100.0).count()
    
    # Progresso médio
    progresso_medio = db.session.query(
        db.func.avg(ProgressoTrilha.progresso)
    ).filter_by(aluno_id=aluno_id).scalar() or 0
    
    # Tempo total de estudo
    tempo_total = db.session.query(
        db.func.sum(ProgressoTrilha.tempo_gasto)
    ).filter_by(aluno_id=aluno_id).scalar() or 0
    
    # Sessões de estudo realizadas
    sessoes_realizadas = db.session.query(SessaoEstudo).join(CronogramaEstudo).filter(
        CronogramaEstudo.aluno_id == aluno_id,
        SessaoEstudo.realizada == True
    ).count()
    
    # Atividades do monitoramento (últimos 7 dias)
    from datetime import timedelta
    data_limite = datetime.now() - timedelta(days=7)
    
    atividades_recentes = MonitoramentoComportamento.query.filter(
        MonitoramentoComportamento.aluno_id == aluno_id,
        MonitoramentoComportamento.data_acao >= data_limite
    ).count()
    
    return jsonify({
        'total_trilhas': total_trilhas,
        'trilhas_concluidas': trilhas_concluidas,
        'progresso_medio': round(progresso_medio, 1),
        'tempo_total_minutos': tempo_total,
        'sessoes_realizadas': sessoes_realizadas,
        'atividades_recentes': atividades_recentes
    })

# 5. ASSISTENTE VIRTUAL
@app.route('/assistente-virtual')
def assistente_virtual():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    return render_template('assistente_virtual.html')

@app.route('/conversar-assistente', methods=['POST'])
def conversar_assistente():
    if 'usuario_id' not in session:
        return jsonify({'erro': 'Usuário não autenticado'}), 401
    
    data = request.get_json()
    mensagem = data['mensagem']
    contexto = data.get('contexto', 'geral')
    
    # Construir prompt contextualizado
    if session['tipo'] == 'aluno':
        aluno = Aluno.query.filter_by(usuario_id=session['usuario_id']).first()
        perfil = PerfilAprendizagem.query.filter_by(aluno_id=aluno.id).first()
        
        prompt = f"""
        Você é um assistente virtual educacional especializado em auxiliar estudantes.
        
        Contexto do estudante:
        - Nome: {aluno.usuario.nome}
        - Série: {aluno.serie_ano}
        - Tipo de perfil: {perfil.tipo_perfil if perfil else 'Não definido'}
        
        Contexto da conversa: {contexto}
        
        Pergunta do estudante: {mensagem}
        
        Responda de forma acolhedora, educativa e adequada à idade. Use linguagem simples e seja motivacional.
        """
    else:
        prompt = f"""
        Você é um assistente virtual educacional especializado em auxiliar professores.
        
        Contexto da conversa: {contexto}
        Pergunta do professor: {mensagem}
        
        Responda com informações pedagógicas úteis, estratégias de ensino e sugestões práticas.
        """
    
    try:
        resposta = consultar_ia(prompt)
        
        # Salvar interação
        interacao = InteracaoAssistente(
            usuario_id=session['usuario_id'],
            mensagem_usuario=mensagem,
            resposta_assistente=resposta,
            contexto=contexto
        )
        
        db.session.add(interacao)
        db.session.commit()
        
        return jsonify({'resposta': resposta, 'interacao_id': interacao.id})
    
    except Exception as e:
        return jsonify({'erro': f'Erro no assistente: {str(e)}'}), 500

@app.route('/avaliar-resposta-assistente', methods=['POST'])
def avaliar_resposta_assistente():
    if 'usuario_id' not in session:
        return jsonify({'erro': 'Usuário não autenticado'}), 401
    
    data = request.get_json()
    interacao_id = data['interacao_id']
    satisfacao = data['satisfacao']  # 1-5
    resolveu = data.get('resolveu_duvida', None)
    
    interacao = InteracaoAssistente.query.get_or_404(interacao_id)
    interacao.satisfacao_resposta = satisfacao
    interacao.resolveu_duvida = resolveu
    
    db.session.commit()
    
    return jsonify({'sucesso': 'Avaliação salva'})

# 6. CONFIGURAÇÕES DE ACESSIBILIDADE
@app.route('/configuracoes-acessibilidade')
def configuracoes_acessibilidade():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    config = ConfiguracaoAcessibilidade.query.filter_by(
        usuario_id=session['usuario_id']
    ).first()
    
    if not config:
        config = ConfiguracaoAcessibilidade(usuario_id=session['usuario_id'])
        db.session.add(config)
        db.session.commit()
    
    return render_template('configuracoes_acessibilidade.html', config=config)

@app.route('/salvar-configuracoes-acessibilidade', methods=['POST'])
def salvar_configuracoes_acessibilidade():
    if 'usuario_id' not in session:
        return jsonify({'erro': 'Usuário não autenticado'}), 401
    
    config = ConfiguracaoAcessibilidade.query.filter_by(
        usuario_id=session['usuario_id']
    ).first()
    
    if not config:
        config = ConfiguracaoAcessibilidade(usuario_id=session['usuario_id'])
        db.session.add(config)
    
    data = request.get_json()
    
    config.modo_escuro = data.get('modo_escuro', False)
    config.alto_contraste = data.get('alto_contraste', False)
    config.tamanho_fonte = data.get('tamanho_fonte', 'normal')
    config.audio_leitura = data.get('audio_leitura', False)
    config.velocidade_audio = data.get('velocidade_audio', 1.0)
    config.navegacao_simplificada = data.get('navegacao_simplificada', False)
    config.reducao_animacoes = data.get('reducao_animacoes', False)
    config.notificacoes_visuais = data.get('notificacoes_visuais', True)
    config.notificacoes_sonoras = data.get('notificacoes_sonoras', True)
    config.cores_personalizadas = json.dumps(data.get('cores_personalizadas', {}))
    
    db.session.commit()
    
    return jsonify({'sucesso': 'Configurações salvas'})

@app.route('/obter-configuracoes-acessibilidade')
def obter_configuracoes_acessibilidade():
    if 'usuario_id' not in session:
        return jsonify({'erro': 'Usuário não autenticado'}), 401
    
    config = ConfiguracaoAcessibilidade.query.filter_by(
        usuario_id=session['usuario_id']
    ).first()
    
    if not config:
        return jsonify({})
    
    return jsonify({
        'modo_escuro': config.modo_escuro,
        'alto_contraste': config.alto_contraste,
        'tamanho_fonte': config.tamanho_fonte,
        'audio_leitura': config.audio_leitura,
        'velocidade_audio': config.velocidade_audio,
        'navegacao_simplificada': config.navegacao_simplificada,
        'reducao_animacoes': config.reducao_animacoes,
        'notificacoes_visuais': config.notificacoes_visuais,
        'notificacoes_sonoras': config.notificacoes_sonoras,
        'cores_personalizadas': json.loads(config.cores_personalizadas or '{}')
    })

# 7. BIBLIOTECA DE CONTEÚDO
@app.route('/biblioteca')
def biblioteca():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    # Filtros
    tipo = request.args.get('tipo', '')
    categoria = request.args.get('categoria', '')
    nivel = request.args.get('nivel_ensino', '')
    
    query = BibliotecaConteudo.query.filter_by(ativo=True)
    
    if tipo:
        query = query.filter(BibliotecaConteudo.tipo == tipo)
    if categoria:
        query = query.filter(BibliotecaConteudo.categoria == categoria)
    if nivel:
        query = query.filter(BibliotecaConteudo.nivel_ensino == nivel)
    
    conteudos = query.all()
    
    # Buscar categorias e tipos únicos para filtros
    categorias = db.session.query(BibliotecaConteudo.categoria).distinct().all()
    tipos = db.session.query(BibliotecaConteudo.tipo).distinct().all()
    niveis = db.session.query(BibliotecaConteudo.nivel_ensino).distinct().all()
    
    return render_template('biblioteca.html', 
                         conteudos=conteudos,
                         categorias=[c[0] for c in categorias if c[0]],
                         tipos=[t[0] for t in tipos if t[0]],
                         niveis=[n[0] for n in niveis if n[0]],
                         filtros={'tipo': tipo, 'categoria': categoria, 'nivel': nivel})

@app.route('/adicionar-conteudo-biblioteca', methods=['GET', 'POST'])
def adicionar_conteudo_biblioteca():
    if 'usuario_id' not in session or session['tipo'] != 'professor':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        conteudo = BibliotecaConteudo(
            titulo=request.form['titulo'],
            descricao=request.form['descricao'],
            tipo=request.form['tipo'],
            categoria=request.form['categoria'],
            nivel_ensino=request.form.get('nivel_ensino', ''),
            url_conteudo=request.form.get('url_conteudo', ''),
            arquivo_conteudo=request.form.get('arquivo_conteudo', ''),
            tem_legenda=bool(request.form.get('tem_legenda')),
            tem_libras=bool(request.form.get('tem_libras')),
            tem_transcricao=request.form.get('tem_transcricao', ''),
            duracao=int(request.form.get('duracao', 0)) if request.form.get('duracao') else None,
            classificacao_etaria=request.form.get('classificacao_etaria', 'livre'),
            tags=request.form.get('tags', '')
        )
        
        db.session.add(conteudo)
        db.session.commit()
        
        return redirect(url_for('biblioteca'))
    
    return render_template('adicionar_conteudo_biblioteca.html')

# 8. MONITORAMENTO DE COMPORTAMENTO
def registrar_monitoramento(aluno_id, tipo_acao, contexto, tempo_gasto=None, resultado='sucesso', detalhes=None):
    """Função utilitária para registrar ações do aluno"""
    try:
        # Detectar dispositivo (simplificado)
        user_agent = request.headers.get('User-Agent', '')
        if 'Mobile' in user_agent:
            dispositivo = 'mobile'
        elif 'Tablet' in user_agent:
            dispositivo = 'tablet'
        else:
            dispositivo = 'desktop'
        
        monitoramento = MonitoramentoComportamento(
            aluno_id=aluno_id,
            tipo_acao=tipo_acao,
            contexto=contexto,
            tempo_gasto=tempo_gasto,
            dispositivo=dispositivo,
            resultado=resultado,
            detalhes=json.dumps(detalhes) if detalhes else None
        )
        
        db.session.add(monitoramento)
        db.session.commit()
    except Exception as e:
        print(f"Erro ao registrar monitoramento: {e}")

@app.route('/relatorio-comportamento/<int:aluno_id>')
def relatorio_comportamento(aluno_id):
    if 'usuario_id' not in session or session['tipo'] != 'professor':
        return redirect(url_for('login'))
    
    aluno = Aluno.query.get_or_404(aluno_id)
    
    # Estatísticas dos últimos 30 dias
    from datetime import timedelta
    data_limite = datetime.now() - timedelta(days=30)
    
    monitoramentos = MonitoramentoComportamento.query.filter(
        MonitoramentoComportamento.aluno_id == aluno_id,
        MonitoramentoComportamento.data_acao >= data_limite
    ).all()
    
    # Análise de padrões
    total_tempo = sum(m.tempo_gasto for m in monitoramentos if m.tempo_gasto)
    total_acoes = len(monitoramentos)
    
    # Análise por tipo de ação
    acoes_por_tipo = {}
    tempo_por_contexto = {}
    erros_por_contexto = {}
    
    for m in monitoramentos:
        # Contar ações por tipo
        if m.tipo_acao in acoes_por_tipo:
            acoes_por_tipo[m.tipo_acao] += 1
        else:
            acoes_por_tipo[m.tipo_acao] = 1
        
        # Tempo por contexto
        if m.tempo_gasto:
            if m.contexto in tempo_por_contexto:
                tempo_por_contexto[m.contexto] += m.tempo_gasto
            else:
                tempo_por_contexto[m.contexto] = m.tempo_gasto
        
        # Erros por contexto
        if m.resultado == 'erro':
            if m.contexto in erros_por_contexto:
                erros_por_contexto[m.contexto] += 1
            else:
                erros_por_contexto[m.contexto] = 1
    
    # Horários de maior atividade
    atividade_por_hora = {}
    for m in monitoramentos:
        hora = m.data_acao.hour
        if hora in atividade_por_hora:
            atividade_por_hora[hora] += 1
        else:
            atividade_por_hora[hora] = 1
    
    analise = {
        'total_tempo_minutos': total_tempo // 60 if total_tempo else 0,
        'total_acoes': total_acoes,
        'acoes_por_tipo': acoes_por_tipo,
        'tempo_por_contexto': tempo_por_contexto,
        'erros_por_contexto': erros_por_contexto,
        'atividade_por_hora': atividade_por_hora,
        'periodo_analise': '30 dias'
    }
    
    return render_template('relatorio_comportamento.html', 
                         aluno=aluno, 
                         analise=analise,
                         monitoramentos=monitoramentos[:20])  # Últimas 20 ações

@app.route('/logout')
def logout():
    if 'usuario_id' in session and session['tipo'] == 'aluno':
        aluno = Aluno.query.filter_by(usuario_id=session['usuario_id']).first()
        if aluno:
            registrar_monitoramento(aluno.id, 'logout', 'sistema')
    
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=False, host='127.0.0.1', port=5000)

