import asyncio
import logging

from fastapi import APIRouter, HTTPException, Request, status
from ldap3.core.exceptions import (
    LDAPBindError,
    LDAPSocketOpenError,
    LDAPException,
)

from ..config import settings, normalize_login
from ..ldap_client import open_connection
from ..rate_limit import SlidingWindowLimiter
from ..schemas import LoginRequest, TokenResponse
from ..auth import create_token

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Неудачные попытки на логин держим ниже порога блокировки в AD,
# чтобы через справочник нельзя было заблокировать чужую учётку.
_user_failures = SlidingWindowLimiter(
    settings.login_max_failures_per_user, settings.login_window_seconds
)
_ip_attempts = SlidingWindowLimiter(
    settings.login_max_attempts_per_ip, settings.login_window_seconds
)

_INVALID_CREDENTIALS = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Неверный логин или пароль",
)


def _bind_check(username: str, password: str) -> None:
    """Синхронный bind к AD. Выполняется в thread pool."""
    conn = open_connection(username, password)
    try:
        conn.unbind()
    except Exception:
        pass


def _too_many(retry_after: int) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Слишком много попыток входа, попробуйте позже",
        headers={"Retry-After": str(retry_after)},
    )


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    login_name = normalize_login(req.username)

    retry = max(_ip_attempts.retry_after(client_ip), _user_failures.retry_after(login_name))
    if retry:
        log.warning("Вход заблокирован лимитом: login=%r ip=%s", login_name, client_ip)
        raise _too_many(retry)
    _ip_attempts.hit(client_ip)

    if not login_name:
        raise _INVALID_CREDENTIALS

    upn = f"{login_name}@{settings.ad_domain}"
    try:
        await asyncio.to_thread(_bind_check, upn, req.password)
    except LDAPBindError:
        _user_failures.hit(login_name)
        log.info("Неудачный вход: login=%r ip=%s", login_name, client_ip)
        raise _INVALID_CREDENTIALS
    except LDAPSocketOpenError:
        log.exception("AD недоступен при входе")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Сервер авторизации недоступен, попробуйте позже",
        )
    except LDAPException:
        log.exception("Ошибка LDAP при входе login=%r", login_name)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка авторизации, обратитесь к администратору",
        )

    _user_failures.reset(login_name)
    is_admin = login_name in settings.admin_logins
    token = create_token(login_name, is_admin)
    log.info("Успешный вход: login=%r ip=%s admin=%s", login_name, client_ip, is_admin)

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        username=login_name,
        is_admin=is_admin,
    )
