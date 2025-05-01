from fastapi import APIRouter
from fastapi.responses import FileResponse
from report_generator import (
    generate_report,
    generate_inventory_pdf,
    generate_crops_pdf,
    generate_livestock_pdf,
    generate_equipment_pdf,
)

router = APIRouter()

@router.get("/report/full")
def full_report():
    path = generate_report()
    return FileResponse(path, filename="farm_report.pdf", media_type="application/pdf")

@router.get("/report/inventory")
def inventory_report():
    path = generate_inventory_pdf()
    return FileResponse(path, filename="inventory_report.pdf", media_type="application/pdf")

@router.get("/report/crops")
def crops_report():
    path = generate_crops_pdf()
    return FileResponse(path, filename="crop_report.pdf", media_type="application/pdf")

@router.get("/report/livestock")
def livestock_report():
    path = generate_livestock_pdf()
    return FileResponse(path, filename="livestock_report.pdf", media_type="application/pdf")

@router.get("/report/equipment")
def equipment_report():
    path = generate_equipment_pdf()
    return FileResponse(path, filename="equipment_report.pdf", media_type="application/pdf")
