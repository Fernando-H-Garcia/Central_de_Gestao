# Documentação

Documentação técnica do Central de Gestão.

Todos os fatos foram verificados no código em **2026-10-13**.

## Ponto de partida

| Preciso de | Ver |
|---|---|
| **Compilar / gerar instalador** | [`BUILD.md`](BUILD.md) |
| **Publicar uma versão** | [`Release.md`](Release.md) |
| **Entender a estrutura** | [`Arquitetura.md`](Arquitetura.md) |
| **Rodar / escrever testes** | [`Testes.md`](Testes.md) |
| **Regras que não posso quebrar** | [`Composicao-do-Projeto.md`](Composicao-do-Projeto.md) |
| **Saber o que fazer depois** | [`Roadmap.md`](Roadmap.md) |

## Conteúdo

| Documento | Assunto |
|---|---|
| [`Arquitetura.md`](Arquitetura.md) | Camadas, fluxo de boot, banco, Qt, timeline, métricas |
| [`Ambiente-e-Estrutura.md`](Ambiente-e-Estrutura.md) | Ambiente oficial de build, pastas, config, caminhos de dados |
| [`BUILD.md`](BUILD.md) | Procedimento de build passo a passo |
| [`Release.md`](Release.md) | Release em 4 fases, validação e rollback |
| [`Testes.md`](Testes.md) | Suítes, regras de isolamento de banco, cobertura |
| [`Composicao-do-Projeto.md`](Composicao-do-Projeto.md) | Hard rules, versionamento, branches, commits |
| [`DEPRECATION.md`](DEPRECATION.md) | O que está em desuso e o que substitui |
| [`Roadmap.md`](Roadmap.md) | Estado do projeto e pendências |

## ADRs e BUGs

- [`adr/`](adr/) — Architecture Decision Records (imutáveis; desatualizado =
  marcado **Superado**, nunca editado em silêncio)
- [`bugs/`](bugs/) — registro de bugs e correções
- [`templates/`](templates/) — modelos para novos ADRs, bugs, checklists e releases
- [`diagrams/`](diagrams/) — diagramas `.drawio` (arquitetura, banco, build, fluxo, release)

## Três coisas que já erraram nesta documentação

Vale ler antes de confiar em qualquer número aqui:

1. **Versão do Python.** A documentação dizia **3.12**. O correto é
   **3.11** — 3.12+ quebra o PySide6 6.6. Veja
   [BUG-0002](bugs/BUG-0002-DLL-Mismatch.md).

2. **Modo do build.** A documentação dizia **one-folder** com pasta
   `_internal/` e ~300 MB. O correto é **one-file**, um único `.exe` de
   **46,1 MB**. Veja [ADR-011](adr/ADR-011-OneFile.md).

3. **Nome do banco.** A documentação dizia `brain.db`. O correto é
   **`novo_cerebro.db`**. Veja [ADR-001](adr/ADR-001-SQLite.md).

### Duas regras para não repetir

- **Número fixo vira errado.** Não escreva "20 migrations"; escreva "consulte
  `schema_version`". Hoje são 25 arquivos e schema v26.
- **Datas de registro não são datas do projeto.** Os ADRs e BUGs são de 2024,
  quando a documentação foi gerada em bloco. Os fatos posteriores à escrita
  estão marcados com "Nota de revisão (2026-10)". Trate o corpo do documento
  como o registro original e a nota como a correção.