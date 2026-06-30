# BUG-0004: Wiki - Comportamentos Incorretos

**Status**: Corrigido
**Data**: 2024-03-15

## Sintomas
- Parent combo não listava todas as páginas
- Label "Tamanho:" com fundo preto
- Drag-drop de anexos não funcionava
- Ideias não apareciam após criação

## Causas
- Stale current_id filter no combo
- Estilo CSS ausente
- QEvent.DragMove não tratado
- handle_save sem try/except

## Solução
- `_populate_parent_combo()` extraído como método e chamado em load_pages + _open_page
- Style adicionado
- DragMove adicionado ao eventFilter
- Tratamento de erro no save de ideias
