# Release Status Dashboard

> Última atualização: automática via CI

## Versão Atual

| Campo | Valor |
|-------|-------|
| Versão | `v0.8.0` |
| Status do build | ✅ |
| Golden Release | `v0.8.0` |
| Último release | `v0.8.0` |
| Último smoke test | ✅ |
| Score médio | ⏳ pendente |
| Última falha | — |

## Engine Status

| Componente | Status |
|------------|--------|
| `scripts/core/engine.py` | ✅ |
| `scripts/core/config_release.py` | ✅ |
| `scripts/core/error_classifier.py` | ✅ |
| `scripts/ops/control_panel.py` | ✅ |
| `scripts/guards/constitution_rules.py` | ✅ |
| `scripts/guards/freeze_check.py` | ✅ |

## Pipeline

| Job | Status | Última execução |
|-----|--------|----------------|
| Build + Smoke Test | ⏳ | — |
| Instalador | ⏳ | — |
| Publicar Release | ⏳ | — |

## Histórico de Releases

| Versão | Data | Status | Score | Notas |
|--------|------|--------|-------|-------|
| v0.8.0 | 2024-06-30 | ✅ | ⏳ | Arquitetura 3 camadas + engine |
| v0.7.0 | 2024-03-15 | ✅ | ⏳ | UI completa em PySide6 |
| v0.6.0 | 2024-01-20 | ✅ | ⏳ | Primeira versão funcional |

## Health Score

| Check | Status |
|-------|--------|
| App abre | ⏳ |
| Banco SQLite | ⏳ |
| Migrations | ⏳ |
| Config | ⏳ |
| Logs | ⏳ |
| Anexos | ⏳ |

## Estabilidade Geral

| Indicador | Valor |
|-----------|-------|
| Estabilidade | 🟢 Estável |
| Builds consecutivos sem falha | ⏳ |
| Última falha classificada | — |
| Erro mais comum | — |

## Regras de Release

- ✅ Build contract OK → pode gerar instalador
- ✅ Smoke test OK → pode publicar release
- ✅ Instalador validado → pode subir para GitHub
- ✅ Golden release protegida contra overwrite
- ❌ Falha no smoke test → **BLOQUEIA** release manual

---

*Dashboard atualizado automaticamente pelo CI.*
