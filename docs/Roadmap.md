# Roadmap

Estado verificado em **2026-10-13**.

## Concluído

- [x] MVP funcional
- [x] Pipeline de build (PyInstaller one-file + Inno Setup)
- [x] Instalador Windows
- [x] Migrations SQL versionadas (25 arquivos, schema v26)
- [x] EventBus e Repository pattern
- [x] Wiki com `[[` / `{{`, anexos e links clicáveis
- [x] Timeline / Gantt (Planning) com barra arrastável, zoom e prazos
- [x] Design System: fonte única de verdade visual, componentes reutilizáveis
- [x] Testes automatizados (16 suítes)
- [x] Build validado: EXE 46,1 MB · instalador 70,1 MB · EXE executado

## Em andamento

- [ ] **Parte 2 — refactor de Design System, sequência** (branch
      `feature/design-system-refactor`)
  - Sprint 1: Design System (cores, tipografia, espaçamentos) — feito
  - Sprints 2–5: componentes reutilizáveis, barra lateral, cabeçalhos,
    cards de indicadores
- [ ] **Multiusuário** — plano completo em
      [`Plano-Multiusuario.md`](Plano-Multiusuario.md)
  - Etapa 1 (auditoria do banco) — ✅ feita
  - Etapas 2–6 (usuários/permissões, compartilhamento de tarefas,
    sincronização, anexos, transporte P2P) — ⬜ pendentes
  - **Bloqueio de decisão:** o Gerente precisa abrir qualquer projeto
    mesmo com o PC do Desenvolvedor desligado? Isso define se precisa de
    cópia sincronizada total ou de serviço persistente

## Pendente

- [ ] **Pesquisa unificada** — um só mecanismo para listas, documentos e
      autocomplete `[[` / `{{`
- [ ] **Ajuste no campo "Filtrar"** (instruções a definir)
- [ ] **Instalador validado em máquina limpa** (build validado, instalação não)
- [ ] GitHub Actions executando de fato (os workflows existem, mas nunca
      rodaram neste repositório)
- [ ] Tema claro/escuro
- [ ] Pre-commit hook instalado (as regras existem em `scripts/guards/`, mas o
      hook não está em `.git/hooks/`)

## Não planejado

> **Atualizado 2026-10-13:** multiusuário **passou a ter plano próprio** em
> [`Plano-Multiusuario.md`](Plano-Multiusuario.md). O
> [ADR-001](adr/ADR-001-SQLite.md) segue registrando "sem concorrência
> multiusuário" como a decisão atual — ela só será revogada quando a etapa 2
> começar.

## Dívidas técnicas conhecidas

| Item | Onde |
|---|---|
| Aviso de versão do Python invertido (espera 3.12, exige 3.11) | `scripts/build/build_release.py` |
| `snapshot_worker.py` nunca iniciado; risco se alguém iniciar | `core/snapshot_worker.py` |
| `NotesQt` nunca instanciada (código morto) | `gui/views/notes_qt.py` |
| `cleanup_dlls.py` órfão (não é executado) | `scripts/build/templates/` |
| Golden Release documentada, não implementada | [`Release.md`](Release.md) |

Detalhes em [`DEPRECATION.md`](DEPRECATION.md).