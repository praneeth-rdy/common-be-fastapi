from typing import Annotated, Any, Optional, Union

from bson.objectid import ObjectId
from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict, field_validator
from pydantic.fields import Field
from pydantic_core import core_schema

from app.server.utils import date_utils

ListOrDictType = Union[Optional[list[dict[str, Any]]], Optional[dict[str, Any]]]
DictType = dict[str, Any]


class PyObjectId(str):
    @classmethod
    def __get_pydantic_core_schema__(cls, _source_type: Any, _handler: Any) -> core_schema.CoreSchema:
        return core_schema.json_or_python_schema(
            json_schema=core_schema.str_schema(),
            python_schema=core_schema.union_schema(
                [core_schema.is_instance_schema(ObjectId), core_schema.chain_schema([core_schema.str_schema(), core_schema.no_info_plain_validator_function(cls.validate)])]
            ),
            serialization=core_schema.plain_serializer_function_ser_schema(lambda x: str(x)),  # pylint: disable=unnecessary-lambda
        )

    @classmethod
    def validate(cls, value) -> ObjectId:
        if not ObjectId.is_valid(value):
            raise ValueError('Invalid ObjectId')

        return ObjectId(value)


class BaseModel(PydanticBaseModel):
    """Base class for model with predefined Config"""

    model_config = ConfigDict(arbitrary_types_allowed=True, str_strip_whitespace=True, extra='forbid')


class DictWithObjectIdStr(BaseModel):
    """Base class for model that needs auto mongo ObjectId creation to be inserted in database"""

    id: PyObjectId = Field(default_factory=ObjectId, alias='_id')
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


class DateTimeModelMixin(BaseModel):
    created_at: Annotated[int, Field(validate_default=True)] = 0
    updated_at: Annotated[int, Field(validate_default=True)] = created_at

    @field_validator('created_at', 'updated_at')
    @classmethod
    def default_datetime(cls, value: int) -> int:
        return value or date_utils.get_current_timestamp()
