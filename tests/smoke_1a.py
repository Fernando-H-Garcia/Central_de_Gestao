import os
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.getcwd())

from PySide6.QtWidgets import QApplication

app = QApplication(sys.argv)

from gui.theme import GLOBAL_STYLE

app.setStyleSheet(GLOBAL_STYLE)

ok = []
fail = []


def check(name, fn):
    try:
        fn()
        ok.append(name)
    except Exception as e:
        fail.append(f"{name}: {type(e).__name__}: {e}")


def t_project():
    from gui.dialogs_qt.project_dialog_qt import ProjectDialogQt

    ProjectDialogQt()


check("ProjectDialogQt (ent_obj=TitleEdit)", t_project)


def t_event():
    from gui.dialogs_qt.event_dialog_qt import EventDialogQt

    EventDialogQt()


check("EventDialogQt", t_event)


def t_idea():
    from gui.dialogs_qt.idea_dialog_qt import IdeaDialogQt

    IdeaDialogQt()


check("IdeaDialogQt", t_idea)


def t_promote():
    from gui.dialogs_qt.promote_idea_dialog_qt import PromoteIdeaDialogQt
    from models.entities import Idea

    PromoteIdeaDialogQt(idea=Idea())


check("PromoteIdeaDialogQt (CHECKBOX_STYLE)", t_promote)


def t_alarm():
    from gui.dialogs_qt.alarm_dialog_qt import AlarmDialogQt

    AlarmDialogQt()


check("AlarmDialogQt", t_alarm)


def t_newpage():
    from gui.views.wiki_qt import _NewPageDialog

    _NewPageDialog()


check("_NewPageDialog (TitleEdit + fit)", t_newpage)


def t_snooze():
    from gui.dialogs_qt.alarm_popup_qt import AlarmPopupQt

    dlg = AlarmPopupQt([], {})
    fn = dlg._handle_snooze
    # nao executa exec(); valida apenas que o dialogo foi construido sem erro
    assert callable(fn)


check("AlarmPopupQt", t_snooze)


def t_mainwindow():
    from gui.main_window_qt import MainWindow

    w = MainWindow()
    # btn_group deve ter um botao por pagina de NAV_PAGES (fonte unica)
    from gui.main_window_qt import NAV_NAMES
    assert len(w.btn_group.buttons()) == len(NAV_NAMES), \
        f"btn_group com {len(w.btn_group.buttons())} botoes (esperado {len(NAV_NAMES)})"
    # _deselect_nav_buttons deve realmente desmarcar
    assert w.nav_buttons[0].isChecked(), "botao 0 deveria iniciar marcado"
    w._deselect_nav_buttons()
    assert not any(b.isChecked() for b in w.nav_buttons.values()), "nenhum botao deveria restar marcado"
    w.btn_group.setExclusive(True)
    # show_page deve marcar exatamente o botao correspondente
    w._show_page(2)
    assert w.nav_buttons[2].isChecked(), "botao 2 deveria estar marcado apos _show_page(2)"
    assert not w.nav_buttons[0].isChecked(), "botao 0 nao deveria continuar marcado"
    return w


check("MainWindow (btn_group.addButton)", t_mainwindow)


def t_timeline():
    from gui.components.timeline.timeline_view_qt import TimelineViewQt

    tv = TimelineViewQt()
    assert tv.chk_tasks.isChecked()
    assert not tv.chk_completed.isChecked(), "chk_completed deveria iniciar desmarcado"


check("TimelineViewQt (5 CHECKBOX_STYLE)", t_timeline)

print("=" * 60)
for n in ok:
    print(f"  OK   {n}")
for n in fail:
    print(f"  FAIL {n}")
print("=" * 60)
print(f"{len(ok)} ok / {len(fail)} fail")
sys.exit(1 if fail else 0)