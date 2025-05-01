from fastapi import APIRouter, Depends, HTTPException
from database import cursor, db
from auth import get_current_user
from pydantic import BaseModel
from typing import Optional
from datetime import date

router = APIRouter()

# Crop Model
class CropItem(BaseModel):
    id: int
    name: str
    type: str
    variety: Optional[str] = None
    planting_date: date
    growth_stage: str
    status: str
    harvest_date: Optional[date] = None

class CropCreate(BaseModel):
    name: str
    type: str
    variety: Optional[str] = None
    planting_date: date
    growth_stage: str
    status: str
    harvest_date: Optional[date] = None



class CropUpdate(BaseModel):
    name: str
    type: str
    variety: Optional[str] = None
    planting_date: date
    growth_stage: str
    status: str
    harvest_date: Optional[date] = None

@router.post("/add")
def add_crop(item: CropCreate, current_user: dict = Depends(get_current_user)):
    print(item)  
    if current_user['role'] not in ["manager", "farmer"]:
        raise HTTPException(status_code=403, detail="Unauthorized")

    cursor.execute("""
        INSERT INTO crops (name, type, variety, planting_date, growth_stage, status, harvest_date, last_updated, added_by)
        VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), %s)
    """, (item.name, item.type, item.variety, item.planting_date, item.growth_stage, item.status, item.harvest_date, current_user['id']))
    cursor.execute("""
            INSERT INTO system_logs 
            (action, details, performed_by)
            VALUES (%s, %s, %s)
            """,
            (
                "crop_added",
                f"added crop name {item.name}",
                current_user["id"]
            )
        )
    db.commit()

    return {"message": "Crop added successfully"}

@router.put("/update/{crop_id}")
def update_crop(
    crop_id: int,
    crop_data: CropUpdate,  # Changed from 'item' to 'crop_data'
    current_user: dict = Depends(get_current_user)
):
    if current_user['role'] not in ["manager", "farmer"]:
        raise HTTPException(status_code=403, detail="Unauthorized")

    try:
        cursor.execute("""
            UPDATE crops 
            SET name=%s, type=%s, variety=%s, planting_date=%s,
                growth_stage=%s, status=%s, harvest_date=%s, last_updated=NOW()
            WHERE id=%s
        """, (
            crop_data.name,
            crop_data.type,
            crop_data.variety,
            crop_data.planting_date,
            crop_data.growth_stage,
            crop_data.status,
            crop_data.harvest_date,
            crop_id
        ))
        db.commit()

        # Log the update
        action = f"Updated crop: {crop_data.name}, stage: {crop_data.growth_stage}"
        cursor.execute(
            "INSERT INTO crop_logs (crop_id, action, performed_by) VALUES (%s, %s, %s)",
            (crop_id, action, current_user['id'])
        )
        cursor.execute("""
            INSERT INTO system_logs 
            (action, details, performed_by)
            VALUES (%s, %s, %s)
            """,
            (
                "crop_updated",
                f"updated crop ID {crop_id}",
                current_user["id"]
            )
        )
        db.commit()

        return {"message": "Crop updated successfully"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/")
def get_crops():
    cursor.execute("SELECT * FROM crops")
    rows = cursor.fetchall()
    return {"items": [dict(zip([col[0] for col in cursor.description], row)) for row in rows]}

@router.delete("/delete/{crop_id}")
def delete_crop(crop_id: int, current_user: dict = Depends(get_current_user)):
    if current_user['role'] not in ["manager", "farmer"]:
        raise HTTPException(status_code=403, detail="Unauthorized")

    cursor.execute("DELETE FROM crop_logs WHERE crop_id = %s", (crop_id,))

    cursor.execute("DELETE FROM crops WHERE id=%s", (crop_id,))
    cursor.execute("""
            INSERT INTO system_logs 
            (action, details, performed_by)
            VALUES (%s, %s, %s)
            """,
            (
                "crop_deleted",
                f"Deleted crop ID {crop_id}",
                current_user["id"]
            )
        )
    db.commit()
    return {"message": "Crop deleted"}

@router.get("/{crop_id}/details")
def get_crop_details(crop_id: int):
    # Fetch crop details
    cursor.execute("""
        SELECT c.id, c.name, c.type, c.variety, c.planting_date, c.growth_stage, c.status, 
               c.harvest_date, COALESCE(u.name, 'System') as added_by
        FROM crops c
        LEFT JOIN users u ON c.added_by = u.id
        WHERE c.id = %s
    """, (crop_id,))
    item = cursor.fetchone()

    if not item:
        raise HTTPException(status_code=404, detail="Crop not found")

    # Convert the single row to a list of one dictionary
    item_columns = [col[0] for col in cursor.description]
    crop_details = dict(zip(item_columns, item))

    # Fetch crop logs
    cursor.execute("""
        SELECT cl.action, cl.timestamp, COALESCE(u.name, 'Unknown') as performed_by
        FROM crop_logs cl
        LEFT JOIN users u ON cl.performed_by = u.id
        WHERE cl.crop_id = %s
        ORDER BY cl.timestamp DESC
    """, (crop_id,))
    logs = cursor.fetchall()
    logs_list = [dict(zip([col[0] for col in cursor.description], row)) for row in logs]

    return {
        "item": crop_details, 
        "logs": logs_list  
    }

