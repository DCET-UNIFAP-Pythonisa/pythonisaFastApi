"""Converte exceções em respostas no formato padrão: {"erro": {"codigo", "mensagem"}}."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from pythonisa_api.erros import ErroDominio

STATUS_POR_CODIGO = {
    "LINHA_NAO_ENCONTRADA": 404,
    "PARADA_NAO_ENCONTRADA": 404,
    "PARADA_FORA_DA_LINHA": 422,
    "DADOS_INVALIDOS": 422,
}


def resposta_erro(status: int, codigo: str, mensagem: str) -> JSONResponse:
    return JSONResponse(
        status_code=status, content={"erro": {"codigo": codigo, "mensagem": mensagem}}
    )


def _resumo_validacao(erro: RequestValidationError) -> str:
    partes = []
    for item in erro.errors():
        campo = ".".join(str(p) for p in item["loc"] if p not in ("body", "query", "path"))
        partes.append(f"{campo}: {item['msg']}" if campo else item["msg"])
    return "; ".join(partes)


def registrar_tratadores(app: FastAPI) -> None:
    @app.exception_handler(ErroDominio)
    async def _dominio(_request: Request, erro: ErroDominio):
        return resposta_erro(STATUS_POR_CODIGO.get(erro.codigo, 400), erro.codigo, erro.mensagem)

    @app.exception_handler(RequestValidationError)
    async def _validacao(_request: Request, erro: RequestValidationError):
        return resposta_erro(422, "DADOS_INVALIDOS", _resumo_validacao(erro))

    @app.exception_handler(StarletteHTTPException)
    async def _http(_request: Request, erro: StarletteHTTPException):
        codigo = "NAO_ENCONTRADO" if erro.status_code == 404 else "ERRO_HTTP"
        mensagem = "Recurso não encontrado." if erro.status_code == 404 else str(erro.detail)
        return resposta_erro(erro.status_code, codigo, mensagem)
