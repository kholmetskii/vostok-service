import asyncio
from types import SimpleNamespace

import pytest

from app.application.services.warehouse_config_service import WarehouseConfigService
from app.application.validators.warehouse_config_validator import ConfigValidationError


class WarehouseRepository:
    async def read_warehouse(self, warehouse_id):
        return SimpleNamespace(width_m=10, length_m=10, floor_count=1)


class MutationRepository:
    def __init__(self, calls, operation):
        self._calls = calls
        setattr(self, operation, self._record)

    async def _record(self, warehouse_id):
        self._calls.append(warehouse_id)


class FakeUnitOfWork:
    def __init__(self):
        self.delete_calls = []
        self.exit_exception = None
        self.warehouses = WarehouseRepository()
        self.edges = MutationRepository(self.delete_calls, "delete_edges_by_warehouse")
        self.obstacles = MutationRepository(self.delete_calls, "delete_obstacles_by_warehouse")
        self.shelves = MutationRepository(self.delete_calls, "delete_shelves_by_warehouse")
        self.nodes = MutationRepository(self.delete_calls, "delete_nodes_by_warehouse")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        self.exit_exception = exc


def test_invalid_configuration_is_rejected_before_existing_rows_are_deleted():
    uow = FakeUnitOfWork()
    service = WarehouseConfigService(lambda: uow)
    invalid_payload = {
        "nodes": [],
        "shelves": [],
        "edges": [
            {
                "ext_id": 1,
                "from_node_ext_id": 10,
                "to_node_ext_id": 20,
                "weight_multiplier": 1,
            }
        ],
        "obstacles": [],
    }

    with pytest.raises(ConfigValidationError, match="unknown node"):
        asyncio.run(service.replace_config(1, invalid_payload))

    assert uow.delete_calls == []
    assert isinstance(uow.exit_exception, ConfigValidationError)
