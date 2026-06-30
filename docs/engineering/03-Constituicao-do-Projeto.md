# Constituição do Projeto

## Métricas

- 110 arquivos `.py`
- 19 migrations SQL
- 22.898 linhas de código
- Framework: PySide6 6.6.3.1

## Regras Proibidas (Hard Rules)

Estas regras não podem ser quebradas em nenhuma circunstância:

### Build e Empacotamento
- ❌ **Proibido alterar Services para resolver build**
  - Problema de build se resolve no `build.spec` ou ambiente, nunca na lógica de negócio
- ❌ **Proibido mexer em lógica de negócio para empacotamento**
  - Nada de `if getattr(sys, 'frozen', False)` para desviar fluxo
- ❌ **Proibido rodar build fora do ambiente oficial**
  - Ambiente oficial: Python 3.12.1 puro + PySide6 6.6.3.1 + PyInstaller 6.21.0
  - Build feito com Conda ou versão diferente de Qt é **inaceitável**

### Dependências
- ❌ **Proibido adicionar dependências sem registrar ADR**
  - Toda nova dependência externa precisa de ADR documentando:
    - Por que é necessária
    - Alternativas consideradas
    - Impacto no tamanho do bundle
- ❌ **Proibido remover dependências do `build.spec` sem validação**
  - Hidden imports só podem ser removidos após build + teste confirmarem que não são necessários

### Versionamento e Release
- ❌ **Proibido liberar versão sem checklist completo**
  - Release só acontece com ReleaseChecklist.md 100% preenchido
- ❌ **Proibido pular fases do processo de release**
  - As 4 fases (preparação, build, validação, publicação) são obrigatórias
- ❌ **Proibido fazer commit diretamente na main sem PR**
  - Toda mudança na main passa por pull request

### Código
- ❌ **Proibido expor tokens, senhas ou credenciais em logs ou commits**
  - `app_errors.log` só captura exceções, nunca dados sensíveis
- ❌ **Proibido desabilitar tratamento de erros para "testar rapidamente"**
  - Todo bloco `try/except` tem propósito definido, nunca `except: pass` genérico
- ❌ **Proibido usar parent=None em widgets Qt**
  - Todo widget deve ter parent explícito para evitar dangling pointer

### Documentação
- ❌ **Proibido criar documentação sem revisão de engenharia**
  - docs/engineering/ só contém documentação revisada e aprovada
- ❌ **Proibido remover ADRs**
  - ADRs são imutáveis depois de aprovados. Erros viram novo ADR ou BUG

## Consequências da violação

Violação de qualquer Hard Rule resulta em:
1. Reversão imediata do commit
2. Revisão de impacto
3. Atualização da documentação afetada
4. Registro no docs/bugs/ se aplicável
