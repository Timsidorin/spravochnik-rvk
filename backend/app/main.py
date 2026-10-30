import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from .config import settings
from .database import Base, engine
from .routers import admin, admins, auth, departments, employees, quick_contacts
from .scheduler import start_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger(__name__)


def _add_missing_columns(sync_conn) -> None:
    # create_all не добавляет столбцы в уже существующие таблицы
    columns = {c["name"] for c in inspect(sync_conn).get_columns("employees")}
    if "manual_phone_fields" not in columns:
        sync_conn.execute(text("ALTER TABLE employees ADD COLUMN manual_phone_fields VARCHAR"))
        log.info("БД: добавлен столбец employees.manual_phone_fields")


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_add_missing_columns)
    task = start_scheduler()
    try:
        yield
    finally:
        if task:
            task.cancel()
        await engine.dispose()


app = FastAPI(
    title="РВК Справочник API",
    description="Телефонный справочник организации с синхронизацией из Active Directory",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.enable_docs else None,
    redoc_url="/redoc" if settings.enable_docs else None,
    openapi_url="/openapi.json" if settings.enable_docs else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(departments.router)
app.include_router(employees.router)
app.include_router(admin.router)
app.include_router(admins.router)
app.include_router(quick_contacts.router)


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok"}