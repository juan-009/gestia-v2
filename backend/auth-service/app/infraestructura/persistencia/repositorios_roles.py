from typing import Optional, List, AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete, and_

from app.dominio.modelos import Rol
from app.dominio.excepciones import (
    RolNoEncontrado,
    RolEnUso,
    RoleConflictError,
    DatabaseError
)
from app.infraestructura.persistencia.orm import Base, RolDB, PermisoRolDB
from app.infraestructura.persistencia.adaptadores import mapear_rol

class RepositorioRoles:
    def __init__(self, sesion: AsyncGenerator[AsyncSession, None]):
        self.sesion = sesion

    async def obtener_por_id(self, rol_id: str) -> Optional[Rol]:
        try:
            async with self.sesion() as session:
                resultado = await session.execute(
                    select(RolDB).where(RolDB.id == rol_id)
                )
                rol_db = resultado.scalars().first()
                
                if not rol_db:
                    raise RolNoEncontrado(id=rol_id)
                    
                return mapear_rol(rol_db)
        except Exception as e:
            raise DatabaseError(
                operacion="obtener_rol_por_id",
                error=str(e)
            )
                
        except Exception as e:
            raise DatabaseError(
                operacion="obtener_rol_por_id",
                error=str(e)
            )

    async def obtener_por_nombre(self, nombre: str) -> Optional[Rol]:
        try:
            async with self.sesion() as session:
                resultado = await session.execute(
                    select(RolDB).where(RolDB.nombre == nombre))
                rol_db = resultado.scalars().first()
                
                if not rol_db:
                    raise RolNoEncontrado(nombre=nombre)
                    
                return mapear_rol(rol_db)
                
        except Exception as e:
            raise DatabaseError(
                operacion="obtener_rol_por_nombre",
                error=str(e)
            )

    async def guardar(self, rol: Rol) -> Rol:
        try:
            async with self.sesion() as session:
                rol_db = RolDB(**rol.dict(exclude={"permisos"}))
                
                # Manejo de permisos
                if rol.permisos:
                    permisos = [
                        PermisoRolDB(
                            rol_id=rol_db.id,
                            permiso_id=permiso_id
                        ) for permiso_id in rol.permisos
                    ]
                    rol_db.permisos = permisos
                
                session.add(rol_db)
                await session.commit()
                await session.refresh(rol_db)
                
                return mapear_rol(rol_db)
                
        except Exception as e:
            await session.rollback()
            if "duplicate key value" in str(e).lower():
                raise RoleConflictError(
                    rol=rol.nombre,
                    razon="Rol ya existe en la base de datos"
                )
            raise DatabaseError(
                operacion="guardar_rol",
                error=str(e)
            )

    async def eliminar(self, nombre: str):
        try:
            async with self.sesion() as session:
                if await self.esta_en_uso(nombre):
                    raise RolEnUso(nombre=nombre)
                
                resultado = await session.execute(
                    delete(RolDB).where(RolDB.nombre == nombre))
                    
                if resultado.rowcount == 0:
                    raise RolNoEncontrado(nombre=nombre)
                    
                await session.commit()
                
        except Exception as e:
            await session.rollback()
            raise DatabaseError(
                operacion="eliminar_rol",
                error=str(e)
            )

    async def listar_todos(self) -> List[Rol]:
        try:
            async with self.sesion() as session:
                resultado = await session.execute(
                    select(RolDB).order_by(RolDB.nombre))
                roles_db = resultado.scalars().all()
                
                return [mapear_rol(r) for r in roles_db]
                
        except Exception as e:
            raise DatabaseError(
                operacion="listar_roles",
                error=str(e)
            )

    async def existe(self, nombre: str) -> bool:
        try:
            async with self.sesion() as session:
                resultado = await session.execute(
                    select(RolDB).where(RolDB.nombre == nombre))
                return resultado.scalars().first() is not None
                
        except Exception as e:
            raise DatabaseError(
                operacion="verificar_existencia_rol",
                error=str(e)
            )

    async def esta_en_uso(self, nombre_rol: str) -> bool:
        try:
            async with self.sesion() as session:
                # Verificar si hay usuarios con este rol
                from .repositorio_usuarios import UsuarioDB  # Importación local
                
                usuarios = await session.execute(
                    select(UsuarioDB).where(
                        UsuarioDB.roles.any(nombre_rol))
                )
                if usuarios.scalars().first():
                    return True
                
                # Verificar si es heredado por otros roles
                roles = await session.execute(
                    select(RolDB).where(
                        RolDB.hereda.contains([nombre_rol]))
                )
                return roles.scalars().first() is not None
                
        except Exception as e:
            raise DatabaseError(
                operacion="verificar_rol_en_uso",
                error=str(e)
            )

    async def actualizar_permisos(self, rol_id: str, permisos: List[str]):
        try:
            async with self.sesion() as session:
                # Eliminar permisos existentes
                await session.execute(
                    delete(PermisoRolDB).where(
                        PermisoRolDB.rol_id == rol_id))
                
                # Agregar nuevos permisos
                if permisos:
                    nuevos_permisos = [
                        PermisoRolDB(
                            rol_id=rol_id,
                            permiso_id=permiso_id
                        ) for permiso_id in permisos
                    ]
                    session.add_all(nuevos_permisos)
                
                await session.commit()
                
        except Exception as e:
            await session.rollback()
            raise DatabaseError(
                operacion="actualizar_permisos_rol",
                error=str(e)
            )

    async def agregar_herencia(self, rol_id: str, roles_heredados: List[str]):
        try:
            async with self.sesion() as session:
                await session.execute(
                    update(RolDB)
                    .where(RolDB.id == rol_id)
                    .values(hereda=roles_heredados)
                )
                await session.commit()
                
        except Exception as e:
            await session.rollback()
            if "foreign key constraint" in str(e).lower():
                raise RoleConflictError(
                    rol=rol_id,
                    razon="Rol heredado no existe"
                )
            raise DatabaseError(
                operacion="agregar_herencia_roles",
                error=str(e)
            )