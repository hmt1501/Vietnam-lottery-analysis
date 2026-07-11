__author__ = 'hmt1501'
__github__ = 'https://github.com/hmt1501'
__email__ = 'hmt1501@users.noreply.github.com'

from datetime import date

from pydantic import BaseModel, RootModel


class Result(BaseModel):
    date: date

    special: int

    prize1: int

    prize2_1: int
    prize2_2: int

    prize3_1: int
    prize3_2: int
    prize3_3: int
    prize3_4: int
    prize3_5: int
    prize3_6: int

    prize4_1: int
    prize4_2: int
    prize4_3: int
    prize4_4: int

    prize5_1: int
    prize5_2: int
    prize5_3: int
    prize5_4: int
    prize5_5: int
    prize5_6: int

    prize6_1: int
    prize6_2: int
    prize6_3: int

    prize7_1: int
    prize7_2: int
    prize7_3: int
    prize7_4: int


class ResultList(RootModel):
    root: list[Result]


class ResultCS(BaseModel):
    """Central (Miền Trung) and Southern (Miền Nam) result: 18 numbers per đài.

    Both regions share the same prize structure, unlike the North (`Result`).
    """

    date: date
    province: str

    special: int  # 6 digits

    prize1: int  # 5 digits
    prize2: int  # 5 digits

    prize3_1: int  # 5 digits
    prize3_2: int

    prize4_1: int  # 5 digits
    prize4_2: int
    prize4_3: int
    prize4_4: int
    prize4_5: int
    prize4_6: int
    prize4_7: int

    prize5: int  # 4 digits

    prize6_1: int  # 4 digits
    prize6_2: int
    prize6_3: int

    prize7: int  # 3 digits

    prize8: int  # 2 digits


class ResultCSList(RootModel):
    root: list[ResultCS]
