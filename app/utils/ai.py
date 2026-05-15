import json
import requests
from datetime import datetime
from flask import current_app

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
    base_url = current_app.config['OLLAMA_BASE_URL']
    model = current_app.config['OLLAMA_MODEL']
    timeout = current_app.config['OLLAMA_TIMEOUT']

    data = {
        'model': model,
        'prompt': _prompt_com_guardrails(prompt),
        'stream': False,
        'options': {'temperature': 0.2, 'top_p': 0.9, 'num_ctx': 8192}
    }
    try:
        response = requests.post(f"{base_url}/api/generate", json=data, timeout=timeout)
        if response.status_code == 200:
            return response.json().get('response', '').strip()
        return f"Erro no Ollama local: HTTP {response.status_code}"
    except requests.exceptions.ConnectionError:
        return (
            f"IA local indisponivel: o Ollama nao esta rodando em {base_url}. "
            f"Inicie o Ollama e garanta que o modelo {model} esteja instalado."
        )
    except Exception as e:
        return f"Erro no Ollama local: {str(e)}"


def consultar_gemini(prompt):
    api_key = current_app.config['GEMINI_API_KEY']
    gemini_url = current_app.config['GEMINI_URL']

    if not api_key:
        return "IA externa desativada: GEMINI_API_KEY nao configurada."

    data = {"contents": [{"parts": [{"text": _prompt_com_guardrails(prompt)}]}]}
    try:
        response = requests.post(
            f"{gemini_url}?key={api_key}",
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
    if current_app.config['AI_PROVIDER'] == 'gemini':
        return consultar_gemini(prompt)
    return consultar_ollama(prompt)


def gerar_perfil_basico(aluno, respostas_por_bloco):
    medias = {}
    for bloco, respostas in respostas_por_bloco.items():
        medias[bloco] = sum(respostas) / len(respostas) if respostas else 2.5

    blocos_nomes = {
        1: 'Percepção Sensorial', 2: 'Atenção e Foco', 3: 'Comunicação',
        4: 'Organização', 5: 'Aprendizagem', 6: 'Interação Social', 7: 'Criatividade'
    }
    pontos_fortes = [blocos_nomes[b] for b, m in medias.items() if m >= 4.0]

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

    pf = ', '.join(pontos_fortes) if pontos_fortes else 'múltiplas áreas'
    pf2 = ', '.join(pontos_fortes[:2]) if len(pontos_fortes) >= 2 else 'diferentes modalidades'
    pf3 = ', '.join(pontos_fortes[:3]) if pontos_fortes else 'múltiplas áreas'

    return {
        'perfil_geral': f"O aluno {aluno.usuario.nome} apresenta um perfil de aprendizagem com características marcantes em {pf}.",
        'potenciais_expressivos': f"O aluno demonstra facilidade para se expressar através de {pf2}.",
        'potenciais_cognitivos': f"As áreas de maior destaque cognitivo são {pf}.",
        'indicios_neurodivergencias': "As respostas indicam um perfil neurotípico com características individuais de aprendizagem.",
        'recomendacoes_professores': f"1. Valorizar os pontos fortes em {pf3}. 2. Oferecer atividades diversificadas. 3. Respeitar o ritmo individual.",
        'reforco_motivacional': f"Você tem talentos únicos! Continue explorando suas habilidades em {pf2}!",
        'tipo_perfil': tipo_perfil
    }


def gerar_perfil_aprendizagem(aluno_id):
    from ..models import Aluno, QuestionarioNeuroLearn, PerfilAprendizagem
    from ..extensions import db

    aluno = Aluno.query.get(aluno_id)
    respostas = QuestionarioNeuroLearn.query.filter_by(aluno_id=aluno_id).all()

    respostas_por_bloco = {i: [] for i in range(1, 8)}
    for r in respostas:
        respostas_por_bloco[r.bloco].append(r.resposta)

    perfil_data = gerar_perfil_basico(aluno, respostas_por_bloco)

    try:
        prompt = f"""
        Analise as respostas do questionário NeuroLearn e gere um perfil focado e objetivo.
        Dados do Aluno: Nome: {aluno.usuario.nome}, Série: {aluno.serie_ano}, Idade: {aluno.idade} anos
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
        resultado_limpo = resultado_ia.strip().lstrip('```json').lstrip('```').rstrip('```').strip()
        perfil_ia = json.loads(resultado_limpo)
        for key, value in perfil_ia.items():
            if value and len(str(value).strip()) > 0:
                perfil_data[key] = value
    except Exception as e:
        current_app.logger.warning(f"Perfil IA falhou, usando básico: {e}")

    def s(v):
        if v is None:
            return ''
        if isinstance(v, list):
            return '\n'.join(str(i) for i in v)
        if isinstance(v, dict):
            return '\n'.join(f"{k}: {val}" for k, val in v.items())
        return str(v)

    try:
        perfil = PerfilAprendizagem.query.filter_by(aluno_id=aluno_id).first()
        if perfil:
            perfil.perfil_geral = s(perfil_data.get('perfil_geral'))
            perfil.potenciais_expressivos = s(perfil_data.get('potenciais_expressivos'))
            perfil.potenciais_cognitivos = s(perfil_data.get('potenciais_cognitivos'))
            perfil.indicios_neurodivergencias = s(perfil_data.get('indicios_neurodivergencias'))
            perfil.recomendacoes_professores = s(perfil_data.get('recomendacoes_professores'))
            perfil.reforco_motivacional = s(perfil_data.get('reforco_motivacional'))
            perfil.tipo_perfil = s(perfil_data.get('tipo_perfil'))
            perfil.data_geracao = datetime.utcnow()
        else:
            perfil = PerfilAprendizagem(
                aluno_id=aluno_id,
                perfil_geral=s(perfil_data.get('perfil_geral')),
                potenciais_expressivos=s(perfil_data.get('potenciais_expressivos')),
                potenciais_cognitivos=s(perfil_data.get('potenciais_cognitivos')),
                indicios_neurodivergencias=s(perfil_data.get('indicios_neurodivergencias')),
                recomendacoes_professores=s(perfil_data.get('recomendacoes_professores')),
                reforco_motivacional=s(perfil_data.get('reforco_motivacional')),
                tipo_perfil=s(perfil_data.get('tipo_perfil'))
            )
            db.session.add(perfil)
        aluno.perfil_gerado = True
        db.session.commit()
    except Exception as e:
        current_app.logger.error(f"Erro ao salvar perfil: {e}")
        db.session.rollback()


def analisar_resposta_ia(aluno_id, resposta_id):
    from ..models import Aluno, RespostaAluno, AnaliseIA
    from ..extensions import db

    aluno = Aluno.query.get(aluno_id)
    resposta = RespostaAluno.query.get(resposta_id)
    todas_respostas = RespostaAluno.query.filter_by(aluno_id=aluno_id).all()

    historico = '\n'.join(
        f"- {r.atividade.titulo}: {r.resposta[:100]}..."
        for r in todas_respostas[-5:]
    )
    prompt = f"""
    Analise as respostas de um aluno para identificar possíveis neurodivergências e padrões de aprendizagem.
    Dados do Aluno: Série: {aluno.serie_ano}
    Última Resposta: Atividade: {resposta.atividade.titulo} (Tipo: {resposta.atividade.tipo})
    Resposta: {resposta.resposta}, Tempo: {resposta.tempo_resposta} segundos
    Histórico (últimas 5): {historico}
    Forneça análise: padrões, possíveis neurodivergências, estratégias pedagógicas, nível de confiança (0-100%).
    Responda em formato JSON.
    """
    try:
        resultado_ia = consultar_ia(prompt)
        analise = AnaliseIA(
            aluno_id=aluno_id,
            tipo_analise='neurodivergencia',
            resultado=resultado_ia,
            confianca=0.8
        )
        db.session.add(analise)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(f"Erro na análise IA: {e}")


def analisar_consistencia_respostas(aluno_id):
    from ..models import QuestionarioNeuroLearn

    respostas = QuestionarioNeuroLearn.query.filter_by(aluno_id=aluno_id).all()
    if len(respostas) < 60:
        return {'nivel_confianca': 0.5, 'inconsistencias': ['Questionário incompleto'], 'recomendacao': 'Completar questionário'}

    respostas_por_bloco = {i: [] for i in range(1, 8)}
    for r in respostas:
        respostas_por_bloco[r.bloco].append(r.resposta)

    medias = {b: sum(v) / len(v) for b, v in respostas_por_bloco.items() if v}
    variancias = {b: sum((x - medias[b]) ** 2 for x in v) / len(v) for b, v in respostas_por_bloco.items() if v}

    inconsistencias = []
    alta_variancia = [b for b, var in variancias.items() if var > 2.5]
    if alta_variancia:
        inconsistencias.append(f"Alta variabilidade nos blocos: {', '.join(map(str, alta_variancia))}")
    if abs(medias.get(2, 3) - medias.get(4, 3)) > 2.0:
        inconsistencias.append("Contradição entre Atenção e Organização")
    if abs(medias.get(3, 3) - medias.get(6, 3)) > 2.0:
        inconsistencias.append("Contradição entre Comunicação e Interação Social")

    todas = [r.resposta for r in respostas]
    if sum(1 for r in todas if r in [1, 5]) / len(todas) > 0.7:
        inconsistencias.append("Excesso de respostas extremas")

    seqs = sum(1 for i in range(len(todas) - 4) if len(set(todas[i:i+5])) == 1)
    if seqs > 3:
        inconsistencias.append("Padrões repetitivos detectados")

    n = len(inconsistencias)
    if n == 0:
        return {'nivel_confianca': 0.95, 'inconsistencias': [], 'recomendacao': 'Perfil altamente confiável', 'num_inconsistencias': 0}
    elif n == 1:
        return {'nivel_confianca': 0.8, 'inconsistencias': inconsistencias, 'recomendacao': 'Perfil confiável com pequenas ressalvas', 'num_inconsistencias': 1}
    elif n == 2:
        return {'nivel_confianca': 0.6, 'inconsistencias': inconsistencias, 'recomendacao': 'Validar com observação comportamental', 'num_inconsistencias': 2}
    else:
        return {'nivel_confianca': 0.3, 'inconsistencias': inconsistencias, 'recomendacao': 'ATENÇÃO: Reaplicar questionário com supervisão', 'num_inconsistencias': n}


def gerar_analise_teste_aleatorio(aluno_id):
    import random
    cenarios = [
        {'nivel_confianca': random.uniform(0.85, 0.95), 'inconsistencias': [], 'recomendacao': 'Perfil altamente confiável'},
        {'nivel_confianca': random.uniform(0.75, 0.84), 'inconsistencias': ['Pequena variabilidade no bloco de Atenção'], 'recomendacao': 'Perfil confiável com pequenas ressalvas'},
        {'nivel_confianca': random.uniform(0.55, 0.74), 'inconsistencias': ['Contradição entre Comunicação e Interação Social'], 'recomendacao': 'Validar com observação comportamental'},
        {'nivel_confianca': random.uniform(0.25, 0.54), 'inconsistencias': ['Padrões repetitivos', 'Alta variabilidade', 'Excesso de respostas extremas'], 'recomendacao': 'ATENÇÃO: Reaplicar questionário com supervisão'},
    ]
    c = random.choice(cenarios)
    c['num_inconsistencias'] = len(c['inconsistencias'])
    return c
