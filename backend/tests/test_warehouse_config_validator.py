import pytest

from app.application.validators.warehouse_config_validator import (
    ConfigValidationError,
    WarehouseConfigValidator,
)


def valid_config():
    return {
        "nodes": [
            {"ext_id": 1, "floor_level": 1, "x_m": 1, "y_m": 1},
            {"ext_id": 2, "floor_level": 2, "x_m": 9, "y_m": 9},
        ],
        "shelves": [
            {
                "ext_id": 10,
                "floor_level": 1,
                "x_m": 0,
                "y_m": 0,
                "width_m": 2,
                "length_m": 1,
                "shelving_code": "A",
                "section_code": "01",
                "node_ext_id": 1,
            }
        ],
        "edges": [
            {
                "ext_id": 20,
                "from_node_ext_id": 1,
                "to_node_ext_id": 2,
                "weight_multiplier": 1,
            }
        ],
        "obstacles": [],
    }


def validate(config):
    return WarehouseConfigValidator().validate(
        config,
        warehouse_width_m=10,
        warehouse_length_m=10,
        warehouse_floor_count=2,
    )


def test_valid_config_accepts_cross_floor_edges():
    assert validate(valid_config()) == {1, 2}


def test_duplicate_external_ids_are_rejected():
    config = valid_config()
    config["nodes"].append(dict(config["nodes"][0]))

    with pytest.raises(ConfigValidationError, match="Duplicate ext_id"):
        validate(config)


def test_unknown_node_references_are_rejected():
    config = valid_config()
    config["shelves"][0]["node_ext_id"] = 999

    with pytest.raises(ConfigValidationError, match="unknown node"):
        validate(config)


def test_shelves_must_fit_inside_the_warehouse():
    config = valid_config()
    config["shelves"][0]["x_m"] = 9
    config["shelves"][0]["width_m"] = 2

    with pytest.raises(ConfigValidationError, match="out of warehouse bounds"):
        validate(config)


def test_floor_levels_are_one_based_and_bounded():
    config = valid_config()
    config["nodes"][0]["floor_level"] = 0

    with pytest.raises(ConfigValidationError, match="Expected in \\[1..2\\]"):
        validate(config)
