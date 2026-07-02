import dataclasses
import datetime
import json
import re
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, ClassVar, Literal, NotRequired, TypedDict, TypeVar, cast

from .serialization import (
    SerializeType,
    deserialize_value,
    json_encoder,
    serialize_value,
)

EnumType = TypeVar("EnumType", bound=Enum)


class MetadataDict(TypedDict):
    db_field: tuple[str, str]
    store: bool
    update: bool
    exclude: NotRequired[bool]
    serialize: NotRequired[Callable[[Any], Any] | SerializeType | None]
    deserialize: NotRequired[Callable[[Any], Any] | None]
    enum_class: NotRequired[type[Enum] | None]
    timezone: NotRequired[str | datetime.tzinfo | None]


@dataclass
class DBDataModel:
    """
    Base class for all database models.

    Attributes:
    - schema_name (str): The name of the schema in the database.
    - table_name (str): The name of the table in the database.
    - table_alias (str): The alias of the table in the database.
    - id_key (str): The name of the primary key column in the database.
    - id_value (Any): The value of the primary key for the current instance.
    - id (int): The primary key value for the current instance.

    Methods:
    - __post_init__(): Initializes the instance after it has been created.
    - __repr__(): Returns a string representation of the instance.
    - __str__(): Returns a JSON string representation of the instance.
    - to_dict(): Returns a dictionary representation of the instance.
    - to_formatted_dict(): Returns a formatted dictionary representation of the instance.
    - to_json_schema(): Returns a JSON schema for the instance.
    - json_encoder(obj: Any): Encodes the given object as JSON.
    - to_json_string(pretty: bool = False): Returns a JSON string representation of the instance.
    - str_to_datetime(value: Any): Converts a string to a datetime object.
    - str_to_bool(value: Any): Converts a string to a boolean value.
    - str_to_int(value: Any): Converts a string to an integer value.
    - validate(): Validates the instance.

    To enable storing and updating fields that by default are not stored or updated, use the following methods:
    - set_store(field_name: str, enable: bool = True): Enable/Disable storing a field.
    - set_update(field_name: str, enable: bool = True): Enable/Disable updating a field.

    To exclude a field from the dictionary representation of the instance, set metadata key "exclude" to True.
    To change exclude status of a field, use the following method:
    - set_exclude(field_name: str, enable: bool = True): Exclude a field from dict representation.
    """

    ######################
    ### Default fields ###
    ######################

    @property
    def schema_name(self) -> str | None:
        return None

    @property
    def table_name(self) -> str:
        raise NotImplementedError("`table_name` property is not implemented")

    @property
    def table_alias(self) -> str | None:
        return None

    @property
    def id_key(self) -> str:
        return "id"

    @property
    def id_value(self) -> Any:
        return getattr(self, self.id_key)

    # Id should be readonly by default and should be always present if record exists
    id: int = field(
        default=0,
        metadata=MetadataDict(
            db_field=("id", "bigint"),
            store=False,
            update=False,
        ),
    )
    """id is readonly by default"""

    # Raw data
    raw_data: dict[str, Any] = field(
        default_factory=dict,
        metadata=MetadataDict(
            db_field=("raw_data", "jsonb"),
            exclude=True,
            store=False,
            update=False,
        ),
    )
    """This is for storing temporary raw data"""

    ##########################
    ### Conversion methods ###
    ##########################

    def fill_data_from_dict(self, kwargs: dict[str, Any]) -> None:
        field_names = set([f.name for f in dataclasses.fields(self)])
        for key in kwargs:
            if key in field_names:
                setattr(self, key, kwargs[key])

        self.__post_init__()

    # Init data
    def __post_init__(self) -> None:
        for field_name, field_obj in self.__dataclass_fields__.items():
            metadata = cast(MetadataDict, field_obj.metadata)
            value = getattr(self, field_name)

            # If value is not set, we skip it
            if value is None:
                continue

            # If serialize is set, and serialize is a SerializeType,
            # we use our serialization function
            # Here we actually need to deserialize the value to correct class type
            serialize = metadata.get("serialize", None)
            enum_class = metadata.get("enum_class", None)
            timezone = metadata.get("timezone", None)
            if serialize is not None and isinstance(serialize, SerializeType):
                value = deserialize_value(value, serialize, enum_class, timezone)
                setattr(self, field_name, value)

            else:
                deserialize = metadata.get("deserialize", None)
                if deserialize is not None:
                    value = deserialize(value)
                    setattr(self, field_name, value)

    # String - representation
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.__dict__}>"

    def __str__(self) -> str:
        return self.to_json_string()

    def dict_filter(self, pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        new_dict: dict[str, Any] = {}
        for field_name, value in pairs:
            class_field = self.__dataclass_fields__.get(field_name, None)
            if class_field is None:
                # asdict() also calls this factory for nested dataclasses whose
                # fields are not on this model - pass them through unfiltered
                new_dict[field_name] = value
                continue

            metadata = cast(MetadataDict, class_field.metadata)
            if not metadata.get("exclude", False):
                new_dict[field_name] = value

        return new_dict

    def to_dict(self) -> dict[str, Any]:
        return asdict(self, dict_factory=self.dict_filter)

    def to_formatted_dict(self) -> dict[str, Any]:
        return self.to_dict()

    # JSON
    def to_json_schema(self) -> dict[str, Any]:
        schema: dict[str, Any] = {
            "type": "object",
            "properties": {
                "id": {"type": "number"},
            },
        }
        for field_name, field_obj in self.__dataclass_fields__.items():
            metadata = cast(MetadataDict, field_obj.metadata)
            assert (
                "db_field" in metadata and isinstance(metadata["db_field"], tuple) and len(metadata["db_field"]) == 2
            ), f"db_field metadata is not set for {field_name}"
            field_type: str = metadata["db_field"][1]
            schema["properties"][field_name] = {"type": field_type}

        return schema

    def json_encoder(self, obj: Any) -> Any:
        return json_encoder(obj)

    def to_json_string(self, pretty: bool = False) -> str:
        if pretty:
            return json.dumps(
                self.to_dict(),
                ensure_ascii=False,
                sort_keys=True,
                indent=4,
                separators=(",", ": "),
                default=self.json_encoder,
            )

        return json.dumps(self.to_dict(), default=self.json_encoder)

    #######################
    ### Helper methods ####
    #######################

    @staticmethod
    def str_to_datetime(value: Any) -> datetime.datetime:
        if isinstance(value, datetime.datetime):
            return value

        if value and isinstance(value, str):
            pattern = r"^\d+(\.\d+)?$"
            if re.match(pattern, value):
                return datetime.datetime.fromtimestamp(float(value))

            return datetime.datetime.fromisoformat(value)

        return datetime.datetime.now(datetime.UTC)

    @staticmethod
    def str_to_bool(value: Any) -> bool:
        if isinstance(value, bool):
            return value

        if value:
            if isinstance(value, str):
                return value.lower() in ("true", "1")

            if isinstance(value, int):
                return value == 1

        return False

    @staticmethod
    def str_to_int(value: Any) -> int:
        if isinstance(value, int):
            return value

        if value and isinstance(value, str):
            return int(value)

        return 0

    def validate(self) -> Literal[True] | str:
        """
        True if the instance is valid, otherwise an error message.
        """
        raise NotImplementedError("`validate` is not implemented")

    def set_id_value(self, id_value: Any) -> None:
        """
        Set the value of the primary key for the current instance.

        Args:
            id_value (Any): The value to set for the primary key.
        """
        setattr(self, self.id_key, id_value)

    ############################
    ### Store/update policies ###
    ############################

    @classmethod
    def _should_store(cls, field_name: str, metadata: MetadataDict) -> bool:
        """
        Decide whether this field should be included in INSERT payload.
        Base behavior: rely on field metadata.
        Subclasses can override.
        """
        return bool(metadata.get("store", False))

    @classmethod
    def _should_update(cls, field_name: str, metadata: MetadataDict) -> bool:
        """
        Decide whether this field should be included in UPDATE payload.
        Base behavior: rely on field metadata.
        Subclasses can override.
        """
        return bool(metadata.get("update", False))

    @classmethod
    def _should_exclude(cls, field_name: str, metadata: MetadataDict) -> bool:
        return bool(metadata.get("exclude", False))

    ########################
    ### Database methods ###
    ########################

    def query_base(self) -> Any:
        """
        Base query for all queries
        """
        return None

    def store_data(self) -> dict[str, Any] | None:
        """
        Store data to database
        """
        store_data: dict[str, Any] = {}
        for field_name, field_obj in self.__dataclass_fields__.items():
            metadata = cast(MetadataDict, field_obj.metadata)
            if self.__class__._should_store(field_name, metadata):
                value = getattr(self, field_name)

                # If serialize is set, and serialize is a SerializeType,
                # we use our serialization function.
                # Otherwise, we use the provided serialize function
                # and we assume that it is callable
                serialize = metadata.get("serialize", None)
                if serialize is not None:
                    if isinstance(serialize, SerializeType):
                        value = serialize_value(value, serialize)
                    else:
                        value = serialize(value)

                store_data[field_name] = value
        return store_data

    def update_data(self) -> dict[str, Any] | None:
        """
        Update data to database
        """

        update_data: dict[str, Any] = {}
        for field_name, field_obj in self.__dataclass_fields__.items():
            metadata = cast(MetadataDict, field_obj.metadata)
            if self.__class__._should_update(field_name, metadata):
                value = getattr(self, field_name)

                # If serialize is set, and serialize is a SerializeType,
                # we use our serialization function.
                # Otherwise, we use the provided serialize function
                # and we assume that it is callable
                serialize = metadata.get("serialize", None)
                if serialize is not None:
                    if isinstance(serialize, SerializeType):
                        value = serialize_value(value, serialize)
                    else:
                        value = serialize(value)

                update_data[field_name] = value
        return update_data


@dataclass
class DBDefaultsDataModel(DBDataModel):
    """
    DBDataModel with conventional default columns.
    Subclasses can set `_defaults_config` to select which defaults are active.

    Attributes:
    - created_at (datetime.datetime): The timestamp of when the instance was created.
    - updated_at (datetime.datetime): The timestamp of when the instance was last updated.
    - disabled_at (datetime.datetime): The timestamp of when the instance was disabled.
    - deleted_at (datetime.datetime): The timestamp of when the instance was deleted.
    - enabled (bool): Whether the instance is enabled or not. Deprecated.
    - deleted (bool): Whether the instance is deleted or not. Deprecated.
    """

    # Subclasses override this as a class attribute, e.g.:
    # _defaults_config = ["created_at", "updated_at"]
    _defaults_config: ClassVar[list[str]] = ["created_at", "updated_at", "disabled_at", "deleted_at"]

    ######################
    ### Default fields ###
    ######################

    created_at: datetime.datetime = field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC),
        metadata=MetadataDict(
            db_field=("created_at", "timestamptz"),
            store=True,
            update=False,
            serialize=SerializeType.DATETIME,
        ),
    )

    updated_at: datetime.datetime = field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC),
        metadata=MetadataDict(
            db_field=("updated_at", "timestamptz"),
            store=True,
            update=True,
            serialize=SerializeType.DATETIME,
        ),
    )

    # Important: default None, otherwise everything becomes disabled/deleted on insert.
    disabled_at: datetime.datetime | None = field(
        default=None,
        metadata=MetadataDict(
            db_field=("disabled_at", "timestamptz"),
            store=True,
            update=True,
            serialize=SerializeType.DATETIME,
        ),
    )

    deleted_at: datetime.datetime | None = field(
        default=None,
        metadata=MetadataDict(
            db_field=("deleted_at", "timestamptz"),
            store=True,
            update=True,
            serialize=SerializeType.DATETIME,
        ),
    )

    # @deprecated
    enabled: bool = field(
        default=True,
        metadata=MetadataDict(
            db_field=("enabled", "boolean"),
            store=False,
            update=False,
        ),
    )

    # @deprecated
    deleted: bool = field(
        default=False,
        metadata=MetadataDict(
            db_field=("deleted", "boolean"),
            store=False,
            update=False,
        ),
    )

    ############################
    ### Store/update policies ###
    ############################

    @classmethod
    def _should_store(cls, field_name: str, metadata: MetadataDict) -> bool:
        # For the 4 defaults, defer to _defaults_config.
        if field_name in ("created_at", "updated_at", "disabled_at", "deleted_at"):
            return field_name in cls._defaults_config
        return super()._should_store(field_name, metadata)

    @classmethod
    def _should_update(cls, field_name: str, metadata: MetadataDict) -> bool:
        # created_at is never updated
        if field_name == "created_at":
            return False
        if field_name in ("updated_at", "disabled_at", "deleted_at"):
            return field_name in cls._defaults_config
        return super()._should_update(field_name, metadata)

    def update_data(self) -> dict[str, Any] | None:
        # Always refresh updated_at if present in this model
        if "updated_at" in self.__dataclass_fields__ and "updated_at" in self._defaults_config:
            self.updated_at = datetime.datetime.now(datetime.UTC)
        return super().update_data()
