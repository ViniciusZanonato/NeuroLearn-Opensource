# Politica de IA Local do NeuroLearn

O NeuroLearn usa `AI_PROVIDER=ollama` por padrao para manter prompts e dados de alunos no computador/servidor da escola.

## Modelo recomendado

- Padrao: `gemma3:12b`
- Alternativa para hardware mais fraco: ajuste `OLLAMA_MODEL` para um modelo instruction-tuned menor disponivel no Ollama.

O modelo precisa ser instruction-tuned e validado localmente pela equipe antes de uso real com alunos. O sistema nao afirma diagnosticos; ele produz hipoteses pedagogicas para revisao humana.

## Regras de seguranca

- Nao enviar dados de alunos para provedores externos por padrao.
- Nao produzir laudos ou diagnosticos clinicos.
- Sempre tratar resultados como indicadores observacionais.
- Revisao humana obrigatoria por professor/coordenacao.
- Encaminhamento profissional quando houver necessidade clinica.

## Como instalar o modelo padrao

```bash
ollama pull gemma3:12b
```

Depois, mantenha o Ollama rodando em:

```text
http://127.0.0.1:11434
```
