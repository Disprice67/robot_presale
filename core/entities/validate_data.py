from pydantic import BaseModel, Field, field_validator, ValidationError
from typing import Optional, Union


class InputData(BaseModel):
    customer: Optional[str] = Field(alias="ЗАКАЗЧИК")
    part_number: str = Field(alias="P/N")
    vendor: Optional[str] = Field(alias="ВЕНДОР")
    amount: int = Field(alias="КОЛИЧЕСТВО")
    description: Optional[str] = Field(alias="ОПИСАНИЕ")

    @field_validator('amount', mode='before')
    def validate_amount(cls, a: Union[str, int, float]) -> Optional[int]:
        if isinstance(a, str):
            return 0
        elif a is None:
            return 0
        else:
            if not isinstance(a, (int, float)):
                raise ValueError(f'Неверный тип данных для количества: {a}')
            if a % 1 != 0:
                raise ValueError(f'Количество должно быть целым: {a}')
            return int(a)

    @field_validator('part_number', mode='before')
    def validate_part_number(cls, pn: Union[str, None]) -> str:
        if pn is None or pn.strip() == '':
            raise ValueError(f'P/N не должен быть пустым: {pn}')
        pn = str(pn)
        vals = [val for val in pn if val.isalnum()]
        result = "".join(vals).upper()
        if result == '':
            raise ValueError(f'P/N не прошел валидацию: {pn}')
        return result


class DataGenerate(BaseModel):
    input_data: Union[str, list[InputData]]
    sheet_name: str

    @field_validator('input_data', mode='before')
    def validate_input_data_before(cls, lists: list[dict]) -> Union[list, str]:
        input_fields = [value.alias for value in list(InputData.model_fields.values())]
        if len(set(lists[0]).intersection(input_fields)) != len(input_fields):
            raise ValidationError("Валидация не пройдена", cls)
        return lists
