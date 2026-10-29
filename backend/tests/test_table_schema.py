import pytest
from pydantic import ValidationError

from app.services.tools.schemas import Table


def table(**dimensions):
    return Table(rows=2, columns=1, cells=[[{"text": "a", "cStyle": "cS_1"}], [{"text": "b", "cStyle": "cS_1"}]],
                 tStyle="tS_1", **dimensions)


def test_table_heights_are_flat_and_rules_round_trip():
    value = table(rowHeights=[25, 30], rowHeightRules=[1, 2])
    assert value.model_dump()["rowHeights"] == [25, 30]
    assert value.rowHeightRules == [1, 2]
    assert Table.model_json_schema()["properties"]["rowHeights"]["anyOf"][0]["items"]["type"] == "number"


def test_legacy_row_height_pairs_normalize_without_advertising_the_old_shape():
    value = table(rowHeights=[[25, 1], [30, 2]])
    assert value.rowHeights == [25, 30]
    assert value.rowHeightRules == [1, 2]


@pytest.mark.parametrize("dimensions", [
    {"rowHeights": [25]}, {"rowHeights": [25, -1]}, {"rowHeights": [25, float("inf")]},
    {"rowHeights": [25, 30], "rowHeightRules": [1]},
    {"rowHeights": [25, 30], "rowHeightRules": [1, 9]}, {"rowHeightRules": [1, 2]},
])
def test_invalid_row_dimensions_are_rejected(dimensions):
    with pytest.raises(ValidationError):
        table(**dimensions)
