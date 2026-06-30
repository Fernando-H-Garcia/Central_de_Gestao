# Rollback Checklist

## Procedimento
1. [ ] Desinstalar versão atual (Painel de Controle)
2. [ ] Verificar `%LOCALAPPDATA%\CentralGestao\` preservado
3. [ ] Instalar versão anterior
4. [ ] Verificar dados migrados corretamente
5. [ ] Testar funcionalidades principais

## Se necessário restaurar backup
1. [ ] Localizar `brain.db` em backup
2. [ ] Parar app
3. [ ] Substituir `brain.db` em `%LOCALAPPDATA%`
4. [ ] Reiniciar app
