from typing import Dict, List, Union
from loguru import logger
from pydantic import BaseModel, Field, root_validator, validator
from models import enums


class GABaseModel(BaseModel):
    def validate_class(self):
        from pydantic import validate_model

        object_setattr = object.__setattr__
        values, fields_set, validation_error = validate_model(self.__class__, self.dict())
        if validation_error:
            raise validation_error
        object_setattr(self, "__dict__", values)
        object_setattr(self, "__fields_set__", fields_set)

    def update(self, update_dict: dict):
        for key in update_dict:
            setattr(self, key, update_dict[key])
        self.validate_class()

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def __getitem__(self, key):
        return getattr(self, key)

class HTTPError(BaseModel):
    detail: str