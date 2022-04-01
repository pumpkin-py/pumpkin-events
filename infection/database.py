from __future__ import annotations

import datetime
import nextcord
from typing import List, Optional, Set

from sqlalchemy import BigInteger, Boolean, Column, Float, Integer, Interval

from pie.database import database, session


class InfectionConfig(database.base):
    __tablename__ = "private_infection_config"

    guild_id = Column(BigInteger, primary_key=True)
    role_id = Column(BigInteger)
    probability = Column(Float, default=0.05)
    symptom_delay = Column(Interval, default=datetime.timedelta(hours=3))
    cure_delay = Column(Interval, default=datetime.timedelta(hours=12))
    quiet = Column(Boolean, default=False)
    enabled = Column(Boolean, default=True)

    @classmethod
    def get_all(cls) -> List[InfectionConfig]:
        return session.query(cls).all()

    @classmethod
    def get_guild_ids(cls) -> Set[int]:
        configs = session.query(cls).all()
        return set(c.guild_id for c in configs)

    @classmethod
    def get(cls, guild_id: int) -> Optional[InfectionConfig]:
        return session.query(cls).filter_by(guild_id=guild_id).one_or_none()

    @classmethod
    def add(cls, guild_id: int, role_id: int) -> Optional[InfectionConfig]:
        if cls.get(guild_id) is not None:
            return None
        config = InfectionConfig(guild_id=guild_id, role_id=role_id)
        session.add(config)
        session.commit()
        return config

    def save(self) -> InfectionConfig:
        session.commit()
        return self

    def dump(self):
        return {
            "guild_id": self.guild_id,
            "role_id": self.role_id,
            "probability": self.probability,
            "symptom_delay": self.symptom_delay,
            "cure_delay": self.cure_delay,
            "quiet": self.quiet,
            "enabled": self.enabled,
        }

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} "
            + " ".join(f"{k}='{v}'" for (k, v) in self.dump().items())
            + ">"
        )


class Infected(database.base):
    __tablename__ = "private_infection_data"

    idx = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger)
    guild_id = Column(BigInteger)
    channel_id = Column(BigInteger)
    message_id = Column(BigInteger)
    infected_by = Column(BigInteger)
    symptomatic = Column(Boolean, default=False)
    cured = Column(Boolean, default=False)

    @property
    def infected_at(self) -> datetime.datetime:
        return nextcord.Object(self.message_id).created_at

    @classmethod
    def is_infected(cls, guild_id: int, user_id: int) -> bool:
        query = (
            session.query(cls)
            .filter_by(guild_id=guild_id, user_id=user_id, cured=False)
            .count()
        )
        return query > 0

    @classmethod
    def get_all(cls, guild_id: int) -> List[Infected]:
        query = (
            session.query(cls)
            .filter_by(guild_id=guild_id)
            .order_by(cls.message_id.asc())
            .all()
        )
        return query

    @classmethod
    def get_spreaders(cls) -> List[Infected]:
        query = session.query(cls).filter_by(cured=False).all()
        return query

    @classmethod
    def get(cls, guild_id: int, user_id: int) -> Optional[Infected]:
        query = (
            session.query(cls)
            .filter_by(guild_id=guild_id, user_id=user_id)
            .one_or_none()
        )
        return query

    @classmethod
    def add(
        cls,
        user_id: int,
        *,
        guild_id: int,
        channel_id: int,
        message_id: int,
        infected_by: int,
    ) -> Optional[Infected]:
        if cls.get(guild_id, user_id):
            return None

        infected = Infected(
            user_id=user_id,
            guild_id=guild_id,
            channel_id=channel_id,
            message_id=message_id,
            infected_by=infected_by,
        )
        session.add(infected)
        session.commit()
        return infected

    def save(self):
        session.commit()
        return self

    def dump(self):
        return {
            "user_id": self.user_id,
            "guild_id": self.guild_id,
            "channel_id": self.channel_id,
            "message_id": self.message_id,
            "infected_by": self.infected_by,
            "symptomatic": self.symptomatic,
            "cured": self.cured,
        }

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} "
            + " ".join(f"{k}='{v}'" for (k, v) in self.dump().items())
            + ">"
        )
