#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Filtro para melhorar a apresentação dos relatórios JSON de neurodivergência
Projetado para a equipe Control + Amizade
"""

import json
import re
from datetime import datetime
from typing import Dict, Any, List

class FiltroRelatorioNeurodivergencia:
    """Filtro para processar e melhorar relatórios de neurodivergência"""
    
    def __init__(self):
        self.tipos_perfil_map = {
            'neurotipico': '🟢 Neurotípico',
            'tdah': '🔵 TDAH - Transtorno do Déficit de Atenção/Hiperatividade',
            'tea': '🟡 TEA - Transtorno do Espectro Autista',
            'superdotacao': '🟣 Superdotação/Altas Habilidades',
            'dislexia': '🟠 Dislexia',
            'misto': '🔄 Perfil Misto'
        }
    
    def processar_json_bruto(self, json_texto: str) -> Dict[str, Any]:
        """Processa JSON bruto da IA e limpa formatação"""
        try:
            # Limpar markdown
            texto_limpo = json_texto.strip()
            if texto_limpo.startswith('```json'):
                texto_limpo = texto_limpo[7:]
            if texto_limpo.endswith('```'):
                texto_limpo = texto_limpo[:-3]
            texto_limpo = texto_limpo.strip()
            
            # Parsear JSON
            dados = json.loads(texto_limpo)
            return dados
            
        except json.JSONDecodeError as e:
            print(f"Erro ao processar JSON: {e}")
            return self._gerar_json_padrao()
    
    def _gerar_json_padrao(self) -> Dict[str, Any]:
        """Gera estrutura JSON padrão em caso de erro"""
        return {
            'perfil_geral': 'Perfil não pôde ser gerado automaticamente. Requer análise manual.',
            'potenciais_expressivos': 'A ser determinado através de observação direta.',
            'potenciais_cognitivos': 'A ser avaliado com instrumentos específicos.',
            'indicios_neurodivergencias': 'Análise inconclusiva. Recomenda-se avaliação especializada.',
            'recomendacoes_professores': 'Aplicar estratégias pedagógicas diversificadas e observar resposta do aluno.',
            'reforco_motivacional': 'Utilizar reforços positivos e reconhecer esforços individuais.',
            'tipo_perfil': 'indefinido'
        }
    
    def formatar_relatorio_detalhado(self, dados_json: Dict[str, Any], nome_aluno: str = "", serie: str = "") -> str:
        """Formata relatório detalhado e legível"""
        
        # Cabeçalho
        relatorio = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                        RELATÓRIO DE NEURODIVERGÊNCIA                        ║
║                          Sistema NeuroLearn v2.0                            ║
╚══════════════════════════════════════════════════════════════════════════════╝

📊 INFORMAÇÕES GERAIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👤 Aluno: {nome_aluno if nome_aluno else 'Nome não informado'}
📚 Série/Ano: {serie if serie else 'Não informado'}
📅 Data do Relatório: {datetime.now().strftime('%d/%m/%Y às %H:%M')}
🏷️  Tipo de Perfil: {self._obter_tipo_perfil_formatado(dados_json.get('tipo_perfil', 'indefinido'))}

🎯 PERFIL GERAL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{self._formatar_texto(dados_json.get('perfil_geral', 'Não disponível'))}

✨ POTENCIAIS EXPRESSIVOS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{self._formatar_texto(dados_json.get('potenciais_expressivos', 'Não identificados'))}

🧠 POTENCIAIS COGNITIVOS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{self._formatar_texto(dados_json.get('potenciais_cognitivos', 'Não identificados'))}

🔍 INDÍCIOS DE NEURODIVERGÊNCIAS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{self._formatar_texto(dados_json.get('indicios_neurodivergencias', 'Não identificados'))}

👨‍🏫 RECOMENDAÇÕES PARA PROFESSORES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{self._formatar_lista_estrategias(dados_json.get('recomendacoes_professores', 'Nenhuma recomendação específica'))}

💪 ESTRATÉGIAS DE REFORÇO MOTIVACIONAL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{self._formatar_lista_estrategias(dados_json.get('reforco_motivacional', 'Estratégias padrão de motivação'))}

⚠️  OBSERVAÇÕES IMPORTANTES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Este relatório é baseado em análise computacional e deve ser complementado
  por observação pedagógica e, se necessário, avaliação especializada.
• Os indícios de neurodivergência requerem confirmação profissional.
• As estratégias sugeridas devem ser adaptadas ao contexto escolar específico.

───────────────────────────────────────────────────────────────────────────────
Gerado pelo Sistema NeuroLearn - Equipe Control + Amizade
📧 Para dúvidas técnicas, contate: suporte@neurolearn.com
───────────────────────────────────────────────────────────────────────────────
"""
        return relatorio
    
    def _obter_tipo_perfil_formatado(self, tipo_perfil: str) -> str:
        """Obtém versão formatada do tipo de perfil"""
        tipo_limpo = tipo_perfil.lower().strip()
        return self.tipos_perfil_map.get(tipo_limpo, f"🔄 {tipo_perfil.title()}")
    
    def _formatar_texto(self, texto: str) -> str:
        """Formata texto com quebras de linha adequadas"""
        if not texto or texto.strip() == "":
            return "• Informação não disponível"
        
        # Quebrar linhas longas
        linhas = texto.split('\n')
        texto_formatado = ""
        
        for linha in linhas:
            if len(linha) > 78:
                palavras = linha.split(' ')
                linha_atual = ""
                for palavra in palavras:
                    if len(linha_atual + palavra) > 78:
                        texto_formatado += linha_atual.strip() + "\n"
                        linha_atual = "  " + palavra + " "
                    else:
                        linha_atual += palavra + " "
                texto_formatado += linha_atual.strip() + "\n"
            else:
                texto_formatado += linha + "\n"
        
        return texto_formatado.strip()
    
    def _formatar_lista_estrategias(self, texto: str) -> str:
        """Formata texto como lista de estratégias"""
        if not texto or texto.strip() == "":
            return "• Nenhuma estratégia específica identificada"
        
        # Se já contém bullets ou números, manter formatação
        if '•' in texto or re.search(r'\d+\.', texto):
            return self._formatar_texto(texto)
        
        # Se é um texto corrido, tentar quebrar em estratégias
        frases = re.split(r'[.;]', texto)
        estrategias = []
        
        for frase in frases:
            frase = frase.strip()
            if len(frase) > 10:  # Ignorar frases muito curtas
                estrategias.append(f"• {frase.capitalize()}")
        
        if estrategias:
            return "\n".join(estrategias)
        else:
            return f"• {texto}"
    
    def gerar_relatorio_resumido(self, dados_json: Dict[str, Any]) -> Dict[str, str]:
        """Gera versão resumida do relatório para exibição rápida"""
        return {
            'tipo_perfil': self._obter_tipo_perfil_formatado(dados_json.get('tipo_perfil', 'indefinido')),
            'principais_potenciais': self._extrair_principais_pontos(dados_json.get('potenciais_cognitivos', '')),
            'indicios_principais': self._extrair_principais_pontos(dados_json.get('indicios_neurodivergencias', '')),
            'recomendacao_prioritaria': self._extrair_primeira_recomendacao(dados_json.get('recomendacoes_professores', ''))
        }
    
    def _extrair_principais_pontos(self, texto: str, max_chars: int = 150) -> str:
        """Extrai os principais pontos de um texto longo"""
        if not texto or len(texto) <= max_chars:
            return texto
        
        # Pegar primeira frase ou até o primeiro ponto
        primeira_parte = texto.split('.')[0] + '.'
        if len(primeira_parte) <= max_chars:
            return primeira_parte
        
        # Se ainda for muito longo, cortar e adicionar reticências
        return texto[:max_chars-3] + "..."
    
    def _extrair_primeira_recomendacao(self, texto: str) -> str:
        """Extrai a primeira recomendação do texto"""
        if not texto:
            return "Observar padrões de aprendizagem do aluno"
        
        # Se contém bullets, pegar o primeiro
        if '•' in texto:
            partes = texto.split('•')
            if len(partes) > 1:
                return partes[1].split('\n')[0].strip()
        
        # Se contém números, pegar o primeiro
        if re.search(r'1\.', texto):
            partes = re.split(r'\d+\.', texto)
            if len(partes) > 1:
                return partes[1].split('\n')[0].strip()
        
        # Caso contrário, pegar primeira frase
        primeira_frase = texto.split('.')[0] + '.'
        return primeira_frase if len(primeira_frase) < 100 else primeira_frase[:97] + "..."
    
    def salvar_relatorio_arquivo(self, relatorio_texto: str, nome_arquivo: str = None) -> str:
        """Salva relatório em arquivo de texto"""
        if not nome_arquivo:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            nome_arquivo = f"relatorio_neurodivergencia_{timestamp}.txt"
        
        try:
            with open(nome_arquivo, 'w', encoding='utf-8') as arquivo:
                arquivo.write(relatorio_texto)
            return nome_arquivo
        except Exception as e:
            print(f"Erro ao salvar arquivo: {e}")
            return ""

# Função de conveniência para uso direto
def filtrar_relatorio_json(json_texto: str, nome_aluno: str = "", serie: str = "") -> str:
    """Função de conveniência para filtrar relatório JSON"""
    filtro = FiltroRelatorioNeurodivergencia()
    dados = filtro.processar_json_bruto(json_texto)
    return filtro.formatar_relatorio_detalhado(dados, nome_aluno, serie)

# Exemplo de uso
if __name__ == "__main__":
    # Exemplo de JSON da IA
    exemplo_json = '''
    {
        "perfil_geral": "O aluno apresenta características compatíveis com alta criatividade e foco seletivo intenso, com algumas dificuldades atencionais em tarefas menos estimulantes.",
        "potenciais_expressivos": "Destaque em atividades criativas, capacidade de pensamento divergente, expressão artística desenvolvida.",
        "potenciais_cognitivos": "Raciocínio lógico-matemático acima da média, excelente memória para assuntos de interesse, capacidade de síntese.",
        "indicios_neurodivergencias": "Possível TDAH do tipo combinado: dificuldades atencionais, hiperatividade mental, mas com hiperfoco em áreas de interesse. Recomenda-se avaliação especializada.",
        "recomendacoes_professores": "Utilizar metodologias ativas. Permitir movimento controlado. Fragmentar tarefas longas. Usar estímulos visuais. Valorizar criatividade.",
        "reforco_motivacional": "Reconhecer conquistas individuais. Permitir escolhas. Conectar conteúdo com interesses. Oferecer desafios graduais.",
        "tipo_perfil": "tdah"
    }
    '''
    
    print("Testando filtro de relatório...")
    relatorio_formatado = filtrar_relatorio_json(exemplo_json, "João Silva", "7º Ano")
    print(relatorio_formatado)

