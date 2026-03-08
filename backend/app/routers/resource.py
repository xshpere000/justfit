"""Resource Management API Router."""

from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.errors import NotFoundError, error_response, AppError
from app.services.collection import CollectionService
from app.services.task import TaskService


router = APIRouter()
logger = structlog.get_logger(__name__)


@router.get("/connections/{connection_id}/clusters", response_model=dict)
async def get_clusters(
    connection_id: int,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get clusters for a connection."""
    from sqlalchemy import select
    from app.models import Cluster

    result = await db.execute(
        select(Cluster).where(Cluster.connection_id == connection_id)
    )
    clusters = result.scalars().all()

    return {
        "success": True,
        "data": {
            "items": [
                {
                    "id": c.id,
                    "name": c.name,
                    "datacenter": c.datacenter,
                    "totalCpu": c.total_cpu,
                    "totalMemory": c.total_memory,
                    "numHosts": c.num_hosts,
                    "numVms": c.num_vms,
                }
                for c in clusters
            ],
            "total": len(clusters),
        },
    }


@router.get("/connections/{connection_id}/hosts", response_model=dict)
async def get_hosts(
    connection_id: int,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get hosts for a connection."""
    from sqlalchemy import select
    from app.models import Host

    result = await db.execute(
        select(Host).where(Host.connection_id == connection_id)
    )
    hosts = result.scalars().all()

    return {
        "success": True,
        "data": {
            "items": [
                {
                    "id": h.id,
                    "name": h.name,
                    "datacenter": h.datacenter,
                    "ipAddress": h.ip_address,
                    "cpuCores": h.cpu_cores,
                    "cpuMhz": h.cpu_mhz,
                    "memoryGb": round(h.memory_bytes / (1024**3), 2),
                    "numVms": h.num_vms,
                    "powerState": h.power_state,
                }
                for h in hosts
            ],
            "total": len(hosts),
        },
    }


@router.get("/connections/{connection_id}/vms", response_model=dict)
async def get_vms(
    connection_id: int,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get virtual machines for a connection."""
    from sqlalchemy import select
    from app.models import VM

    result = await db.execute(
        select(VM).where(VM.connection_id == connection_id)
    )
    vms = result.scalars().all()

    return {
        "success": True,
        "data": {
            "items": [
                {
                    "id": v.id,
                    "name": v.name,
                    "datacenter": v.datacenter,
                    "uuid": v.uuid,
                    "vmKey": v.vm_key,
                    "cpuCount": v.cpu_count,
                    "memoryGb": round(v.memory_bytes / (1024**3), 2),
                    "powerState": v.power_state,
                    "guestOs": v.guest_os,
                    "ipAddress": v.ip_address,
                    "hostIp": v.host_ip,
                }
                for v in vms
            ],
            "total": len(vms),
        },
    }


@router.post("/connections/{connection_id}/collect", response_model=dict)
async def collect_resources(
    connection_id: int,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Collect resources from connection."""
    logger.info("collect_resources_requested", connection_id=connection_id)

    service = CollectionService(db)

    try:
        result = await service.collect_resources(connection_id)
        logger.info(
            "collect_resources_success",
            connection_id=connection_id,
            task_id=result.get("task_id"),
        )
        return {
            "success": True,
            "data": result,
        }
    except (NotFoundError, AppError) as e:
        logger.error(
            "collect_resources_failed",
            connection_id=connection_id,
            error=str(e),
            error_type=type(e).__name__,
        )
        return error_response(e)


@router.get("/connections/{connection_id}/vms/list", response_model=dict)
async def get_collectable_vms(
    connection_id: int,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get list of VMs available for collection."""
    service = CollectionService(db)

    try:
        vms = await service.get_collectable_vms(connection_id)
        return {
            "success": True,
            "data": {
                "items": vms,
                "total": len(vms),
            },
        }
    except (NotFoundError, AppError) as e:
        return error_response(e)
