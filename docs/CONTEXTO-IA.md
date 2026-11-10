# Contexto para continuar o projeto (handoff entre máquinas/IAs)

> Leia este arquivo antes de qualquer ação. Atualizado em 2026-11-09, ao fim da Parte 1.

## 1. O projeto

**Pythonisa** é um sistema de previsão de chegada de ônibus urbanos com foco na **UNIFAP** (Macapá-AP), feito em três repositórios:

1. App Mobile em Flutter: `github.com/Unifap-pythonisa/pythonisa_app`. Está desatualizado: tem só a tela Companhia → Linha, com dados fixos no código, e vai se adaptar ao contrato desta API.
2. Visão Computacional (OCR de letreiro): repositório separado. Fora do escopo agora.
3. **Este repositório:** servidor intermediário em **Python/FastAPI**, com SQLite, dados simulados e modelo de previsão (Regressão Linear).

**Fluxo da demo:** o usuário escolhe a parada onde está (ou o app usa o GPS) → vê as linhas que passam ali → vê a previsão no estilo Google Maps: "programado 07:30, previsto 07:27, adiantado 3 min, faltam 6 min".

## 2. Como trabalhar com o usuário

- **Idioma:** responder sempre em **português (pt-BR)**. Código e identificadores também estão em português.
- **MANTER SIMPLES.** O usuário achou o projeto *overengineered*. Implemente só o que aparece na demo do MVP. Nada de mecanismos "para o futuro" sem pedir antes.
- **Explicar de forma didática.** É o primeiro contato do usuário com FastAPI. Ao concluir cada parte, explique **no chat** (não em arquivos novos) como foi feito: o papel de cada arquivo e biblioteca, e o que é gerado por ferramenta e o que foi escrito à mão. Analogias com Flutter ajudam.
- **Instruções de teste concretas.** Ao final de cada parte, diga se os testes passaram (com o resultado real) e dê **JSONs prontos** para testar no `/docs`. O usuário estranhou o JSON de exemplo do Swagger, com `"string"` em todos os campos.
- **Fluxo de trabalho:**
  - para algo novo e não trivial: spec aprovada → plano em passos pequenos → execução com **TDD** (teste falhando → implementação mínima → testes verdes);
  - nunca declarar algo pronto sem rodar `pytest` e `ruff` e mostrar a saída;
  - commits pequenos, terminando com `Co-Authored-By`.
- **Subagentes:** só use quando o usuário pedir.
- **Ferramentas do usuário:** macOS + zsh, VS Code, DBeaver conectado em `data/pythonisa.db`.

## 3. Decisões tomadas (não reabrir sem motivo)

- **Escopo:** 2 linhas reais, **Macapaba – Amapá Garden** e **Brasil Novo – Universidade**. Elas substituem a "131 Universidade Jardim", cujo letreiro "UNIVERSIDADE" é ambíguo para o OCR.
- **Paradas:** só as do **território da UNIFAP** (campus Marco Zero), não a cidade toda. Os ônibus não entram no campus, então as paradas ficam no perímetro: Rod. JK, R. Inspetor Aimoré e R. Inspetor Marcelino.
  - As **coordenadas são reais**, de nós `bus_stop` do OpenStreetMap.
  - Os **nomes foram inventados** a partir da rua mais próxima. O usuário aceitou isso.
  - Os **itinerários são estimados**, porque o OSM não tem as rotas de Macapá.
  - A **grade de horários é fictícia**.
- **Cada lado da rua é uma `Parada` distinta.** O itinerário é uma sequência única de ida + volta (`ordem` 1..N), com `sentido` só informativo.
- **`Empresa` não é entidade.** É um atributo opcional de `Linha`.
- **Sem `Veículo`:** não há placa nem frota. `Viagem` agrupa as passagens de uma ida do ônibus.
- **Previsão:** um ônibus é "detectado" na **1ª parada** (câmera simulada). O modelo prevê o **Δt de cada trecho** entre paradas e soma esses tempos até a parada do usuário. A hora do dia entra como categoria, para o modelo representar o pico. O horário programado vem da grade.
- **Integração com a VC (letreiro, confiança do OCR, deduplicação) foi ADIADA.** Hoje `POST /deteccoes` é só um "registrar passagem" simples.
- **Datetimes:** gravados como horário local naive (`America/Belem`, UTC−3). A API devolve ISO com `-03:00` e exige fuso na entrada.

## 4. Estado atual

**Parte 1 (fundação): CONCLUÍDA.** São 49 testes passando e `ruff` limpo, na branch `lucas`.

| Item | Onde |
|---|---|
| Spec (design completo; seções 3.3/3.4/5.2 marcadas como adiadas) | `docs/superpowers/specs/2026-11-08-servidor-fastapi-mvp-design.md` |
| Plano da Parte 1 (executado) | `docs/superpowers/plans/2026-11-08-fundacao-servidor.md` |
| Overview original do grupo e MER antigo | `docs/Overview Outubro Pythonisa.md` |
| Notebook original de predição (referência) | `predicaoChegada.ipynb` |

**Endpoints prontos** (prefixo `/api/v1`):

| Endpoint | Função |
|---|---|
| `GET /health` | Saúde do servidor |
| `GET /linhas` | Lista as linhas |
| `GET /linhas/{id}/paradas` | Itinerário ordenado da linha |
| `GET /paradas?id_linha=` | Lista de paradas, com filtro opcional por linha |
| `GET /paradas/proxima?latitude=&longitude=` | Parada mais próxima de um ponto |
| `GET /paradas/{id}/linhas` | Linhas que atendem a parada |
| `POST /deteccoes` | Registra uma passagem `{id_linha, id_parada, timestamp_passagem, id_viagem?}`. Na ordem 1, cria uma `Viagem` ligada ao horário mais próximo (±15 min). |

**Formato de erro:** `{"erro": {"codigo": "...", "mensagem": "..."}}`. Os códigos são `LINHA_NAO_ENCONTRADA`, `PARADA_NAO_ENCONTRADA`, `PARADA_FORA_DA_LINHA`, `DADOS_INVALIDOS` e `NAO_ENCONTRADO`.

**Estrutura:**

```
src/pythonisa_api/
  main.py (create_app) · config.py (.env) · tempo.py (fuso) · erros.py · cli.py (init-db, seed)
  api/      deps.py · erros.py (handlers) · v1/{saude,linhas,paradas,deteccoes}.py
  schemas/  consulta.py · passagem.py           (Pydantic = contrato JSON)
  services/ consulta.py · geo.py · passagem.py  (regras, sem FastAPI)
  db/       base.py (engine, PRAGMA foreign_keys) · models.py (8 tabelas)
  seed/     carregar.py · dados/*.json (+ README com os nós OSM)
tests/      conftest.py · unit/ · integration/ · fixtures/seed_mini/
```

**Stack:** Python 3.13, FastAPI, Uvicorn, SQLAlchemy 2 (síncrono), Pydantic v2, pydantic-settings, tzdata, pytest, httpx2 e ruff. O ambiente usa `venv` + `pip`. Não há Alembic: se o modelo mudar, apague o `.db` e rode `init-db` + `seed`.

## 5. Preparar a máquina nova

```bash
cd pythonisaFastApi
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m pythonisa_api.cli init-db
python -m pythonisa_api.cli seed       # esperado: linhas=2 paradas=12 itinerario=14 horarios=143 padroes_letreiro=2
pytest && ruff check .                 # esperado: 49 passed
uvicorn pythonisa_api.main:app --reload   # http://localhost:8000/docs
```

`data/`, `.venv/` e `.env` não vão para o git. Por isso o banco precisa ser recriado na máquina nova.

## 6. Próximo passo: Parte 2 (o que aparece na demo)

Antes de implementar, **escrever um plano curto e enxuto** e mostrar ao usuário. O conteúdo previsto:

1. **Simulador de tráfego e histórico:** gera N dias de passagens em **todas** as paradas, via `services.passagem.registrar_passagem`, informando o `id_viagem`.
   - `Δt = base × fator_horario × fator_dia × ruído`.
   - `fator_horario` ≈ 1,3 nos picos (06:30–08:30, 11:30–13:30, 17:00–19:00) e ≈ 0,85 fora deles.
   - O ruído log-normal tem desvio de ~10%.
   - O tempo base fica abaixo do programado, para o ônibus adiantar fora do pico.
   - A semente é fixa, para o resultado ser reprodutível.
   - Detalhes na spec, seção 6.
2. **ML:** `PreditorTrecho` com `prever_segundos(id_linha, ordem_origem, momento)`.
   - O modelo é Regressão Linear (`OneHotEncoder` + `LinearRegression`) sobre trecho, hora cheia e tipo de dia.
   - O baseline é a média histórica.
   - O teste usa divisão temporal (últimos 7 dias).
   - Comando `treinar`, artefato salvo com `joblib` e `GET /modelo` com métricas. Detalhes na spec, seção 7.
3. **Previsão:** `GET /previsoes?id_linha=&id_parada=` e `GET /paradas/{id}/previsoes`.
   - Parâmetro opcional `agora` para a demo, permitindo simular um horário de pico.
   - Contrato na spec, seção 5.1.
4. **Passagens "ao vivo":** só na 1ª parada, geradas de forma determinística conforme o relógio.
5. Comando `resetar` (init-db + seed + histórico + treino) e um roteiro de demo.

## 7. Pendências

- **O grupo precisa validar** paradas e itinerários (`src/pythonisa_api/seed/dados/README.md`). Na Macapaba, as ordens 3 e 4 ficam frente a frente na Rod. JK e têm o mesmo horário programado (é o retorno da linha).
- **Pontos menores conhecidos, não corrigidos:**
  - importar `main.py` cria a pasta `data/`;
  - a `DATABASE_URL` relativa depende da pasta de onde o servidor é iniciado;
  - uma passagem duplicada na ordem 1 cria duas viagens;
  - um timestamp no futuro é aceito.
- **Revisão independente:** o usuário ainda não decidiu se um revisor por subagente olha a Parte 1 agora ou tudo no fim da Parte 2.
- **Arquivos do usuário:** `docs/assets/` tem imagens antigas apagadas e um `MER_pytonisa.png` novo, além de PDFs da spec e do plano. Não foram commitados por mim, e a decisão sobre eles é do usuário.
