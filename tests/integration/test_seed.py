import json
import shutil
from datetime import time
from pathlib import Path

import pytest
from sqlalchemy import func, select

from pythonisa_api.db.models import (
    HorarioProgramado,
    Linha,
    PadraoLetreiro,
    Parada,
    RotaParada,
)
from pythonisa_api.seed.carregar import ErroSeed, ResumoSeed, carregar_seed
from pythonisa_api.services.geo import haversine_metros

MINI = Path(__file__).parent.parent / "fixtures" / "seed_mini"


def _contagens(sessao):
    def n(modelo):
        return sessao.scalar(select(func.count()).select_from(modelo))

    return ResumoSeed(
        linhas=n(Linha),
        paradas=n(Parada),
        itens_itinerario=n(RotaParada),
        horarios=n(HorarioProgramado),
        padroes=n(PadraoLetreiro),
    )


def _copia_mini(tmp_path) -> Path:
    destino = tmp_path / "seed_copia"
    shutil.copytree(MINI, destino)
    return destino


def _editar_json(diretorio: Path, nome: str, alterar) -> None:
    arquivo = diretorio / nome
    dados = json.loads(arquivo.read_text(encoding="utf-8"))
    alterar(dados)
    arquivo.write_text(json.dumps(dados), encoding="utf-8")


def test_resumo(sessao):
    resumo = carregar_seed(sessao, MINI)
    assert resumo == ResumoSeed(linhas=2, paradas=5, itens_itinerario=7, horarios=8, padroes=2)


def test_minutos_programados_linha_a(sessao):
    carregar_seed(sessao, MINI)
    linha = sessao.get(Linha, "linha-a")
    assert [r.minutos_programados for r in linha.itinerario] == [0, 4, 8, 12]


def test_grade_expandida(sessao):
    carregar_seed(sessao, MINI)
    horas = sessao.scalars(
        select(HorarioProgramado.hora_partida)
        .where(HorarioProgramado.id_linha == "linha-a", HorarioProgramado.tipo_dia == "util")
        .order_by(HorarioProgramado.hora_partida)
    ).all()
    assert horas == [time(6, 0), time(6, 30), time(7, 0)]


def test_idempotente(sessao):
    carregar_seed(sessao, MINI)
    carregar_seed(sessao, MINI)
    assert _contagens(sessao) == ResumoSeed(
        linhas=2, paradas=5, itens_itinerario=7, horarios=8, padroes=2
    )


def test_itinerario_substituido(sessao, tmp_path):
    carregar_seed(sessao, MINI)
    copia = _copia_mini(tmp_path)
    _editar_json(copia, "itinerarios.json", lambda d: d.update({"linha-a": d["linha-a"][:2]}))
    carregar_seed(sessao, copia)
    sessao.expire_all()
    assert [r.id_parada for r in sessao.get(Linha, "linha-a").itinerario] == ["p1", "p2"]


def test_parada_inexistente_no_itinerario(sessao, tmp_path):
    copia = _copia_mini(tmp_path)
    _editar_json(
        copia,
        "itinerarios.json",
        lambda d: d["linha-a"].append({"id_parada": "p-fantasma", "sentido": "ida"}),
    )
    with pytest.raises(ErroSeed, match="p-fantasma"):
        carregar_seed(sessao, copia)


def test_sentido_invalido(sessao, tmp_path):
    copia = _copia_mini(tmp_path)
    _editar_json(copia, "itinerarios.json", lambda d: d["linha-a"][0].update(sentido="norte"))
    with pytest.raises(ErroSeed, match="norte"):
        carregar_seed(sessao, copia)


def test_erro_nao_grava_nada(sessao, tmp_path):
    copia = _copia_mini(tmp_path)
    _editar_json(copia, "itinerarios.json", lambda d: d["linha-b"][0].update(sentido="norte"))
    with pytest.raises(ErroSeed):
        carregar_seed(sessao, copia)
    assert _contagens(sessao).linhas == 0


# Centro aproximado do campus Marco Zero da UNIFAP (polígono do OpenStreetMap).
UNIFAP_LAT, UNIFAP_LON = -0.0039, -51.0854


def test_seed_real_valido(sessao):
    carregar_seed(sessao)
    linhas = sessao.scalars(select(Linha)).all()
    assert {linha.id for linha in linhas} == {"macapaba-amapa-garden", "brasil-novo-universidade"}
    for linha in linhas:
        assert len(linha.itinerario) >= 3
    paradas_por_linha = [{r.id_parada for r in linha.itinerario} for linha in linhas]
    assert paradas_por_linha[0] & paradas_por_linha[1], "nenhuma parada compartilhada"


def test_seed_real_so_territorio_unifap(sessao):
    carregar_seed(sessao)
    for parada in sessao.scalars(select(Parada)).all():
        distancia = haversine_metros(parada.latitude, parada.longitude, UNIFAP_LAT, UNIFAP_LON)
        assert distancia <= 1500, f"{parada.id} está a {distancia:.0f} m da UNIFAP"
