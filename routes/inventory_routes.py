from fastapi import APIRouter, Depends, HTTPException
from database import cursor, db
from auth import get_current_user
from pydantic import BaseModel
from datetime import date
from datetime import datetime
from typing import Optional


router = APIRouter()

# Inventory Model
class InventoryItem(BaseModel):
    name: str
    category: str
    quantity: int
    expiry_date: Optional[date] = None

class UpdateInventory(BaseModel):
    name: str
    category: str
    quantity: int
    expiry_date: str | None = None

# Add Inventory Item
@router.post("/add")
def add_inventory(item: InventoryItem ,current_user: dict = Depends(get_current_user)):
    name = item.name
    category = item.category
    quantity = item.quantity
    expiry = item.expiry_date

    now = datetime.utcnow()
    status = "valid"

    if expiry:
        days_left = (expiry - now.date()).days
        if days_left <= 7:
            status = "near_expiry"
    if quantity < 5:
        status = "low"

    cursor.execute("""
        INSERT INTO inventory (name, category, quantity, expiry_date, status, last_updated)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (name, category, quantity, expiry, status, now))
    cursor.execute("""
            INSERT INTO system_logs 
            (action, details, performed_by)
            VALUES (%s, %s, %s)
            """,
            (
                "inventory_item_Added",
                f"Added inventory item: {name}",
                current_user["id"]
            )
        )
    
    db.commit()
    return {"message": "Inventory item added successfully"}


@router.put("/update/{item_id}")
def update_inventory_item(item_id: int, item: UpdateInventory, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["manager", "stock_manager"]:
        raise HTTPException(status_code=403, detail="Unauthorized")

    # Update inventory
    cursor.execute("""
        UPDATE inventory 
        SET name=%s, category=%s, quantity=%s, expiry_date=%s, last_updated=NOW()
        WHERE id=%s
    """, (item.name, item.category, item.quantity, item.expiry_date, item_id))
    cursor.execute("""
            INSERT INTO system_logs 
            (action, details, performed_by)
            VALUES (%s, %s, %s)
            """,
            (
                "inventory_item_updated",
                f"Updated Inventory ID {item_id}",
                current_user["id"]
            )
        )
    db.commit()

    # Log update - get user ID
    cursor.execute("SELECT id FROM users WHERE email = %s", (current_user["email"],))
    user_id_row = cursor.fetchone()
    performed_by = user_id_row[0] if user_id_row else None

    action_msg = f"Updated item: {item.name}, quantity: {item.quantity}"

    cursor.execute("""
        INSERT INTO inventory_logs (inventory_id, action, quantity_change, performed_by)
        VALUES (%s, %s, %s,%s)
    """, (item_id, action_msg, item.quantity,performed_by))
    db.commit()

    return {"message": "Inventory item updated successfully"}


# Get All Inventory Items
@router.get("/inventory")
def get_inventory():
    cursor.execute("SELECT * FROM inventory")
    rows = cursor.fetchall()
    return {"items": [dict(zip([col[0] for col in cursor.description], row)) for row in rows]}


# Get Low Stock & Expired Items
@router.get("/inventory_alerts")
def inventory_alerts():
    cursor.execute("SELECT id, name, quantity FROM inventory WHERE quantity < 5")
    low_stock = cursor.fetchall()

    cursor.execute("SELECT id, name, expiry_date FROM inventory WHERE expiry_date < CURDATE()")
    expired_items = cursor.fetchall()

    return {
        "low_stock": [{"id": item[0], "name": item[1], "quantity": item[2]} for item in low_stock],
        "expired_items": [{"id": item[0], "name": item[1], "expiry_date": item[2]} for item in expired_items]
    }

#delete inventory item
@router.delete("/delete/{item_id}")
def delete_inventory(item_id: int, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["manager", "stock_manager"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    cursor.execute("DELETE FROM inventory WHERE id=%s", (item_id,))
    cursor.execute("""
            INSERT INTO system_logs 
            (action, details, performed_by)
            VALUES (%s, %s, %s)
            """,
            (
                "inventory_item_deleted",
                f"Deleted inventory ID {item_id}",
                current_user["id"]
            )
        )
    db.commit()
    return {"message": "Inventory item deleted"}

@router.get("/{item_id}/details")
def get_inventory_details(item_id: int):
    # Get item details
    cursor.execute("""
        SELECT i.id, i.name, i.category, i.quantity, i.expiry_date, i.last_updated, i.status, 
               COALESCE(u.name, 'System') as added_by
        FROM inventory i
        LEFT JOIN users u ON i.updated_by = u.id
        WHERE i.id = %s
    """, (item_id,))
    item = cursor.fetchone()

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    item_details = {
        "id": item[0],
        "name": item[1],
        "category": item[2],
        "quantity": item[3],
        "expiry_date": item[4],
        "last_updated": item[5],
        "status": item[6],
        "added_by": item[7]
    }

    # Fetch logs with user names
    cursor.execute("""
        SELECT il.action, il.timestamp, il.quantity_change, 
               COALESCE(u.name, 'System') as performed_by_name
        FROM inventory_logs il
        LEFT JOIN users u ON il.performed_by = u.id
        WHERE il.inventory_id = %s 
        ORDER BY il.timestamp DESC
    """, (item_id,))
    
    logs = [{
        "action": log[0],
        "timestamp": log[1],
        "quantity_change": log[2],
        "performed_by": log[3] 
    } for log in cursor.fetchall()]

    return {
        "item": item_details,
        "logs": logs
    }

@router.get("/inventory/stockmanager")
def get_inventory_forWorkers():
    try:
        cursor.execute("""
            SELECT 
                i.id,
                i.name,
                i.category,
                i.quantity,
                DATE_FORMAT(i.expiry_date, '%Y-%m-%d') as expiry_date,
                i.status,
                DATE_FORMAT(i.last_updated, '%Y-%m-%d %H:%i:%s') as last_updated,
                CONCAT(u.name) as updated_by_name
            FROM inventory i
            LEFT JOIN users u ON i.updated_by = u.id
            ORDER BY i.last_updated DESC
        """)
        rows = cursor.fetchall()
        
        items = []
        for row in rows:
            items.append({
                "id": row[0],
                "name": row[1],
                "category": row[2],
                "quantity": row[3],
                "expiry_date": row[4],
                "status": row[5],
                "last_updated": row[6],
                "updated_by": row[7]
            })
        
        return {"items": items}
        
    except Exception as e:
        return {"error": str(e)}