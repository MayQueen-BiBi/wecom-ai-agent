from sqlalchemy import create_engine, Column, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime

# 创建数据库引擎（使用SQLite）
engine = create_engine('sqlite:///appointments.db', echo=True)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基类
Base = declarative_base()


class Appointment(Base):
    """预约模型"""
    __tablename__ = "appointments"
    
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    time = Column(String, nullable=False)
    service = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    status = Column(String, default="pending")


# 创建表
def init_db():
    Base.metadata.create_all(bind=engine)


# 依赖项，用于获取数据库会话
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
