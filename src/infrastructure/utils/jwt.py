from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from jose import jwt


def encode_jwt(
    payload: Mapping[str, Any],
    key: str,
    *,
    expires_in: int | timedelta = 300,
    issuer: str | None = None,
    audience: str | list[str] | None = None,
    algorithm: str | None = None,
) -> str:
    """
    Подписывает JWT короткоживущим токеном.

    Аргументы:
      - payload: произвольные пользовательские клеймы (полезная нагрузка JWT).
        Будут объединены со служебными полями: "iat" (Issued At), "exp" (Expiration Time),
        "jti" (JWT ID). Обратите внимание: если в `payload` уже есть ключи
        "iat"/"exp"/"jti", они переопределят автоматически рассчитанные значения.
        Это обычно нежелательно.

      - key: ключ подписи.
        - Для HS256 — симметричный секрет (строка/байты).
        - Для RS256/ES256 — приватный ключ в PEM.

      - expires_in: время жизни токена.
        - int — секунды TTL.
        - timedelta — длительность напрямую.

      - issuer: значение клейма "iss" (идентификатор издателя токена).
        Рекомендуется указывать каноничный идентификатор (часто HTTPS-URL),
        чтобы потребитель мог верифицировать источник.

      - audience: значение(я) клейма "aud" (целевые получатели токена).
        Может быть строкой или списком строк. Используется потребителем для
        проверки, что токен предназначен именно для него.

      - algorithm: алгоритм подписи JWT (например, "HS256", "RS256", "ES256").
        По умолчанию используется "HS256".

    Возвращает:
      - Строка compact JWT (JWS) в кодировке base64url (формат header.payload.signature).

    Примечания по безопасности:
      - Устанавливайте короткий TTL (через `expires_in`) для access-токенов.
      - При проверке на принимающей стороне валидируйте как минимум подпись, `exp`,
        а также `iss` и `aud`, если они установлены.
    """
    # 1) Срок действия
    if isinstance(expires_in, int):
        expires_in = timedelta(seconds=expires_in)
    now = datetime.now(UTC)
    exp = now + expires_in

    # 2) Базовые зарегистрированные клеймы
    claims: dict[str, Any] = {
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "jti": str(uuid4()),
        **payload,
    }
    if issuer is not None:
        claims["iss"] = issuer
    if audience is not None:
        claims["aud"] = audience

    # 3) Авто-выбор алгоритма, если не задан
    alg = algorithm or "HS256"

    # 4) Подпись
    return jwt.encode(claims, key, algorithm=alg)
