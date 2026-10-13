# BUG-0001: BadgeDelegate Segfault

**Status**: Corrigido
**Data**: 2024-03-10

> **Nota de revisão (2026-10):** um dos arquivos citados não existe mais.
> Ver a correção no final.

## Sintoma
Segfault (`0xC0000005`) ao abrir a tela de projeto.

## Causa
`BadgeDelegate("status")` e `BadgeDelegate("priority")` eram criados sem dono
e recebiam `setParent()` apenas depois. Nesse intervalo o objeto Python
existia sem referência, o *shiboken* o coletava, e o `C++`_pointer passava a
apontar para memória liberada. `QStackedWidget.addWidget()` então
desreferenciava memória morta.

## Solução
Criar o delegate já com o pai, ou garantir que nada o descarta entre a
criação e o momento em que entra na hierarquia.

> Não é uma exigência do Qt que todo widget tenha `parent` — ver a ressalva
> em [ADR-005](../adr/ADR-005-BadgeDelegate.md). Diálogos com `parent=None`
> são normais neste projeto.

## Arquivos afetados (no momento da correção)
- `gui/components/badge_delegate.py`
- `gui/views/project_360_qt.py`
- `gui/views/ideas_qt.py`

## Correção factual (2026-10)
- `gui/views/tasks_qt.py`, citado no registro original, **não existe mais** —
  foi removido na etapa de limpeza de código morto (queima de ~484 KB),
  junto com `timeline_canvas.py` e outros arquivos nunca instanciados.
- O componente que o substituiu é `gui/components/drag_drop_tree_qt.py`
  (`DragDropTreeWidget`).