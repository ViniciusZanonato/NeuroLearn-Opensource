from datetime import datetime, timedelta
from flask import render_template, request, jsonify, session, redirect, url_for
from . import bp
from ...extensions import db
from ...models import (Aluno, AnaliseIA, RespostaAluno, PerfilAprendizagem,
                       QuestionarioNeuroLearn, MonitoramentoComportamento)
from ...utils.ai import gerar_analise_teste_aleatorio
from filtro_relatorio_neurodivergencia import FiltroRelatorioNeurodivergencia

BLOCOS_INFO = {
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


def _professor_required():
    if 'usuario_id' not in session or session.get('tipo') != 'professor':
        return redirect(url_for('auth.login'))
    return None


@bp.route('/relatorio-aluno/<int:aluno_id>')
def relatorio_aluno(aluno_id):
    r = _professor_required()
    if r:
        return r
    aluno = Aluno.query.get_or_404(aluno_id)
    analises = AnaliseIA.query.filter_by(aluno_id=aluno_id).all()
    respostas = RespostaAluno.query.filter_by(aluno_id=aluno_id).all()
    return render_template('relatorio_aluno.html', aluno=aluno, analises=analises, respostas=respostas)


@bp.route('/visualizar-perfil/<int:aluno_id>')
def visualizar_perfil(aluno_id):
    r = _professor_required()
    if r:
        return r
    aluno = Aluno.query.get_or_404(aluno_id)
    perfil = PerfilAprendizagem.query.filter_by(aluno_id=aluno_id).first()
    perfil_formatado = None
    if perfil:
        filtro = FiltroRelatorioNeurodivergencia()
        dados = {
            'perfil_geral': perfil.perfil_geral or '',
            'potenciais_expressivos': perfil.potenciais_expressivos or '',
            'potenciais_cognitivos': perfil.potenciais_cognitivos or '',
            'indicios_neurodivergencias': perfil.indicios_neurodivergencias or '',
            'recomendacoes_professores': perfil.recomendacoes_professores or '',
            'reforco_motivacional': perfil.reforco_motivacional or '',
            'tipo_perfil': perfil.tipo_perfil or ''
        }
        perfil_formatado = {
            'perfil_geral': filtro._formatar_texto(dados['perfil_geral']),
            'potenciais_expressivos': filtro._formatar_texto(dados['potenciais_expressivos']),
            'potenciais_cognitivos': filtro._formatar_texto(dados['potenciais_cognitivos']),
            'indicios_neurodivergencias': filtro._formatar_texto(dados['indicios_neurodivergencias']),
            'recomendacoes_professores': filtro._formatar_lista_estrategias(dados['recomendacoes_professores']),
            'reforco_motivacional': filtro._formatar_texto(dados['reforco_motivacional']),
            'tipo_perfil': filtro._obter_tipo_perfil_formatado(dados['tipo_perfil'])
        }
    return render_template('visualizar_perfil.html', aluno=aluno, perfil=perfil, perfil_formatado=perfil_formatado)


@bp.route('/perfil-aluno/<int:aluno_id>')
def perfil_aluno_simples(aluno_id):
    r = _professor_required()
    if r:
        return r
    aluno = Aluno.query.get_or_404(aluno_id)
    perfil = PerfilAprendizagem.query.filter_by(aluno_id=aluno_id).first()
    return render_template('perfil_aluno_simples.html', aluno=aluno, perfil=perfil)


@bp.route('/ver-respostas-questionario/<int:aluno_id>')
def ver_respostas_questionario(aluno_id):
    r = _professor_required()
    if r:
        return r
    aluno = Aluno.query.get_or_404(aluno_id)
    respostas = QuestionarioNeuroLearn.query.filter_by(aluno_id=aluno_id).all()
    respostas_por_bloco = {i: [] for i in range(1, 8)}
    respostas_dict = {}
    estatisticas = {}
    for r_item in respostas:
        respostas_por_bloco[r_item.bloco].append(r_item)
        respostas_dict[r_item.questao] = r_item.resposta
        estatisticas[r_item.resposta] = estatisticas.get(r_item.resposta, 0) + 1
    return render_template('ver_respostas_questionario.html', aluno=aluno, respostas=respostas,
                           respostas_por_bloco=respostas_por_bloco, respostas_dict=respostas_dict,
                           estatisticas=estatisticas, blocos_info=BLOCOS_INFO)


@bp.route('/analisar-consistencia/<int:aluno_id>')
def analisar_consistencia(aluno_id):
    if 'usuario_id' not in session or session.get('tipo') != 'professor':
        return jsonify({'erro': 'Acesso negado - Apenas professores'}), 403
    Aluno.query.get_or_404(aluno_id)
    analise = gerar_analise_teste_aleatorio(aluno_id)
    return jsonify(analise)


@bp.route('/relatorio-detalhado/<int:aluno_id>')
def relatorio_detalhado(aluno_id):
    r = _professor_required()
    if r:
        return r
    aluno = Aluno.query.get_or_404(aluno_id)
    perfil = PerfilAprendizagem.query.filter_by(aluno_id=aluno_id).first()
    if not perfil:
        return jsonify({'erro': 'Perfil não encontrado'}), 404
    perfil_json = {
        'perfil_geral': perfil.perfil_geral,
        'potenciais_expressivos': perfil.potenciais_expressivos,
        'potenciais_cognitivos': perfil.potenciais_cognitivos,
        'indicios_neurodivergencias': perfil.indicios_neurodivergencias,
        'recomendacoes_professores': perfil.recomendacoes_professores,
        'reforco_motivacional': perfil.reforco_motivacional,
        'tipo_perfil': perfil.tipo_perfil
    }
    filtro = FiltroRelatorioNeurodivergencia()
    relatorio_formatado = filtro.formatar_relatorio_detalhado(perfil_json, aluno.usuario.nome, aluno.serie_ano)
    return render_template('relatorio_detalhado.html', aluno=aluno, perfil=perfil,
                           relatorio_formatado=relatorio_formatado)


@bp.route('/relatorio-comportamento/<int:aluno_id>')
def relatorio_comportamento(aluno_id):
    r = _professor_required()
    if r:
        return r
    aluno = Aluno.query.get_or_404(aluno_id)
    data_limite = datetime.now() - timedelta(days=30)
    monitoramentos = MonitoramentoComportamento.query.filter(
        MonitoramentoComportamento.aluno_id == aluno_id,
        MonitoramentoComportamento.data_acao >= data_limite
    ).all()
    total_tempo = sum(m.tempo_gasto for m in monitoramentos if m.tempo_gasto)
    acoes_por_tipo = {}
    tempo_por_contexto = {}
    erros_por_contexto = {}
    atividade_por_hora = {}
    for m in monitoramentos:
        acoes_por_tipo[m.tipo_acao] = acoes_por_tipo.get(m.tipo_acao, 0) + 1
        if m.tempo_gasto:
            tempo_por_contexto[m.contexto] = tempo_por_contexto.get(m.contexto, 0) + m.tempo_gasto
        if m.resultado == 'erro':
            erros_por_contexto[m.contexto] = erros_por_contexto.get(m.contexto, 0) + 1
        hora = m.data_acao.hour
        atividade_por_hora[hora] = atividade_por_hora.get(hora, 0) + 1
    analise = {
        'total_tempo_minutos': total_tempo // 60 if total_tempo else 0,
        'total_acoes': len(monitoramentos),
        'acoes_por_tipo': acoes_por_tipo,
        'tempo_por_contexto': tempo_por_contexto,
        'erros_por_contexto': erros_por_contexto,
        'atividade_por_hora': atividade_por_hora,
        'periodo_analise': '30 dias'
    }
    return render_template('relatorio_comportamento.html', aluno=aluno, analise=analise,
                           monitoramentos=monitoramentos[:20])
