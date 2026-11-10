# Fundação do Servidor (Parte 1 de 2) — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Servidor FastAPI com banco SQLite das 8 entidades, seed das duas linhas, endpoints de consulta para o app e ingestão de detecções (letreiro → linha → viagem).

**Architecture:** Pacote `pythonisa_api` em layout `src/`. `api/` traduz HTTP ↔ `services/` (regras, sem FastAPI) ↔ `db/` (SQLAlchemy 2 síncrono). App criado por `create_app(settings)`, com engine e fábrica de sessão em `app.state`. Erros de domínio (`ErroDominio`) são convertidos em `{"erro": {"codigo", "mensagem"}}`.

**Tech Stack:** Python 3.13, FastAPI, Uvicorn, SQLAlchemy 2.x, Pydantic v2, pydantic-settings, tzdata, pytest, httpx, ruff. Ambiente com `venv` + `pip`.

**Spec:** `docs/superpowers/specs/2026-11-08-servidor-fastapi-mvp-design.md` (seções 3, 4, 5.1, 5.2, 6.1 e checklist 1–5). A Parte 2 (simulador, ML, previsão, ao vivo) terá plano próprio.

## Global Constraints

- Prefixo da API: `/api/v1`.
- Formato de erro: `{"erro": {"codigo": "<CODIGO>", "mensagem": "<texto>"}}`. Códigos e status: `LINHA_NAO_ENCONTRADA` 404, `PARADA_NAO_ENCONTRADA` 404, `NAO_ENCONTRADO` 404 (rota inexistente), `PARADA_FORA_DA_LINHA` 422, `DADOS_INVALIDOS` 422. (Códigos de letreiro e confiança: adiados, ver Task 5.)
- Fuso: `America/Belem`. Datetimes **persistidos como naive em horário local** (UTC−3 fixo). A API devolve ISO 8601 com offset `-03:00`. A entrada de datetime **exige** offset.
- Variáveis de ambiente (nomes exatos): `DATABASE_URL` (padrão `sqlite:///data/pythonisa.db`), `CORS_ORIGINS` (padrão `["*"]`).
- `PRAGMA foreign_keys=ON` em toda conexão SQLite.
- Domínios fechados: `sentido` ∈ {`ida`, `volta`}; `origem` ∈ {`simulado`, `ocr`}; `tipo_dia` ∈ {`util`, `sabado`, `domingo`}; `fonte` ∈ {`deteccao`, `programado`}.
- Identificadores de código e nomes de campos em português, como na spec.
- Todo comando é rodado dentro do venv (`source .venv/bin/activate`), a partir da raiz `pythonisaFastApi/`.

## Review Focus

- `timestamp_passagem` sem offset deve ser rejeitado com `DADOS_INVALIDOS`, e não interpretado silenciosamente. Teste na Task 5.
- Rota inexistente deve devolver o formato padrão de erro, não o `{"detail": ...}` do FastAPI. Teste na Task 4.
- Rodar o seed duas vezes ou após editar o JSON não pode duplicar linhas, padrões ou horários, e o itinerário é substituído. Teste na Task 3.

---

### Task 1: Base do projeto e `/health`

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `.env.example`, `README.md`
- Create: `src/pythonisa_api/__init__.py`, `src/pythonisa_api/config.py`, `src/pythonisa_api/main.py`, `src/pythonisa_api/api/__init__.py`, `src/pythonisa_api/api/v1/__init__.py`, `src/pythonisa_api/api/v1/saude.py`
- Test: `tests/conftest.py`, `tests/integration/test_saude.py`

**Interfaces:**
- Produces:
  - `Settings` (pydantic-settings), com campos `database_url: str`, `cors_origins: list[str]`, `confianca_ocr_minima: float`, `janela_associacao_min: int` e `env_file=".env"`.
  - `create_app(settings: Settings | None = None) -> FastAPI`, que guarda `app.state.settings`.
  - Fixtures `settings_teste` (banco em `tmp_path`), `app` e `cliente` (`TestClient`).

- [ ] **Step 1:** criar `pyproject.toml`:
  - build backend `hatchling`;
  - `requires-python = ">=3.13"`;
  - deps: `fastapi`, `uvicorn[standard]`, `sqlalchemy>=2.0`, `pydantic>=2`, `pydantic-settings`, `tzdata`;
  - extra `dev`: `pytest`, `httpx`, `ruff`;
  - `[tool.pytest.ini_options] testpaths=["tests"]`;
  - `[tool.ruff] line-length=100`, `target-version="py313"`, lint `select=["E","F","I","UP","B"]`.

  Criar `.gitignore` (`.venv/`, `data/`, `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `.env`) e `.env.example` com as 4 variáveis.
- [ ] **Step 2:** criar o venv e instalar.
  - Run: `python3 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"`
  - Expected: instalação termina sem erro.
- [ ] **Step 3: teste que falha** (`tests/integration/test_saude.py`)

```python
def test_health_responde_ok(cliente):
    r = cliente.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "modelo_carregado": False}

def test_cors_liberado_para_origem_configurada(cliente):
    r = cliente.get("/api/v1/health", headers={"Origin": "http://localhost:5555"})
    assert r.headers["access-control-allow-origin"] in ("*", "http://localhost:5555")
```

- [ ] **Step 4:** Run `pytest tests/integration/test_saude.py -v`. Expected: FAIL (import de `pythonisa_api.main`).
- [ ] **Step 5:** implementar `config.py`, `main.py` e `api/v1/saude.py`:
  - `create_app` monta o `CORSMiddleware` com `settings.cors_origins` e o router v1 em `/api/v1`;
  - `modelo_carregado` fica fixo em `False` até a Parte 2.
- [ ] **Step 6:** Run `pytest -v && ruff check . && ruff format --check .`. Expected: tudo passa.
- [ ] **Step 7:** README com seções "Requisitos", "Instalação", "Rodar" (`uvicorn pythonisa_api.main:app --reload`, com `app = create_app()` no módulo) e "Testes/Lint". Conferir subindo o servidor e chamando `curl localhost:8000/api/v1/health`.
- [ ] **Step 8:** commit `feat: base do projeto FastAPI com /health`.

### Task 2: Banco de dados (8 entidades) e `init-db`

**Files:**
- Create: `src/pythonisa_api/tempo.py`, `src/pythonisa_api/db/__init__.py`, `src/pythonisa_api/db/base.py`, `src/pythonisa_api/db/models.py`, `src/pythonisa_api/cli.py`, `src/pythonisa_api/api/deps.py`
- Modify: `src/pythonisa_api/main.py` (engine e sessão no `app.state`)
- Test: `tests/unit/test_tempo.py`, `tests/integration/test_models.py`, `tests/integration/test_cli.py`

**Interfaces:**
- Consumes: `Settings.database_url`.
- Produces:
  - `tempo.FUSO: ZoneInfo`
  - `tempo.para_local_naive(dt: datetime) -> datetime`: um datetime aware é convertido para o FUSO e perde o tz; um naive é devolvido sem mudança.
  - `tempo.para_aware(dt: datetime) -> datetime`: anexa o FUSO a um naive.
  - `tempo.agora_local() -> datetime`: naive.
  - `db.base.Base(DeclarativeBase)`, `criar_engine(url: str) -> Engine`, `criar_fabrica_sessao(engine) -> sessionmaker[Session]`, `criar_tabelas(engine) -> None`.
    - `criar_engine` cria o diretório do arquivo SQLite e liga `PRAGMA foreign_keys=ON` via `event.listens_for(engine, "connect")`.
  - Modelos em `db/models.py`:

    | Classe | Tabela |
    |---|---|
    | `Linha` | `linha` |
    | `PadraoLetreiro` | `padrao_letreiro` |
    | `Parada` | `parada` |
    | `RotaParada` | `rota_parada` |
    | `HorarioProgramado` | `horario_programado` |
    | `Viagem` | `viagem` |
    | `RegistroDeteccao` | `registro_deteccao` |
    | `PrevisaoViagem` | `previsao_viagem` |

    - Colunas conforme a spec 3.2, incluindo `RegistroDeteccao.ordem_itinerario`.
    - PKs string de `Viagem`, `RegistroDeteccao` e `PrevisaoViagem` com default `uuid4().hex`.
    - `RotaParada` com PK `(id_linha, ordem)`.
    - `UniqueConstraint`: `padrao_letreiro(id_linha, padrao)` e `horario_programado(id_linha, tipo_dia, hora_partida)`.
    - `CheckConstraint` para os domínios fechados e para `confianca_ocr` entre 0 e 1.
    - `relationship`: `Linha.itinerario` (ordenado por `RotaParada.ordem`), `Linha.padroes`, `RotaParada.parada`.
  - `api.deps.obter_sessao(request) -> Iterator[Session]`: sessão de `request.app.state.fabrica_sessao`.
  - CLI: `python -m pythonisa_api.cli init-db` (argparse com subcomandos).
  - Fixture `sessao` em `conftest.py`: a fixture `app` passa a chamar `criar_tabelas(app.state.engine)`, e `sessao` abre a partir de `app.state.fabrica_sessao`. Assim o teste e o `cliente` enxergam o mesmo banco temporário.

- [ ] **Step 1: testes que falham**
  - `test_tempo.py`:
    - `para_local_naive(datetime(2026,11,8,12,0,tzinfo=UTC)) == datetime(2026,11,8,9,0)`;
    - `para_aware(datetime(2026,11,8,9,0)).isoformat().endswith("-03:00")`.
  - `test_models.py`:
    - `test_fk_ativa`: `RotaParada` com `id_linha` inexistente → `IntegrityError` no `flush`;
    - `test_pk_rota_parada_linha_ordem`: duas `RotaParada` com a mesma `(id_linha, ordem)` → `IntegrityError`;
    - `test_mesma_parada_duas_vezes_na_linha_permitido`: mesma parada em ordens 1 e 5 → OK;
    - `test_sentido_invalido`: `sentido="norte"` → `IntegrityError`;
    - `test_confianca_fora_do_intervalo`: `confianca_ocr=1.5` → `IntegrityError`;
    - `test_itinerario_ordenado`: inseridas as ordens 3, 1, 2 → `[r.ordem for r in linha.itinerario] == [1,2,3]`.
  - `test_cli.py`:
    - `test_init_db_cria_tabelas(tmp_path, monkeypatch)`: com `DATABASE_URL` apontando para `tmp_path`, `cli.main(["init-db"])` retorna 0;
    - o `inspect(engine).get_table_names()` contém as 8 tabelas.
- [ ] **Step 2:** Run `pytest -v`. Expected: FAIL (módulos inexistentes).
- [ ] **Step 3:** implementar `tempo.py`, `db/base.py`, `db/models.py`, `cli.py` e `api/deps.py`. Em `create_app`, guardar `app.state.engine` e `app.state.fabrica_sessao` (sem criar tabelas na subida: isso é papel do `init-db`).
- [ ] **Step 4:** Run `pytest -v && ruff check . && ruff format --check .`. Expected: tudo passa.
- [ ] **Step 5:** commit `feat: modelos SQLAlchemy das 8 entidades e comando init-db`.

### Task 3: Seed (dados das linhas) e comando `seed`

**Files:**
- Create: `src/pythonisa_api/services/__init__.py`, `src/pythonisa_api/services/geo.py`, `src/pythonisa_api/seed/__init__.py`, `src/pythonisa_api/seed/carregar.py`
- Create: `src/pythonisa_api/seed/dados/{linhas,paradas,itinerarios,grade,letreiros}.json` (dados reais estimados)
- Create: `tests/fixtures/seed_mini/{linhas,paradas,itinerarios,grade,letreiros}.json`
- Modify: `src/pythonisa_api/cli.py` (subcomando `seed`)
- Test: `tests/unit/test_geo.py`, `tests/integration/test_seed.py`

**Interfaces:**
- Produces:
  - `geo.haversine_metros(lat1, lon1, lat2, lon2) -> float` (R = 6 371 000 m).
  - `seed.carregar.DIRETORIO_PADRAO: Path`.
  - `seed.carregar.carregar_seed(sessao: Session, diretorio: Path = DIRETORIO_PADRAO) -> ResumoSeed` (dataclass com `linhas`, `paradas`, `itens_itinerario`, `horarios` e `padroes`, todos `int`).
  - `seed.carregar.ErroSeed(Exception)`.
  - Fixture `sessao_com_seed_mini`.

**Formato dos JSONs:**

```json
// linhas.json
[{"id": "macapaba-amapa-garden", "codigo": null, "nome": "Macapaba - Amapá Garden", "empresa": "Capital Morena"}]
// paradas.json
[{"id": "unifap-guarita-jk-ida", "nome": "UNIFAP - Guarita Rod. JK", "referencia": "lado da UNIFAP", "latitude": 0.0, "longitude": 0.0}]
// itinerarios.json — ordem = posição na lista (1..N); o circuito não repete a parada inicial no fim
{"macapaba-amapa-garden": [{"id_parada": "terminal-macapaba", "sentido": "ida"}]}
// grade.json — chaves de tipo_dia opcionais; "fim" inclusivo se cair no intervalo
{"macapaba-amapa-garden": {"util": {"inicio": "05:30", "fim": "22:00", "intervalo_min": 30},
                           "sabado": {"inicio": "05:30", "fim": "22:00", "intervalo_min": 45},
                           "domingo": {"inicio": "06:00", "fim": "21:00", "intervalo_min": 60}}}
// letreiros.json
{"macapaba-amapa-garden": [{"padrao": "MACAPABA GARDEN", "prioridade": 0}]}
```

**`minutos_programados`:**
- Na ordem 1 vale 0.
- Na ordem k vale `round(distancia_acumulada_m × 1.3 / (20 000 / 60))`.
- A distância acumulada é a soma das haversines entre paradas consecutivas e o arredondamento é feito sobre o acumulado.

**Seed mini (`tests/fixtures/seed_mini`):**
- **Paradas:**

  | id | lat | lon |
  |---|---|---|
  | `p1` | 0.0 | −51.0 |
  | `p2` | 0.0 | −51.009 |
  | `p3` | 0.009 | −51.009 |
  | `p4` | 0.009 | −51.0 |
  | `p5` | 0.018 | −51.009 |

- **Linhas:**
  - `linha-a` ("Linha A", empresa "Empresa X"), itinerário p1 ida, p2 ida, p3 ida, p4 volta;
  - `linha-b` ("Linha B", empresa null), itinerário p5 ida, p3 ida, p2 volta.
- **Grade:** as duas linhas com `util` 06:00–07:00/30 (3 horários) e `sabado` 06:00–06:00/60 (1 horário).
- **Letreiros:** `linha-a` `["ALFA CENTRO"]`, `linha-b` `["BETA CENTRO"]`.

- [ ] **Step 1: testes que falham**
  - `test_geo.py`: `haversine_metros(0, -51, 0, -51.009) == pytest.approx(1000.75, abs=0.5)`.
  - `test_seed.py`, com o seed mini:
    - `test_resumo`: `ResumoSeed(linhas=2, paradas=5, itens_itinerario=7, horarios=8, padroes=2)`;
    - `test_minutos_programados_linha_a`: `[0, 4, 8, 12]`;
    - `test_grade_expandida`: horários `util` da `linha-a` = 06:00, 06:30, 07:00;
    - `test_idempotente`: rodar duas vezes mantém as contagens no banco;
    - `test_itinerario_substituido`: rodar de novo com um diretório cópia em que `linha-a` tem só p1 e p2 deixa 2 itens;
    - `test_parada_inexistente_no_itinerario`: levanta `ErroSeed` com o id da parada na mensagem;
    - `test_sentido_invalido`: levanta `ErroSeed`;
    - `test_seed_real_valido`: `carregar_seed(sessao)` com `DIRETORIO_PADRAO` executa sem erro, tem 2 linhas, cada linha tem ≥ 8 itens no itinerário, e existe ao menos 1 parada atendida pelas duas linhas.
- [ ] **Step 2:** Run `pytest tests/unit/test_geo.py tests/integration/test_seed.py -v`. Expected: FAIL.
- [ ] **Step 3:** implementar `geo.py` e `carregar.py`:
  - upsert de `Linha` e `Parada` via `sessao.merge`;
  - `RotaParada` da linha apagada e reinserida;
  - `HorarioProgramado` e `PadraoLetreiro` inseridos só se não existirem (pelas unique constraints);
  - validação antes de gravar (parada existente, sentido válido, linha conhecida em todos os arquivos), levantando `ErroSeed`;
  - commit único no fim.

  Adicionar o subcomando `seed` ao CLI.
- [ ] **Step 4:** Run os testes do mini. Expected: PASS, exceto `test_seed_real_valido`.
- [ ] **Step 5: levantar os dados reais** das linhas Macapaba – Amapá Garden e Brasil Novo – Universidade:
  - consultar no OpenStreetMap (Overpass API: `highway=bus_stop` e relações `route=bus` na área de Macapá, bbox aprox. `-0.02,-51.15,0.12,-51.03`) e no mapa público;
  - montar o itinerário plausível (8 a 12 paradas por sentido), com as paradas da UNIFAP dos dois lados da Rod. JK compartilhadas pelas duas linhas;
  - preencher os 5 JSONs reais e marcar no README que itinerários e coordenadas são **estimados e simulados, pendentes de validação do grupo**.
- [ ] **Step 6:** Run `pytest -v && ruff check . && ruff format --check .`. Expected: tudo passa. Run `python -m pythonisa_api.cli init-db && python -m pythonisa_api.cli seed`. Expected: imprime o resumo.
- [ ] **Step 7:** commit `feat: seed das linhas Macapaba-Amapá Garden e Brasil Novo-Universidade`.

### Task 4: Endpoints de consulta e formato de erro

**Files:**
- Create: `src/pythonisa_api/erros.py`, `src/pythonisa_api/api/erros.py`, `src/pythonisa_api/schemas/__init__.py`, `src/pythonisa_api/schemas/consulta.py`, `src/pythonisa_api/services/consulta.py`, `src/pythonisa_api/api/v1/linhas.py`, `src/pythonisa_api/api/v1/paradas.py`
- Modify: `src/pythonisa_api/main.py`, `src/pythonisa_api/services/geo.py`
- Test: `tests/integration/test_api_consulta.py`

**Interfaces:**
- Consumes: modelos (Task 2), `haversine_metros` (Task 3), fixture `sessao_com_seed_mini`.
- Produces:
  - `erros.ErroDominio(Exception)`, com atributos `codigo: str` e `mensagem: str`, e as subclasses `LinhaNaoEncontrada(id_linha)`, `ParadaNaoEncontrada(id_parada)`, `ParadaForaDaLinha(id_linha, id_parada)`, `LetreiroDesconhecido(texto)`, `LetreiroAmbiguo(texto, ids_linhas)`, `ConfiancaBaixa(valor, minimo)`, `DadosInvalidos(mensagem)`.
  - `api.erros.registrar_tratadores(app)`:
    - `ErroDominio` → status pela tabela de Global Constraints;
    - `RequestValidationError` → 422 `DADOS_INVALIDOS`, com a mensagem resumindo campo e erro;
    - `StarletteHTTPException` 404 → `NAO_ENCONTRADO`.
  - Schemas: `LinhaSaida(id, codigo, nome, empresa)`, `LinhaResumo(id, nome)`, `ParadaSaida(id, nome, referencia, latitude, longitude)`, `ItemItinerario(ordem, sentido, minutos_programados, parada: ParadaSaida)`, `ItinerarioSaida(linha: LinhaResumo, itinerario: list[ItemItinerario])`, `ParadaProximaSaida(parada: ParadaSaida, distancia_metros: int)`.
  - Serviços:
    - `services.consulta.listar_linhas(sessao) -> list[Linha]` (ordem por nome);
    - `obter_linha(sessao, id_linha) -> Linha` (levanta `LinhaNaoEncontrada`);
    - `listar_paradas(sessao, id_linha: str | None) -> list[Parada]` (sem repetição, ordem por nome);
    - `obter_parada(sessao, id_parada) -> Parada`;
    - `linhas_da_parada(sessao, id_parada) -> list[Linha]`;
    - `geo.parada_mais_proxima(paradas: Sequence[Parada], latitude, longitude) -> tuple[Parada, float]`.
  - Rotas:
    - `GET /linhas`
    - `GET /linhas/{id_linha}/paradas`
    - `GET /paradas?id_linha=`
    - `GET /paradas/proxima?latitude=&longitude=` (Query com `ge=-90, le=90` / `ge=-180, le=180`)
    - `GET /paradas/{id_parada}/linhas`

- [ ] **Step 1: testes que falham** (sobre o seed mini)
  - `GET /linhas` → 2 itens; o primeiro é `{"id":"linha-a","codigo":None,"nome":"Linha A","empresa":"Empresa X"}`.
  - `GET /linhas/linha-a/paradas`:
    - `linha == {"id":"linha-a","nome":"Linha A"}`;
    - as ordens `[1,2,3,4]`;
    - o item 4 tem `sentido=="volta"` e `minutos_programados==12`;
    - `parada.id=="p4"`.
  - `GET /linhas/xyz/paradas` → 404, com `erro.codigo=="LINHA_NAO_ENCONTRADA"`.
  - `GET /paradas` → 5 itens.
  - `GET /paradas?id_linha=linha-b` → ids `{"p5","p3","p2"}`.
  - `GET /paradas/proxima?latitude=0.0085&longitude=-51.0085` → `parada.id=="p3"`, com `distancia_metros` entre 60 e 85.
  - `GET /paradas/proxima?latitude=200&longitude=0` → 422 `DADOS_INVALIDOS`.
  - `GET /paradas/proxima` sem parâmetros → 422 `DADOS_INVALIDOS`.
  - `GET /paradas/p3/linhas` → ids `["linha-a","linha-b"]`.
  - `GET /paradas/zzz/linhas` → 404 `PARADA_NAO_ENCONTRADA`.
  - `GET /rota-que-nao-existe` → 404, com o corpo contendo a chave `"erro"` e `erro.codigo=="NAO_ENCONTRADO"`.
- [ ] **Step 2:** Run `pytest tests/integration/test_api_consulta.py -v`. Expected: FAIL.
- [ ] **Step 3:** implementar `erros.py`, `api/erros.py`, os schemas, os serviços e as rotas. Declarar `/paradas/proxima` antes das rotas com `{id_parada}`.
- [ ] **Step 4:** Run `pytest -v && ruff check . && ruff format --check .`. Expected: tudo passa.
- [ ] **Step 5:** commit `feat: endpoints de consulta de linhas e paradas`.

### Task 5: Registrar passagem (versão simples)

> **Revisado em 2026-11-09:** o usuário pediu para manter o projeto simples. Ficaram de fora a resolução de letreiro, a deduplicação, o limiar de confiança e a associação automática de viagens em ordem > 1. Esses itens entram quando a integração com a VC for priorizada. A tabela `padrao_letreiro` e o seed continuam, mas sem lógica.

**Files:**
- Create: `src/pythonisa_api/services/passagem.py`, `src/pythonisa_api/schemas/passagem.py`, `src/pythonisa_api/api/v1/deteccoes.py`
- Modify: `src/pythonisa_api/erros.py`, `src/pythonisa_api/api/erros.py` (remove códigos de letreiro e confiança), `src/pythonisa_api/config.py` e `.env.example` (remove `CONFIANCA_OCR_MINIMA` e `JANELA_ASSOCIACAO_MIN`)
- Test: `tests/integration/test_passagem.py`

**Interfaces:**
- `schemas.passagem.PassagemEntrada`:
  - `id_linha: str`, `id_parada: str`;
  - `timestamp_passagem: AwareDatetime`;
  - `origem: Literal["simulado","ocr"] = "simulado"`;
  - `id_viagem: str | None = None`;
  - `texto_letreiro: str | None = None` (max 200);
  - `confianca_ocr: float | None = None` (0..1).
- `schemas.passagem.PassagemSaida(id, id_linha, id_parada, id_viagem, ordem_itinerario, timestamp_passagem, origem)`, com `timestamp_passagem` devolvido com offset `-03:00`.
- `services.passagem.registrar_passagem(sessao, entrada: PassagemEntrada) -> RegistroDeteccao`:
  1. Busca linha e parada (404 se não existirem).
  2. Calcula as ordens da parada no itinerário; se não houver, levanta `ParadaForaDaLinha`.
  3. Com `id_viagem` informado, a viagem precisa existir e ser da linha (senão `DadosInvalidos`); a ordem usada é a primeira ordem da parada.
  4. Sem `id_viagem` e com a ordem 1 entre as ordens, cria uma `Viagem` ligada ao horário programado mais próximo (±15 min, do tipo de dia da data).
  5. Nos demais casos, `id_viagem=None`.
- `services.passagem.horario_mais_proximo(sessao, id_linha, momento: datetime) -> HorarioProgramado | None`.
- Rota `POST /api/v1/deteccoes` → 201.

- [ ] **Step 1: testes que falham** (seed mini; segunda-feira 2026-11-09, offset `-03:00`)
  - `p1` 06:01 em `linha-a` → 201, `ordem_itinerario==1`, `id_viagem` não nulo, viagem ligada ao horário 06:00 `util`;
  - `p1` 08:00 → viagem sem horário;
  - `p1` no sábado 2026-11-14 06:05 → viagem ligada ao horário 06:00 `sabado`;
  - `p2` 06:05 com o `id_viagem` anterior → mesmo `id_viagem`, ordem 2;
  - `p2` sem `id_viagem` → `id_viagem` nulo, ordem 2;
  - `p5` em `linha-a` → 422 `PARADA_FORA_DA_LINHA`;
  - linha `xyz` → 404 `LINHA_NAO_ENCONTRADA`; parada `zzz` → 404 `PARADA_NAO_ENCONTRADA`;
  - timestamp sem offset → 422 `DADOS_INVALIDOS`;
  - `id_viagem` inexistente → 422 `DADOS_INVALIDOS`;
  - `"2026-11-09T09:01:00Z"` → resposta com `timestamp_passagem == "2026-11-09T06:01:00-03:00"`.
- [ ] **Step 2:** Run `pytest tests/integration/test_passagem.py -v`. Expected: FAIL.
- [ ] **Step 3:** implementar.
- [ ] **Step 4:** Run `pytest -v && ruff check . && ruff format --check .`. Expected: tudo passa.
- [ ] **Step 5:** commit `feat: registrar passagem (POST /deteccoes) em versão simples`.

---

**Fim da Parte 1.** Entregáveis:
- o servidor sobe com os dados das duas linhas;
- o app já consegue listar linhas, paradas, itinerários, a parada mais próxima e as linhas de cada parada;
- a VC tem `POST /deteccoes` funcionando.

A Parte 2 cobre o simulador de tráfego, o ML, `/previsoes` e o simulador ao vivo.
