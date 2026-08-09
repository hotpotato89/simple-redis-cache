import json
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID


class CustomJSONEncoder(json.JSONEncoder):
    """
    Кастомный JSON-энкодер для поддержки дополнительных типов данных.

    Поддерживает сериализацию:
        - `datetime`, `date`, `time` → ISO-строка
        - `timedelta` → количество секунд (float)
        - `Decimal` → строка (для сохранения точности)
        - `UUID` → строка
        - Pydantic-модели → через `model_dump()`

    Если тип не поддерживается, вызывает стандартное исключение `TypeError`.

    Example:
        >>> import json
        >>> from datetime import datetime, date, timedelta
        >>> from decimal import Decimal
        >>> from uuid import uuid4
        >>>
        >>> data = {
        ...     "created": datetime.now(),
        ...     "birthday": date(2000, 1, 1),
        ...     "duration": timedelta(hours=2),
        ...     "price": Decimal("99.99"),
        ...     "id": uuid4(),
        ... }
        >>>
        >>> json.dumps(data, cls=CustomJSONEncoder)
        '{"created": "2026-07-12T12:00:00", "birthday": "2000-01-01", "duration": 7200.0, "price": "99.99", "id": "550e8400-e29b-41d4-a716-446655440000"}'
    """

    def default(self, obj: Any) -> Any:
        # --- Дата и время ---
        if isinstance(obj, (datetime, date, time)):
            return obj.isoformat()

        # --- Timedelta (храним как секунды) ---
        if isinstance(obj, timedelta):
            return obj.total_seconds()

        # --- Decimal (храним как строку для точности) ---
        if isinstance(obj, Decimal):
            return str(obj)

        # --- UUID (конкретная проверка) ---
        if isinstance(obj, UUID):
            return str(obj)

        # --- Pydantic модели (v2) ---
        if hasattr(obj, "model_dump"):
            return obj.model_dump()

        # --- Всё остальное ---
        return super().default(obj)
