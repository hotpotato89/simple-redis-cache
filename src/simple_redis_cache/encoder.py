from datetime import datetime
from decimal import Decimal
import json
from typing import Any


class CustomJSONEncoder(json.JSONEncoder):
    """
    Кастомный JSON-энкодер для поддержки дополнительных типов данных.

    Поддерживает сериализацию:
        - `datetime` → ISO-строка (`YYYY-MM-DDTHH:MM:SS`)
        - `Decimal` → `float`
        - `UUID` → строка (через `hex`)
        - Pydantic-модели → через `model_dump()`

    Если тип не поддерживается, вызывает стандартное исключение `TypeError`.

    Example:
        >>> import json
        >>> from datetime import datetime
        >>> from decimal import Decimal
        >>> from uuid import uuid4
        >>>
        >>> data = {
        ...     "created": datetime.now(),
        ...     "price": Decimal("99.99"),
        ...     "id": uuid4(),
        ... }
        >>>
        >>> json.dumps(data, cls=CustomJSONEncoder)
        '{"created": "2026-07-12T12:00:00", "price": 99.99, "id": "550e8400-e29b-41d4-a716-446655440000"}'
    """

    def default(self, obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        if hasattr(obj, "hex"):
            return str(obj)
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)
