# Deprecation Tracker

Este documento lista funcionalidades, scripts e práticas que estão sendo descontinuadas.

---

## 📋 Deprecações Ativas

| # | Item | Tipo | Status | Deprecado Em | Previsão de Remoção | Substituído Por |
|---|------|------|--------|-------------|---------------------|-----------------|
| 1 | Scripts soltos em `scripts/build/` chamados diretamente | Script | `DEPRECATED` | v0.8.0 | v1.0.0 | `scripts/core/engine.py` via `scripts/ops/control_panel.py` |
| 2 | Scripts soltos em `scripts/release/` chamados diretamente | Script | `DEPRECATED` | v0.8.0 | v1.0.0 | `scripts/core/engine.py` via `scripts/ops/control_panel.py` |
| 3 | Scripts soltos em `scripts/tests/` chamados diretamente | Script | `DEPRECATED` | v0.8.0 | v1.0.0 | `scripts/core/engine.py` via `scripts/ops/control_panel.py` |
| 4 | Lógica de build fora de `scripts/core/engine.py` | Arquitetura | `DEPRECATED` | v0.8.0 | v1.0.0 | `scripts/core/engine.py` |

## 🟢 Removidos

| # | Item | Tipo | Removido Em | Motivo | Substituído Por |
|---|------|------|------------|--------|-----------------|
| — | *Nenhum removido ainda* | | | | |

## ⏳ Em Observação

| # | Item | Motivo | Observação Desde |
|---|------|--------|-----------------|
| — | *Nenhum em observação* | | |

## Regras de Deprecação

1. Um item marcado `DEPRECATED` ainda funciona mas emitirá warning.
2. Um item marcado `REMOVED` foi removido do repositório.
3. Deprecações duram no mínimo um release cycle (minor bump).
4. Remoção só ocorre em major bump (ex: v0.x → v1.0.0).
