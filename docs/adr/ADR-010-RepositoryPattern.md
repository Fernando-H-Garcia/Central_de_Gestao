# ADR-010: Repository Pattern

**Data**: 2024-01-15

## Contexto
Acesso a dados precisa ser testável e desacoplado do SQL bruto.

## Decisão
Repository pattern: `BaseRepository` com métodos CRUD genéricos, repositórios específicos por entidade.

## Consequências
- Código de acesso a dados centralizado
- Fácil adicionar novos repositórios
- Serviços dependem de abstrações
