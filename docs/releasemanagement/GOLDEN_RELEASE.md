# Golden Release Tag

## Conceito

A **Golden Release** é a release oficial estável do Central de Gestão. Existe **sempre uma única** golden release apontando para a versão estável mais recente.

## Propriedades

- ✅ **Protegida contra overwrite**: a tag `golden-release` nunca é sobrescrita sem aprovação explícita.
- ✅ **Fallback automático**: se uma nova release falhar, o pipeline usa a golden release como fallback.
- ✅ **Rastreável**: a golden release sempre referencia um commit e uma tag semântica (`vX.Y.Z`).

## Gerenciamento

### Criar / Atualizar Golden Release

```bash
# Após validar uma nova release, promover a golden:
git tag -f golden-release v0.8.0
git push origin golden-release --force

# Atualizar golden-release local:
git fetch origin golden-release
git checkout golden-release
```

### Verificar Golden Release Atual

```bash
git tag -l golden-release
git show golden-release --format="%H %s" --no-patch
```

### Fallback Automático (CI)

Em caso de falha na pipeline de release, o CI deve automaticamente:

```yaml
- name: Fallback to golden
  run: |
    git fetch origin golden-release
    git checkout golden-release
    python scripts/ops/control_panel.py build --release
```

## Política de Promoção

1. A golden release só é promovida após **todos os checks passarem**:
   - ✅ Smoke test
   - ✅ Installer validation
   - ✅ Health check
   - ✅ Release score ≥ 50
2. A golden release pode ser **revertida** para uma versão anterior se a nova apresentar problemas.
3. A reversão é registrada no `AUDIT_LOG.md`.
