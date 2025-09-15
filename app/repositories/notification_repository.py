from app.models import Notification, NotificationChannel
from app.db import SessionLocal
from typing import Tuple, List, Optional
from sqlalchemy import select, func

class NotificationRepository:

    def __init__(self, db: Session):
        self.db = db

    def obtenerRegistrosNotificacion(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        user_id: Optional[str] = None,
        channel: Optional[str] = None,
        order_desc: bool = True
    ) -> Tuple[List[Notification], int]:
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 20

        # Construir query base
        stmt = select(Notification)
        count_stmt = select(func.count(Notification.id))

        # Aplicar filtros opcionales
        from sqlalchemy import and_
        filters = []
        if status is not None:
            filters.append(Notification.status == status)
        if user_id is not None:
            filters.append(Notification.user_id == user_id)
        if channel is not None:
            filters.append(Notification.channel == channel)

        if filters:
            stmt = stmt.where(and_(*filters))
            count_stmt = count_stmt.where(and_(*filters))

        # Orden
        if order_desc:
            stmt = stmt.order_by(Notification.created_at.desc())
        else:
            stmt = stmt.order_by(Notification.created_at.asc())

        # Paginación: cálculo de offset
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)

        # Ejecutar consultas
        result = self.db.execute(stmt).scalars().all()
        total = self.db.execute(count_stmt).scalar() or 0

        return result, int(total)
    
