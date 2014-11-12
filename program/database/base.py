from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql.expression import text
from sqlalchemy import Column, DateTime
Base = declarative_base()

class DataTableTemplate(Base):
    created_at = Column(DateTime, server_default=text('NOW()'))