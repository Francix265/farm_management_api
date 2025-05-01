from fastapi import APIRouter, Depends, HTTPException
from database import cursor, db
from auth import get_current_user
from datetime import datetime

router = APIRouter()

@router.get("/notifications")
def get_notifications(current_user: dict = Depends(get_current_user)):
    cursor.execute("""
        SELECT id, message, status, created_at, sender FROM notifications WHERE user_id = %s ORDER BY created_at DESC """, (current_user["id"],))
    result = cursor.fetchall()

    return {"notifications": [{"id": n[0], "message": n[1], "status": n[2], "created_at": n[3], "sender": n[4]}for n in result]}

@router.put("/notifications/{notification_id}/read")
def mark_notification_as_read(notification_id: int, current_user: dict = Depends(get_current_user)):
    cursor.execute("SELECT message, user_id FROM notifications WHERE id = %s", (notification_id,))
    notification = cursor.fetchone()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    message_content, user_id = notification

    if user_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to mark this notification as read")
    
    cursor.execute(
        "UPDATE notifications SET status = 'read' WHERE id = %s AND user_id = %s",
        (notification_id, current_user["id"])
    )
    db.commit()
    
    if current_user["id"] != 1:
        now = datetime.utcnow()
        
        notification_type = "task"
        if "overdue" in message_content.lower():
            notification_type = "overdue task"
        elif "assigned" in message_content.lower():
            notification_type = "new task"
        
        message = f"{current_user['name']} has seen the {notification_type} notification"
        
        cursor.execute(
            "INSERT INTO notifications (user_id, sender, message, status, created_at) VALUES (%s, %s, %s, %s, %s)",
            (1, current_user["email"], message, "unread", now)
        )
        db.commit()
    
    return {"message": "Notification marked as read"}

@router.get("/unread_notification")
def get_unread_notification(current_user: dict = Depends(get_current_user)):
    cursor.execute("SELECT COUNT(*) FROM notifications WHERE user_id = %s AND status = 'unread'", (current_user["id"],))
    unread_messages = cursor.fetchone()[0]

    return {
        "unread_count":unread_messages
    }


def mark_overdue_tasks():
    now = datetime.utcnow()

    print("[Scheduler] Running mark_overdue_tasks...")
    cursor.execute("""
        SELECT t.id AS task_id, t.title AS task_title, t.assigned_to AS worker_id, u.name AS worker_name
        FROM tasks t
        JOIN users u ON t.assigned_to = u.id
        WHERE t.status != 'completed' AND t.status != 'overdue' AND t.due_date < %s
    """, (now,))
    
    overdue_tasks = cursor.fetchall()

    for task_id, task_title, worker_id, worker_name in overdue_tasks:
        cursor.execute("UPDATE tasks SET status = 'overdue' WHERE id = %s", (task_id,))

        cursor.execute("""
            INSERT INTO notifications (user_id, sender, message, status, created_at)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            worker_id,
            "System",
            f"Hi {worker_name}, your task '{task_title}' is now overdue.",
            'unread',
            now
        ))
        print("[Scheduler] Finished mark_overdue_tasks!")
        cursor.execute("SELECT id FROM users WHERE role = 'manager' LIMIT 1")
        manager = cursor.fetchone()

        if manager:
            manager_id = manager[0]
            cursor.execute("""
                INSERT INTO notifications (user_id, sender, message, status, created_at)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                manager_id,
                "System",
                f"Worker {worker_name} has an overdue task: '{task_title}'.",
                'unread',
                now
            ))
        print("[Scheduler] Sending the messages!")
    db.commit()
