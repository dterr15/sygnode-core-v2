"""
SQLAlchemy type compatibility layer.
On PostgreSQL: uses native ARRAY, JSONB, UUID types.
On SQLite (tests): falls back to TEXT/JSON-based equivalents.
"""

import json
import uuid as _uuid

from sqlalchemy import Text, String
from sqlalchemy.types import TypeDecorator, UserDefinedType


class JSONType(TypeDecorator):
    """JSONB-compatible type that stores as TEXT on SQLite."""
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return json.dumps(value, default=str)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return json.loads(value)


class ArrayType(TypeDecorator):
    """ARRAY-compatible type that stores as JSON TEXT on SQLite."""
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return json.dumps([])
        return json.dumps([str(v) if not isinstance(v, str) else v for v in value], default=str)

    def process_result_value(self, value, dialect):
        if value is None:
            return []
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return []


class UUIDType(TypeDecorator):
    """UUID-compatible type: native UUID on PostgreSQL, TEXT on SQLite."""
    impl = Text
    cache_ok = True

    def __init__(self, as_uuid=True, *args, **kwargs):
        self.as_uuid = as_uuid
        super().__init__(*args, **kwargs)

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import UUID as PG_UUID
            return dialect.type_descriptor(PG_UUID(as_uuid=self.as_uuid))
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, _uuid.UUID):
            return str(value) if dialect.name != "postgresql" else value
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if self.as_uuid and not isinstance(value, _uuid.UUID):
            try:
                return _uuid.UUID(str(value))
            except (ValueError, AttributeError):
                return value
        return value


def get_uuid():
    """Return a UUID type that works on both PostgreSQL and SQLite."""
    return UUIDType(as_uuid=True)


def get_jsonb():
    """Return a JSONB-compatible type."""
    return JSONType()


def get_array(item_type=None):
    """Return an ARRAY-compatible type."""
    return ArrayType()
