from fastapi import APIRouter, Depends, HTTPException
from database import cursor, db
from auth import get_current_user
from pydantic import BaseModel
from datetime import date
from typing import Optional

router = APIRouter()


class LivestockItem(BaseModel):
    id: int
    tag_id: str
    type: str
    breed: Optional[str] = None
    birth_date: date
    health_status: str  
    status: str
      

class VaccinationEntry(BaseModel):
    vaccine_name: str
    administered_date: date
    next_due_date: Optional[date] = None
    notes: Optional[str] = None


class LivestockAddItem(BaseModel):
    tag_id: str
    type: str
    breed: Optional[str] = None
    birth_date: date
    health_status: str  
    status: str

# Add Livestock Item
@router.post("/add")
def add_livestock(item: LivestockAddItem, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["manager", "shepherd"]:
        raise HTTPException(status_code=403, detail="Unauthorized")

    try:
        # Option 1: Use provided birth_date and current timestamp for last_updated
        cursor.execute("""
            INSERT INTO livestock (tag_id, type, breed, health_status, status, birth_date, last_updated)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
        """, (item.tag_id, item.type, item.breed, item.health_status, item.status, item.birth_date))
        cursor.execute("""
            INSERT INTO system_logs 
            (action, details, performed_by)
            VALUES (%s, %s, %s)
            """,
            (
                "livestock_added",
                f"Added livestock tag_ID: {item.tag_id}",
                current_user["id"]
            )
        )
        db.commit()
        return {"message": "Livestock item added successfully"}
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

# Update Livestock Item
@router.put("/update/{livestock_id}")
def update_livestock(livestock_id: int, item: LivestockItem, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["manager", "shepherd"]:
        raise HTTPException(status_code=403, detail="Unauthorized")

    cursor.execute("""
        UPDATE livestock 
        SET tag_id=%s, type=%s, breed=%s, health_status=%s, status=%s, birth_date=%s, last_updated=NOW()
        WHERE id=%s
    """, (item.tag_id, item.type, item.breed, item.health_status, item.status, item.birth_date, livestock_id))
    db.commit()

    return {"message": "Livestock item updated successfully"}

# Get All Livestock Items
@router.get("/")
def get_livestock():
    cursor.execute("SELECT * FROM livestock")
    rows = cursor.fetchall()
    return {"items": [dict(zip([col[0] for col in cursor.description], row)) for row in rows]}

# Get Livestock Alerts
@router.get("/alerts")
def livestock_alerts():
    cursor.execute("SELECT id, tag_id, type FROM livestock WHERE health_status IN ('Sick', 'In Treatment')")
    alerts = cursor.fetchall()
    return {"alerts": [{"id": item[0], "tag_id": item[1], "type": item[2]} for item in alerts]}

# Delete Livestock Item
@router.delete("/delete/{livestock_id}")
def delete_livestock(livestock_id: int, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["manager", "shepherd"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    cursor.execute("DELETE FROM livestock WHERE id=%s", (livestock_id,))
    cursor.execute("""
            INSERT INTO system_logs 
            (action, details, performed_by)
            VALUES (%s, %s, %s)
            """,
            (
                "livestock_deleted",
                f"Deleted livestock ID {livestock_id}",
                current_user["id"]
            )
        )
    db.commit()
    return {"message": "Livestock item deleted"}

# Get Livestock Details
@router.get("/{livestock_id}/details")
def get_livestock_details(livestock_id: int):
    cursor.execute("""
        SELECT l.id, l.tag_id, l.type, l.breed, l.health_status, l.status, l.last_updated,
               COALESCE(u.name, 'System') as added_by
        FROM livestock l
        LEFT JOIN users u ON l.added_by = u.id
        WHERE l.id = %s
    """, (livestock_id,))
    item = cursor.fetchone()

    if not item:
        raise HTTPException(status_code=404, detail="animal not found")

    item_columns = [col[0] for col in cursor.description]
    livestock_details = dict(zip(item_columns, item))

    cursor.execute("""
        SELECT lv.vaccine_name, lv.administered_date, lv.next_due_date, lv.notes, COALESCE(u.name, 'Unknown') as administered_by
        FROM livestock_vaccinations lv
        LEFT JOIN users u ON lv.administered_by = u.id
        WHERE lv.livestock_id = %s
        ORDER BY lv.administered_date DESC
    """, (livestock_id,))
    logs = cursor.fetchall()
    logs_list = [dict(zip([col[0] for col in cursor.description], row)) for row in logs]

    return {
        "item": livestock_details,
        "logs": logs_list 
    }

@router.post("/vaccinate/{livestock_id}")
def vaccinate_livestock(
    livestock_id: int,
    entry: VaccinationEntry,
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"] not in ["manager", "shepherd"]:
        raise HTTPException(status_code=403, detail="Unauthorized")

    cursor.execute("SELECT id FROM users WHERE email=%s", (current_user["email"],))
    user_id_row = cursor.fetchone()
    administered_by = user_id_row[0] if user_id_row else None

    cursor.execute("""
        INSERT INTO livestock_vaccinations 
        (livestock_id, vaccine_name, administered_date, next_due_date, administered_by, notes)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        livestock_id, entry.vaccine_name, entry.administered_date,
        entry.next_due_date, administered_by, entry.notes
    ))

    db.commit()
    return {"message": "Vaccination recorded successfully"}

@router.get("/{livestock_id}/vaccinations")
def get_vaccination_history(livestock_id: int, current_user: dict = Depends(get_current_user)):
    cursor.execute("""
        SELECT vaccine_name, administered_date, next_due_date, notes,
               COALESCE(u.name, 'System') AS administered_by
        FROM livestock_vaccinations v
        LEFT JOIN users u ON v.administered_by = u.id
        WHERE v.livestock_id = %s
        ORDER BY administered_date DESC
    """, (livestock_id,))
    
    rows = cursor.fetchall()
    return {
        "records": [
            {
                "vaccine_name": row[0],
                "administered_date": row[1],
                "next_due_date": row[2],
                "notes": row[3],
                "administered_by": row[4]
            } for row in rows
        ]
    }
