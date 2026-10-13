# ADR-005: BadgeDelegate para Status e Prioridade

**Data**: 2024-03-10
**Status**: Vigente, com ressalva

> **Nota de revisão (2026-10):** ver a ressalva no final — a explicação
> original atribuía ao Qt uma exigência que ele não tem.

## Contexto
Status e prioridade precisavam de indicadores visuais coloridos em tabelas,
com mais controle do que um `QStyledItemDelegate` padrão oferece.

## Decisão
`QStyledItemDelegate` personalizado (`gui/components/badge_delegate.py`) para
desenhar badges coloridos, **sempre instanciado com `parent` explícito**.

## Consequências
- Cores padronizadas por tipo (status, prioridade, saúde)
- O crash de `parent=None` foi corrigido

## Ressalva importante (2026-10)

A documentação original dizia que `parent=None` **causava** o segfault, como se
fosse uma exigência do Qt. Não é. O que aconteceu foi um problema de
**ciclo de vida**:

O delegate era criado e só passava a ter referência (o `QTableWidget`) depois,
via um `setParent()` tardio. Entre a criação e o `setParent()`, o objeto Python
existia sem dono, o *shiboken* o coletava, e o `C++`_pointer ficava
apontando para memória liberada. O `QStackedWidget.addWidget()` então
desreferenciava memória morta.

Portanto:

- **Não** é que "todo widget precisa de parent explícito". Diálogos e widgets
  sem dono são perfectly normais no Qt.
- **É** que um objeto native do Qt não pode ficar sem dono entre o momento em
  que é criado e o momento em que passa a fazer parte de uma hierarquia viva.
  Crie-o já com o pai, ou garanta que nada o descarta nesse intervalo.

`parent=None` continua sendo o padrão correto para a maioria dos widgets deste
projeto — inclusive nos diálogos, que recebem o pai no construtor.