import uuid
from app.services.database import SessionLocal, Appointment, init_db

# 初始化数据库
init_db()

def get_slots():
    """获取可预约时段"""
    return ["14:00", "15:00", "16:30"]

def create_appointment(name, phone, time, service):
    """创建预约并保存到数据库"""
    db = SessionLocal()
    try:
        # 生成唯一ID
        appointment_id = str(uuid.uuid4())
        
        # 创建预约对象
        appointment = Appointment(
            id=appointment_id,
            name=name,
            phone=phone,
            time=time,
            service=service
        )
        
        # 保存到数据库
        db.add(appointment)
        db.commit()
        db.refresh(appointment)
        
        return "预约成功"
    finally:
        db.close()

def get_appointments():
    """获取所有预约"""
    db = SessionLocal()
    try:
        return db.query(Appointment).all()
    finally:
        db.close()
