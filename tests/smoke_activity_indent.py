"""Escadinha uniforme no Resumo das Atividades (headless, offscreen).

Regra: projeto=0, tarefa=1 passo, subtarefa=2 passos... cada nivel adiciona
exatamente INDENT_STEP (16px). Antes o corpo indentava 8 + depth*18
(8/8/26/44...) e o prefixo somava espacos por nivel.
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

app = QApplication(sys.argv)

results = []


def check(name, cond, extra=""):
    results.append((name, bool(cond), extra))
    print(f"  {'ok  ' if cond else 'FALHA'} {name}" + (f"  -> {extra}" if extra else ""))


from gui.components.collapsible_section_qt import CollapsibleSection

STEP = CollapsibleSection.INDENT_STEP
check("passo da escadinha e 16 (dobro da base 8)", STEP == 16, f"STEP={STEP}")

# 1. corpo indenta igual em todo nivel
margins = {}
_keep = []
for d in range(5):
    sec = CollapsibleSection(f"n{d}", depth=d)
    _keep.append(sec)
    left = sec.body_layout.contentsMargins().left()
    margins[d] = left
check("corpo uniforme em todos os niveis",
      all(v == STEP for v in margins.values()), f"margins={margins}")

# 2. set_depth mantem uniforme
sec = CollapsibleSection("x", depth=0)
sec.set_depth(3)
check("set_depth mantem passo uniforme",
      sec.body_layout.contentsMargins().left() == STEP,
      f"left={sec.body_layout.contentsMargins().left()}")

# 3. prefixo: nivel 0 sem ramo, niveis >=1 com "└─ " unico (sem espacos extras)
# (segura referencia: sem pai, o temporario e coletado e o C++ e deletado)
_s0 = CollapsibleSection("proj", depth=0)
_s1 = CollapsibleSection("t1", depth=1)
_s2 = CollapsibleSection("t2", depth=2)
_s3 = CollapsibleSection("t3", depth=3)
t0, t1, t2, t3 = _s0.header.text(), _s1.header.text(), _s2.header.text(), _s3.header.text()
check("nivel 0 sem ramo", "└─" not in t0, t0)
check("nivel 1 com ramo unico", t1.count("└─") == 1, t1)
check("nivel 2 sem espacos extras (prefixo igual ao nivel 1)",
      t2.replace("t2", "t1") == t1.replace("t1", "t1") and t2.count("└─") == 1, t2)
check("nivel 3 prefixo igual ao nivel 1",
      t3.split("└─")[0] == t1.split("└─")[0] and t3.count("└─") == 1, t3)

# 4. escadinha acumulada: aninhando como a view faz
# (secao filha dentro do body da pai), cada cabecalho desloca +STEP
proj = CollapsibleSection("projeto", depth=0)
root = CollapsibleSection("tarefa", depth=0)
sub = CollapsibleSection("sub", depth=1)
subsub = CollapsibleSection("subsub", depth=2)
proj.body_layout.addWidget(root)
root.body_layout.addWidget(sub)
sub.body_layout.addWidget(subsub)
offsets = {
    "root": proj.body_layout.contentsMargins().left(),
    "sub": proj.body_layout.contentsMargins().left() + root.body_layout.contentsMargins().left(),
    "subsub": proj.body_layout.contentsMargins().left() + root.body_layout.contentsMargins().left()
              + sub.body_layout.contentsMargins().left(),
}
check("escadinha 16/32/48",
      offsets == {"root": 16, "sub": 32, "subsub": 48}, f"{offsets}")

ok = sum(1 for _, c, _ in results if c)
fail = len(results) - ok
print(f"{ok} ok / {fail} fail")
sys.exit(1 if fail else 0)
