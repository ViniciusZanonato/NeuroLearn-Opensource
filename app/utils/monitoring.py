import json
from datetime import datetime, timedelta
from flask import request, current_app
from ..extensions import db


def registrar_monitoramento(aluno_id, tipo_acao, contexto, tempo_gasto=None, resultado='sucesso', detalhes=None):
    from ..models import MonitoramentoComportamento
    try:
        user_agent = request.headers.get('User-Agent', '')
        if 'Mobile' in user_agent:
            dispositivo = 'mobile'
        elif 'Tablet' in user_agent:
            dispositivo = 'tablet'
        else:
            dispositivo = 'desktop'

        m = MonitoramentoComportamento(
            aluno_id=aluno_id,
            tipo_acao=tipo_acao,
            contexto=contexto,
            tempo_gasto=tempo_gasto,
            dispositivo=dispositivo,
            resultado=resultado,
            detalhes=json.dumps(detalhes) if detalhes else None
        )
        db.session.add(m)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(f"Erro ao registrar monitoramento: {e}")


def gerar_sessoes_estudo(cronograma_id):
    from ..models import CronogramaEstudo, SessaoEstudo

    cronograma = CronogramaEstudo.query.get(cronograma_id)
    if not cronograma:
        return

    data_atual = cronograma.data_inicio
    dias_semana_lista = [int(d) for d in cronograma.dias_semana.split(',')]

    while data_atual <= cronograma.data_fim:
        dia_semana = data_atual.weekday() + 1
        if dia_semana in dias_semana_lista:
            num_sessoes = int((cronograma.horas_por_dia * 60) / cronograma.tempo_sessao)
            for i in range(num_sessoes):
                if cronograma.horario_preferido == 'manha':
                    hora_inicio = 8 + (i * ((cronograma.tempo_sessao + cronograma.tempo_pausa) / 60))
                elif cronograma.horario_preferido == 'tarde':
                    hora_inicio = 14 + (i * ((cronograma.tempo_sessao + cronograma.tempo_pausa) / 60))
                else:
                    hora_inicio = 19 + (i * ((cronograma.tempo_sessao + cronograma.tempo_pausa) / 60))

                hora = int(hora_inicio)
                minuto = int((hora_inicio - hora) * 60)
                data_sessao = datetime.combine(
                    data_atual,
                    datetime.min.time().replace(hour=hora, minute=minuto)
                )
                db.session.add(SessaoEstudo(
                    cronograma_id=cronograma_id,
                    data_sessao=data_sessao,
                    duracao_planejada=cronograma.tempo_sessao
                ))
        data_atual += timedelta(days=1)

    db.session.commit()
