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


def test_letreiro_repetido_no_json_nao_quebra(sessao, tmp_path):
    copia = _copia_mini(tmp_path)
    _editar_json(copia, "letreiros.json", lambda d: d["linha-a"].append(d["linha-a"][0]))
    carregar_seed(sessao, copia)
    assert _contagens(sessao).padroes == 2


def test_rodar_de_novo_atualiza_nome_da_parada(sessao, tmp_path):
    carregar_seed(sessao, MINI)
    copia = _copia_mini(tmp_path)
    _editar_json(copia, "paradas.json", lambda d: d[0].update(nome="Parada Um"))
    carregar_seed(sessao, copia)
    sessao.expire_all()
    assert sessao.get(Parada, "p1").nome == "Parada Um"


def _editar(nome: str, alterar):
    return lambda diretorio: _editar_json(diretorio, nome, alterar)


def _escrever(nome: str, texto: str):
    return lambda diretorio: (diretorio / nome).write_text(texto, encoding="utf-8")


def _apagar(nome: str):
    return lambda diretorio: (diretorio / nome).unlink()


# Cada caso: como estragar uma cópia do seed mini e o trecho esperado na mensagem de erro.
CASOS_DE_ERRO = {
    "arquivo_ausente": (_apagar("grade.json"), "grade.json"),
    "json_malformado": (_escrever("linhas.json", "[{"), "linhas.json"),
    "arquivo_em_outra_codificacao": (
        lambda diretorio: (diretorio / "linhas.json").write_bytes(
            '[{"id": "x", "nome": "Amapá"}]'.encode("cp1252")
        ),
        "linhas.json",
    ),
    "parada_inexistente": (
        _editar(
            "itinerarios.json",
            lambda d: d["linha-a"].append({"id_parada": "p-fantasma", "sentido": "ida"}),
        ),
        "p-fantasma",
    ),
    "sentido_invalido": (
        _editar("itinerarios.json", lambda d: d["linha-b"][0].update(sentido="norte")),
        "norte",
    ),
    "itinerario_vazio": (_editar("itinerarios.json", lambda d: d.update({"linha-a": []})), "vazio"),
    "linha_desconhecida": (_editar("grade.json", lambda d: d.update({"linha-z": {}})), "linha-z"),
    "linha_sem_dados": (_editar("letreiros.json", lambda d: d.pop("linha-b")), "linha-b"),
    "tipo_dia_invalido": (
        _editar("grade.json", lambda d: d["linha-a"].update(feriado=d["linha-a"]["util"])),
        "feriado",
    ),
    "horario_invalido": (
        _editar("grade.json", lambda d: d["linha-a"]["util"].update(inicio="25:00")),
        "25:00",
    ),
    "intervalo_nao_positivo": (
        _editar("grade.json", lambda d: d["linha-a"]["util"].update(intervalo_min=0)),
        "intervalo_min",
    ),
    "inicio_depois_do_fim": (
        _editar("grade.json", lambda d: d["linha-a"]["util"].update(inicio="08:00")),
        "depois do fim",
    ),
    "campo_ausente": (
        _editar("grade.json", lambda d: d["linha-a"]["util"].pop("intervalo_min")),
        "intervalo_min",
    ),
    "letreiro_sem_padrao": (
        _editar("letreiros.json", lambda d: d["linha-a"][0].pop("padrao")),
        "padrao",
    ),
    "chave_desconhecida": (_editar("linhas.json", lambda d: d[0].update(empressa="X")), "empressa"),
    "parada_sem_latitude": (_editar("paradas.json", lambda d: d[0].pop("latitude")), "latitude"),
}


@pytest.mark.parametrize("caso", CASOS_DE_ERRO)
def test_erro_nos_arquivos_vira_erro_seed_e_nada_e_gravado(sessao, tmp_path, caso):
    estragar, trecho = CASOS_DE_ERRO[caso]
    copia = _copia_mini(tmp_path)
    estragar(copia)
    with pytest.raises(ErroSeed, match=trecho):
        carregar_seed(sessao, copia)
    assert _contagens(sessao) == ResumoSeed(0, 0, 0, 0, 0)
