# Composição do Projeto

Regras que não podem ser quebradas sem uma decisão registrada. Este
documento substitui o antigo `docs/engineering/03-Constituicao-do-Projeto.md`.

## Ambiente de build

Ambiente oficial (medido em 2026-10-13): Python **3.11.5**, PySide6 6.6.3.1,
Qt 6.6.3, PyInstaller 6.21.0, Windows 10/11.

1. **Proibido build com Python 3.12+.** O PySide6 6.6 falha com
   `DLL load failed while importing QtWidgets`. A faixa que funciona é
   PySide6 `>=6.6,<6.7` **com** Python 3.11.
   > O `build_release.py` emite hoje `[AVISO] Versao Python: 3.11.5
   > (esperado 3.12)` — o valor esperado está invertido. Ignore o aviso.

2. **Proibido alterar Services/Repositories para resolver problema de
   build.** Build se resolve no spec ou no ambiente, nunca na lógica de
   negócio.

3. **Proibido `if getattr(sys, 'frozen', False)` para desviar fluxo.** Isso
   cria dois caminhos de código que divergem silenciosamente.

4. **Proibido chamar PyInstaller direto.** Sempre via
   `scripts/ops/control_panel.py`.

## Dependências

5. **Proibido adicionar dependência sem ADR.** Precisa documentar por que é
   necessária, alternativas consideradas e impacto no tamanho do bundle.

6. **Hidden imports do spec só podem ser removidos depois de build + teste**
   confirmarem que não são necessários. Remover sem validar quebra o app
   apenas em runtime — o build passa.

## Código

7. **Proibido `except: pass` genérico.** Todo `try/except` tem propósito
   definido. Se a exceção é esperada e irrelevante, comente o motivo.

8. **Proibido `setStyleSheet` local em componente existente.** Tem
   precedência sobre o `QApplication` e anula o `GLOBAL_STYLE`. Para um visual
   novo: acrescente uma variante `#nome` no `GLOBAL_STYLE` e uma classe em
   `gui/components/`.

9. **Proibido expor credenciais em logs ou commits.**

10. **Widgets sem pai são normais.** A regra real (ver
    [ADR-005](adr/ADR-005-BadgeDelegate.md)) é que um objeto native do Qt
    não pode ficar sem dono entre ser criado e entrar numa hierarquia viva.

## Dados

11. **Testes com banco são obrigados a redirecionar `config.DB_PATH` antes de
    qualquer import**, a instalar trava de segurança e a verificar o SHA-256
    do banco depois. Ver [`Testes.md`](Testes.md).

12. **Backup antes de build** e conferência do hash depois. O banco de
    desenvolvimento não é versionado de forma confiável.

## Documentação

13. **Proibido remover ADR.** ADRs são imutáveis depois de aprovados; erro vira
    ADR novo ou BUG novo. Quando um ADR fica desatualizado, ele é marcado
    como **Superado** e apontado para o novo — não editado em silêncio.

14. **Documento com número vira medida desatualizada.** Prefira escrever a
    método ("consulte `schema_version`") em vez de valor fixo ("20
    migrations").

## Versionamento

Semântico `MAJOR.MINOR.PATCH`, com `MAJOR = 0` (pré-1.0). Versão atual:
**0.8.1** (`VERSION_SHORT` = `0.8`, usado pelo instalador).

Fonte da versão: `scripts/build/version.py`. Não edite a versão dentro do
`.iss` — use `scripts/build/bump_version.py`.

## Branches

```
main                          estável, sempre funcional
feature/<assunto>             trabalho em curso
release/v0.x (futuro)         congela funcionalidades
fix/<descricao> (opcional)     correções pontuais
```

Toda mudança entra na `main` por PR. Sem commit direto.

> Não existe branch `develop` neste repositório — documentos antigos citavam
> um fluxo com `develop`, que nunca foi adotado.

## Convenção de commits

Commits no **Conventional Commits**: `feat:`, `fix:`, `refactor:`, `build:`,
`docs:`, `chore:`, com escopo opcional.

```
fix(prazos): menu de contexto na posição do mouse
```

> Um documento antigo exigia prefixos tipo `FIX:` / `FEATURE:` e afirmava
> haver um pre-commit hook e um "Constitution Check" no CI que validariam
> isso. O hook **não está instalado** (`.git/hooks/pre-commit` não existe).
> A regra é convenção, não imposição automática.