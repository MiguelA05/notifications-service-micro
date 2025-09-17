import json
from typing import List, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, func, or_, and_
from .models import Notification, NotificationChannelConfig, NotificationMetrics, NotificationStatus, NotificationChannel
from .schemas import ChannelInfo, NotificationCreate, NotificationDB, NotificationFilter, PageMeta, PaginatedResponse, MetricsSummary


def list_channels(db: Session) -> List[ChannelInfo]:
    rows = db.execute(select(NotificationChannelConfig)).scalars().all()
    channels: List[ChannelInfo] = []
    for row in rows:
        provider: Optional[str] = None
        try:
            cfg = json.loads(row.config) if row.config else {}
            provider = cfg.get("provider")
        except Exception:
            provider = None
        channels.append(ChannelInfo(name=row.name.value, enabled=row.enabled, provider=provider))
    return channels


def _apply_filters(stmt, f: NotificationFilter):
    conds = []
    if f.channel:
        conds.append(Notification.channel == NotificationChannel(f.channel))
    if f.status:
        conds.append(Notification.status == NotificationStatus(f.status))
    if f.q:
        like = f"%{f.q}%"
        conds.append(or_(Notification.destination.ilike(like), Notification.message.ilike(like)))
    if f.since:
        conds.append(Notification.created_at >= f.since)
    if f.until:
        conds.append(Notification.created_at <= f.until)
    if conds:
        stmt = stmt.where(and_(*conds))
    return stmt


def list_notifications(db: Session, f: NotificationFilter) -> PaginatedResponse:
    stmt = select(Notification).order_by(Notification.created_at.desc())
    stmt = _apply_filters(stmt, f)

    total = db.execute(_apply_filters(select(func.count()).select_from(Notification), f)).scalar() or 0

    offset = (f.page - 1) * f.size
    items = db.execute(stmt.offset(offset).limit(f.size)).scalars().all()
    items_schema = [NotificationDB(
        id=i.id,
        channel=i.channel.value,
        destination=i.destination,
        message=i.message,
        subject=i.subject,
        status=i.status.value,
        created_at=i.created_at,
        updated_at=i.updated_at,
    ) for i in items]
    meta = PageMeta(page=f.page, size=f.size, total=total)
    return PaginatedResponse(items=items_schema, meta=meta)


def get_notification(db: Session, notification_id: int) -> Optional[NotificationDB]:
    i = db.get(Notification, notification_id)
    if not i:
        return None
    return NotificationDB(
        id=i.id,
        channel=i.channel.value,
        destination=i.destination,
        message=i.message,
        subject=i.subject,
        status=i.status.value,
        created_at=i.created_at,
        updated_at=i.updated_at,
    )


def create_notification(db: Session, payload: NotificationCreate, user_id: str = "system") -> NotificationDB:
    status = NotificationStatus.SCHEDULED if payload.schedule_at else NotificationStatus.PENDING
    row = Notification(
        user_id=user_id,
        channel=NotificationChannel(payload.channel),
        destination=payload.destination,
        subject=payload.subject,
        message=payload.message,
        status=status,
        scheduled_at=payload.schedule_at,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return NotificationDB(
        id=row.id,
        channel=row.channel.value,
        destination=row.destination,
        message=row.message,
        subject=row.subject,
        status=row.status.value,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def get_metrics(db: Session) -> MetricsSummary:
    total = db.execute(select(func.count(Notification.id))).scalar() or 0
    sent = db.execute(select(func.count()).where(Notification.status == NotificationStatus.SENT)).scalar() or 0
    failed = db.execute(select(func.count()).where(Notification.status == NotificationStatus.FAILED)).scalar() or 0
    scheduled = db.execute(select(func.count()).where(Notification.status == NotificationStatus.SCHEDULED)).scalar() or 0
    in_process = db.execute(select(func.count()).where(Notification.status == NotificationStatus.PENDING)).scalar() or 0

    per_channel: dict[str, int] = {}
    rows = db.execute(select(Notification.channel, func.count()).group_by(Notification.channel)).all()
    for ch, cnt in rows:
        per_channel[str(ch.value)] = int(cnt)

    return MetricsSummary(
        total_notifications=total,
        sent=sent,
        failed=failed,
        scheduled=scheduled,
        in_process=in_process,
        per_channel=per_channel,
    )


# Schedules persistentes (usa Notification con status=scheduled)

def list_schedules(db: Session, page: int = 1, size: int = 20) -> PaginatedResponse:
    stmt = (
        select(Notification)
        .where(Notification.status == NotificationStatus.SCHEDULED)
        .order_by(Notification.scheduled_at.asc())
    )
    total = db.execute(select(func.count()).select_from(Notification).where(Notification.status == NotificationStatus.SCHEDULED)).scalar() or 0
    offset = (page - 1) * size
    items = db.execute(stmt.offset(offset).limit(size)).scalars().all()
    items_schema = [NotificationDB(
        id=i.id,
        channel=i.channel.value,
        destination=i.destination,
        message=i.message,
        subject=i.subject,
        status=i.status.value,
        created_at=i.created_at,
        updated_at=i.updated_at,
    ) for i in items]
    return PaginatedResponse(items=items_schema, meta=PageMeta(page=page, size=size, total=total))


def get_schedule(db: Session, schedule_id: int) -> Optional[NotificationDB]:
    i = db.get(Notification, schedule_id)
    if not i or i.status != NotificationStatus.SCHEDULED:
        return None
    return NotificationDB(
        id=i.id,
        channel=i.channel.value,
        destination=i.destination,
        message=i.message,
        subject=i.subject,
        status=i.status.value,
        created_at=i.created_at,
        updated_at=i.updated_at,
    )


def cancel_schedule(db: Session, schedule_id: int) -> bool:
    i = db.get(Notification, schedule_id)
    if not i or i.status != NotificationStatus.SCHEDULED:
        return False
    i.status = NotificationStatus.CANCELLED
    i.scheduled_at = None
    db.add(i)
    db.commit()
    return True


