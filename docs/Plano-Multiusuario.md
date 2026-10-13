# Plano: Multiusuário

Planejamento da evolução do Central de Gestão para vários usuários, com
bancos locais independentes e compartilhamento seletivo.

## A ideia

Bancos locais independentes, com compartilhamento seletivo de projetos,
tarefas e arquivos, controlado por perfis de usuário. Preserva a ideia
original da Central de Gestão e permite acrescentar colaboração online sem
exigir que todos tenham acesso ao banco inteiro.

Distinção importante: o **Gerente** precisa de acesso a todos os projetos,
enquanto os **Desenvolvedores** mantêm seus projetos privados e acessam
somente o que lhes foi compartilhado.

## 1. Modelo de usuários

### Gerente — acesso global
- Visualiza e abre todos os projetos de todos os usuários
- Consulta tarefas, responsáveis, prazos e progresso
- Cria projetos e tarefas e atribui-os a colaboradores
- Acompanha tarefas sugeridas, aceitas, recusadas ou concluídas
- Administra usuários e permissões

### Desenvolvedor — acesso restrito
- Cria e administra seus próprios projetos
- Cria, edita e organiza suas tarefas
- Sugere tarefas para outros colaboradores
- Visualiza tarefas e projetos compartilhados com ele
- Consulta os arquivos autorizados para cada compartilhamento
- Não abre projetos privados de outros desenvolvedores

### Propriedade ≠ permissão

Um projeto pertence a quem o criou ou a quem foi designado como proprietário,
mas o Gerente pode acessá-lo independentemente dessa propriedade.

Isso evita que transferir uma tarefa para alguém transfira, por acidente, a
propriedade do projeto inteiro.

## 2. Sugestão de tarefa

Cenário: o **Desenvolvedor A**, no projeto "Central de Gestão", cria a tarefa
"Implementar sincronização de anexos" e a sugere para o **Desenvolvedor B**.

São compartilhados a descrição, os critérios de conclusão, o prazo e os
anexos autorizados. O estado fica **Aguardando resposta**, e o projeto
original continua privado.

- **Aceitar** → a tarefa entra na lista de trabalho do B e passa a receber
  atualizações
- **Recusar** → o remetente é notificado e a tarefa continua sob controle do
  proprietário original

### Ciclo de vida próprio

A sugestão não é uma transferência definitiva. Estados:

```
Rascunho → Sugerida → Aceita → Em andamento → Concluída
              ↓           ↓
          Recusada    Cancelada
```

O Desenvolvedor B **não** recebe acesso ao projeto original. Recebe uma
representação compartilhada da tarefa, vinculada à tarefa de origem por um
identificador único. O Gerente acompanha tanto a original quanto o trabalho
delegado.

## 3. Como organizar os bancos de dados

Evitar um único arquivo SQLite compartilhado diretamente por torrent. Cada
computador tem sua própria base local, com os dados que aquele usuário está
autorizado a acessar.

```
Camada de sincronização  →  Identidades, permissões, eventos, notificações, controle de versões
Banco do Gerente         →  Todos os projetos
Banco do Desenvolvedor   →  Projetos próprios e dados compartilhados
```

### Conceitos de modelo de dados

| Entidade | Finalidade |
|---|---|
| `users` | Identidade, perfil e estado da conta |
| `projects` | Projeto, proprietário e metadados |
| `project_permissions` | Usuários com acesso a cada projeto e nível de permissão |
| `tasks` | Tarefas originais, responsáveis e status |
| `task_shares` | Relação entre tarefa de origem, destinatário e tarefa compartilhada |
| `sync_events` | Registro de alterações pendentes de sincronização |
| `attachments` | Metadados, localização, integridade e permissões |

> Nomes conceituais, **não** indicação de que seja preciso recriar tabelas que
> já existam no banco atual. Ver a auditoria abaixo.

### Regra de segurança

Não basta esconder projetos na interface. Cada operação de leitura ou escrita
deve validar as permissões, e o banco local de um Desenvolvedor **não deve
receber** os dados privados dos demais projetos.

## 4. Anexos e links

Tratado separadamente do banco, preservando o mecanismo de links já existente
(`[[ ]]` e `{{ }}`) e acrescentando uma camada de compartilhamento.

Um anexo passa a ter três componentes:

- **Referência** — o caminho ou link já armazenado no projeto
- **Identidade do arquivo** — identificador único e hash para verificar que o
  conteúdo recebido corresponde ao original
- **Permissões** — quem pode visualizar ou baixar

Quando uma tarefa é compartilhada, o sistema avalia quais anexos podem
acompanhá-la. O link original continua funcionando para o proprietário; o
destinatário recebe uma referência acessível dentro das permissões dele.

⚠️ Se o link apontar para um arquivo que só existe no computador do remetente,
**ele não será acessível automaticamente**. Será preciso disponibilizar o
arquivo por sincronização P2P, torrent ou outro mecanismo de transferência.

Sobre torrent para arquivos grandes, dois cuidados:

1. Os arquivos precisam ser distribuídos **apenas aos destinatários autorizados**
2. O torrent **não substitui** a gestão de permissões, a revogação de acesso
   nem a sincronização dos metadados

## 5. Etapas de implementação

Preservando o funcionamento do Central de Gestão atual.

| # | Etapa | Estado |
|---|---|---|
| 1 | Auditar o banco existente: tabelas, relacionamentos, formato dos anexos, forma como os links são armazenados | ✅ Feito — ver abaixo |
| 2 | Implementar usuários e permissões: Gerente, Desenvolvedor, propriedade de projetos e acesso seletivo | ⬜ Pendente |
| 3 | Implementar compartilhamento de tarefas: convite, aceite, recusa, atualização e conclusão | ⬜ Pendente |
| 4 | Implementar sincronização: envio de alterações, controle de versões, deduplicação e resolução de conflitos | ⬜ Pendente |
| 5 | Integrar anexos: reutilizar os links existentes e adicionar transferência segura | ⬜ Pendente |
| 6 | Avaliar o transporte P2P: conectividade entre redes, computadores offline, distribuição de arquivos | ⬜ Pendente |

## A decisão mais importante

Definir o que significa o Gerente ter acesso a todos os projetos: isso precisa
funcionar **mesmo quando o computador de um Desenvolvedor estiver desligado**.

Se o Gerente deve sempre conseguir abrir qualquer projeto, será preciso uma
**cópia sincronizada dos dados de todos os projetos no ambiente dele**, ou algum
serviço persistente que os disponibilize. Um torrent isolado **não garante essa
disponibilidade**.

Esta é a pergunta a responder antes da etapa 2.

---

# Auditoria (etapa 1) — 2026-10-13

Verificada no banco real (`database/novo_cerebro.db`, modo leitura).

## Estado atual: 27 tabelas

```
activity_logs  agenda_items  alerts  attachments  entity_links
events  global_search*  idea_tags  ideas  knowledge_page_tags
knowledge_pages  notes  project_tags  projects  schema_version
settings  tags  task_deadlines  task_dependencies  task_tags  tasks
user_capacity
```

## Achado principal: não existe nenhuma noção de usuário

Varredura nas 27 tabelas procurando colunas com `user`, `owner`, `assign`,
`respons`, `permiss`, `role`, `author`:

> **NENHUMA ocorrência.**

Isso significa que hoje:
- Não há como saber **quem criou** um projeto
- Não há **responsável** atribuído a uma tarefa
- Não há proprietário, permissão ou papel

**Atenção ao falso positivo:** a tabela `user_capacity` **não** é sobre
usuários — é `id, date, available_hours, created_at`, usada para planejamento
de capacidade de horas. O nome engana.

### Impacto na etapa 2
As entidades `users`, `project_permissions` e `task_shares` não adapts
existentes — serão structs novas. Mas `projects` e `tasks` precisam ganhar
colunas de vínculo (`owner_id`, `assignee_id`) sem quebrar o que já existe.

## O que já está pronto

| Conceito do plano | Estado atual |
|---|---|
| Identidade de arquivo (`uuid`) | ✅ Já existe em `projects`, `tasks`, `attachments` |
| Integridade de arquivo (`checksum`) | ✅ Já existe em `attachments` |
| Localização do anexo (`file_path`) | ✅ Já existe em `attachments` |
| Vínculo anexo ↔ entidade | ✅ `attachments.entity_type` + `entity_id` |
| Links entre entidades | ✅ `entity_links` (`source_type`/`source_id`/`target_type`/`target_id`) |
| Metadados de wiki/anexos | ✅ `knowledge_pages`, `attachments` |

Ou seja: a **identidade e a integridade do anexo já existem** — a etapa 5
precisa acrescentar permissões e transporte, não reinventar identidade.

## Estruturas relevantes

```sql
projects    : id, uuid, name, objective, priority, health_status, status,
              is_favorite, is_archived, archived_at, deleted_at, created_at,
              completed_at, due_date, alert_date, originated_from_idea_id
              -- (sem owner_id / created_by)

tasks       : id, uuid, parent_task_id, project_id, title, context,
              energy_level, status, position, is_archived, deleted_at,
              due_date, created_at, completed_at, estimated_hours,
              is_milestone, start_date, estimated_deadline,
              estimated_deadline_desc
              -- (sem assignee_id / responsible_id)

attachments : id, uuid, entity_type, entity_id, file_path, file_name,
              mime_type, file_size, checksum, deleted_at, created_at

entity_links: id, source_type, source_id, target_type, target_id,
              relationship_type, created_at
```

## Achado lateral: a "pesquisa unificada" já tem base

Existe uma tabela `global_search` (`entity_type`, `entity_id`, `title`,
`content`) com tabelas FTS5 de apoio (`global_search_content`,
`global_search_idx`, `global_search_docsize`, `global_search_data`).

Isto é relevante para o outro lembrete em aberto (mecanismo único de
pesquisa): a infraestrutura de busca centralizada já existe e foipopulate.

## Nada foi alterado nesta auditoria

Auditoria de leitura. Nenhuma migration criada, nenhuma tabela modificada.