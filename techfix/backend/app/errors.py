class AppError(Exception):
    """Erro de negócio convertido em resposta HTTP pelo handler global."""

    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail
