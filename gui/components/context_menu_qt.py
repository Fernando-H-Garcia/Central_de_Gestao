"""Menu de contexto (PySide6).

Substitui o QMenu cru espalhado pelas telas. Antes havia 18 pontos de
construcao com tres formatos diferentes (comparar o retorno de exec,
conectar no `triggered`, misturar os dois), a lista de status repetida em
3 telas e nenhuma distincao visual entre acao destrutiva e acao normal --
"Excluir" ficava identico a "Abrir".

O visual vem do `QMenu` do GLOBAL_STYLE (gui/theme.py). Nao aplique
setStyleSheet aqui.

Exemplo (comparando o retorno):

    menu = ContextMenuQt(self)
    act_open = menu.add_command("👁️ Abrir")
    menu.add_separator()
    menu.add_command("🗑️ Excluir", danger=True).triggered.connect(self._delete)
    if menu.popup(event.globalPos()) == act_open:
        self._open()

Exemplo (com submenu de status):

    menu = ContextMenuQt(self)
    menu.add_status_items(on_click=self._change_status)
    if menu.popup_at(self.table, pos) is not None:
        pass
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu

from gui.theme import get_status_color, create_color_icon, ERROR_RED

# Ordem canonica dos status de tarefa. Antes estava escrita a mao em
# tasks_qt e project_360_qt (duplicadas).
TASK_STATUSES = [
    "Pendente",
    "Em Andamento",
    "Pausado",
    "Aguardando",
    "Bloqueado",
    "Concluído",
]


class ContextMenuQt:
    """Wrapper sobre QMenu com API encadeavel.

    Mantem o QMenu acessivel em `.menu` para os casos que exigem algo
    fora desta API (item desabilitado com texto de motivo, acao com
    atalho, menu persistente).
    """

    def __init__(self, title="", parent=None, menu=None):
        self.menu = menu if menu is not None else QMenu(title, parent)
        self._parent_menu = menu

    # -- construcao -------------------------------------------------------
    def add_command(self, label, icon=None, danger=False, enabled=True,
                    callback=None):
        """Adiciona um item. Retorna a QAction (util para comparar com
        o retorno de popup).

        danger=True aplica um ponto vermelho a esquerda, para que acao
        destrutiva nao pareca igual a acao normal. O texto NAO e
        alterado -- o emoji do rotulo (ex.: "🗑️ Excluir") ja sinaliza.
        O Qt reserva espaco de icone para todos os itens quando algum
        tem icone, entao o alinhamento do texto se mantem.
        """
        action = QAction(label, self.menu)
        if icon is not None:
            action.setIcon(icon)
        elif danger:
            action.setIcon(create_color_icon(ERROR_RED))
        if not enabled:
            action.setEnabled(False)
        if callback is not None:
            action.triggered.connect(callback)
        self.menu.addAction(action)
        return action

    def add_separator(self):
        self.menu.addSeparator()

    def add_submenu(self, title, icon=None):
        """Retorna outro ContextMenuQt sobre o submenu, para continuar
        encadeando."""
        sub = self.menu.addMenu(title)
        if icon is not None:
            sub.menuAction().setIcon(icon)
        return ContextMenuQt(title, parent=sub, menu=sub)

    def add_status_items(self, statuses=None, on_click=None):
        """Itens de status com a bolinha na cor do status.

        Deduplica o codigo que estava em tasks_qt, project_360_qt,
        task_detail_qt e ideas_qt: a lista, o create_color_icon e o loop.
        """
        for st in (statuses or TASK_STATUSES):
            # _checked: QAction.triggered emite um bool que nao e o valor
            # do status. Sem este parametro ele cairia no `s`.
            self.add_command(
                st,
                icon=create_color_icon(get_status_color(st)),
                callback=(lambda _c=False, s=st: on_click(s)) if on_click else None,
            )

    def add_color_items(self, values, color_of, on_click=None):
        """Itens coloridos com uma funcao cor -> hex (ex.: get_energy_color).

        Usado pelo menu de Prioridade das ideias, que repete o mesmo
        padrao do de Status com outra paleta.
        """
        for v in values:
            self.add_command(
                v,
                icon=create_color_icon(color_of(v)),
                callback=(lambda _c=False, x=v: on_click(x)) if on_click else None,
            )

    def add_header(self, text):
        """Rotulo de secao, nao clicavel."""
        action = QAction(text, self.menu)
        action.setEnabled(False)
        self.menu.addAction(action)
        return action

    # -- exibicao ---------------------------------------------------------
    def popup(self, global_pos):
        """Abre o menu e devolve a QAction escolhida (ou None)."""
        return self.menu.exec(global_pos)

    def popup_at(self, widget, pos):
        """Abre o menu na posicao `pos` (coordenadas do widget) e devolve a
        acao escolhida."""
        return self.menu.exec(widget.viewport().mapToGlobal(pos))

    def exec(self, global_pos):
        return self.menu.exec(global_pos)

    def exec_(self, global_pos):
        return self.menu.exec(global_pos)

    def clear(self):
        self.menu.clear()

    # -- compatibilidade --------------------------------------------------
    # A migracao dos 18 menus e gradual: enquanto um call site ainda usa
    # `menu.addAction(...)` / `menu.addSeparator()` / `menu.addMenu(...)`
    # no estilo QMenu, o proxy evita AttributeError em runtime. Nao
    # plataforma para a API nova, que e a recomendada.
    def __getattr__(self, name):
        return getattr(self.menu, name)