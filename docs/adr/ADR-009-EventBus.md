# ADR-009: EventBus para Comunicação entre Views

**Data**: 2024-02-01

## Contexto
Views precisam reagir a mudanças em outras views sem acoplamento direto.

## Decisão
EventBus singleton com `emit`/`subscribe`. Usa QTimer para flush diferido.

## Consequências
- Desacoplamento total entre views
- Eventos podem ser perdidos se subscription for tarde demais
