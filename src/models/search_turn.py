from sqlalchemy import Column, String, JSON, TIMESTAMP, Integer, text
from sqlalchemy.dialects.postgresql import UUID
from db.sqlalchemy import Base

class SearchTurn(Base):
    __tablename__ = "search_turns"
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    ts = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"))
    session_id = Column(String, nullable=False)
    original_query = Column(String, nullable=False)
    rewritten_query = Column(String)
    used_query = Column(String)
    provider = Column(String)
    inferred_prefs = Column(JSON)
    result_meta = Column(JSON)