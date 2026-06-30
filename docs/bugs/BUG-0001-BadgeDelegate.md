# BUG-0001: BadgeDelegate Segfault

**Status**: Corrigido
**Data**: 2024-03-10

## Sintoma
Segfault (0xC0000005) ao abrir tela de projeto.

## Causa
`BadgeDelegate("status")` e `BadgeDelegate("priority")` criados com `parent=None`. Shiboken destruía o objeto C++ imediatamente, causando dangling pointer no QStackedWidget::addWidget().

## Solução
Adicionar `parent=self.tbl_tasks` / `parent=self.table` em todos os BadgeDelegates.

## Arquivos afetados
- `gui/views/project_360_qt.py`
- `gui/views/tasks_qt.py`
- `gui/views/ideas_qt.py`
- `gui/components/badge_delegate.py`
