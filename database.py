import mysql.connector
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection
db = mysql.connector.connect(
    host="localhost",
    user="root", 
    password="", 
    database="farm_management"
)

cursor = db.cursor()
