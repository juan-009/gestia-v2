from typing import Optional, List, AsyncGenerator
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete, and_

from app.dominio.modelos import Usuario
from app.dominio.excepciones import (
    UsuarioNoEncontrado,
    CuentaBloqueada,
    EmailDuplicado,
    DatabaseError
)
from app.infraestructura.persistencia.orm import Base, UsuarioDB, RolUsuarioDB
from app.infraestructura.persistencia.adaptadores import mapear_usuario

class RepositorioUsuarios:
    def __init__(self, sesion: AsyncGenerator[AsyncSession, None]):
        self.sesion = sesion
        self.max_intentos_fallidos = 5
        self.tiempo_bloqueo = 300  # 5 minutos en segundos

    async def obtener_por_id(self, usuario_id: str) -> Optional[Usuario]:
        try:
            async with self.sesion() as session:
                resultado = await session.execute(
                    select(UsuarioDB)
                    .options(selectinload(UsuarioDB.roles))
                    .where(UsuarioDB.id == usuario_id)
                )
                usuario_db = resultado.scalars().first()
                
                if not usuario_db:
                    raise UsuarioNoEncontrado(id=usuario_id)
                    
                return mapear_usuario(usuario_db)
                
        except Exception as e:
            raise DatabaseError(
                operacion="obtener_usuario_por_id",
                error=str(e)
            )

    async def obtener_por_email(self, email: str) -> Optional[Usuario]:
        try:
            async with self.sesion() as session:
                resultado = await session.execute(
                    select(UsuarioDB)
                    .options(selectinload(UsuarioDB.roles))
                    .where(UsuarioDB.email == email)
                )
                usuario_db = resultado.scalars().first()
                
                if not usuario_db:
                    raise UsuarioNoEncontrado(email=email)
                    
                return mapear_usuario(usuario_db)
                
        except Exception as e:
            raise DatabaseError(
                operacion="obtener_usuario_por_email",
                error=str(e)
            )

    async def guardar(self, usuario: Usuario) -> Usuario:
        try:
            async with self.sesion() as session:
                usuario_db = UsuarioDB(**usuario.dict(exclude={
                    'roles', 
                    'mfa_secreto',
                    'password'
                }))
                
                # Manejo de campos sensibles
                usuario_db.hashed_password = usuario.hashed_password
                usuario_db.mfa_secreto = usuario.mfa_secreto
                
                # Manejo de roles
                if usuario.roles:
                    roles = [
                        RolUsuarioDB(
                            usuario_id=usuario_db.id,
                            rol_nombre=rol
                        ) for rol in usuario.roles
                    ]
                    usuario_db.roles = roles
                
                session.add(usuario_db)
                await session.commit()
                await session.refresh(usuario_db)
                
                return mapear_usuario(usuario_db)
                
        except Exception as e:
            await session.rollback()
            if 'unique constraint' in str(e).lower():
                raise EmailDuplicado(email=usuario.email)
            raise DatabaseError(
                operacion="guardar_usuario",
                error=str(e)
            )

    async def eliminar(self, usuario_id: str):
        try:
            async with self.sesion() as session:
                resultado = await session.execute(
                    delete(UsuarioDB).where(UsuarioDB.id == usuario_id))
                    
                if resultado.rowcount == 0:
                    raise UsuarioNoEncontrado(id=usuario_id)
                    
                await session.commit()
                
        except Exception as e:
            await session.rollback()
            raise DatabaseError(
                operacion="eliminar_usuario",
                error=str(e)
            )

    async def listar_todos(
        self, 
        offset: int = 0, 
        limit: int = 100,
        solo_activos: bool = True
    ) -> List[Usuario]:
        try:
            async with self.sesion() as session:
                query = select(UsuarioDB)
                if solo_activos:
                    query = query.where(UsuarioDB.esta_activo == True)
                
                resultado = await session.execute(
                    query.offset(offset).limit(limit)
                )
                usuarios_db = resultado.scalars().all()
                
                return [mapear_usuario(u) for u in usuarios_db]
                
        except Exception as e:
            raise DatabaseError(
                operacion="listar_usuarios",
                error=str(e)
            )

    async def existe(self, email: str) -> bool:
        try:
            async with self.sesion() as session:
                resultado = await session.execute(
                    select(UsuarioDB).where(UsuarioDB.email == email))
                return resultado.scalars().first() is not None
                
        except Exception as e:
            raise DatabaseError(
                operacion="verificar_existencia_usuario",
                error=str(e)
            )

    async def actualizar(
        self, 
        usuario_id: str, 
        campos_actualizados: dict
    ) -> Usuario:
        try:
            async with self.sesion() as session:
                # Actualizar campos básicos
                if campos_actualizados:
                    await session.execute(
                        update(UsuarioDB)
                        .where(UsuarioDB.id == usuario_id)
                        .values(**campos_actualizados)
                    )
                
                # Actualizar roles si están presentes
                if 'roles' in campos_actualizados:
                    await session.execute(
                        delete(RolUsuarioDB)
                        .where(RolUsuarioDB.usuario_id == usuario_id)
                    )
                    if campos_actualizados['roles']:
                        nuevos_roles = [
                            RolUsuarioDB(
                                usuario_id=usuario_id,
                                rol_nombre=rol
                            ) for rol in campos_actualizados['roles']
                        ]
                        session.add_all(nuevos_roles)
                
                await session.commit()
                return await self.obtener_por_id(usuario_id)
                
        except Exception as e:
            await session.rollback()
            raise DatabaseError(
                operacion="actualizar_usuario",
                error=str(e)
            )

    async def esta_bloqueado(self, usuario_id: str) -> bool:
        try:
            usuario = await self.obtener_por_id(usuario_id)
            if usuario.intentos_fallidos < self.max_intentos_fallidos:
                return False
                
            tiempo_transcurrido = (datetime.utcnow() - usuario.ultimo_intento_fallido).seconds
            return tiempo_transcurrido < self.tiempo_bloqueo
            
        except Exception as e:
            raise DatabaseError(
                operacion="verificar_bloqueo_usuario",
                error=str(e)
            )

    async def incrementar_intento_fallido(self, usuario_id: str):
        try:
            async with self.sesion() as session:
                await session.execute(
                    update(UsuarioDB)
                    .where(UsuarioDB.id == usuario_id)
                    .values(
                        intentos_fallidos=UsuarioDB.intentos_fallidos + 1,
                        ultimo_intento_fallido=datetime.utcnow()
                    )
                )
                await session.commit()
                
        except Exception as e:
            await session.rollback()
            raise DatabaseError(
                operacion="incrementar_intento_fallido",
                error=str(e)
            )

    async def actualizar_secreto_mfa(self, usuario_id: str, secreto: str):
        try:
            async with self.sesion() as session:
                await session.execute(
                    update(UsuarioDB)
                    .where(UsuarioDB.id == usuario_id)
                    .values(mfa_secreto=secreto)
                )
                await session.commit()
                
        except Exception as e:
            await session.rollback()
            raise DatabaseError(
                operacion="actualizar_secreto_mfa",
                error=str(e)
            )

    async def actualizar_estado_mfa(self, usuario_id: str, habilitado: bool):
        try:
            async with self.sesion() as session:
                await session.execute(
                    update(UsuarioDB)
                    .where(UsuarioDB.id == usuario_id)
                    .values(mfa_habilitado=habilitado)
                )
                await session.commit()
                
        except Exception as e:
            await session.rollback()
            raise DatabaseError(
                operacion="actualizar_estado_mfa",
                error=str(e)
            )

    async def actualizar_ultimo_cambio_password(self, usuario_id: str):
        try:
            async with self.sesion() as session:
                await session.execute(
                    update(UsuarioDB)
                    .where(UsuarioDB.id == usuario_id)
                    .values(ultimo_cambio_password=datetime.utcnow())
                )
                await session.commit()
                
        except Exception as e:
            await session.rollback()
            raise DatabaseError(
                operacion="actualizar_ultimo_cambio_password",
                error=str(e)
            )