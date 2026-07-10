import datetime
from decimal import Decimal
import json
from typing import Any


class CustomJSONEncoder(json.JSONEncoder):
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
