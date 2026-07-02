import datetime
import json
from decimal import Decimal
from enum import Enum
from typing import Any
from zoneinfo import ZoneInfo


class SerializeType(Enum):
    DATETIME = "datetime"
    DATE = "date"
    TIME = "time"
    JSON = "json"
    ENUM = "enum"


def json_encoder(obj: Any) -> Any:
    if isinstance(obj, Decimal):
        return float(obj)

    # isoformat preserves timezone offset and sub-second precision;
    # plain dates render as date-only strings
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()

    if isinstance(obj, Enum):
        return obj.value

    if isinstance(obj, int) or isinstance(obj, float) or isinstance(obj, str):
        return obj

    return str(obj)


def serialize_value(value: Any, s_type: SerializeType) -> Any:
    # None always serializes to SQL NULL - otherwise nullable enum fields crash
    # on .value and JSON fields store the string 'null' instead of NULL
    if value is None:
        return None

    if s_type == SerializeType.DATETIME:
        if not isinstance(value, datetime.datetime):
            return value

        return value.isoformat()

    if s_type == SerializeType.DATE:
        if not isinstance(value, datetime.date):
            return value

        return value.isoformat()

    if s_type == SerializeType.TIME:
        if not isinstance(value, datetime.time):
            return value

        return value.isoformat()

    if s_type == SerializeType.JSON:
        return json.dumps(value, default=json_encoder)

    if s_type == SerializeType.ENUM:
        return value.value
    return value


def deserialize_value(
    value: Any,
    s_type: SerializeType,
    enum_class: type[Enum] | None = None,
    timezone: str | datetime.tzinfo | None = None,
) -> Any:
    if s_type == SerializeType.DATETIME:
        if timezone is not None and isinstance(timezone, str):
            timezone = ZoneInfo(timezone)

        if isinstance(value, datetime.datetime):
            return value

        value = str(value)
        if value.replace(".", "", 1).isdigit():
            timestamp = float(value)
            if timestamp > 1e10:  # Check if timestamp is in milliseconds
                timestamp /= 1000

            return datetime.datetime.fromtimestamp(timestamp, tz=timezone)

        parsed = datetime.datetime.fromisoformat(value)
        if timezone is not None and parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone)

        return parsed

    if s_type == SerializeType.DATE:
        if isinstance(value, datetime.date):
            return value

        return datetime.date.fromisoformat(str(value))

    if s_type == SerializeType.TIME:
        if isinstance(value, datetime.time):
            return value

        return datetime.time.fromisoformat(str(value))

    if s_type == SerializeType.JSON:
        if isinstance(value, dict) or isinstance(value, list) or value is None:
            return value

        return json.loads(value)

    if s_type == SerializeType.ENUM:
        if enum_class is None:
            raise ValueError("enum_class must be provided when deserializing Enum")

        if isinstance(value, Enum) or value is None:
            return value

        return enum_class(value)

    return value
