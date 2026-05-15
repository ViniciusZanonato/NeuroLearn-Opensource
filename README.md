# NeuroLearn OpenSource

Sistema Flask para apoiar educadores na identificacao de perfis de aprendizagem e possiveis indicadores de neurodivergencia a partir de questionarios, atividades e relatorios com IA.

## Funcionalidades

- Cadastro e login de professores e alunos.
- Questionario NeuroLearn com 67 questoes em 7 dimensoes.
- Geracao de perfil de aprendizagem com Google Gemini.
- Dashboard do educador com atividades, alunos e leitura pedagogica.
- Dashboard do aluno com privacidade: hipoteses completas ficam restritas ao professor.
- Relatorios e filtros para leitura pedagogica.
- Configuracoes de acessibilidade.

## Stack

- Python + Flask
- Flask-SQLAlchemy
- SQLite local
- Jinja2 templates
- CSS proprio baseado no design system editorial da pasta local `Design/`
- IA local via Ollama por padrao

## Estrutura

```text
.
├── app.py
├── filtro_relatorio_neurodivergencia.py
├── init_db.py
├── iniciar_servidor.py
├── requirements.txt
├── static/
│   ├── logo.jpg
│   └── neurolearn.css
└── templates/
```

Arquivos locais como banco SQLite, caches Python e a pasta `Design/` ficam fora do versionamento.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python init_db.py
python iniciar_servidor.py
```

O app roda em:

```text
http://127.0.0.1:5000
```

## Variaveis de ambiente

Configure no `.env`:

```text
SECRET_KEY=troque-esta-chave
GEMINI_API_KEY=sua-chave-gemini
```

Por padrao, o NeuroLearn usa Ollama local para evitar envio de dados sensiveis de alunos a servicos externos:

```text
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=gemma3:12b
```

Antes de usar IA, inicie o Ollama e instale um modelo instruction-tuned adequado ao hardware:

```bash
ollama pull gemma3:12b
```

Se o computador nao tiver memoria suficiente, use um modelo menor e ajuste `OLLAMA_MODEL`.

O Gemini continua disponivel apenas como opcional, definindo `AI_PROVIDER=gemini` e `GEMINI_API_KEY`. Use isso somente se a politica de privacidade da escola permitir envio externo de dados.

Importante: a IA gera hipoteses pedagogicas e recomendacoes de apoio. Ela nao substitui avaliacao clinica, diagnostico profissional ou decisao pedagogica humana.

## Repositorio

Repositorio publico limpo:

```text
https://github.com/ViniciusZanonato/NeuroLearn-Opensource
```
