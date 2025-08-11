from sqlalchemy import Column, String, JSON, TIMESTAMP, text
from sqlalchemy.dialects.postgresql import UUID
from db.sqlalchemy import Base

class MCPLog(Base):
    __tablename__ = "mcp_logs"
    id = Column(UUID(as_uuid=True), primary_key=True,
                server_default=text("gen_random_uuid()"))
    ts = Column(TIMESTAMP(timezone=True), nullable=False,
                server_default=text("now()"))
    session_id = Column(String)
    request_id = Column(String)
    level = Column(String, nullable=False)   
    message = Column(String, nullable=False)
    meta = Column(JSON)