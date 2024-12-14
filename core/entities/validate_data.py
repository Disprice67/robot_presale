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
        try:
            if isinstance(a, str):
                return 0
            elif a is None:
                return 0
            else:
                assert a % 1 == 0, f'Количество должно быть целым: {a}'
                return a
        except AssertionError as e:
            return f'Additional info: {e}'

    @field_validator('part_number', mode='before')
    def validate_part_number(cls, pn: str) -> str:
        try:
            assert pn != '', f'P/N не должен быть пустым: {pn}'
            if isinstance(pn, str):
                vals = [val for val in pn if val.isalpha() or val.isnumeric()]
                result = "".join(vals).upper()
                assert result != '', f'P/N не прошел валидация: {pn}'
            # assert str(pn) != 'nan', f'Не должен быть пустым: {pn}'
            return pn.replace(' ', '').upper()
        except AssertionError as e:
            return f'Additional info: {e}'


MESSAGE_INFO = ['nullable']


class DataGenerate(BaseModel):

    input_data: Union[str, list[InputData]]
    sheet_name: str

    @field_validator('input_data', mode='before')
    def validate_input_data_before(cls, lists: list[dict]) -> Union[list, str]:
        input_fields = [value.alias for value in list(InputData.model_fields.values())]
        if len(set(lists[0]).intersection(input_fields)) != len(input_fields):
            raise ValidationError("Валидация не пройдена", cls)
        return lists
