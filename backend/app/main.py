import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import Base, engine
from .routers import auth, departments, employees, admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not settings.ad_uses_tls:
        logging.getLogger(__name__).warning(
            "Соединение с AD не шифруется: пароли передаются открытым текстом. "
            "Используйте AD_SERVER=ldaps://... или AD_START_TLS=true."
        )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="РВК Справочник API",
    description="Телефонный справочник организации с синхронизацией из Active Directory",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(auth.router)
app.include_router(departments.router)
app.include_router(employees.router)
app.include_router(admin.router)


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok"}