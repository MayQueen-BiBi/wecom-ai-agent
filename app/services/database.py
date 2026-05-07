from sqlalchemy import create_engine, Column, String, DateTime, Text, Date, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import datetime

# 创建数据库引擎（使用SQLite）
engine = create_engine('sqlite:///appointments.db', echo=True)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基类
Base = declarative_base()


class Doctor(Base):
    """医生模型"""
    __tablename__ = "doctors"
    
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)    # 医生姓名
    department = Column(String)              # 科室（如口腔科、正畸科）
    title = Column(String)                   # 职称（主任医师、副主任医师等）
    specialties = Column(Text)               # 擅长领域
    phone = Column(String)                   # 联系电话
    
    # 关联关系
    schedules = relationship("Schedule", back_populates="doctor")
    appointments = relationship("Appointment", back_populates="doctor")


class Schedule(Base):
    """排班模型"""
    __tablename__ = "schedules"
    
    id = Column(String, primary_key=True, index=True)
    doctor_id = Column(String, ForeignKey("doctors.id"))  # 关联医生
    date = Column(Date, nullable=False)       # 排班日期
    time_slot = Column(String, nullable=False) # 时间段（如 14:00）
    status = Column(String, default="available")  # available/busy/reserved
    
    # 关联关系
    doctor = relationship("Doctor", back_populates="schedules")


class Appointment(Base):
    """预约模型"""
    __tablename__ = "appointments"
    
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)    # 用户姓名
    phone = Column(String, nullable=False)   # 用户电话
    time = Column(String, nullable=False)    # 预约时间
    service = Column(String, nullable=False) # 服务类型（如种植牙、洗牙）
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # 新增字段
    doctor_id = Column(String, ForeignKey("doctors.id"))  # 关联医生
    status = Column(String, default="pending")  # pending/confirmed/visited/canceled
    visit_notes = Column(Text)  # 就诊记录/诊断结果
    
    # 关联关系
    doctor = relationship("Doctor", back_populates="appointments")


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
