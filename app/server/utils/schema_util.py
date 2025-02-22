from pydantic import BaseModel, create_model


def is_pydantic_model(obj):
    try:
        return issubclass(obj, BaseModel)
    except TypeError:
        return False


def unset_required(model_class: BaseModel, name: str = None) -> BaseModel:
    """
    Makes every field of a pydantic model and it's submodels Optional so that it can be used in patch request
    where every field is not required to be sent in payload

    Example usage:
    class ExampleCreateRequest(BaseModel):
        name: str
        age: int
    ExampleUpdateRequest = unset_required(ExampleCreateRequest)
    Args:
        model_class: Pydantic model to make optional
        name: Optional name if the name is different

    Returns:
        a pydantic class where each field is Optional including all its submodels
    """
    fields = {}
    for k, val in model_class.model_fields.items():
        if is_pydantic_model(val.annotation):
            fields[k] = (unset_required(val.annotation), None)
        else:
            fields[k] = (val.annotation, None)
    return create_model(name if name is not None else model_class.__name__, **fields)
