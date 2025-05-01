from datetime import datetime
from database import cursor, db
from email_utils import send_email
from fastapi import APIRouter, Depends, HTTPException
from auth import get_current_user
from pydantic import BaseModel

router = APIRouter()

class TaskUpdateData(BaseModel):
    task_id: int
    status: str

@router.post("/assign_task")
def assign_task(data: dict, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "manager":
        raise HTTPException(status_code=403, detail="Unauthorized")

    cursor.execute(
        "INSERT INTO tasks (title, description, assigned_to, status, due_date) VALUES (%s, %s, %s, %s, %s)",
        (data["title"], data["description"], data["assigned_to"], "pending", data["due_date"])
    )
    db.commit()

    now = datetime.utcnow()
    message = f"You have been assigned a new task: {data['title']}"
    cursor.execute(
        "INSERT INTO notifications (user_id, sender, message, status, created_at) VALUES (%s, %s, %s, %s, %s)",
        (data["assigned_to"], current_user["email"], message, "unread", now)
    )
    db.commit()

    return {"message": "Task assigned successfully, notification sent"}


# Worker Updates Task Status
@router.put("/update_task_status")
def update_task_status(data: TaskUpdateData, current_user: dict = Depends(get_current_user)):
    cursor.execute("SELECT title FROM tasks WHERE id = %s", (data.task_id,))
    task = cursor.fetchone()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task_title = task[0]  # ✅ Corrected access

    cursor.execute(
        "UPDATE tasks SET status = %s WHERE id = %s",
        (data.status, data.task_id)
    )
    db.commit()

    if data.status.lower() == "completed":
        now = datetime.utcnow()
        message = f"{current_user['name']} has completed the ({task_title}) task"

        cursor.execute(
            "INSERT INTO notifications (user_id, sender, message, status, created_at) VALUES (%s, %s, %s, %s, %s)",
            (1, current_user["email"], message, "unread", now)
        )
        db.commit()
    
    return {"message": "Task status updated successfully"}


# Get Tasks Assigned to Worker
@router.get("/mytasks")
def get_tasks(current_user: dict = Depends(get_current_user)):
    cursor.execute("SELECT id, title,description, status, set_on, due_date FROM tasks WHERE assigned_to=%s", (current_user["id"],))
    tasks = cursor.fetchall()

    return {"tasks": [{"id": t[0], "title": t[1],"description":t[2], "status": t[3], "set_on":t[4], "due_date": t[5]} for t in tasks]}

# Get all Tasks
@router.get("/all_tasks")
def get_all_tasks():
    current_date = datetime.now().date()

    cursor.execute("""
        SELECT tasks.id, tasks.title, tasks.description, tasks.status, tasks.set_on, tasks.due_date, users.name
        FROM tasks
        JOIN users ON tasks.assigned_to = users.id
    """)
    tasks = cursor.fetchall()

    for task in tasks:
        task_due_date = task[5]  # Assuming task[5] is already a datetime.date object
        if isinstance(task_due_date, str):  # In case it's still a string, convert it
            task_due_date = datetime.strptime(task_due_date, "%Y-%m-%d").date()

        if task_due_date < current_date and task[3] != "overdue":
            cursor.execute("""
                UPDATE tasks
                SET status = %s
                WHERE id = %s
            """,("overdue", task[0])) 

            db.commit() 

    cursor.execute("""
        SELECT tasks.id, tasks.title, tasks.description, tasks.status, tasks.set_on, tasks.due_date, users.name
        FROM tasks
        JOIN users ON tasks.assigned_to = users.id
    """)
    tasks = cursor.fetchall()
    print(tasks)

    return {"tasks": [{"id": task[0], "title": task[1], "description": task[2], "status": task[3], 
                       "set_on": task[4], "due_date": task[5], "assigned_to": task[6]} for task in tasks]}
# Manager deletes a task
@router.delete("/delete")
def delete_task(data: dict, current_user: dict = Depends(get_current_user)):
    task_id = data.get("task_id")
    if current_user["role"] != "manager":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    cursor.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
    db.commit()
    
    return {"message": "task deleted successfully."}

