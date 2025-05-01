from fastapi import FastAPI
from apscheduler.schedulers.background import BackgroundScheduler

from routes.user_routes import router as user_router
from routes.task_routes import router as task_router
from routes.notification_routes import router as notification_router
from routes.inventory_routes import router as inventory_router
from routes.equipment_routes import router as equipment_router
from routes.livestock_routes import router as livestock_router
from routes.crop_routes import router as crop_router
from routes.report_routes import router as report_router
from routes.notification_routes import mark_overdue_tasks
from routes.equipment_routes import check_maintenance_due  

app = FastAPI(title="Farm Management System API", version="1.0")

scheduler = BackgroundScheduler()
scheduler.add_job(mark_overdue_tasks, 'interval', minutes=60)
scheduler.add_job(check_maintenance_due, 'interval', hours=12)
scheduler.start()

app.include_router(user_router, prefix="/users", tags=["Users"])
app.include_router(task_router, prefix="/tasks", tags=["Tasks"])
app.include_router(notification_router, prefix="/notifications", tags=["Notifications"])
app.include_router(inventory_router, prefix="/inventory", tags=["Inventory"])
app.include_router(equipment_router, prefix="/equipment", tags=["Equipment"])
app.include_router(livestock_router, prefix="/livestock", tags=["Livestock"])
app.include_router(crop_router, prefix="/crops", tags=["Crops"])
app.include_router(report_router, prefix="/reports", tags=["Reports"])

@app.get("/")
def home():
    return {"message": "Welcome to the Farm Management System API"}
