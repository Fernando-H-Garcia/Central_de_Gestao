# ADR-009: EventBus para Comunicação entre Views

**Data**: 2024-02-01
**Status**: Vigente

## Contexto
Views precisam reagir a mudanças feitas em outras views sem acoplamento
direto entre elas.

## Decisão
EventBus singleton (`core/event_bus.py`) com `emit()` / `subscribe()`,
usando `QTimer` para flush diferido.

## Consequências
- Desacoplamento entre views
- Views assinam no `__init__` e desassinam no `destroyed`

## Comportamento que exige cuidado (2026-10)

### 1. `emit` é assíncrono
O `emit` agrupa os eventos pendentes e despacha num `QTimer` de **16 ms**.
**Não assuma atualização síncrona logo após o `emit`.**

Handler que precisa de refresh imediato precisa fazer o `load_data()` local,
além de receber o evento:

```python
def _on_something(self, *_):
    self.load_data()          # imediato
    # o event_bus chega depois, para as outras views
```

### 2. `emit("entity_updated")` sem payload chega como `data=None`
Handlers precisam tolerar isso. Use `safe_load_data(_=None)`, ou aceite
`data=None` na assinatura.

### 3. View sem subscription fica congelada
Sintoma: edita algo numa tela e outra tela (já aberta) não muda. Causa: a view
nunca assinou `entity_updated`. **Toda view de topo precisa assinar
`snapshot_updated` + `entity_updated`**, e desassinar no `destroyed`.

Views que assinam hoje: `tasks_qt`, `projects_qt`, `project_360_qt`,
`task_detail_qt`, `agenda_qt`, `activity_summary_qt`, `workbench_qt`,
`ideas_qt`, `notes_qt`, `wiki_qt` (só `snapshot_updated`).

### 4. Views em cache ficam ocultas e continuem disparando
Views em cache (`_project_views`, `_task_views`) continuam "vivas" quando
ocultas. Sem guarda de `isVisible()`, uma view escondida dispara popup de
alarme ou recarrega em background. Foi exatamente o que aconteceu com o
popup de alarmes.

### 5. Repo direto não notifica
Os **services** notificam. Atualizações feitas **direto no repositório** não:
`alert_repo.update`, `page_repo.update`, `deadline_repo.update`,
`ActivityLogRepository`. Ou use o service, ou emita manualmente:

```python
notify_entity_updated(entity_type, id, action)
```

Foi a causa raiz de "arrastei na timeline, gravei no banco, e a tela de
Tarefas continuou mostrando a data antiga".

### 6. O snapshot do `data_context` está morto
`core/snapshot_worker.py` nunca é iniciado e `request_reload()` não é chamado
de lugar nenhum. `get_snapshot()` devolve um snapshot vazio, e os getters caem
no fallback do repositório — por isso os dados aparecem certos.

**Consequência perigosa:** se alguém iniciar o worker, as views passam a ler
um snapshot velho e a persistência de drag/dialog passa a não aparecer. Se
for fazer isso, invalide o snapshot a cada `entity_updated` primeiro.