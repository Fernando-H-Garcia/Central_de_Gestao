# Change Classification System

Todo commit no Central de Gestão DEVE ser classificado com um dos tipos abaixo.

## Tipos Obrigatórios

| Tipo | Descrição | Exemplo |
|------|-----------|---------|
| **FIX** | Correção de bug | `FIX: crash ao abrir wiki sem paginas` |
| **FEATURE** | Nova funcionalidade | `FEATURE: adiciona filtro por data na agenda` |
| **REFACTOR** | Refatoração sem mudança de comportamento | `REFACTOR: extrai validate_bundle() para modulo separado` |
| **BUILD** | Mudança no pipeline de build, CI, instalador | `BUILD: adiciona step de smoke test no CI` |
| **RISKY** | Mudança de alto risco (review obrigatória) | `RISKY: substitui SQLite por PostgreSQL` |
| **BREAKING** | Mudança incompatível com versões anteriores | `BREAKING: remove suporte a Python 3.11` |
| **docs** | Documentação | `docs: atualiza Release Checklist` |
| **chore** | Tarefas de manutenção | `chore: atualiza .gitignore` |

## Regras

1. **Todo commit** precisa de classificação no início da mensagem
2. **Commits sem classificação** geram warning no CI (Constitution Check)
3. **BREAKING** requer:
   - Aprovação de 2 revisores
   - ADR documentando a mudança
   - Atualização do CHANGELOG com breaking changes
4. **RISKY** requer:
   - Code review obrigatório
   - Smoke test completo antes do merge
   - Nota no commit descrevendo o risco

## Exemplos

```
FEATURE: adiciona exportacao CSV na tela de projetos
FIX: corrige segfault ao fechar alarm popup
REFACTOR: centraliza logica de conexao com banco
BUILD: adiciona job de instalador no CI
RISKY: migra de SQLite para PostgreSQL
BREAKING: remove campo 'categoria' do modelo de tarefas
docs: atualiza Build Contract com novos criterios
chore: limpa imports nao utilizados
```

## Formato

```
TIPO[(escopo)]: descricao

Opcional: corpo com detalhes
```

Exemplo com escopo:
```
FIX(wiki): parent combo nao listava paginas arquivadas
```

## Ferramentas

O pre-commit hook valida que o commit tem classificação.
O CI (Constitution Check) valida em PRs.
