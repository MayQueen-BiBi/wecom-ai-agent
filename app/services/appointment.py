appointments = []

def get_slots():
    return ["14:00", "15:00", "16:30"]

def create_appointment(name, phone, time, service):
    appointments.append({
        "name": name,
        "phone": phone,
        "time": time,
        "service": service
    })
    return "预约成功"