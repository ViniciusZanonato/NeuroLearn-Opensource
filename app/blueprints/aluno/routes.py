import json
from datetime import datetime
from flask import (render_template, request, jsonify, session,
                   redirect, url_for)
from . import bp
from ...extensions import db
from ...models import (Aluno, Atividade, RespostaAluno, PerfilAprendizagem,
                       QuestionarioNeuroLearn, TestePerfiliCognitivo,
                       TrilhaAprendizado, ProgressoTrilha, CronogramaEstudo,
                       SessaoEstudo, InteracaoAssistente, ConfiguracaoAcessibilidade,
                       BibliotecaConteudo)
from ...utils.ai import (gerar_perfil_aprendizagem, analisar_resposta_ia, consultar_ia)
from ...utils.monitoring import registrar_monitoramento, gerar_sessoes_estudo

QUESTOES = {
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


def _aluno_required():
    if 'usuario_id' not in session or session.get('tipo') != 'aluno':
        return redirect(url_for('auth.login'))
    return None


def _login_required():
    if 'usuario_id' not in session:
        return redirect(url_for('auth.login'))
    return None


@bp.route('/dashboard-aluno')
def dashboard_aluno():
    r = _aluno_required()
    if r:
        return r
    aluno = Aluno.query.filter_by(usuario_id=session['usuario_id']).first()
    if not aluno.questionario_completo:
        return redirect(url_for('aluno.questionario_neurolearn'))
    atividades = Atividade.query.all()
    perfil_status = {'gerado': aluno.perfil_gerado, 'data_geracao': None}
    if aluno.perfil_gerado:
        perfil = PerfilAprendizagem.query.filter_by(aluno_id=aluno.id).first()
        if perfil:
            perfil_status['data_geracao'] = perfil.data_geracao
    return render_template('dashboard_aluno.html', atividades=atividades, perfil_status=perfil_status)


@bp.route('/questionario-neurolearn')
def questionario_neurolearn():
    r = _aluno_required()
    if r:
        return r
    aluno = Aluno.query.filter_by(usuario_id=session['usuario_id']).first()
    if aluno.questionario_completo:
        return redirect(url_for('aluno.dashboard_aluno'))
    return render_template('questionario_neurolearn.html', questoes=QUESTOES)


@bp.route('/salvar-questionario', methods=['POST'])
def salvar_questionario():
    if 'usuario_id' not in session or session['tipo'] != 'aluno':
        return jsonify({'erro': 'Usuário não autenticado'}), 401
    aluno = Aluno.query.filter_by(usuario_id=session['usuario_id']).first()
    data = request.get_json()
    try:
        QuestionarioNeuroLearn.query.filter_by(aluno_id=aluno.id).delete()
        for questao_id, resposta in data['respostas'].items():
            bloco = ((int(questao_id) - 1) // 10) + 1
            db.session.add(QuestionarioNeuroLearn(
                aluno_id=aluno.id,
                bloco=bloco,
                questao=int(questao_id),
                resposta=int(resposta)
            ))
        aluno.questionario_completo = True
        db.session.commit()
        gerar_perfil_aprendizagem(aluno.id)
        return jsonify({'sucesso': 'Questionário salvo com sucesso'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 500


@bp.route('/perfil-aprendizagem')
def perfil_aprendizagem():
    r = _login_required()
    if r:
        return r
    if session['tipo'] == 'aluno':
        return redirect(url_for('aluno.dashboard_aluno'))
    elif session['tipo'] == 'professor':
        return redirect(url_for('professor.painel_professor'))
    return redirect(url_for('auth.login'))


@bp.route('/responder-atividade/<int:atividade_id>', methods=['GET', 'POST'])
def responder_atividade(atividade_id):
    r = _aluno_required()
    if r:
        return r
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
        analisar_resposta_ia(aluno.id, resposta.id)
        return redirect(url_for('aluno.dashboard_aluno'))
    return render_template('responder_atividade.html', atividade=atividade)


@bp.route('/trilhas-aprendizado')
def trilhas_aprendizado():
    r = _login_required()
    if r:
        return r
    if session['tipo'] == 'aluno':
        aluno = Aluno.query.filter_by(usuario_id=session['usuario_id']).first()
        perfil = PerfilAprendizagem.query.filter_by(aluno_id=aluno.id).first()
        trilhas = TrilhaAprendizado.query.filter_by(ativo=True).all()
        trilhas_recomendadas = []
        if perfil and perfil.tipo_perfil:
            trilhas_recomendadas = TrilhaAprendizado.query.filter(
                TrilhaAprendizado.perfil_alvo.like(f'%{perfil.tipo_perfil}%'),
                TrilhaAprendizado.ativo == True
            ).all()
        return render_template('trilhas_aluno.html', trilhas=trilhas,
                               trilhas_recomendadas=trilhas_recomendadas, aluno=aluno)
    else:
        trilhas = TrilhaAprendizado.query.all()
        return render_template('trilhas_professor.html', trilhas=trilhas)


@bp.route('/iniciar-trilha/<int:trilha_id>')
def iniciar_trilha(trilha_id):
    r = _aluno_required()
    if r:
        return r
    aluno = Aluno.query.filter_by(usuario_id=session['usuario_id']).first()
    trilha = TrilhaAprendizado.query.get_or_404(trilha_id)
    progresso = ProgressoTrilha.query.filter_by(aluno_id=aluno.id, trilha_id=trilha_id).first()
    if not progresso:
        progresso = ProgressoTrilha(aluno_id=aluno.id, trilha_id=trilha_id, progresso=0.0)
        db.session.add(progresso)
        db.session.commit()
    registrar_monitoramento(aluno.id, 'inicio_trilha', f'trilha_{trilha_id}')
    return render_template('executar_trilha.html', trilha=trilha, progresso=progresso)


@bp.route('/atualizar-progresso-trilha', methods=['POST'])
def atualizar_progresso_trilha():
    if 'usuario_id' not in session or session['tipo'] != 'aluno':
        return jsonify({'erro': 'Usuário não autenticado'}), 401
    aluno = Aluno.query.filter_by(usuario_id=session['usuario_id']).first()
    data = request.get_json()
    progresso = ProgressoTrilha.query.filter_by(aluno_id=aluno.id, trilha_id=data['trilha_id']).first()
    if progresso:
        progresso.progresso = data['progresso']
        progresso.tempo_gasto += data.get('tempo_adicional', 0)
        if data['progresso'] >= 100.0:
            progresso.data_conclusao = datetime.utcnow()
        db.session.commit()
        registrar_monitoramento(aluno.id, 'progresso_trilha', f"trilha_{data['trilha_id']}",
                               tempo_gasto=data.get('tempo_adicional', 0))
    return jsonify({'sucesso': 'Progresso atualizado'})


@bp.route('/cronograma-estudos')
def cronograma_estudos():
    r = _aluno_required()
    if r:
        return r
    aluno = Aluno.query.filter_by(usuario_id=session['usuario_id']).first()
    cronogramas = CronogramaEstudo.query.filter_by(aluno_id=aluno.id, ativo=True).all()
    return render_template('cronograma_estudos.html', cronogramas=cronogramas, aluno=aluno)


@bp.route('/criar-cronograma', methods=['GET', 'POST'])
def criar_cronograma():
    r = _aluno_required()
    if r:
        return r
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
        gerar_sessoes_estudo(cronograma.id)
        return redirect(url_for('aluno.cronograma_estudos'))
    return render_template('criar_cronograma.html')


@bp.route('/sessoes-hoje')
def sessoes_hoje():
    if 'usuario_id' not in session or session['tipo'] != 'aluno':
        return jsonify({'erro': 'Usuário não autenticado'}), 401
    aluno = Aluno.query.filter_by(usuario_id=session['usuario_id']).first()
    hoje = datetime.now().date()
    sessoes = db.session.query(SessaoEstudo).join(CronogramaEstudo).filter(
        CronogramaEstudo.aluno_id == aluno.id,
        db.func.date(SessaoEstudo.data_sessao) == hoje
    ).all()
    return jsonify({'sessoes': [
        {'id': s.id, 'horario': s.data_sessao.strftime('%H:%M'),
         'duracao': s.duracao_planejada, 'realizada': s.realizada,
         'objetivo': s.cronograma.objetivo}
        for s in sessoes
    ]})


@bp.route('/marcar-sessao-realizada/<int:sessao_id>', methods=['POST'])
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
    aluno = Aluno.query.join(CronogramaEstudo).filter(CronogramaEstudo.id == sessao.cronograma_id).first()
    registrar_monitoramento(aluno.id, 'sessao_estudo', 'cronograma',
                           tempo_gasto=sessao.duracao_real * 60)
    return jsonify({'sucesso': 'Sessão marcada como realizada'})


@bp.route('/painel-progresso')
def painel_progresso():
    r = _login_required()
    if r:
        return r
    if session['tipo'] == 'aluno':
        aluno = Aluno.query.filter_by(usuario_id=session['usuario_id']).first()
        return render_template('painel_progresso_aluno.html', aluno=aluno)
    elif session['tipo'] == 'professor':
        alunos = Aluno.query.all()
        return render_template('painel_progresso_professor.html', alunos=alunos)
    return redirect(url_for('auth.login'))


@bp.route('/dados-progresso-aluno/<int:aluno_id>')
def dados_progresso_aluno(aluno_id):
    if 'usuario_id' not in session:
        return jsonify({'erro': 'Usuário não autenticado'}), 401
    if session['tipo'] == 'aluno':
        aluno_session = Aluno.query.filter_by(usuario_id=session['usuario_id']).first()
        if aluno_session.id != aluno_id:
            return jsonify({'erro': 'Acesso negado'}), 403
    elif session['tipo'] != 'professor':
        return jsonify({'erro': 'Acesso negado'}), 403

    total_trilhas = ProgressoTrilha.query.filter_by(aluno_id=aluno_id).count()
    trilhas_concluidas = ProgressoTrilha.query.filter_by(aluno_id=aluno_id).filter(
        ProgressoTrilha.progresso >= 100.0).count()
    progresso_medio = db.session.query(db.func.avg(ProgressoTrilha.progresso)).filter_by(
        aluno_id=aluno_id).scalar() or 0
    tempo_total = db.session.query(db.func.sum(ProgressoTrilha.tempo_gasto)).filter_by(
        aluno_id=aluno_id).scalar() or 0
    sessoes_realizadas = db.session.query(SessaoEstudo).join(CronogramaEstudo).filter(
        CronogramaEstudo.aluno_id == aluno_id, SessaoEstudo.realizada == True).count()
    from datetime import timedelta
    atividades_recentes = db.session.query(db.func.count()).filter(
        db.text(f"aluno_id = {aluno_id}")).scalar() or 0

    return jsonify({
        'total_trilhas': total_trilhas,
        'trilhas_concluidas': trilhas_concluidas,
        'progresso_medio': round(progresso_medio, 1),
        'tempo_total_minutos': tempo_total,
        'sessoes_realizadas': sessoes_realizadas,
        'atividades_recentes': atividades_recentes
    })


@bp.route('/assistente-virtual')
def assistente_virtual():
    r = _login_required()
    if r:
        return r
    return render_template('assistente_virtual.html')


@bp.route('/conversar-assistente', methods=['POST'])
def conversar_assistente():
    if 'usuario_id' not in session:
        return jsonify({'erro': 'Usuário não autenticado'}), 401
    data = request.get_json()
    mensagem = data['mensagem']
    contexto = data.get('contexto', 'geral')

    if session['tipo'] == 'aluno':
        aluno = Aluno.query.filter_by(usuario_id=session['usuario_id']).first()
        perfil = PerfilAprendizagem.query.filter_by(aluno_id=aluno.id).first()
        prompt = f"""
        Você é um assistente virtual educacional especializado em auxiliar estudantes.
        Contexto do estudante: Nome: {aluno.usuario.nome}, Série: {aluno.serie_ano},
        Tipo de perfil: {perfil.tipo_perfil if perfil else 'Não definido'}
        Contexto da conversa: {contexto}
        Pergunta do estudante: {mensagem}
        Responda de forma acolhedora, educativa e adequada à idade.
        """
    else:
        prompt = f"""
        Você é um assistente virtual educacional especializado em auxiliar professores.
        Contexto: {contexto}
        Pergunta do professor: {mensagem}
        Responda com informações pedagógicas úteis e estratégias de ensino.
        """

    try:
        resposta = consultar_ia(prompt)
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


@bp.route('/avaliar-resposta-assistente', methods=['POST'])
def avaliar_resposta_assistente():
    if 'usuario_id' not in session:
        return jsonify({'erro': 'Usuário não autenticado'}), 401
    data = request.get_json()
    interacao = InteracaoAssistente.query.get_or_404(data['interacao_id'])
    interacao.satisfacao_resposta = data['satisfacao']
    interacao.resolveu_duvida = data.get('resolveu_duvida')
    db.session.commit()
    return jsonify({'sucesso': 'Avaliação salva'})


@bp.route('/configuracoes-acessibilidade')
def configuracoes_acessibilidade():
    r = _login_required()
    if r:
        return r
    config = ConfiguracaoAcessibilidade.query.filter_by(usuario_id=session['usuario_id']).first()
    if not config:
        config = ConfiguracaoAcessibilidade(usuario_id=session['usuario_id'])
        db.session.add(config)
        db.session.commit()
    return render_template('configuracoes_acessibilidade.html', config=config)


@bp.route('/salvar-configuracoes-acessibilidade', methods=['POST'])
def salvar_configuracoes_acessibilidade():
    if 'usuario_id' not in session:
        return jsonify({'erro': 'Usuário não autenticado'}), 401
    config = ConfiguracaoAcessibilidade.query.filter_by(usuario_id=session['usuario_id']).first()
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


@bp.route('/obter-configuracoes-acessibilidade')
def obter_configuracoes_acessibilidade():
    if 'usuario_id' not in session:
        return jsonify({'erro': 'Usuário não autenticado'}), 401
    config = ConfiguracaoAcessibilidade.query.filter_by(usuario_id=session['usuario_id']).first()
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


@bp.route('/teste-perfil-cognitivo')
def teste_perfil_cognitivo():
    r = _aluno_required()
    if r:
        return r
    aluno = Aluno.query.filter_by(usuario_id=session['usuario_id']).first()
    return render_template('teste_perfil_cognitivo.html', aluno=aluno)


@bp.route('/executar-teste-cognitivo', methods=['POST'])
def executar_teste_cognitivo():
    if 'usuario_id' not in session or session['tipo'] != 'aluno':
        return jsonify({'erro': 'Usuário não autenticado'}), 401
    aluno = Aluno.query.filter_by(usuario_id=session['usuario_id']).first()
    data = request.get_json()
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


@bp.route('/biblioteca')
def biblioteca():
    r = _login_required()
    if r:
        return r
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
    categorias = [c[0] for c in db.session.query(BibliotecaConteudo.categoria).distinct().all() if c[0]]
    tipos = [t[0] for t in db.session.query(BibliotecaConteudo.tipo).distinct().all() if t[0]]
    niveis = [n[0] for n in db.session.query(BibliotecaConteudo.nivel_ensino).distinct().all() if n[0]]
    return render_template('biblioteca.html', conteudos=conteudos, categorias=categorias,
                           tipos=tipos, niveis=niveis,
                           filtros={'tipo': tipo, 'categoria': categoria, 'nivel': nivel})
