# Release Status Dashboard

> Última atualização: automática via CI

## Versão Atual

| Campo | Valor |
|-------|-------|
| Versão | `v0.8.0` |
| Status do build | ✅ |
| Último release | `v0.8.0` |
| Último smoke test | ✅ |
| Health score | ⏳ pendente |

## Pipeline

| Job | Status | Última execução |
|-----|--------|----------------|
| Build + Smoke Test | ⏳ | — |
| Instalador | ⏳ | — |
| Publicar Release | ⏳ | — |

## Histórico de Releases

| Versão | Data | Status | Notas |
|--------|------|--------|-------|
| v0.8.0 | 2024-06-30 | ✅ | Documentação + pipeline + release automation |
| v0.7.0 | 2024-03-15 | ✅ | UI completa em PySide6 |
| v0.6.0 | 2024-01-20 | ✅ | Primeira versão funcional |

## Health Score

| Check | Status |
|-------|--------|
| App abre | ⏳ |
| Banco SQLite | ⏳ |
| Migrations | ⏳ |
| Config | ⏳ |
| Logs | ⏳ |
| Anexos | ⏳ |

## Regras de Release

- ✅ Build contract OK → pode gerar instalador
- ✅ Smoke test OK → pode publicar release
- ✅ Instalador validado → pode subir para GitHub
- ❌ Falha no smoke test → **BLOQUEIA** release manual

---

*Dashboard atualizado automaticamente pelo CI.*
