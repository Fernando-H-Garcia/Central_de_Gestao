# ADR-005: BadgeDelegate para Status e Prioridade

**Data**: 2024-03-10

## Contexto
Status e prioridade precisavam de indicadores visuais coloridos em tabelas.

## Decisão
`QStyledItemDelegate` personalizado para desenhar badges coloridos. Parent explícito para evitar dangling pointer.

## Consequências
- Segfault corrigido (parent=None causava crash)
- Cores padronizadas por tipo
