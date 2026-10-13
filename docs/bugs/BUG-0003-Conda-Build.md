# BUG-0003: Conda Build Quebrado

**Status**: Corrigido
**Data**: 2024-03-12

> **Nota de revisão (2026-10):** a "solução" original está com a versão do
> Python **invertida**. Ver a correção no final.

## Sintoma
PyInstaller em ambiente Conda produzia bundle com erro de inicialização.

## Causa
Conda gerencia bibliotecas de forma diferente do pip. O PySide6 6.11.1
instalado pelo Conda não é compatível com o runtime empacotado.

## Solução (original, incorreta)
> Ambiente oficial: **Python 3.12.1** puro + PySide6 6.6.3.1 (pip, não Conda).

## Correção (2026-10)

A solução correta é **Python 3.11.5** puro + PySide6 6.6.3.1. O registro
original inverteu a regra (ver também [BUG-0002](../bugs/BUG-0002-DLL-Mismatch.md)):

- PySide6 **6.6.x exige Python ≤ 3.11**.
- Python 3.12+ com PySide6 6.6 falha com `DLL load failed while importing QtWidgets`.
- PySide6 **6.11+** falha em Python 3.11 (o mesmo erro, pelo outro lado).

Faixa que funciona: `PySide6>=6.6,<6.7` **com** Python 3.11.

## Ambiente oficial (medido em 2026-10-13)

```powershell
& "C:\Anaconda\python.exe" -m venv venv_build
.\venv_build\Scripts\pip.exe install "PySide6>=6.6,<6.7" "pyinstaller>=6.21,<7.0" Markdown>=3.5
```

Note que o **Cona serve só para criar o venv** (`python.exe -m venv`); o venv
resultante não carrega os pacotes do Conda. Por isso o passo 1 pode usar o
interpreter do Conda e o passo 2 usa `venv_build\Scripts\pip.exe`.

Procedimento completo em [`docs/BUILD.md`](../BUILD.md).