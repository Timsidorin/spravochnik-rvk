# phonebook-backend

```bash
cp .env.example .env   # заполнить AD_* и JWT_SECRET
uv sync
uv run python run.py
```

Тесты (AD замокан, реальный контроллер не нужен):

```bash
uv run pytest
```
