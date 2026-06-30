# ADR-004: Instalador com Inno Setup

**Data**: 2024-01-20

## Contexto
PyInstaller gera pasta avulsa. Necessário instalador Windows.

## Decisão
Inno Setup com script `build/installer.iss`. Inclui VC++ Redist.

## Consequências
- Instalação simplificada (next, next, finish)
- Remoção via Painel de Controle
- VC++ Redist garante funcionamento
