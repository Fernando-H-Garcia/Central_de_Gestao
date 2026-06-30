# Fluxo de Versão

Define o padrão de versionamento e branches do Central de Gestão.

## Versionamento Semântico

Formato: `vMAJOR.MINOR.PATCH`

| Componente | Quando incrementar | Exemplo |
|-----------|-------------------|---------|
| MAJOR | Mudanças incompatíveis com versões anteriores | v2.0.0 |
| MINOR | Novas funcionalidades compatíveis | v0.2.0 |
| PATCH | Correções de bugs compatíveis | v0.1.1 |

Versão atual: **v0.8** (pré-estável, MAJOR = 0)

## Estrutura de Branches

```
main
  ├── develop (futuro)
  ├── release/v0.x
  └── fix/descricao-do-bug
```

### main
- Branch estável e sempre funcional
- Toda mudança entra via PR
- Build automático via GitHub Actions
- Proibido commit direto

### release/v0.x (quando criado)
- Congela funcionalidades para uma versão
- Apenas correções de bugs críticos
- Quando aprovado: merge para main + tag

### fix/descricao-do-bug (opcional)
- Branch temporária para correções
- Nome descritivo: `fix/badge-delegate-crash`
- Removida após merge

## Fluxo de Release

```
[develop] → [release/v0.x] → [main] → tag v0.x
                ↓
         validação e correções
                ↓
         instalador + publicação
```

## Regras

1. **main** sempre em estado deployável
2. **release** só recebe fix de bugs, nunca features novas
3. **Tag** é criada APÓS validação completa
4. **Instalador** anexado ao release do GitHub
5. **Checklist** obrigatório antes de publicar

## Exemplo prático

```bash
# Iniciar release v0.9
git checkout -b release/v0.9 main

# Corrigir bug durante validação
git commit -m "fix: corrijge crash ao abrir wiki"

# Finalizar release
git checkout main
git merge release/v0.9
git tag -a v0.9 -m "Release v0.9"
git push origin main --tags

# Publicar no GitHub
python scripts/release/create_tag.py 0.9
```
