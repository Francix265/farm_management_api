from fastapi import APIRouter, Depends, HTTPException
from database import cursor, db
from auth import get_current_user
from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional

router = APIRouter()

# Pydantic Models
class EquipmentCreate(BaseModel):
    name: str
    type: str
    usage_hours: Optional[float] = 0
    last_maintenance: Optional[date] = None
    next_maintenance: Optional[date] = None
    status: str  

class EquipmentUpdateStatus(BaseModel):
    status: str

class EquipmentUsageLog(BaseModel):
    hours_used: float

class MaintenanceLogCreate(BaseModel):
    equipment_id: int
    action: str
    details: str
    parts_replaced: Optional[str] = None
    cost: Optional[float] = 0.0
    next_maintenance: date

# ROUTES

# Add Equipment
@router.post("/add")
def add_equipment(item: EquipmentCreate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["manager", "equipment_manager"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    cursor.execute("""
        INSERT INTO equipment 
        (name, type, usage_hours, last_maintenance, next_maintenance, status, last_updated, last_updated_by)
        VALUES (%s, %s, %s, %s, %s, %s, NOW(), %s)
    """, (item.name, item.type, item.usage_hours, item.last_maintenance, item.next_maintenance, item.status, current_user["id"]))
    cursor.execute("""
            INSERT INTO system_logs 
            (action, details, performed_by)
            VALUES (%s, %s, %s)
            """,
            (
                "equipment_added",
                f"added equipment name: {item.name}",
                current_user["id"]
            )
        )
    db.commit()
    return {"message": "Equipment added successfully"}

# Update Equipment Status
@router.put("/update_status/{equipment_id}")
def update_equipment_status(equipment_id: int, update: EquipmentUpdateStatus, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["manager", "equipment_manager"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    cursor.execute("""
        UPDATE equipment 
        SET status=%s, last_updated=NOW(), last_updated_by=%s
        WHERE id=%s
    """, (update.status, current_user["id"], equipment_id))
    cursor.execute("""
            INSERT INTO system_logs 
            (action, details, performed_by)
            VALUES (%s, %s, %s)
            """,
            (
                "equipment_status_updated",
                f"updated equipment status ID {equipment_id}",
                current_user["id"]
            )
        )
    db.commit()
    return {"message": "Equipment status updated"}

# Log Equipment Usage
@router.put("/log_usage/{equipment_id}")
def log_equipment_usage(equipment_id: int, usage: EquipmentUsageLog, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["manager", "equipment_manager"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    cursor.execute("SELECT usage_hours FROM equipment WHERE id=%s", (equipment_id,))
    result = cursor.fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Equipment not found")

    new_usage_hours = result[0] + usage.hours_used

    cursor.execute("""
        UPDATE equipment 
        SET usage_hours=%s, last_updated=NOW(), last_updated_by=%s
        WHERE id=%s
    """, (new_usage_hours, current_user["id"], equipment_id))
    db.commit()

    return {"message": f"{usage.hours_used} hours logged. Total usage: {new_usage_hours}"}

# Log Maintenance Activity
@router.post("/log_maintenance")
def log_maintenance(log: MaintenanceLogCreate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["manager", "equipment_manager"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    now = datetime.utcnow()

    cursor.execute("""
        INSERT INTO maintenance_logs (equipment_id, action, details, parts_replaced, cost, timestamp, performed_by)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (log.equipment_id, log.action, log.details, log.parts_replaced, log.cost, now, current_user["id"]))

    cursor.execute("""
        UPDATE equipment 
        SET last_maintenance=%s, last_updated=NOW(), next_maintenance=%s, last_updated_by=%s
        WHERE id=%s
    """, (now.date(), log.next_maintenance, current_user["id"], log.equipment_id))
    cursor.execute("""
            INSERT INTO system_logs 
            (action, details, performed_by)
            VALUES (%s, %s, %s)
            """,
            (
                "equipment_maintenance_logged",
                f"maintenance log equipment ID {log.equipment_id}",
                current_user["id"]
            )
        )
    db.commit()

    return {"message": "Maintenance log recorded"}

# Get All Equipment
@router.get("/")
def get_all_equipment():
    cursor.execute("""
        SELECT e.id, e.name, e.type, e.usage_hours, e.last_maintenance, e.next_maintenance, 
               e.status, u.name AS last_updated_by
        FROM equipment e
        LEFT JOIN users u ON e.last_updated_by = u.id
        ORDER BY e.name
    """)
    rows = cursor.fetchall()
    equipment = [dict(zip([col[0] for col in cursor.description], row)) for row in rows]
    return {"items": equipment}

@router.delete("/delete/{equipment_id}")
def delete_equipment(
    equipment_id: int,
    current_user: dict = Depends(get_current_user)
):
    # Authorization check - only managers and equipment managers can delete
    if current_user["role"] not in ["manager", "equipment_manager"]:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to delete equipment"
        )

    try:
        # First check if equipment exists
        cursor.execute("SELECT id FROM equipment WHERE id = %s", (equipment_id,))
        if not cursor.fetchone():
            raise HTTPException(
                status_code=404,
                detail="Equipment not found"
            )

        # Begin transaction
        cursor.execute("BEGIN")

        # Delete related maintenance logs first (to maintain referential integrity)
        cursor.execute(
            "DELETE FROM maintenance_logs WHERE equipment_id = %s",
            (equipment_id,)
        )

        # Delete the equipment
        cursor.execute(
            "DELETE FROM equipment WHERE id = %s",
            (equipment_id,)
        )
        cursor.execute("""
            INSERT INTO system_logs 
            (action, details, performed_by)
            VALUES (%s, %s, %s)
            """,
            (
                "equipment_deleted",
                f"Deleted equipment ID {equipment_id}",
                current_user["id"]
            )
        )

        db.commit()

        return {
            "message": "Equipment deleted successfully",
            "deleted_id": equipment_id
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting equipment: {str(e)}"
        )



# View Maintenance Logs of a Specific Equipment
@router.get("/{equipment_id}/maintenance_logs")
def get_equipment_maintenance_logs(equipment_id: int):
    cursor.execute("""
        SELECT e.id, e.name, e.type, e.usage_hours, 
               e.last_maintenance, e.next_maintenance, e.status,
               e.last_updated, COALESCE(u.name, 'System') as last_updated_by
        FROM equipment e
        LEFT JOIN users u ON e.last_updated_by = u.id
        WHERE e.id = %s
    """, (equipment_id,))
    equipment = cursor.fetchone()

    if not equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")

    equipment_columns = [col[0] for col in cursor.description]
    equipment_details = dict(zip(equipment_columns, equipment))

    cursor.execute("""
        SELECT m.action, m.details, m.parts_replaced, m.cost, m.timestamp, 
               COALESCE(u.name, 'Unknown') AS performed_by
        FROM maintenance_logs m
        LEFT JOIN users u ON m.performed_by = u.id
        WHERE m.equipment_id = %s
        ORDER BY m.timestamp DESC
    """, (equipment_id,))
    rows = cursor.fetchall()
    logs = [dict(zip([col[0] for col in cursor.description], row)) for row in rows]

    return {
        "equipment": equipment_details,
        "logs": logs
    }

def check_maintenance_due():
    print("Checking maintenance schedules...")

    now = datetime.utcnow().date()

    cursor.execute("""
        SELECT id, name, next_maintenance 
        FROM equipment 
        WHERE next_maintenance IS NOT NULL 
          AND next_maintenance <= %s
          AND status != 'out_of_service'
    """, (now,))
    equipment_list = cursor.fetchall()

    if not equipment_list:
        print("No maintenance due today.")
        return

    for equipment in equipment_list:
        equipment_id, name, next_maintenance = equipment

        cursor.execute("""
            SELECT id, email FROM users WHERE role IN ('manager', 'equipment_manager')
        """)
        users = cursor.fetchall()

        message = f"Maintenance is due for equipment: {name} (Scheduled for {next_maintenance})"

        now_time = datetime.utcnow()

        for user in users:
            user_id, email = user
            cursor.execute("""
                INSERT INTO notifications (user_id, sender, message, status, created_at)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, "System", message, "unread", now_time))
        
        # Optional: Also mark equipment as `maintenance_due`
        cursor.execute("""
            UPDATE equipment SET status = 'maintenance_due', last_updated=NOW()
            WHERE id = %s
        """, (equipment_id,))

        db.commit()

    print(f"Maintenance alerts sent for {len(equipment_list)} equipment.")

    
@router.get("/equipment/equipmentmanager")
def get_equipment_forWorkers():
    try:
        cursor.execute("""
            SELECT 
                i.id,
                i.name,
                i.type,
                i.usage_hours,
                i.status,
                DATE_FORMAT(i.last_maintenance, '%Y-%m-%d %H:%i:%s') as last_maintenance,
                CONCAT(u.name) as updated_by_name,
                DATE_FORMAT(i.last_updated, '%Y-%m-%d %H:%i:%s') as last_updated
            FROM equipment i
            LEFT JOIN users u ON i.last_updated_by = u.id
            ORDER BY i.last_updated DESC
        """)
        rows = cursor.fetchall()
        
        items = []
        for row in rows:
            items.append({
                "id": row[0],
                "name": row[1],
                "type": row[2],
                "usage_hours": row[3],
                "status": row[4],
                "last_maintenance": row[5],
                "updated_by": row[6],
                "last_updated": row[7]
            })
        
        return {"items": items}
        
    except Exception as e:
        return {"error": str(e)}