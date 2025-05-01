import random
import string
from passlib.context import CryptContext
from fastapi import Form
from email_utils import send_email
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from fastapi import Depends
from fastapi.responses import JSONResponse
from database import cursor, db
from auth import get_current_user
from auth import verify_password
from auth import create_access_token


router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Function to generate a random password
def generate_password():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=8))

# User Model
class NewUser(BaseModel):
    name: str
    email: str
    role: str 

class LoginRequest(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    login_count: int

class TokenData(BaseModel):
    email: str | None = None

# Adds a New Worker
@router.post("/add_user")
def add_user(user: NewUser):


    # Generate a random password
    temp_password = generate_password()
    hashed_password = pwd_context.hash(temp_password)

    try:
        cursor.execute("INSERT INTO users (name, email, role, password) VALUES (%s, %s, %s, %s)",
                       (user.name, user.email, user.role, hashed_password))
        db.commit()

        subject = "Your Farm Management System Login Details"
        body = f"""
        Hello {user.name},

        Your account has been created successfully.

        Login details:
        - Email: {user.email}
        - Temporary Password: {temp_password}

        Please log in and change your password immediately.

        Regards,
        Farm Management Team
        """
        send_email(user.email, subject, body)

        return {"message": "User added successfully, credentials sent via email"}
    
    except Exception as e:
        return {"error": str(e)}

#get the current user
@router.get("/user/me")
def read_current_user(current_user: dict = Depends(get_current_user)):
    print(f"Current user: {current_user}")
    return {
        "email": current_user["email"],
        "role": current_user["role"],
        "name": current_user["name"]
    }

#get all users
@router.get("/users")
def get_users():
    cursor.execute("SELECT id, name, email, role, created_at FROM users")
    users= cursor.fetchall()

    return {"users": [{"id": user[0], "name": user[1], "email": user[2], "role": user[3], "enrolledon": user[4]} for user in users]}


# Manager deletes a worker
@router.delete("/delete")
def delete_user(data: dict, current_user: dict = Depends(get_current_user)):
    email = data.get("email")
    if current_user["role"] != "manager":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    cursor.execute("DELETE FROM users WHERE email = %s", (email,))
    db.commit()
    
    return {"message": f"User {email} deleted successfully."}


# Pydantic model for password change
class ChangePassword(BaseModel):
    old_password: str
    new_password: str

# Change Password API
@router.put("/change_password")
def change_password(password_data: ChangePassword, current_user: dict = Depends(get_current_user)):
    # Get the user's stored password
    cursor.execute("SELECT password FROM users WHERE email = %s", (current_user["email"],))
    result = cursor.fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="User not found")

    stored_password = result[0]

    # Verify old password
    if not pwd_context.verify(password_data.old_password, stored_password):
        raise HTTPException(status_code=401, detail="Incorrect old password")

    # Hash the new password
    hashed_new_password = pwd_context.hash(password_data.new_password)

    # Update password in database
    cursor.execute("UPDATE users SET password = %s, login_count = GREATEST(login_count, 1) WHERE email = %s", (hashed_new_password, current_user["email"]))
    db.commit()

    return {"message": "Password updated successfully"}

# Login API
@router.post("/login", response_model=Token)
async def login(request: LoginRequest):
    """User login endpoint: Returns JWT token if credentials are valid."""
    
    cursor.execute("SELECT email, password, role, login_count FROM users WHERE email=%s", (request.email,))
    user = cursor.fetchone()
    
    if not user or not verify_password(request.password, user[1]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    updated_count = user[3] + 1
    cursor.execute("UPDATE users SET login_count = %s WHERE email = %s", (updated_count, request.email))
    db.commit()

    # Generate token
    access_token = create_access_token(data={"sub": user[0]})

    return {"access_token": access_token, "token_type": "bearer","role": user[2], "login_count": updated_count}


@router.get("/farmers/summary")
def get_farmer_summary(current_user: dict = Depends(get_current_user)):
    # Count open tasks
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE assigned_to = %s AND status = 'pending'", (current_user["id"],))
    open_tasks = cursor.fetchone()[0]

    # Count overdue tasks
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE assigned_to = %s AND due_date < CURRENT_DATE AND status != 'Completed'", (current_user["id"],))
    overdue_tasks = cursor.fetchone()[0]

    # Count active crops (e.g., planted but not harvested)
    cursor.execute("SELECT COUNT(*) FROM crops WHERE added_by = %s AND growth_stage = 'Growing'", (current_user["id"],))
    active_crops = cursor.fetchone()[0]

    return {
        "open_tasks": open_tasks,
        "overdue_tasks": overdue_tasks,
        "active_crops": active_crops
    }

@router.get("/shepherd/summary")
def get_sherpherd_summary(current_user: dict = Depends(get_current_user)):
    # Count open tasks
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE assigned_to = %s AND status = 'pending'", (current_user["id"],))
    open_tasks = cursor.fetchone()[0]

    # Count overdue tasks
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE assigned_to = %s AND due_date < CURRENT_DATE AND status != 'Completed'", (current_user["id"],))
    overdue_tasks = cursor.fetchone()[0]

    # Count breeding animals 
    cursor.execute("SELECT COUNT(*) FROM livestock WHERE status = 'Breeding'",)
    Breeding_livestock = cursor.fetchone()[0]

    return {
        "open_tasks": open_tasks,
        "overdue_tasks": overdue_tasks,
        "breeding_livestock": Breeding_livestock
    }

@router.get("/inventory_manager/summary")
def get_inventory_manager_summary(current_user: dict = Depends(get_current_user)):
    # Count open tasks
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE assigned_to = %s AND status = 'pending'", (current_user["id"],))
    open_tasks = cursor.fetchone()[0]

    # Count overdue tasks
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE assigned_to = %s AND due_date < CURRENT_DATE AND status != 'Completed'", (current_user["id"],))
    overdue_tasks = cursor.fetchone()[0]

    # Count low stock (e.g., planted but not harvested)
    cursor.execute("SELECT COUNT(*) FROM inventory WHERE status = 'near_expiry'",)
    near_expiry = cursor.fetchone()[0]

    return {
        "open_tasks": open_tasks,
        "overdue_tasks": overdue_tasks,
        "near_expiry": near_expiry
    }

@router.get("/equipment_manager/summary")
def get_equipment_manager_summary(current_user: dict = Depends(get_current_user)):
    # Count open tasks
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE assigned_to = %s AND status = 'pending'", (current_user["id"],))
    open_tasks = cursor.fetchone()[0]

    # Count overdue tasks
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE assigned_to = %s AND due_date < CURRENT_DATE AND status != 'Completed'", (current_user["id"],))
    overdue_tasks = cursor.fetchone()[0]

    # Count low stock (e.g., planted but not harvested)
    cursor.execute("SELECT COUNT(*) FROM equipment WHERE status = 'maintenance'",)
    due_maintenance = cursor.fetchone()[0]

    return {
        "open_tasks": open_tasks,
        "overdue_tasks": overdue_tasks,
        "due_maintenance": due_maintenance
    }