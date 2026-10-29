import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, Response, status
from ldap3.core.exceptions import (
    LDAPBindError,
    LDAPException,
    LDAPPasswordIsMandatoryError,
    LDAPSocketOpenError,
)

from ..auth import clear_auth_cookie, create_token, get_current_user, set_auth_cookie
from ..config import settings
from ..ldap_client import open_connection
from ..schemas import LoginRequest, TokenResponse, UserInfo

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


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
async def login(req: LoginRequest, response: Response):
    login_name = normalize_login(req.username)
    if not login_name:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
        )
    upn = f"{login_name}@{settings.ad_domain}"

    try:
        await asyncio.to_thread(_bind_check, upn, req.password)
    except (LDAPBindError, LDAPPasswordIsMandatoryError):
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

    admins = settings.admin_logins
    is_admin = login_name in admins or upn.lower() in admins
    token = create_token(login_name, is_admin)
    set_auth_cookie(response, token)

    return TokenResponse(username=login_name, is_admin=is_admin)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response):
    clear_auth_cookie(response)


@router.get("/me", response_model=UserInfo)
async def me(user: dict = Depends(get_current_user)):
    return UserInfo(username=user["sub"], is_admin=bool(user.get("is_admin")))
