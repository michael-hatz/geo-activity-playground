import datetime

import sqlalchemy as sa
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship


class Base(DeclarativeBase):
    pass


tile_visits_table = Table(
    "tile_visits_auto",
    Base.metadata,
    Column(
        "activity_id", ForeignKey("activities.id", name="activity_id"), primary_key=True
    ),
    Column("tile_id", ForeignKey("tiles.id", name="tile_id"), primary_key=True),
)


class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(primary_key=True)
    updated: Mapped[datetime.timedelta] = mapped_column(sa.DateTime, nullable=False)

    calories: Mapped[int] = mapped_column(sa.Integer, nullable=True)
    consider_for_achievements: Mapped[bool] = mapped_column(
        sa.Boolean, default=True, nullable=False
    )
    distance_km: Mapped[float] = mapped_column(sa.Float, nullable=False)
    elapsed_time: Mapped[datetime.timedelta] = mapped_column(
        sa.Interval, nullable=False
    )
    end_latitude: Mapped[float] = mapped_column(sa.Float, nullable=True)
    end_longitude: Mapped[float] = mapped_column(sa.Float, nullable=True)
    moving_time: Mapped[datetime.timedelta] = mapped_column(sa.Interval, nullable=True)
    name: Mapped[str] = mapped_column(sa.String, nullable=False)
    path: Mapped[str] = mapped_column(sa.String, nullable=True)
    start_latitude: Mapped[float] = mapped_column(sa.Float, nullable=True)
    start_longitude: Mapped[float] = mapped_column(sa.Float, nullable=True)
    start: Mapped[datetime.datetime] = mapped_column(sa.DateTime, nullable=False)
    steps: Mapped[int] = mapped_column(sa.Integer, nullable=True)

    equipment_id: Mapped[int] = mapped_column(
        ForeignKey("equipments.id", name="equipment_id")
    )
    equipment: Mapped["Equipment"] = relationship(back_populates="activities")
    kind_id: Mapped[int] = mapped_column(ForeignKey("kinds.id", name="kind_id"))
    kind: Mapped["Kind"] = relationship(back_populates="activities")
    tile_visits: Mapped[list["Tile"]] = relationship(
        back_populates="tile_visits", secondary=tile_visits_table
    )
    new_tiles: Mapped[list["Tile"]] = relationship(back_populates="first_visit")


class Equipment(Base):
    __tablename__ = "equipments"

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(String)

    activities: Mapped[list["Activity"]] = relationship(
        back_populates="equipment", cascade="all, delete-orphan"
    )

    __table_args__ = (sa.UniqueConstraint("name", name="equipments_name"),)


class Kind(Base):
    __tablename__ = "kinds"

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(String)

    activities: Mapped[list["Activity"]] = relationship(
        back_populates="kind", cascade="all, delete-orphan"
    )

    __table_args__ = (sa.UniqueConstraint("name", name="kinds_name"),)


class Tile(Base):
    __tablename__ = "tiles"

    id: Mapped[int] = mapped_column(primary_key=True)

    zoom: Mapped[int] = mapped_column(sa.Integer, index=True, nullable=False)
    x: Mapped[int] = mapped_column(sa.Integer, index=True, nullable=False)
    y: Mapped[int] = mapped_column(sa.Integer, index=True, nullable=False)

    first_visit_id: Mapped[int] = mapped_column(
        ForeignKey("activities.id", name="first_visit_id")
    )
    first_visit: Mapped["Activity"] = relationship(
        back_populates="new_tiles", foreign_keys=[first_visit_id]
    )
    tile_visits: Mapped[list["Activity"]] = relationship(
        back_populates="tile_visits", secondary=tile_visits_table
    )
