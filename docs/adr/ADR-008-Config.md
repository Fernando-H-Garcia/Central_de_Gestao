# ADR-008: Sistema de Configuração

**Data**: 2024-01-20

## Contexto
App precisa de configurações default + sobrescrita pelo usuário.

## Decisão
`default_config.json` no bundle. Usuário pode sobrescrever em `%LOCALAPPDATA%`.

## Consequências
- Configurações seguras contra atualizações
- Personalização por usuário
