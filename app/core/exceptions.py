class AppError(Exception):
    status_code = 400
    default_detail = "Некорректный запрос"

    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail or self.default_detail
        super().__init__(self.detail)


class BadRequestError(AppError):
    status_code = 400
    default_detail = "Некорректный запрос"


class AuthenticationError(AppError):
    status_code = 401
    default_detail = "Требуется аутентификация"


class PermissionDeniedError(AppError):
    status_code = 403
    default_detail = "Недостаточно прав"


class NotFoundError(AppError):
    status_code = 404
    default_detail = "Объект не найден"


class ConflictError(AppError):
    status_code = 409
    default_detail = "Конфликт данных"
