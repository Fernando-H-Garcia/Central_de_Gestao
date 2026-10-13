"""Consistencia da acao destrutiva em toda a UI.

Decisao do usuario: sem bolinha vermelha nos menus.

Regra adotada:
  - ITEM DE MENU ....... texto puro (so o emoji do rotulo). Sem icone.
  - DIALOGO DE CONFIR.. botao com variante `danger` do tema (vermelho solido).
  - CARD / LINHA ....... botao com variante `dangerOutline` (contorno), para
                         nao competir com o conteudo do card.

Este teste trava a regra para que nao volte a divergir.
"""
import os
import re
import sys
import pathlib

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.getcwd())

from PySide6.QtWidgets import QApplication

app = QApplication(sys.argv)

from gui.theme import GLOBAL_STYLE
app.setStyleSheet(GLOBAL_STYLE)

ok, fail = [], []


def check(name, fn):
    try:
        fn()
        ok.append(name)
    except Exception as e:
        fail.append(f"{name}: {type(e).__name__}: {e}")


def t_menu_sem_icone():
    from gui.components.context_menu_qt import ContextMenuQt

    m = ContextMenuQt(parent=None)
    a = m.add_command("🗑️ Excluir", danger=True)
    assert a.icon().isNull(), "menu nao deve ter bolinha vermelha"
    sub = m.add_submenu("Status")
    sub.add_status_items()
    for act in sub.menu.actions():
        assert not act.icon().isNull(), "o submenu de status mantem as bolinhas de cor"


check("menu: acao destrutiva SEM icone (decisao do usuario)", t_menu_sem_icone)


def t_botoes_destrutivos():
    """Nenhum botao 'Excluir' pode ter stylesheet inline -- todos devem
    usar uma variante do tema."""
    inline = []
    for p in pathlib.Path("gui").rglob("*.py"):
        src = p.read_text(encoding="utf-8")
        lines = src.splitlines()
        for i, l in enumerate(lines):
            if re.search(r'QPushButton\("[^"]*(Excluir|Excluir tudo|Excluir Nota|Arquivar)', l):
                bloco = "\n".join(lines[i:i + 8])
                if "setStyleSheet" in bloco:
                    inline.append(f"{p.name}:{i+1}")
    assert not inline, "botao destrutivo ainda com CSS inline: " + ", ".join(inline)


check("nenhum botao destrutivo com CSS inline", t_botoes_destrutivos)


def t_dialogo_usa_variante():
    from gui.dialogs_qt.reference_warning_dialog_qt import ReferenceWarningDialog
    from gui.components.buttons import DangerButton, SecondaryButton

    d = ReferenceWarningDialog("tarefa", "T", [{"type_label": "Tarefa",
                                                "title": "Outra tarefa",
                                                "source_name": "pagina"}],
                               None, show_archive=True)
    bts = [b for b in d.findChildren(DangerButton)]
    assert len(bts) == 1, f"esperava 1 DangerButton, achei {len(bts)}"
    assert bts[0].objectName() == "danger"
    assert bts[0].styleSheet() == "", "DangerButton nao deve ter CSS local"
    secs = d.findChildren(SecondaryButton)
    assert len(secs) == 2, f"esperava 2 SecondaryButton, achei {len(secs)}"


check("dialogo de referencia: danger + secondary do tema", t_dialogo_usa_variante)


def t_variantes_no_tema():
    for v in ("danger", "dangerOutline", "secondary"):
        assert f"QPushButton#{v}" in GLOBAL_STYLE, f"variante {v} ausente do tema"


check("tema tem danger / dangerOutline / secondary", t_variantes_no_tema)


def t_card_usa_outline():
    """Acoes dentro de card usam dangerOutline (contorno), nao danger solido."""
    src = pathlib.Path("gui/components/alarm_cards_qt.py").read_text(encoding="utf-8")
    assert 'QPushButton("🗑️ Excluir")' in src
    idx = src.index('QPushButton("🗑️ Excluir")')
    bloco = src[idx:idx + 220]
    assert 'setObjectName("dangerOutline")' in bloco, "card deveria usar dangerOutline"
    assert "setStyleSheet" not in bloco, "card nao deve ter CSS inline"


check("card de alarme: dangerOutline (contorno)", t_card_usa_outline)


def t_header_layout():
    """Cabecalho: o titulo nunca fica sem espaco util."""
    from gui.components.page_header import ElidedTitle
    from PySide6.QtWidgets import QSizePolicy

    t = ElidedTitle("Um titulo bastante longo para precisar de quebrar linha")
    t.resize(300, 30)
    t._refresh()
    assert t.text(), "titulo vazio"
    assert t.toolTip() == t.full_text()
    assert t.sizePolicy().horizontalPolicy() == QSizePolicy.Expanding
    assert t.minimumWidth() >= 200


check("titulo do cabecalho: ocupa espaco e guarda o texto completo", t_header_layout)

print("=" * 64)
for n in ok:
    print(f"  OK   {n}")
for n in fail:
    print(f"  FAIL {n}")
print("=" * 64)
print(f"{len(ok)} ok / {len(fail)} fail")
sys.exit(1 if fail else 0)