import uuid
from app.services.database import SessionLocal, Appointment, Doctor, Schedule, init_db
import datetime

# 初始化数据库
init_db()

# 预设的可预约时段
DEFAULT_TIME_SLOTS = ["10:00", "11:00", "14:00", "15:00", "16:30", "17:30"]

# 预设医生数据
DOCTORS_DATA = [
    {
        "name": "李明",
        "department": "口腔科",
        "title": "主任医师",
        "specialties": "种植牙、口腔修复",
        "phone": "13900139001"
    },
    {
        "name": "王芳",
        "department": "正畸科",
        "title": "副主任医师",
        "specialties": "牙齿矫正、隐形正畸",
        "phone": "13900139002"
    },
    {
        "name": "张伟",
        "department": "口腔科",
        "title": "主治医师",
        "specialties": "洗牙、牙周治疗",
        "phone": "13900139003"
    }
]


def init_default_doctors():
    """初始化默认医生数据"""
    db = SessionLocal()
    try:
        for doctor_data in DOCTORS_DATA:
            existing = db.query(Doctor).filter(Doctor.name == doctor_data["name"]).first()
            if not existing:
                doctor = Doctor(
                    id=str(uuid.uuid4()),
                    **doctor_data
                )
                db.add(doctor)
        db.commit()
    finally:
        db.close()


def init_default_schedules(days=7):
    """初始化默认排班数据（未来7天）"""
    db = SessionLocal()
    try:
        doctors = db.query(Doctor).all()
        today = datetime.date.today()
        
        for i in range(days):
            date = today + datetime.timedelta(days=i)
            # 周末（周六、周日）也排班
            for doctor in doctors:
                for time_slot in DEFAULT_TIME_SLOTS:
                    existing = db.query(Schedule).filter(
                        Schedule.doctor_id == doctor.id,
                        Schedule.date == date,
                        Schedule.time_slot == time_slot
                    ).first()
                    if not existing:
                        schedule = Schedule(
                            id=str(uuid.uuid4()),
                            doctor_id=doctor.id,
                            date=date,
                            time_slot=time_slot,
                            status="available"
                        )
                        db.add(schedule)
        db.commit()
    finally:
        db.close()


def get_doctors(department=None):
    """获取医生列表"""
    db = SessionLocal()
    try:
        query = db.query(Doctor)
        if department:
            query = query.filter(Doctor.department == department)
        return [
            {
                "id": d.id,
                "name": d.name,
                "department": d.department,
                "title": d.title,
                "specialties": d.specialties
            }
            for d in query.all()
        ]
    finally:
        db.close()


def get_slots(doctor_id=None, date=None):
    """获取可预约时段"""
    db = SessionLocal()
    try:
        query = db.query(Schedule).filter(Schedule.status == "available")
        
        if doctor_id:
            query = query.filter(Schedule.doctor_id == doctor_id)
        if date:
            query = query.filter(Schedule.date == date)
        
        slots = {}
        for s in query.all():
            date_str = s.date.strftime("%Y-%m-%d")
            if date_str not in slots:
                slots[date_str] = []
            slots[date_str].append({
                "id": s.id,
                "doctor_id": s.doctor_id,
                "time_slot": s.time_slot,
                "date": date_str
            })
        
        # 如果没有过滤条件，返回简单的时段列表（兼容旧接口）
        if not doctor_id and not date:
            return DEFAULT_TIME_SLOTS
        
        return slots
    finally:
        db.close()


def get_doctor_by_id(doctor_id):
    """根据ID获取医生信息"""
    db = SessionLocal()
    try:
        doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
        if doctor:
            return {
                "id": doctor.id,
                "name": doctor.name,
                "department": doctor.department,
                "title": doctor.title,
                "specialties": doctor.specialties
            }
        return None
    finally:
        db.close()


def create_appointment(name, phone, time, service, doctor_id=None):
    """创建预约并保存到数据库"""
    db = SessionLocal()
    try:
        # 生成唯一ID
        appointment_id = str(uuid.uuid4())
        
        # 查找对应医生（如果指定）
        doctor = None
        if doctor_id:
            doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
            if doctor:
                # 更新排班状态为已预约
                today = datetime.date.today()
                schedule = db.query(Schedule).filter(
                    Schedule.doctor_id == doctor_id,
                    Schedule.date == today,
                    Schedule.time_slot == time,
                    Schedule.status == "available"
                ).first()
                if schedule:
                    schedule.status = "reserved"
        
        # 创建预约对象
        appointment = Appointment(
            id=appointment_id,
            name=name,
            phone=phone,
            time=time,
            service=service,
            doctor_id=doctor_id,
            status="pending"
        )
        
        # 保存到数据库
        db.add(appointment)
        db.commit()
        db.refresh(appointment)
        
        # 获取医生姓名用于返回消息
        doctor_name = doctor.name if doctor else "医生"
        
        return f"已为您预约{service}服务，接诊医生：{doctor_name}，时间：{time}。我们会尽快与您确认。"
    finally:
        db.close()


def get_appointments(status=None):
    """获取所有预约"""
    db = SessionLocal()
    try:
        query = db.query(Appointment)
        if status:
            query = query.filter(Appointment.status == status)
        
        results = []
        for apt in query.all():
            doctor_info = None
            if apt.doctor:
                doctor_info = {
                    "id": apt.doctor.id,
                    "name": apt.doctor.name,
                    "department": apt.doctor.department
                }
            
            results.append({
                "id": apt.id,
                "name": apt.name,
                "phone": apt.phone,
                "time": apt.time,
                "service": apt.service,
                "status": apt.status,
                "doctor": doctor_info,
                "created_at": apt.created_at.strftime("%Y-%m-%d %H:%M:%S") if apt.created_at else None,
                "visit_notes": apt.visit_notes
            })
        
        return results
    finally:
        db.close()


def update_appointment_status(appointment_id, status, visit_notes=None):
    """更新预约状态"""
    db = SessionLocal()
    try:
        appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
        if appointment:
            appointment.status = status
            if visit_notes:
                appointment.visit_notes = visit_notes
            db.commit()
            return "状态更新成功"
        return "预约不存在"
    finally:
        db.close()


def recommend_doctors(service_type):
    """
    根据服务类型推荐医生
    :param service_type: 服务类型（如种植牙、正畸、洗牙等）
    :return: 推荐的医生列表（按匹配度排序）
    """
    db = SessionLocal()
    try:
        doctors = db.query(Doctor).all()
        recommendations = []
        
        for doctor in doctors:
            # 检查擅长领域匹配度
            specialties = doctor.specialties if doctor.specialties else ""
            match_score = 0
            
            # 根据服务类型匹配擅长领域
            if service_type in specialties:
                match_score += 3  # 完全匹配加3分
            else:
                # 检查部分匹配
                service_keywords = service_type.replace("牙", "").replace("齿", "").replace("种", "")
                for specialty in specialties.split("、"):
                    if service_keywords in specialty or specialty in service_type:
                        match_score += 1  # 部分匹配加1分
            
            # 检查医生是否有可用排班
            today = datetime.date.today()
            available_slots = db.query(Schedule).filter(
                Schedule.doctor_id == doctor.id,
                Schedule.date >= today,
                Schedule.status == "available"
            ).count()
            
            # 有可用排班加分
            if available_slots > 0:
                match_score += available_slots // 2  # 每2个可用时段加1分
            
            if match_score > 0:
                recommendations.append({
                    "id": doctor.id,
                    "name": doctor.name,
                    "department": doctor.department,
                    "title": doctor.title,
                    "specialties": specialties,
                    "available_slots": available_slots,
                    "match_score": match_score
                })
        
        # 按匹配度排序
        recommendations.sort(key=lambda x: -x["match_score"])
        
        return recommendations
    finally:
        db.close()


# 初始化默认数据
init_default_doctors()
init_default_schedules()
