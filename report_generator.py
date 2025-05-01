from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from datetime import datetime
from database import cursor
import os

# Common styling for all reports
styles = getSampleStyleSheet()
title_style = styles['Title']
header_style = styles['Heading2']
normal_style = styles['Normal']

def create_report_directory():
    """Ensure reports directory exists"""
    os.makedirs("reports", exist_ok=True)

def generate_report():
    """Generate comprehensive farm report"""
    filename = f"reports/farm_report_{datetime.now().strftime('%Y-%m-%d')}.pdf"
    create_report_directory()
    
    doc = SimpleDocTemplate(filename, pagesize=letter)
    elements = []
    
    # Title
    elements.append(Paragraph("Farm Management System Report", title_style))
    elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}", normal_style))
    elements.append(Paragraph(" ", normal_style))  # Spacer
    
    # Crops Section
    elements.append(Paragraph("Crops", header_style))
    cursor.execute("SELECT name, type, variety, growth_stage, planting_date, harvest_date FROM crops")
    crop_data = [["Name", "Type", "Variety", "Growth Stage", "Planted", "Harvest"]] + list(cursor.fetchall())
    crop_table = Table(crop_data)
    crop_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey),
    ]))
    elements.append(crop_table)
    elements.append(Paragraph(" ", normal_style))  # Spacer
    
    # Inventory Section
    elements.append(Paragraph("Inventory", header_style))
    cursor.execute("SELECT name, category, quantity, expiry_date FROM inventory")
    inventory_data = [["Item", "Category", "Quantity", "Expiry Date"]] + list(cursor.fetchall())
    inventory_table = Table(inventory_data)
    inventory_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgreen),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey),
    ]))
    elements.append(inventory_table)
    elements.append(Paragraph(" ", normal_style))  # Spacer

    # Livestock section
    elements.append(Paragraph("Livestock", header_style))
    cursor.execute("""
        SELECT tag_id, type, breed, DATE_FORMAT(birth_date, '%Y-%m-%d'), 
               health_status, 
               DATE_FORMAT(last_updated, '%Y-%m-%d')
        FROM livestock
    """)
    livestock_data = [["Tag ID", "Type", "Breed", "Health Status", "Last Health Check"]] + list(cursor.fetchall())
    livestock_table = Table(livestock_data)
    livestock_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey),
    ]))
    elements.append(livestock_table)
    elements.append(Paragraph(" ", normal_style)) 
    
    # Equipment Section
    elements.append(Paragraph("Equipment", header_style))
    cursor.execute("""
        SELECT name, type, usage_hours, 
               DATE_FORMAT(last_maintenance, '%Y-%m-%d'), 
               DATE_FORMAT(next_maintenance, '%Y-%m-%d'), 
               status 
        FROM equipment
    """)
    equipment_data = [["Name", "Type", "Usage Hours", "Last Maintenance", "Next Maintenance", "Status"]] + list(cursor.fetchall())
    equipment_table = Table(equipment_data)
    equipment_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey),
    ]))
    elements.append(equipment_table)
    
    doc.build(elements)
    return filename

def generate_inventory_pdf():
    """Generate detailed inventory report"""
    filename = "reports/inventory_report.pdf"
    create_report_directory()
    
    doc = SimpleDocTemplate(filename, pagesize=letter)
    elements = []
    
    elements.append(Paragraph("Inventory Report", title_style))
    elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}", normal_style))
    elements.append(Paragraph(" ", normal_style))
    
    cursor.execute("SELECT name, category, quantity, expiry_date, status FROM inventory")
    data = [["Name", "Category", "Quantity", "Expiry date", "Status"]] + list(cursor.fetchall())
    
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#4F81BD")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    
    elements.append(table)
    doc.build(elements)
    return filename

def generate_equipment_pdf():
    """Generate professional equipment report"""
    filename = "reports/equipment_report.pdf"
    create_report_directory()
    
    doc = SimpleDocTemplate(filename, pagesize=letter)
    elements = []
    
    elements.append(Paragraph("Equipment Maintenance Report", title_style))
    elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}", normal_style))
    elements.append(Paragraph(" ", normal_style))
    
    # Main equipment table
    cursor.execute("""
        SELECT e.name, e.type, e.usage_hours, 
               DATE_FORMAT(e.last_maintenance, '%Y-%m-%d'), 
               DATE_FORMAT(e.next_maintenance, '%Y-%m-%d'), 
               e.status,
               u.name as updated_by
        FROM equipment e
        LEFT JOIN users u ON e.last_updated_by = u.id
    """)
    equipment_data = [["Name", "Type", "Usage Hours", "Last Maint.", "Next Maint.", "Status", "Updated By"]] + list(cursor.fetchall())
    
    equipment_table = Table(equipment_data)
    equipment_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#9BBB59")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey),
    ]))
    elements.append(equipment_table)
    elements.append(Paragraph(" ", normal_style))
    
    # Maintenance history table
    elements.append(Paragraph("Recent Maintenance History", header_style))
    cursor.execute("""
        SELECT e.name, m.action, 
               DATE_FORMAT(m.timestamp, '%Y-%m-%d'), 
               m.parts_replaced, m.cost,
               u.name as performed_by
        FROM maintenance_logs m
        JOIN equipment e ON m.equipment_id = e.id
        LEFT JOIN users u ON m.performed_by = u.id
        ORDER BY m.timestamp DESC
        LIMIT 20
    """)
    maintenance_data = [["Equipment", "Action", "Date", "Parts", "Cost", "Technician"]] + list(cursor.fetchall())
    
    maintenance_table = Table(maintenance_data)
    maintenance_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#C0504D")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey),
    ]))
    elements.append(maintenance_table)
    
    doc.build(elements)
    return filename

def generate_livestock_pdf():
    """Generate professional livestock report"""
    filename = "reports/livestock_report.pdf"
    create_report_directory()
    
    doc = SimpleDocTemplate(filename, pagesize=letter)
    elements = []
    
    elements.append(Paragraph("Livestock Health Report", title_style))
    elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}", normal_style))
    elements.append(Paragraph(" ", normal_style))
    
    cursor.execute("""
        SELECT tag_id, type, breed, birth_date, 
               health_status, 
               DATE_FORMAT(last_updated, '%Y-%m-%d'),
        FROM livestock
    """)
    data = [["ID", "Type", "Breed", "Birth", "Health", "Last Check"]] + list(cursor.fetchall())
    
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#8064A2")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey),
        ('TEXTCOLOR', (4, 1), (4, -1), colors.red, lambda r, c, v: v == "Critical"),
        ('TEXTCOLOR', (4, 1), (4, -1), colors.orange, lambda r, c, v: v == "Poor"),
        ('TEXTCOLOR', (4, 1), (4, -1), colors.green, lambda r, c, v: v == "Good"),
    ]))
    
    elements.append(table)
    doc.build(elements)
    return filename

def generate_crops_pdf():
    """Generate professional crop report"""
    filename = "reports/crop_report.pdf"
    create_report_directory()
    
    doc = SimpleDocTemplate(filename, pagesize=letter)
    elements = []
    
    elements.append(Paragraph("Crop Production Report", title_style))
    elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}", normal_style))
    elements.append(Paragraph(" ", normal_style))
    
    cursor.execute("""
        SELECT name, type, variety, growth_stage, 
               DATE_FORMAT(planting_date, '%Y-%m-%d'), 
               DATE_FORMAT(harvest_date, '%Y-%m-%d'),
               status    
        FROM crops
    """)
    data = [["Name", "Type", "Variety", "Stage", "Planted", "Harvest", "Status"]] + list(cursor.fetchall())
    
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#F79646")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey),
        ('TEXTCOLOR', (7, 1), (7, -1), colors.red, lambda r, c, v: v == "Diseased"),
        ('TEXTCOLOR', (7, 1), (7, -1), colors.green, lambda r, c, v: v == "Healthy"),
    ]))
    
    elements.append(table)
    doc.build(elements)
    return filename