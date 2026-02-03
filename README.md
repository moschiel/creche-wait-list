Se a posição na lista de espera da creche de Carapicuíba mudar, reporta via telegram a posição na lista de espera.

O script pode ser excutado via GitHub Actions ativando a ação "Creche Monitor" configurado no arquivo .yml

Observação:
O configuração do CRON no arquivo .yml para executação automática não estava funcionando.
Por isso, nesse projeto a ação é ativada externamente via uma API (cron.org), que executa a ação 2x ao dia.
