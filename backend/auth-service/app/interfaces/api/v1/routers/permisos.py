from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from http import HTTPStatus
import re

from app.dominio.modelos import Permiso
from app.dominio.excepciones import (
    PermisoNoEncontrado,
    PermisoExistente,
    PermisoEnUso,
    PermissionDeniedError,
    DatabaseError
)
from app.infraestructura.persistencia.repositorios import (
    PermisoRepository,
    RoleRepository,
    get_db
)
from app.aplicacion.dependencias import obtener_usuario_actual
from app.aplicacion.servicios import PermissionChecker
from app.interfaces.api.v1.esquemas import (
    PermissionCreate,
    PermissionOut,
    HTTPError,
    PaginatedResponse
)
from app.infraestructura.mensajeria.adapters import AuditProducer

router = APIRouter(prefix="/permisos", tags=["Gestión de Permisos"])
seguridad = HTTPBearer()

@router.post(
    "",
    response_model=PermissionOut,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": HTTPError, "description": "Formato de permiso inválido"},
        403: {"model": HTTPError, "description": "Permisos insuficientes"},
        409: {"model": HTTPError, "description": "Permiso ya existe"}
    }
)
async def crear_permiso(
    permiso: PermissionCreate,
    db: AsyncSession = Depends(get_db),
    usuario_actual=Depends(obtener_usuario_actual)
):
    try:
        if not await PermissionChecker.verificar(usuario_actual, "permisos:crear"):
            raise PermissionDeniedError(permission="permisos:crear")
        
        if not re.match(r"^[a-z]+:[a-z]+$", permiso.name):
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail=HTTPError(
                    detail="Formato de permiso inválido",
                    code="VAL_003",
                    status_code=HTTPStatus.BAD_REQUEST
                ).dict()
            )
        
        repo = PermisoRepository(db)
        if await repo.existe(permiso.name):
            raise PermisoExistente(nombre=permiso.name)
            
        nuevo_permiso = Permiso(
            name=permiso.name,
            description=permiso.description
        )
        
        permiso_creado = await repo.guardar(nuevo_permiso)
        
        await AuditProducer().enviar_evento(
            tipo="PERMISO_CREADO",
            detalles={
                "usuario": usuario_actual.id,
                "permiso": permiso_creado.name
            }
        )
        
        return PermissionOut(**permiso_creado.__dict__)
        
    except PermisoExistente as e:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail=HTTPError(
                detail=str(e),
                code="PERM_001",
                status_code=HTTPStatus.CONFLICT
            ).dict()
        )
    except DatabaseError as e:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=HTTPError(
                detail="Error de base de datos",
                code="DB_001",
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR
            ).dict()
        )

@router.get(
    "",
    response_model=PaginatedResponse[List[PermissionOut]],
    summary="Listar todos los permisos",
    responses={
        403: {"model": HTTPError, "description": "Permisos insuficientes"}
    }
)
async def listar_permisos(
    db: AsyncSession = Depends(get_db),
    usuario_actual=Depends(obtener_usuario_actual)
):
    try:
        if not await PermissionChecker.verificar(usuario_actual, "permisos:leer"):
            raise PermissionDeniedError(permission="permisos:leer")
        
        repo = PermisoRepository(db)
        permisos = await repo.listar_todos()
        return PaginatedResponse(
            data=[PermissionOut(**p.__dict__) for p in permisos],
            total=len(permisos),
            limit=len(permisos),
            offset=0
        )
        
    except DatabaseError as e:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=HTTPError(
                detail="Error de base de datos",
                code="DB_001",
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR
            ).dict()
        )

@router.get(
    "/{nombre_permiso}",
    response_model=PermissionOut,
    summary="Obtener detalles de un permiso",
    responses={
        404: {"model": HTTPError, "description": "Permiso no encontrado"}
    }
)
async def obtener_permiso(
    nombre_permiso: str,
    db: AsyncSession = Depends(get_db)
):
    try:
        repo = PermisoRepository(db)
        permiso = await repo.obtener_por_nombre(nombre_permiso)
        if not permiso:
            raise PermisoNoEncontrado(nombre=nombre_permiso)
            
        return PermissionOut(**permiso.__dict__)
        
    except PermisoNoEncontrado as e:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=HTTPError(
                detail=str(e),
                code="PERM_002",
                status_code=HTTPStatus.NOT_FOUND
            ).dict()
        )

@router.put(
    "/{nombre_permiso}",
    response_model=PermissionOut,
    summary="Actualizar un permiso",
    responses={
        403: {"model": HTTPError},
        404: {"model": HTTPError}
    }
)
async def actualizar_permiso(
    nombre_permiso: str,
    datos_actualizacion: PermissionCreate,
    db: AsyncSession = Depends(get_db),
    usuario_actual=Depends(obtener_usuario_actual)
):
    try:
        if not await PermissionChecker.verificar(usuario_actual, "permisos:actualizar"):
            raise PermissionDeniedError(permission="permisos:actualizar")
        
        repo = PermisoRepository(db)
        permiso = await repo.obtener_por_nombre(nombre_permiso)
        if not permiso:
            raise PermisoNoEncontrado(nombre=nombre_permiso)
            
        permiso.description = datos_actualizacion.description
        
        permiso_actualizado = await repo.guardar(permiso)
        
        await AuditProducer().enviar_evento(
            tipo="PERMISO_ACTUALIZADO",
            detalles={
                "usuario": usuario_actual.id,
                "permiso": nombre_permiso,
                "cambios": datos_actualizacion.dict()
            }
        )
        
        return PermissionOut(**permiso_actualizado.__dict__)
        
    except DatabaseError as e:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=HTTPError(
                detail="Error de base de datos",
                code="DB_001",
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR
            ).dict()
        )

@router.delete(
    "/{nombre_permiso}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar un permiso",
    responses={
        403: {"model": HTTPError},
        404: {"model": HTTPError},
        409: {"model": HTTPError, "description": "Permiso en uso"}
    }
)
async def eliminar_permiso(
    nombre_permiso: str,
    db: AsyncSession = Depends(get_db),
    usuario_actual=Depends(obtener_usuario_actual)
):
    try:
        if not await PermissionChecker.verificar(usuario_actual, "permisos:eliminar"):
            raise PermissionDeniedError(permission="permisos:eliminar")
        
        permiso_repo = PermisoRepository(db)
        rol_repo = RoleRepository(db)
        
        permiso = await permiso_repo.obtener_por_nombre(nombre_permiso)
        if not permiso:
            raise PermisoNoEncontrado(nombre=nombre_permiso)
            
        if await rol_repo.permiso_en_uso(nombre_permiso):
            raise PermisoEnUso(nombre=nombre_permiso)
            
        await permiso_repo.eliminar(permiso)
        
        await AuditProducer().enviar_evento(
            tipo="PERMISO_ELIMINADO",
            detalles={
                "usuario": usuario_actual.id,
                "permiso": nombre_permiso
            }
        )
        
    except PermisoEnUso as e:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail=HTTPError(
                detail=str(e),
                code="PERM_003",
                status_code=HTTPStatus.CONFLICT
            ).dict()
        )