# Regras Globais do Projeto

1. **Idioma da Interface:** Utilize SEMPRE Português do Brasil (pt-BR) para todos os textos exibidos ao usuário. CUIDADO especial com componentes padrão de bibliotecas (como `QMessageBox` do PySide6), cujos botões padrão (Yes/No/Cancel) aparecem em Inglês. Nesses casos, crie botões customizados com textos em Português (Ex: `"Sim"`, `"Não"`, `"Cancelar"`).

2. **Formato de Data:** Sempre utilize o padrão brasileiro de data: dd/mm/yyyy (exemplo: 24/06/2026).

3. **Padronização Visual e Estilo:** O programa possui um padrão definido em \gui/theme.py\. Todos os componentes da interface devem utilizar este padrão de botões, cores, e layouts, para garantir total uniformidade em todo o sistema. Nunca insira estilos hardcoded (como \Qt.darkGray\, etc.) que fujam das diretrizes visuais do projeto. Certifique-se também de que novos componentes, como listas e árvores (ex: Agenda), respeitem as cores de background e texto do tema (ex: \#2d2d55\ para destaques).

4. **Menus de Contexto (Estrutura e Ordem):** A estrutura de todos os menus de contexto (clique com o botão direito) do projeto DEVE seguir uma ordem rígida:
    - **Grupo 1 (Acesso Rápido - Topo):** Ações para entrar ou visualizar (ex: `🗂️ Abrir Projeto`, `📋 Abrir Tarefa`) e ações de edição básica (ex: `✏️ Editar`).
    - `menu.addSeparator()`
    - **Grupo 2 (Ações de Negócio - Meio):** Ações específicas como mudar status, alterar prioridade, `📦 Arquivar` ou `📦 Desarquivar`, promover, etc.
    - `menu.addSeparator()`
    - **Grupo 3 (Destrutivo - Fim):** A opção de deleção (ex: `🗑️ Excluir`) DEVE SEMPRE ser o último item do menu, totalmente isolado por um separador, para evitar cliques acidentais.

5. **Ícones em Menus:** Ao criar itens de menu (QAction) ou botões de ação, sempre utilize emojis textuais padronizados no início do texto para servir como ícones, melhorando a experiência visual sem exigir arquivos de imagem. Padrões recomendados: `✏️ Editar`, `🗑️ Excluir`, `🗂️ Abrir Projeto`, `📋 Abrir Tarefa`, `📦 Arquivar / Desarquivar`.
