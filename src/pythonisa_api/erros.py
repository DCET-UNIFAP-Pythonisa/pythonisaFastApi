"""Erros de domínio. Não dependem de HTTP; a camada api/ traduz cada código para um status."""


class ErroDominio(Exception):
    codigo = "ERRO"

    def __init__(self, mensagem: str):
        super().__init__(mensagem)
        self.mensagem = mensagem


class LinhaNaoEncontrada(ErroDominio):
    codigo = "LINHA_NAO_ENCONTRADA"

    def __init__(self, id_linha: str):
        super().__init__(f"Linha '{id_linha}' não encontrada.")


class ParadaNaoEncontrada(ErroDominio):
    codigo = "PARADA_NAO_ENCONTRADA"

    def __init__(self, id_parada: str):
        super().__init__(f"Parada '{id_parada}' não encontrada.")


class NenhumaParadaCadastrada(ErroDominio):
    codigo = "PARADA_NAO_ENCONTRADA"

    def __init__(self):
        super().__init__("Nenhuma parada cadastrada. Rode o comando seed.")


class ParadaForaDaLinha(ErroDominio):
    codigo = "PARADA_FORA_DA_LINHA"

    def __init__(self, id_linha: str, id_parada: str):
        super().__init__(f"A linha '{id_linha}' não atende a parada '{id_parada}'.")


class LetreiroDesconhecido(ErroDominio):
    codigo = "LETREIRO_DESCONHECIDO"

    def __init__(self, texto: str):
        super().__init__(f"O letreiro '{texto}' não corresponde a nenhuma linha.")


class LetreiroAmbiguo(ErroDominio):
    codigo = "LETREIRO_AMBIGUO"

    def __init__(self, texto: str, ids_linhas: list[str]):
        super().__init__(f"O letreiro '{texto}' corresponde a mais de uma linha: {ids_linhas}.")


class ConfiancaBaixa(ErroDominio):
    codigo = "CONFIANCA_BAIXA"

    def __init__(self, valor: float, minimo: float):
        super().__init__(f"Confiança do OCR {valor:.2f} abaixo do mínimo {minimo:.2f}.")


class DadosInvalidos(ErroDominio):
    codigo = "DADOS_INVALIDOS"
