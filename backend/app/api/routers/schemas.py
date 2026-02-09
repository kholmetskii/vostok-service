from __future__ import annotations

from typing import List

from pydantic import BaseModel, ConfigDict, Field
from pydantic import PositiveFloat, PositiveInt, NonNegativeInt, NonNegativeFloat
from pydantic import field_validator, model_validator


# -----------------------
# Base schema
# -----------------------

class Schema(BaseModel):
    # from_attributes=True позволяет строить схемы из ORM объектов
    # extra="forbid" запрещает лишние поля в запросах/ответах (ловит ошибки рано)
    model_config = ConfigDict(from_attributes=True, extra="forbid")


# -----------------------
# Warehouses
# -----------------------

class WarehouseCreate(Schema):
    name: str
    width_m: PositiveFloat
    length_m: PositiveFloat
    floor_count: PositiveInt


class WarehouseRead(WarehouseCreate):
    id: PositiveInt


# -----------------------
# OUT schemas
# -----------------------

class NodeOut(Schema):
    ext_id: PositiveInt
    floor_level: NonNegativeInt
    x_m: NonNegativeFloat
    y_m: NonNegativeFloat


class ShelfOut(Schema):
    ext_id: PositiveInt
    floor_level: NonNegativeInt
    x_m: NonNegativeFloat
    y_m: NonNegativeFloat
    width_m: PositiveFloat
    length_m: PositiveFloat
    shelving_code: str
    section_code: str
    node_ext_id: PositiveInt


class EdgeOut(Schema):
    ext_id: PositiveInt
    from_node_ext_id: PositiveInt
    to_node_ext_id: PositiveInt
    weight_multiplier: PositiveFloat

    @model_validator(mode="after")
    def _distinct_nodes(self) -> "EdgeOut":
        if self.from_node_ext_id == self.to_node_ext_id:
            raise ValueError("from_node_ext_id must be different from to_node_ext_id")
        return self


class ObstacleOut(Schema):
    ext_id: PositiveInt
    from_node_ext_id: PositiveInt
    to_node_ext_id: PositiveInt

    @model_validator(mode="after")
    def _distinct_nodes(self) -> "ObstacleOut":
        if self.from_node_ext_id == self.to_node_ext_id:
            raise ValueError("from_node_ext_id must be different from to_node_ext_id")
        return self


class WarehouseConfigOut(Schema):
    warehouse: WarehouseRead
    nodes: List[NodeOut]
    shelves: List[ShelfOut]
    edges: List[EdgeOut]
    obstacles: List[ObstacleOut]


# -----------------------
# IN schemas
# -----------------------

class NodeIn(Schema):
    ext_id: PositiveInt
    floor_level: NonNegativeInt
    x_m: NonNegativeFloat
    y_m: NonNegativeFloat


class ShelfIn(Schema):
    ext_id: PositiveInt
    floor_level: NonNegativeInt
    x_m: NonNegativeFloat
    y_m: NonNegativeFloat
    width_m: PositiveFloat
    length_m: PositiveFloat
    shelving_code: str
    section_code: str
    node_ext_id: PositiveInt


class EdgeIn(Schema):
    ext_id: PositiveInt
    from_node_ext_id: PositiveInt
    to_node_ext_id: PositiveInt
    weight_multiplier: PositiveFloat = 1.0

    @model_validator(mode="after")
    def _distinct_nodes(self) -> "EdgeIn":
        if self.from_node_ext_id == self.to_node_ext_id:
            raise ValueError("from_node_ext_id must be different from to_node_ext_id")
        return self


class ObstacleIn(Schema):
    ext_id: PositiveInt
    from_node_ext_id: PositiveInt
    to_node_ext_id: PositiveInt

    @model_validator(mode="after")
    def _distinct_nodes(self) -> "ObstacleIn":
        if self.from_node_ext_id == self.to_node_ext_id:
            raise ValueError("from_node_ext_id must be different from to_node_ext_id")
        return self


class WarehouseConfigIn(Schema):
    nodes: List[NodeIn] = Field(default_factory=list)
    shelves: List[ShelfIn] = Field(default_factory=list)
    edges: List[EdgeIn] = Field(default_factory=list)
    obstacles: List[ObstacleIn] = Field(default_factory=list)


class FindPathRequest(BaseModel):
    from_shelf_ext_id: int
    to_shelf_ext_id: int


class FindPathResponse(BaseModel):
    distance_m: float
    path_edges: List[EdgeOut]