import mysql.connector

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Ayush@888",
    database="smart_attendence_db"
)

cursor = db.cursor()

print("Database Connected Successfully")