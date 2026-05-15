from datetime import datetime
from .extensions import db


class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    senha_hash = db.Column(db.String(100), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)


class Aluno(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    email_escola = db.Column(db.String(100))
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
    tipo = db.Column(db.String(50), nullable=False)
    professor_id = db.Column(db.Integer, db.ForeignKey('professor.id'), nullable=False)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    data_limite = db.Column(db.DateTime)
    arquivo_anexo = db.Column(db.String(200))
    arquivo_original = db.Column(db.String(200))
    pontuacao_maxima = db.Column(db.Integer, default=100)
    instrucoes_especiais = db.Column(db.Text)
    professor = db.relationship('Professor', backref='atividades')


class RespostaAluno(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey('aluno.id'), nullable=False)
    atividade_id = db.Column(db.Integer, db.ForeignKey('atividade.id'), nullable=False)
    resposta = db.Column(db.Text, nullable=False)
    tempo_resposta = db.Column(db.Integer)
    data_envio = db.Column(db.DateTime, default=datetime.utcnow)
    aluno = db.relationship('Aluno', backref='respostas')
    atividade = db.relationship('Atividade', backref='respostas')


class AnaliseIA(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey('aluno.id'), nullable=False)
    tipo_analise = db.Column(db.String(100), nullable=False)
    resultado = db.Column(db.Text, nullable=False)
    confianca = db.Column(db.Float)
    data_analise = db.Column(db.DateTime, default=datetime.utcnow)
    aluno = db.relationship('Aluno', backref='analises')


class QuestionarioNeuroLearn(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey('aluno.id'), nullable=False)
    bloco = db.Column(db.Integer, nullable=False)
    questao = db.Column(db.Integer, nullable=False)
    resposta = db.Column(db.Integer, nullable=False)
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
    tipo_perfil = db.Column(db.String(100))
    data_geracao = db.Column(db.DateTime, default=datetime.utcnow)
    aluno = db.relationship('Aluno', backref=db.backref('perfil_aprendizagem', uselist=False))


class TestePerfiliCognitivo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey('aluno.id'), nullable=False)
    tipo_teste = db.Column(db.String(50), nullable=False)
    pontuacao = db.Column(db.Integer, nullable=False)
    tempo_resposta = db.Column(db.Integer)
    data_teste = db.Column(db.DateTime, default=datetime.utcnow)
    resultados_detalhados = db.Column(db.Text)
    aluno = db.relationship('Aluno', backref='testes_cognitivos')


class TrilhaAprendizado(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), nullable=False)
    descricao = db.Column(db.Text)
    tipo_conteudo = db.Column(db.String(50), nullable=False)
    nivel_dificuldade = db.Column(db.String(20), nullable=False)
    area_conhecimento = db.Column(db.String(100), nullable=False)
    perfil_alvo = db.Column(db.String(100))
    duracao_estimada = db.Column(db.Integer)
    url_conteudo = db.Column(db.String(500))
    arquivo_conteudo = db.Column(db.String(200))
    ativo = db.Column(db.Boolean, default=True)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)


class ProgressoTrilha(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey('aluno.id'), nullable=False)
    trilha_id = db.Column(db.Integer, db.ForeignKey('trilha_aprendizado.id'), nullable=False)
    progresso = db.Column(db.Float, default=0.0)
    tempo_gasto = db.Column(db.Integer, default=0)
    data_inicio = db.Column(db.DateTime, default=datetime.utcnow)
    data_conclusao = db.Column(db.DateTime)
    feedback_aluno = db.Column(db.Text)
    dificuldade_percebida = db.Column(db.Integer)
    aluno = db.relationship('Aluno', backref='progressos_trilha')
    trilha = db.relationship('TrilhaAprendizado', backref='progressos')


class CronogramaEstudo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey('aluno.id'), nullable=False)
    data_inicio = db.Column(db.Date, nullable=False)
    data_fim = db.Column(db.Date, nullable=False)
    objetivo = db.Column(db.String(200), nullable=False)
    horas_por_dia = db.Column(db.Float, nullable=False)
    dias_semana = db.Column(db.String(20), nullable=False)
    horario_preferido = db.Column(db.String(20))
    tempo_pausa = db.Column(db.Integer, default=10)
    tempo_sessao = db.Column(db.Integer, default=25)
    lembretes_ativos = db.Column(db.Boolean, default=True)
    ativo = db.Column(db.Boolean, default=True)
    aluno = db.relationship('Aluno', backref='cronogramas')


class SessaoEstudo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cronograma_id = db.Column(db.Integer, db.ForeignKey('cronograma_estudo.id'), nullable=False)
    data_sessao = db.Column(db.DateTime, nullable=False)
    duracao_planejada = db.Column(db.Integer, nullable=False)
    duracao_real = db.Column(db.Integer)
    realizada = db.Column(db.Boolean, default=False)
    feedback = db.Column(db.Text)
    nivel_concentracao = db.Column(db.Integer)
    trilha_estudada = db.Column(db.Integer, db.ForeignKey('trilha_aprendizado.id'))
    cronograma = db.relationship('CronogramaEstudo', backref='sessoes')
    trilha = db.relationship('TrilhaAprendizado', backref='sessoes_estudo')


class BibliotecaConteudo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    descricao = db.Column(db.Text)
    tipo = db.Column(db.String(50), nullable=False)
    categoria = db.Column(db.String(100), nullable=False)
    nivel_ensino = db.Column(db.String(20))
    url_conteudo = db.Column(db.String(500))
    arquivo_conteudo = db.Column(db.String(200))
    tem_legenda = db.Column(db.Boolean, default=False)
    tem_libras = db.Column(db.Boolean, default=False)
    tem_transcricao = db.Column(db.String(500))
    duracao = db.Column(db.Integer)
    classificacao_etaria = db.Column(db.String(10))
    tags = db.Column(db.String(500))
    ativo = db.Column(db.Boolean, default=True)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)


class MonitoramentoComportamento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey('aluno.id'), nullable=False)
    data_acao = db.Column(db.DateTime, default=datetime.utcnow)
    tipo_acao = db.Column(db.String(50), nullable=False)
    contexto = db.Column(db.String(100))
    tempo_gasto = db.Column(db.Integer)
    dispositivo = db.Column(db.String(50))
    resultado = db.Column(db.String(20))
    detalhes = db.Column(db.Text)
    aluno = db.relationship('Aluno', backref='monitoramentos')


class ConfiguracaoAcessibilidade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False, unique=True)
    modo_escuro = db.Column(db.Boolean, default=False)
    alto_contraste = db.Column(db.Boolean, default=False)
    tamanho_fonte = db.Column(db.String(20), default='normal')
    audio_leitura = db.Column(db.Boolean, default=False)
    velocidade_audio = db.Column(db.Float, default=1.0)
    navegacao_simplificada = db.Column(db.Boolean, default=False)
    reducao_animacoes = db.Column(db.Boolean, default=False)
    notificacoes_visuais = db.Column(db.Boolean, default=True)
    notificacoes_sonoras = db.Column(db.Boolean, default=True)
    cores_personalizadas = db.Column(db.String(500))
    usuario = db.relationship('Usuario', backref=db.backref('config_acessibilidade', uselist=False))


class InteracaoAssistente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    mensagem_usuario = db.Column(db.Text, nullable=False)
    resposta_assistente = db.Column(db.Text, nullable=False)
    contexto = db.Column(db.String(100))
    satisfacao_resposta = db.Column(db.Integer)
    data_interacao = db.Column(db.DateTime, default=datetime.utcnow)
    resolveu_duvida = db.Column(db.Boolean)
    usuario = db.relationship('Usuario', backref='interacoes_assistente')
