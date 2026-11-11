# Previsão de Chegada (Parte 2) — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Criar o `GET /api/v1/previsoes`, primeiro com o horário programado (Nível 1) e depois com o previsto vindo de uma regressão linear treinada em histórico simulado (Nível 2), sem mudar o JSON.

**Architecture:**
- `services/previsao.py` escolhe a próxima chegada a partir da grade.
- A duração até a parada vem dos `minutos_programados` (Nível 1) ou de um `PreditorTrecho` (Nível 2).
- O simulador grava o histórico direto no banco.
- O comando `treinar` gera `data/modelo.joblib`. O app carrega esse arquivo na subida (`app.state.preditor`); se ele não existir, o app funciona no Nível 1.

**Tech Stack:** o da Parte 1, mais `scikit-learn` (que já traz `numpy` e `joblib`). Sem pandas.

**Spec:** `docs/superpowers/specs/2026-11-08-servidor-fastapi-mvp-design.md`. A **seção 12** é a autoridade e prevalece sobre 5.1, 6.3 e 7.4.

## Global Constraints

- **Manter simples (preferência do dono):**
  - nada de tarefa em segundo plano, retreino pela API, gravação de previsões, painel da parada ou comando `resetar`;
  - só o que está nas tasks abaixo.
- **Contrato:** o JSON de `/previsoes` é o da spec, seção 12, e é idêntico nos Níveis 1 e 2. Datas saem com offset `-03:00`. Erros seguem o formato padrão `{"erro": {"codigo", "mensagem"}}`.
- **`agora`:** parâmetro opcional que exige fuso. Sem ele, vale `tempo.agora_local()`.
- **`situacao`:**
  - `adiantado` se `diferenca_minutos < -1`;
  - `atrasado` se `> 1`;
  - `no_horario` nos demais casos;
  - `sem_servico` quando não há chegada ≥ `agora` no dia. Nesse caso horários, minutos e diferença vêm `null`.
- **Arredondamentos:**
  - `minutos_restantes = round((previsto - agora).total_seconds() / 60)`;
  - `diferenca_minutos = round((previsto - programado).total_seconds() / 60)`.
- **Tipo de dia:** reutilizar `services.passagem.TIPO_DIA_POR_DIA_DA_SEMANA`.
- **Simulador:**
  - `Δt = max(30, programado_trecho_s × fator_horario × fator_dia × ruído)`;
  - `fator_horario` = 1,3 em [06:30, 08:30), [11:30, 13:30) e [17:00, 19:00), senão 0,85;
  - `fator_dia`: util 1,0, sabado 0,9, domingo 0,8;
  - ruído `lognormvariate(0, 0.1)`;
  - atraso de partida `gauss(0, 120)` s;
  - `random.Random(semente)`, com semente padrão 42.
- **Configuração nova:** `CAMINHO_MODELO` (padrão `data/modelo.joblib`).
- **Execução:** comandos no venv, a partir de `pythonisaFastApi/`. Toda task termina com `pytest -q -W error`, `ruff check .` e `ruff format --check .` limpos.

## Review Focus

- `agora` sem fuso → 422 `DADOS_INVALIDOS`. Teste na Task 1.
- Depois da última partida do dia, ou num dia sem grade → `sem_servico` com campos `null`, sem erro 500. Teste na Task 1.
- Rodar `simular-historico` duas vezes não duplica dias já simulados. Teste na Task 2.
- `treinar` sem histórico → mensagem pedindo `simular-historico` e saída 1, sem traceback. Teste na Task 3.
- Arquivo de modelo ausente ou corrompido → o servidor sobe no Nível 1 (`modelo_carregado: false`). Teste na Task 3.

---

### Task 1: `GET /previsoes`, Nível 1 (horário programado)

**Files:**
- Create: `src/pythonisa_api/services/previsao.py`, `src/pythonisa_api/schemas/previsao.py`, `src/pythonisa_api/api/v1/previsoes.py`
- Modify: `src/pythonisa_api/api/v1/__init__.py` (incluir o router)
- Test: `tests/integration/test_previsao.py`

**Interfaces:**
- Produces:
  - `services.previsao.Previsao` (dataclass), com os campos:
    - `linha: Linha` e `parada: Parada`;
    - `situacao: str`;
    - `horario_programado`, `horario_previsto` e `gerado_em`: `datetime` (o `gerado_em` não é opcional; os dois horários aceitam `None`);
    - `minutos_restantes` e `diferenca_minutos`: `int | None`;
    - `versao_modelo: str | None`.
  - `services.previsao.prever_chegada(sessao, id_linha: str, id_parada: str, agora: datetime, preditor=None) -> Previsao`. O `agora` é naive local; o `preditor` só é usado na Task 4.
  - `schemas.previsao.PrevisaoSaida`, com os campos do JSON da spec 12. Os datetimes saem com `para_aware(...).isoformat()` via `field_serializer`.
  - A rota usa `agora: AwareDatetime | None = Query(None)` e converte com `para_local_naive`.
- **Algoritmo de `prever_chegada`:**
  1. Busca linha e parada (404 se não existirem). As ordens da parada na linha vêm do itinerário; se não houver, `ParadaForaDaLinha`.
  2. Para cada horário da grade (`tipo_dia` de `agora`) e cada ordem `k` da parada:
     - `partida = combine(agora.date(), hora_partida)`;
     - `programado = partida + minutos_programados[k]`;
     - `previsto = programado`, no Nível 1.
  3. Escolhe o menor `previsto ≥ agora`. Se não houver, `sem_servico`.

- [ ] **Step 1: testes que falham** (seed mini via fixture `api`, linha-a, segunda 2026-11-09)

```python
def _prever(api, id_parada, agora, id_linha="linha-a"):
    return api.get("/api/v1/previsoes",
                   params={"id_linha": id_linha, "id_parada": id_parada, "agora": agora})
```
  - `test_proxima_partida_ainda_por_vir`: p3 com `agora` em `2026-11-09T06:10:00-03:00`. Espera 200, `horario_programado == horario_previsto == "2026-11-09T06:38:00-03:00"`, `minutos_restantes == 28`, `diferenca_minutos == 0`, `situacao == "no_horario"`, `versao_modelo is None`, `gerado_em == "2026-11-09T06:10:00-03:00"`, `linha == {"id": "linha-a", "nome": "Linha A"}` e `parada["id"] == "p3"`.
  - `test_agora_em_utc`: `"2026-11-09T09:10:00Z"` dá o mesmo resultado do teste anterior.
  - `test_sabado_usa_grade_de_sabado`: p2 em `2026-11-14T05:50:00-03:00` → programado `06:04`.
  - `test_sem_servico_depois_da_ultima_partida`: p3 em `07:30` → `situacao == "sem_servico"`, com horários, minutos e diferença `None`.
  - `test_domingo_sem_grade`: p3 em `2026-11-15T06:00:00-03:00` → `sem_servico`.
  - `test_parada_fora_da_linha`: p5 → 422 `PARADA_FORA_DA_LINHA`.
  - `test_linha_inexistente`: `xyz` → 404 `LINHA_NAO_ENCONTRADA`.
  - `test_agora_sem_fuso`: `"2026-11-09T06:10:00"` → 422 `DADOS_INVALIDOS`.
  - `test_sem_agora_usa_relogio`: sem o parâmetro → 200.
- [ ] **Step 2:** Run `pytest tests/integration/test_previsao.py -v`. Expected: FAIL (404 na rota).
- [ ] **Step 3:** implementar serviço, schema e rota.
- [ ] **Step 4:** Run `pytest -q -W error && ruff check . && ruff format --check .`. Expected: tudo passa.
- [ ] **Step 5:** commit `feat: GET /previsoes com horário programado (nível 1)`.

### Task 2: Simulador de histórico

**Files:**
- Create: `src/pythonisa_api/simulador/__init__.py`, `src/pythonisa_api/simulador/historico.py`
- Modify: `src/pythonisa_api/cli.py`. Os comandos passam a receber `(engine, settings, args)`, e entra o subcomando `simular-historico --dias N` (padrão 60, até ontem).
- Test: `tests/unit/test_trafego.py`, `tests/integration/test_simulador.py`

**Interfaces:**
- Produces:
  - `simulador.historico.fator_horario(hora: time) -> float`
  - `simulador.historico.fator_dia(tipo_dia: str) -> float`
  - `simulador.historico.simular_historico(sessao, ate: date, dias: int, semente: int = 42) -> int`:
    - retorna o número de passagens gravadas;
    - simula os dias `[ate - dias, ate - 1]`;
    - **pula as datas que já têm viagem `origem="simulado"`**;
    - para cada horário da grade do dia, cria uma `Viagem` com `id_horario` e `origem="simulado"` e grava um `RegistroDeteccao` por item do itinerário, com `ordem_itinerario`, `origem="simulado"` e `recebido_em = timestamp`;
    - o tempo de cada trecho segue a fórmula de Global Constraints;
    - faz um commit por dia.

- [ ] **Step 1: testes que falham**
  - unit:
    - `fator_horario(time(7, 0)) == 1.3`, `fator_horario(time(6, 29)) == 0.85`, `fator_horario(time(8, 30)) == 0.85`, `fator_horario(time(18, 0)) == 1.3`;
    - `fator_dia("domingo") == 0.8`.
  - integration, sobre o seed mini, com `ate = date(2026, 11, 11)` e `dias=2` (segunda e terça):
    - retorna `42`: por dia, 3 partidas × 4 paradas na linha-a mais 3 × 3 na linha-b;
    - em toda viagem as ordens são `1..N` e os timestamps são crescentes;
    - toda viagem tem `id_horario` preenchido;
    - toda passagem tem `origem == "simulado"`;
    - rodar de novo com os mesmos argumentos retorna `0` e a contagem no banco não muda;
    - o CLI `simular-historico --dias 1` depois de `init-db` e `seed` (seed real, banco em `tmp_path`) retorna `0` e imprime "Histórico simulado".
- [ ] **Step 2:** Run os testes novos. Expected: FAIL (módulo inexistente).
- [ ] **Step 3:** implementar.
- [ ] **Step 4:** suíte inteira, ruff e format limpos.
- [ ] **Step 5:** commit `feat: simulador de histórico de passagens com efeito de pico`.

### Task 3: Treino da regressão e carregamento do modelo

**Files:**
- Modify: `pyproject.toml` (adicionar `scikit-learn`), `src/pythonisa_api/config.py` (`caminho_modelo: str = "data/modelo.joblib"`), `.env.example`, `src/pythonisa_api/main.py`, `src/pythonisa_api/api/v1/saude.py`, `src/pythonisa_api/api/deps.py`, `src/pythonisa_api/cli.py` (subcomando `treinar`), `src/pythonisa_api/api/erros.py` (código `MODELO_NAO_TREINADO` → 404), `src/pythonisa_api/erros.py`
- Create: `src/pythonisa_api/ml/__init__.py`, `src/pythonisa_api/ml/modelo.py`, `src/pythonisa_api/api/v1/modelo.py`
- Test: `tests/integration/test_modelo.py`

**Interfaces:**
- Consumes: `simular_historico` (Task 2).
- Produces, em `ml/modelo.py`:
  - `Trecho` (dataclass): `id_linha: str`, `ordem_origem: int`, `momento: datetime`, `segundos: float`.
  - `montar_trechos(sessao) -> list[Trecho]`: pares de registros consecutivos (`ordem` e `ordem+1`) da mesma viagem, descartando `segundos <= 0` ou `> 3600`.
  - `PreditorTrecho`: atributos `versao: str` e `metricas: dict`, e o método `prever_segundos(id_linha, ordem_origem, momento) -> float`. Por dentro, é um `Pipeline(OneHotEncoder(handle_unknown="ignore"), LinearRegression())` sobre as colunas `[f"{id_linha}:{ordem}", str(momento.hour), tipo_dia]`.
  - `treinar(trechos, dias_teste: int = 7) -> PreditorTrecho`:
    - divisão temporal: o teste fica com os trechos cuja data é maior que `max(data) - dias_teste`;
    - `metricas = {"mae_segundos", "mae_baseline_segundos", "r2", "amostras_treino", "amostras_teste", "treinado_em"}`;
    - o baseline é a média por (trecho, hora) no treino, com fallback para a média global;
    - `versao = "regressao-linear-" + treinado_em`, com `treinado_em` no formato `YYYY-MM-DDTHH:MM`;
    - levanta `ValueError` se houver menos de 50 trechos.
  - `salvar_preditor(preditor, caminho: Path)` (via `joblib.dump`).
  - `carregar_preditor(caminho: Path) -> PreditorTrecho | None`: devolve `None` se o arquivo não existir **ou** se falhar ao carregar.
- O app faz `app.state.preditor = carregar_preditor(Path(settings.caminho_modelo))`.
- `api.deps.obter_preditor(request)` devolve `app.state.preditor`.
- `/health` passa a devolver `modelo_carregado = preditor is not None`.
- Rota `GET /api/v1/modelo`:
  - sem modelo: 404 `MODELO_NAO_TREINADO`;
  - com modelo: `{"versao", **metricas}`.
- CLI `treinar`: monta os trechos, treina, salva em `settings.caminho_modelo` e imprime MAE do modelo × baseline. Se `treinar` levantar `ValueError`, imprime "Histórico insuficiente: rode simular-historico antes." no stderr e retorna 1.

- [ ] **Step 1: testes que falham** (seed mini com `simular_historico(ate=date(2026, 11, 28), dias=21)`)
  - `montar_trechos` devolve exatamente `3 × (viagens da linha-a) + 2 × (viagens da linha-b)` trechos (itinerários de 4 e 3 paradas), com as viagens contadas no banco. Todos os `segundos` são > 0.
  - `treinar(...)` gera um preditor com `prever_segundos("linha-a", 1, datetime(2026, 11, 30, 7, 0)) > prever_segundos("linha-a", 1, datetime(2026, 11, 30, 6, 0))`. O pico entra às 06:30, e a hora 7 só tem viagens de pico. As `metricas` têm as 6 chaves.
  - `treinar([])` levanta `ValueError`.
  - `salvar_preditor` e depois `carregar_preditor` devolvem a mesma `versao` e a mesma previsão.
  - Um caminho inexistente devolve `None`; um arquivo com bytes aleatórios também devolve `None`.
  - App com `caminho_modelo` apontando para um modelo salvo: `/health` traz `modelo_carregado: true` e `GET /modelo` responde 200 com `versao` e `mae_segundos`. Sem modelo: `false` e 404 `MODELO_NAO_TREINADO`. Para isso, a fixture `settings_teste` passa a usar `caminho_modelo=str(tmp_path / "modelo.joblib")`.
  - CLI `treinar` sem histórico (banco com `init-db` e `seed`) retorna 1, e o stderr contém `simular-historico`.
- [ ] **Step 2:** `pip install -e ".[dev]"` e depois rodar os testes novos. Expected: FAIL.
- [ ] **Step 3:** implementar.
- [ ] **Step 4:** suíte inteira, ruff e format limpos.
- [ ] **Step 5:** commit `feat: treino da regressão linear de tempo entre paradas`.

### Task 4: `/previsoes` usa a regressão (Nível 2) e documentação

**Files:**
- Modify: `src/pythonisa_api/services/previsao.py`, `src/pythonisa_api/api/v1/previsoes.py`, `README.md`, `docs/CONTEXTO-IA.md`
- Test: `tests/integration/test_previsao.py`

**Interfaces:**
- Consumes: `PreditorTrecho` e `obter_preditor` (Task 3).
- **Mudança em `prever_chegada`:** com `preditor`, o previsto deixa de ser igual ao programado:
  - `t = partida`;
  - para cada ordem `i` de 1 a `k−1`: `t += timedelta(seconds=preditor.prever_segundos(id_linha, i, t))`;
  - `previsto = t` e `versao_modelo = preditor.versao`.
- A rota passa `obter_preditor(request)`.

- [ ] **Step 1: testes que falham**, com o preditor falso abaixo atribuído a `app.state.preditor`:

```python
class PreditorFixo:
    versao = "fixo"
    def __init__(self, segundos=120.0):
        self.segundos, self.chamadas = segundos, []
    def prever_segundos(self, id_linha, ordem_origem, momento):
        self.chamadas.append((ordem_origem, momento.time()))
        return self.segundos
```
  - `test_previsto_vem_do_modelo`: p3 em `06:10`. Espera `horario_programado` `06:38`, `horario_previsto` `06:34`, `diferenca_minutos == -4`, `situacao == "adiantado"`, `minutos_restantes == 24` e `versao_modelo == "fixo"`. As chamadas para a viagem escolhida incluem `(1, time(6, 30))` e `(2, time(6, 32))`.
  - `test_previsto_atrasado`: `PreditorFixo(300)` com p3 e `agora` em `06:05`. A viagem das 06:00 chega a p3 às 06:10 (programado 06:08): `horario_previsto` `06:10`, `diferenca_minutos == 2`, `minutos_restantes == 5` e `situacao == "atrasado"`.
- [ ] **Step 2:** Run. Expected: FAIL (o previsto ainda é igual ao programado).
- [ ] **Step 3:** implementar.
- [ ] **Step 4:** suíte inteira, ruff e format limpos. Depois, um teste manual no banco real: `init-db`, `seed`, `simular-historico`, `treinar` e o `uvicorn`. Comparar `GET /previsoes` para `macapaba-amapa-garden` + `unifap-portaria-jk-ida` com `agora` às 07:20 (pico) e às 10:20 (fora do pico). Esperado: previsto depois do programado no pico e antes fora dele.
- [ ] **Step 5:** documentação:
  - **README:** seção "Previsão", com os comandos `simular-historico` e `treinar` e um exemplo de `/previsoes` com `agora`;
  - **CONTEXTO-IA:** marcar a Parte 2 como feita e listar o endpoint novo.

  Commit `feat: previsão com regressão linear (nível 2)`.
