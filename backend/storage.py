import os
from datetime import datetime,timezone
from sqlalchemy import create_engine, String, JSON, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

class Base(DeclarativeBase):pass

class SearchAudit(Base):
    __tablename__='search_audits'
    id:Mapped[str]=mapped_column(String(36),primary_key=True)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
    mode:Mapped[str]=mapped_column(String(16))
    result:Mapped[dict]=mapped_column(JSON)

class HotelMapping(Base):
    __tablename__='hotel_mappings'
    provider_key:Mapped[str]=mapped_column(String(200),primary_key=True)
    canonical_id:Mapped[str]=mapped_column(String(200),index=True)
    evidence:Mapped[dict]=mapped_column(JSON)

class VisaEvidence(Base):
    __tablename__='visa_evidence'
    id:Mapped[str]=mapped_column(String(36),primary_key=True)
    checked_at:Mapped[datetime]=mapped_column(DateTime(timezone=True))
    expires_at:Mapped[datetime]=mapped_column(DateTime(timezone=True))
    evidence:Mapped[dict]=mapped_column(JSON)

engine=None
def initialize_storage():
    global engine
    url=os.getenv('DATABASE_URL')
    if not url:return False
    engine=create_engine(url,pool_pre_ping=True,connect_args={'connect_timeout':3} if url.startswith('postgresql') else {})
    Base.metadata.create_all(engine)
    return True

def save_audit(id,mode,result):
    if engine is None:return
    with sessionmaker(engine)() as session:
        session.add(SearchAudit(id=id,mode=mode,result=result));session.commit()
