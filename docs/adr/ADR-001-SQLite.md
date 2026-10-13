# ADR-001: Uso do SQLite como Banco de Dados

**Data**: 2024-01-15
**Status**: Vigente

> **Nota de revisão (2026-10):** registro escrito em 2024. As correções
> factuais estão marcadas ao final. Ver a política de datas em [`docs/README.md`](../README.md).

## Contexto
Necessidade de um banco de dados local, embarcado, sem necessidade de servidor.

## Decisão
SQLite é o banco oficial. Migrations versionadas em `database/migrations/`.

## Consequências
- Dados ficam em arquivo único: **`novo_cerebro.db`**
- Backup simples (cópia do arquivo)
- Sem concorrência multiusuário (limitação aceita, ver ADR-009 e Roadmap)
- Instala em `Program Files` sem permissão de escrita — dados do usuário ficam
  em `%LOCALAPPDATA%` (ver [ADR-002](ADR-002-LOCALAPPDATA.md))

## Correção factual (2026-10)
- O banco se chama **`novo_cerebro.db`**. Documentos antigos citavam `brain.db`,
  nome que não existe no projeto.
- Hoje há **25 arquivos de migration** em `database/migrations/`, com
  `schema_version = 26` no banco. O número salta quando uma migration entrega
  mais de uma versão de schema, então *contagem de arquivos ≠ versão do schema*.
- A restrição "sem concorrência multiusuário" **segue valendo**. Não existe
  plano de suporte multiusuário em nenhum documento do repositório — se
  isso mudar, esta ADR precisa ser revogada por uma nova.