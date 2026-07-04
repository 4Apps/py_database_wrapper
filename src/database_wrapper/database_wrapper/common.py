from typing import TypeVar

from .db_data_model import DBDataModel

# Bound T to DBDataModel
DataModelType = TypeVar("DataModelType", bound=DBDataModel)

# OrderByItem type
OrderByItem = list[tuple[str, str | None]]


# NoParam class
class NoParam:
    pass


class RawSQL(str):
    """
    Marks a filter/order-by key as a raw SQL expression, skipping identifier
    validation. Only use with trusted, developer-controlled strings - the
    value is interpolated into the query verbatim.

    Example:
        wrapper.get_filtered(model, {RawSQL("LOWER(name)"): "alice"})
    """

    __slots__ = ()
