# Dados do seed (simulados — pendentes de validação do grupo)

Escopo: apenas o **trecho das duas linhas no território da UNIFAP** (campus Marco Zero).
Os ônibus não entram no campus; as paradas ficam no perímetro (Rod. JK a leste,
R. Inspetor Aimoré a oeste, R. Inspetor Marcelino ao sul).

- **Coordenadas**: de pontos de ônibus reais do OpenStreetMap (`highway=bus_stop`), sem nome no OSM;
  os nomes foram dados pela via e referência mais próximas.
- **Itinerários**: **estimados** (o OSM não tem as rotas de ônibus de Macapá). A ordem 1 de cada linha
  é a "entrada" no território da UNIFAP, onde fica a câmera simulada.
- **Grade**: fictícia (dia útil a cada 30 min, sábado 45 min, domingo 60 min).

| id da parada | nó OSM |
|---|---|
| jk-marco-zero-ida | 10226854212 |
| jk-marco-zero-volta | 10310209880 |
| unifap-portaria-jk-ida | 10204471369 |
| unifap-portaria-jk-volta | 9971462635 |
| jk-amapa-garden-ida | 10312072294 |
| jk-amapa-garden-volta | 10312072295 |
| aimore-zerao | 10729010733 |
| aimore-maritano | 10226854211 |
| amadeu-gama-unifap | 13532882600 |
| braulino-universidade | 13532882558 |
| marcelino-unifap-fundos | 10656837773 |
| marcelino-jk | 10312072296 |

Para corrigir nomes, coordenadas ou itinerários: edite os JSON desta pasta e rode
`python -m pythonisa_api.cli seed` de novo. Para remover ou renomear o id de uma parada, ou mudar
a grade, recrie o banco (apague `data/pythonisa.db` e rode `init-db` e `seed`): o seed não apaga
registros que saíram dos JSON.
