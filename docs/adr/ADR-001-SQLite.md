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
- Sem concorrência multiusuário (limitação aceita)
- Instala em `Program Files` sem permissão de escrita — dados do usuário ficam
  em `%LOCALAPPDATA%` (ver [ADR-002](ADR-002-LOCALAPPDATA.md))

## Correção factual (2026-10)
- O banco se chama **`novo_cerebro.db`**. Documentos antigos citavam `brain.db`,
  nome que não existe no projeto.
- Hoje há **25 arquivos de migration** em `database/migrations/`, com
  `schema_version = 26` no banco. O número salta quando uma migration entrega
  mais de uma versão de schema, então *contagem de arquivos ≠ versão do schema*.
- Varredura nas 27 tabelas (2026-10-13): **nenhuma coluna de usuário,
  proprietário, responsável ou permissão**. A restrição multiusuário não é só
  de concorrência — hoje o modelo de dados não tem como expressar *quem* é o
  dono de um projeto ou o responsável por uma tarefa.

## Planejado

A evolução para vários usuários (Gerente / Desenvolvedor, bancos locais
independentes e compartilhamento seletivo) está em
[`Plano-Multiusuario.md`](../Plano-Multiusuario.md). A etapa 1 (auditoria do
banco) foi concluída e está registrada no próprio plano.

Quando a etapa 2 começar, esta ADR deve ser **revogada por uma nova** — este
registro permanece como a decisão que valia até lá.