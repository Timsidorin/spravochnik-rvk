import asyncio
import logging
import re

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from ldap3.core.exceptions import (
    LDAPBindError,
    LDAPException,
    LDAPPasswordIsMandatoryError,
    LDAPSocketOpenError,
)

from ..auth import (
    clear_auth_cookie,
    create_token,
    get_current_user,
    is_admin_login,
    set_auth_cookie,
)
from ..config import settings
from ..ldap_client import open_connection
from ..rate_limit import LoginRateLimiter
from ..schemas import LoginRequest, TokenResponse, UserInfo

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Символы, недопустимые в sAMAccountName, и управляющие символы.
_INVALID_LOGIN = re.compile(r'["/\\\[\]:;|=,+*?<>@\x00-\x1f\x7f]')
_MAX_LOGIN_LENGTH = 64
# С одного IP допускается больше попыток: за NAT/прокси может быть много пользователей.
_IP_LIMIT_FACTOR = 4

login_limiter = LoginRateLimiter(
    settings.login_max_attempts, settings.login_window_seconds
)


def normalize_login(raw: str) -> str:
    """'user', 'user@RVK.local', 'RVK\\user' -> 'user'."""
    login = raw.strip()
    if "\\" in login:
        login = login.rsplit("\\", 1)[1]
    if "@" in login:
        login = login.split("@", 1)[0]
    return login.lower()


def _bind_check(upn: str, password: str) -> None:
    """Синхронный bind к AD. Выполняется в thread pool."""
    conn = open_connection(upn, password)
    try:
        conn.unbind()
    except Exception:
        pass


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, request: Request, response: Response):
    login_name = normalize_login(req.username)
    if (
        not login_name
        or len(login_name) > _MAX_LOGIN_LENGTH
        or _INVALID_LOGIN.search(login_name)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
        )
    upn = f"{login_name}@{settings.ad_domain}"

    user_key = f"user:{login_name}"
    ip_key = f"ip:{request.client.host if request.client else '-'}"
    retry_after = max(
        login_limiter.retry_after(user_key),
        login_limiter.retry_after(ip_key, settings.login_max_attempts * _IP_LIMIT_FACTOR),
    )
    if retry_after:
        log.warning("Вход заблокирован (слишком много попыток): %s, %s", user_key, ip_key)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Слишком много неудачных попыток входа, попробуйте позже",
            headers={"Retry-After": str(retry_after)},
        )

    try:
        await asyncio.to_thread(_bind_check, upn, req.password)
    except (LDAPBindError, LDAPPasswordIsMandatoryError):
        login_limiter.add_failure(user_key)
        login_limiter.add_failure(ip_key)
        log.info("Неудачный вход: %s, %s", user_key, ip_key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
        )
    except LDAPSocketOpenError:
        log.exception("AD недоступен при входе пользователя %s", login_name)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Сервер AD недоступен, попробуйте позже",
        )
    except LDAPException:
        log.exception("Ошибка LDAP при входе пользователя %s", login_name)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка авторизации, обратитесь к администратору",
        )

    login_limiter.reset(user_key)
    is_admin = is_admin_login(login_name)
    token = create_token(login_name, is_admin)
    set_auth_cookie(response, token)

    return TokenResponse(username=login_name, is_admin=is_admin)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response):
    clear_auth_cookie(response)


@router.get("/me", response_model=UserInfo)
async def me(user: dict = Depends(get_current_user)):
    return UserInfo(username=user["sub"], is_admin=bool(user.get("is_admin")))
