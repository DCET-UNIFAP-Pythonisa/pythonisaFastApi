# Pythonisa — Servidor Intermediário (FastAPI)

API entre o app Flutter e os dados do Pythonisa: linhas, paradas, itinerários, registros de passagem (SQLite) e previsão de chegada por Regressão Linear.

- Design: [`docs/superpowers/specs/2026-11-08-servidor-fastapi-mvp-design.md`](docs/superpowers/specs/2026-11-08-servidor-fastapi-mvp-design.md)
- Plano (parte 1): [`docs/superpowers/plans/2026-11-08-fundacao-servidor.md`](docs/superpowers/plans/2026-11-08-fundacao-servidor.md)

## Requisitos

- Python 3.13+

## Instalação

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env               # opcional: ajusta configurações
```

## Banco de dados (uma vez)

```bash
python -m pythonisa_api.cli init-db   # cria data/pythonisa.db
python -m pythonisa_api.cli seed      # carrega linhas, paradas, itinerários, grade e letreiros
```

Os dados ficam em `src/pythonisa_api/seed/dados/` (JSON editável; veja o README dessa pasta).
O `seed` pode ser rodado de novo após editar os JSON: atualiza nomes, coordenadas e itinerários
sem duplicar. Ele não apaga o que saiu dos JSON: para remover ou renomear o id de uma parada ou
mudar a grade, recrie o banco (apague `data/pythonisa.db` e rode `init-db` e `seed`).

## Rodar

```bash
uvicorn pythonisa_api.main:app --reload
```

- Saúde: <http://localhost:8000/api/v1/health>
- Documentação interativa (OpenAPI): <http://localhost:8000/docs>

## Testes e lint

```bash
pytest                      # testes
ruff check .                # lint
ruff format .               # formatação
```
