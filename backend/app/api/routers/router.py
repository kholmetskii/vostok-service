from collections.abc import Callable

from fastapi import APIRouter, Depends, HTTPException, Response, status
from starlette.responses import StreamingResponse

from app.api.deps.uow import get_uow_factory
from app.api.routers.schemas import (
    FindPathRequest,
    FindPathResponse,
    WarehouseConfigIn,
    WarehouseConfigOut,
    WarehouseCreate,
    WarehouseRead,
)
from app.application.services.graph_service import (
    GraphService,
    PathNotFound,
    ShelfNotFound,
    WarehouseNotFound,
)
from app.application.services.warehouse_config_service import WarehouseConfigService
from app.application.services.warehouse_config_service import (
    WarehouseNotFound as WarehouseConfigNotFound,
)
from app.application.services.warehouse_service import WarehouseNotFound as WarehouseServiceNotFound
from app.application.services.warehouse_service import WarehouseService
from app.application.validators.warehouse_config_validator import ConfigValidationError
from app.infrastructure.db.uow import SQLAlchemyUnitOfWork

router = APIRouter(prefix="/warehouses", tags=["warehouses"])


# -----------------------
# Warehouses CRUD
# -----------------------


@router.post(
    "",
    response_model=WarehouseRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create warehouse",
)
async def create_warehouse(
    body: WarehouseCreate,
    uow_factory: Callable[[], SQLAlchemyUnitOfWork] = Depends(get_uow_factory),
) -> WarehouseRead:
    service = WarehouseService(uow_factory)
    created = await service.create_warehouse(
        name=body.name,
        width_m=body.width_m,
        length_m=body.length_m,
        floor_count=body.floor_count,
    )
    return WarehouseRead.model_validate(created, from_attributes=True)


@router.get(
    "",
    response_model=list[WarehouseRead],
    status_code=status.HTTP_200_OK,
    summary="List warehouses",
)
async def list_warehouses(
    uow_factory: Callable[[], SQLAlchemyUnitOfWork] = Depends(get_uow_factory),
) -> list[WarehouseRead]:
    service = WarehouseService(uow_factory)
    warehouses = await service.list_warehouses()
    return [WarehouseRead.model_validate(w, from_attributes=True) for w in warehouses]


@router.get(
    "/{warehouse_id}",
    response_model=WarehouseRead,
    status_code=status.HTTP_200_OK,
    summary="Get warehouse by id",
)
async def get_warehouse(
    warehouse_id: int,
    uow_factory: Callable[[], SQLAlchemyUnitOfWork] = Depends(get_uow_factory),
) -> WarehouseRead:
    service = WarehouseService(uow_factory)
    try:
        warehouse = await service.get_warehouse(warehouse_id)
        return WarehouseRead.model_validate(warehouse, from_attributes=True)
    except WarehouseServiceNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete(
    "/{warehouse_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete warehouse by id",
)
async def delete_warehouse(
    warehouse_id: int,
    uow_factory: Callable[[], SQLAlchemyUnitOfWork] = Depends(get_uow_factory),
) -> Response:
    service = WarehouseService(uow_factory)
    try:
        await service.delete_warehouse(warehouse_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except WarehouseServiceNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/{warehouse_id}/config",
    response_model=WarehouseConfigOut,
    status_code=status.HTTP_200_OK,
    summary="Get warehouse config (warehouse + nodes/shelves/edges/obstacles)",
)
async def get_warehouse_config(
    warehouse_id: int,
    uow_factory: Callable[[], SQLAlchemyUnitOfWork] = Depends(get_uow_factory),
) -> WarehouseConfigOut:
    service = WarehouseConfigService(uow_factory)
    try:
        data = await service.get_config(warehouse_id)
        return WarehouseConfigOut(**data)
    except WarehouseConfigNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.put(
    "/{warehouse_id}/config",
    response_model=WarehouseConfigOut,
    status_code=status.HTTP_200_OK,
    summary="Replace warehouse config (Excel is source of truth)",
)
async def replace_warehouse_config(
    warehouse_id: int,
    config: WarehouseConfigIn,
    uow_factory: Callable[[], SQLAlchemyUnitOfWork] = Depends(get_uow_factory),
) -> WarehouseConfigOut:
    service = WarehouseConfigService(uow_factory)

    # Pydantic v2 -> model_dump, Pydantic v1 -> dict (fallback)
    try:
        payload = config.model_dump()
    except AttributeError:
        payload = config.dict()

    try:
        await service.replace_config(warehouse_id, payload)
        data = await service.get_config(warehouse_id)
        return WarehouseConfigOut(**data)
    except WarehouseConfigNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ConfigValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post(
    "/{warehouse_id}/distance",
    response_model=FindPathResponse,
    status_code=status.HTTP_200_OK,
    summary="Find shortest distance and path (edges) between two shelves",
)
async def find_distance_between_shelves(
    warehouse_id: int,
    body: FindPathRequest,
    uow_factory: Callable[[], SQLAlchemyUnitOfWork] = Depends(get_uow_factory),
) -> FindPathResponse:
    service = GraphService(uow_factory)
    try:
        data = await service.find_path_between_shelves(
            warehouse_id=warehouse_id,
            from_shelf_ext_id=body.from_shelf_ext_id,
            to_shelf_ext_id=body.to_shelf_ext_id,
        )
        return FindPathResponse(**data)
    except ShelfNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PathNotFound as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get(
    "/{warehouse_id}/shelves/distances.jsonl",
    status_code=status.HTTP_200_OK,
    summary="Download all shelf-to-shelf distances as JSONL",
)
async def download_all_shelf_distances_jsonl(
    warehouse_id: int,
    uow_factory: Callable[[], SQLAlchemyUnitOfWork] = Depends(get_uow_factory),
):
    service = GraphService(uow_factory)
    try:
        stream = service.stream_all_shelf_distances_jsonl(warehouse_id)
        filename = f"warehouse_{warehouse_id}_shelf_distances.jsonl"

        return StreamingResponse(
            stream,
            media_type="application/jsonl",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except WarehouseNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
