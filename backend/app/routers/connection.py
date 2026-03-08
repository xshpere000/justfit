"""Connection Management API Router."""

from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.errors import NotFoundError, ValidationError, error_response, AppError
from app.schemas.connection import ConnectionCreate, ConnectionResponse, ConnectionUpdate, ConnectionData
from app.services.connection import ConnectionService


router = APIRouter()
logger = structlog.get_logger(__name__)


def _connection_to_dict(conn) -> dict:
    """Convert connection model to dict."""
    return {
        "id": conn.id,
        "name": conn.name,
        "platform": conn.platform,
        "host": conn.host,
        "port": conn.port,
        "username": conn.username,
        "insecure": conn.insecure,
        "status": conn.status,
        "lastSync": conn.last_sync.isoformat() if conn.last_sync else None,
        "createdAt": conn.created_at.isoformat() if conn.created_at else None,
        "updatedAt": conn.updated_at.isoformat() if conn.updated_at else None,
    }


@router.post("", response_model=ConnectionResponse)
async def create_connection(
    data: ConnectionCreate,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Create a new connection."""
    logger.info(
        "create_connection_requested",
        name=data.name,
        platform=data.platform,
        host=data.host,
        port=data.port,
        username=data.username,
    )

    service = ConnectionService(db)

    try:
        # Convert camelCase to snake_case for model
        connection = await service.create_connection(
            name=data.name,
            platform=data.platform,
            host=data.host,
            port=data.port,
            username=data.username,
            password=data.password,
            insecure=data.insecure,
        )

        logger.info(
            "create_connection_success",
            connection_id=connection.id,
            name=connection.name,
            platform=connection.platform,
            host=connection.host,
        )

        return {
            "success": True,
            "data": _connection_to_dict(connection),
        }
    except (NotFoundError, ValidationError, AppError) as e:
        logger.warning(
            "create_connection_failed",
            name=data.name,
            error=str(e),
            error_type=type(e).__name__,
        )
        return error_response(e)


@router.get("", response_model=dict)
async def list_connections(
    db: AsyncSession = Depends(get_db),
) -> Any:
    """List all connections."""
    logger.debug("list_connections_requested")

    service = ConnectionService(db)
    connections = await service.list_connections()

    logger.info(
        "list_connections_success",
        count=len(connections),
        connection_ids=[c.id for c in connections],
    )

    return {
        "success": True,
        "data": {
            "items": [_connection_to_dict(c) for c in connections],
            "total": len(connections),
        },
    }


@router.get("/{connection_id}", response_model=ConnectionResponse)
async def get_connection(
    connection_id: int,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get connection by ID."""
    logger.debug("get_connection_requested", connection_id=connection_id)

    service = ConnectionService(db)

    try:
        connection = await service.get_connection(connection_id)
        logger.info(
            "get_connection_success",
            connection_id=connection_id,
            name=connection.name,
            platform=connection.platform,
        )
        return {
            "success": True,
            "data": _connection_to_dict(connection),
        }
    except NotFoundError as e:
        logger.warning("get_connection_not_found", connection_id=connection_id)
        return error_response(e)


@router.put("/{connection_id}", response_model=ConnectionResponse)
async def update_connection(
    connection_id: int,
    data: ConnectionUpdate,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Update connection."""
    # Validate connection_id
    if not isinstance(connection_id, int) or connection_id <= 0:
        logger.warning("update_connection_invalid_id", connection_id=connection_id)
        return {
            "success": False,
            "error": {"code": "INVALID_ID", "message": f"Invalid connection ID: {connection_id}"},
        }

    # Build update kwargs from non-None fields
    updates = {}
    if data.name is not None:
        updates["name"] = data.name
    if data.host is not None:
        updates["host"] = data.host
    if data.port is not None:
        updates["port"] = data.port
    if data.username is not None:
        updates["username"] = data.username
    if data.password is not None:
        updates["password"] = data.password
    if data.insecure is not None:
        updates["insecure"] = data.insecure

    logger.info(
        "update_connection_requested",
        connection_id=connection_id,
        fields=list(updates.keys()),
    )

    service = ConnectionService(db)

    try:
        connection = await service.update_connection(connection_id, **updates)
        logger.info(
            "update_connection_success",
            connection_id=connection_id,
            name=connection.name,
            updated_fields=list(updates.keys()),
        )
        return {
            "success": True,
            "data": _connection_to_dict(connection),
        }
    except (NotFoundError, AppError) as e:
        logger.error(
            "update_connection_failed",
            connection_id=connection_id,
            error=str(e),
            error_type=type(e).__name__,
        )
        return error_response(e)


@router.delete("/{connection_id}", response_model=dict)
async def delete_connection(
    connection_id: int,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Delete connection."""
    logger.info("delete_connection_requested", connection_id=connection_id)

    service = ConnectionService(db)

    try:
        await service.delete_connection(connection_id)
        logger.info("delete_connection_success", connection_id=connection_id)
        return {
            "success": True,
            "message": f"Connection {connection_id} deleted",
        }
    except NotFoundError as e:
        logger.warning("delete_connection_not_found", connection_id=connection_id)
        return error_response(e)


@router.post("/{connection_id}/test", response_model=dict)
async def test_connection(
    connection_id: int,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Test connection."""
    logger.info("test_connection_requested", connection_id=connection_id)

    service = ConnectionService(db)

    try:
        result = await service.test_connection(connection_id)
        logger.info(
            "test_connection_success",
            connection_id=connection_id,
            success=result.get("success", False),
            reachable=result.get("reachable", False),
            version=result.get("version"),
        )
        return {
            "success": True,
            "data": result,
        }
    except (NotFoundError, AppError) as e:
        logger.error(
            "test_connection_failed",
            connection_id=connection_id,
            error=str(e),
            error_type=type(e).__name__,
        )
        return error_response(e)


@router.post("/{connection_id}/test-and-fetch-vms", response_model=dict)
async def test_connection_and_fetch_vms(
    connection_id: int,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Test connection and fetch VM list without full collection.

    This endpoint is used in the Wizard to verify connection and get VM list
    without performing a full resource collection.
    """
    logger.info("test_connection_and_fetch_vms_requested", connection_id=connection_id)

    service = ConnectionService(db)

    try:
        # 1. Test connection
        test_result = await service.test_connection(connection_id)

        if test_result.get("status") != "connected":
            logger.warning(
                "test_connection_and_fetch_vms_failed",
                connection_id=connection_id,
                status=test_result.get("status"),
            )
            return {
                "success": False,
                "error": {
                    "code": "CONNECTION_FAILED",
                    "message": test_result.get("message", "Connection test failed"),
                },
            }

        # 2. Get connector and fetch VM list
        connector = await service.get_connector(connection_id)

        # Get VM list directly from vCenter without saving to database
        from app.connectors.base import VMInfo
        vm_infos = await connector.get_vms()

        # Convert to response format
        vms = []
        for info in vm_infos:
            # Generate vm_key (same logic as collection service)
            if info.uuid:
                base_vm_key = f"uuid:{info.uuid.lower()}"
            elif info.datacenter:
                base_vm_key = f"{info.datacenter}:{info.name}"
            else:
                base_vm_key = info.name

            # Add connection_id prefix
            unique_vm_key = f"conn{connection_id}:{base_vm_key}"

            vms.append({
                "id": 0,  # Temporary ID, not saved to DB yet
                "name": info.name,
                "datacenter": info.datacenter or "",
                "uuid": info.uuid or "",
                "vmKey": unique_vm_key,
                "cpuCount": info.cpu_count,
                "memoryGb": round(info.memory_bytes / (1024**3), 2) if info.memory_bytes else 0,
                "powerState": info.power_state or "unknown",
                "guestOs": info.guest_os or "",
                "ipAddress": info.ip_address or "",
                "hostIp": info.host_ip or "",
                "connectionState": info.connection_state or "connected",
            })

        logger.info(
            "test_connection_and_fetch_vms_success",
            connection_id=connection_id,
            vm_count=len(vms),
        )

        return {
            "success": True,
            "data": {
                "status": "connected",
                "message": f"成功连接，获取到 {len(vms)} 台虚拟机",
                "vms": vms,
                "total": len(vms),
            },
        }
    except (NotFoundError, ValidationError, AppError) as e:
        logger.error(
            "test_connection_and_fetch_vms_failed",
            connection_id=connection_id,
            error=str(e),
            error_type=type(e).__name__,
        )
        return error_response(e)
    except Exception as e:
        logger.error(
            "test_connection_and_fetch_vms_unexpected_error",
            connection_id=connection_id,
            error=str(e),
            exc_info=True,
        )
        return {
            "success": False,
            "error": {
                "code": "FETCH_VMS_FAILED",
                "message": f"获取虚拟机列表失败: {str(e)}",
            },
        }
