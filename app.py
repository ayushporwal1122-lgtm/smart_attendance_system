from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
import pandas as pd
from flask import send_file
import os
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, session
from datetime import date
import mysql.connector

app = Flask(__name__)
app.secret_key = "smart_attendance_secret_key"
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Ayush@888",
    database="smart_attendance_db"
)

cursor = db.cursor()

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        if username == "admin" and password == "admin123":

            session["admin"] = username
            return redirect("/dashboard")

        else:
            return "Invalid Username or Password"

    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if "admin" not in session:
     return redirect("/login")
    # Total Students
    cursor.execute("SELECT COUNT(*) FROM students")
    total_students = cursor.fetchone()[0]

    # Present Today
    cursor.execute("""
        SELECT COUNT(*)
        FROM attendance
        WHERE attendance_date = CURDATE()
        AND status = 'Present'
    """)
    present_today = cursor.fetchone()[0]

    # Absent Today
    cursor.execute("""
        SELECT COUNT(*)
        FROM attendance
        WHERE attendance_date = CURDATE()
        AND status = 'Absent'
    """)
    absent_today = cursor.fetchone()[0]

    # Today's Date
    current_date = date.today()

    return render_template(
        "dashboard.html",
        total_students=total_students,
        present_today=present_today,
        absent_today=absent_today,
        current_date=current_date
    )
@app.route("/add_student", methods=["GET", "POST"])
def add_student():
    if "admin" not in session:
      return redirect("/login")
    if request.method == "POST":
        photo = request.files["photo"]

        filename = ""

        if photo.filename != "":
            filename = secure_filename(photo.filename)

            upload_folder = os.path.join(app.root_path, "static", "uploads")
            os.makedirs(upload_folder, exist_ok=True)
            photo.save(os.path.join(upload_folder, filename))
        student_name = request.form["student_name"]
        roll_number = request.form["roll_number"]
        class_name = request.form["class_name"]
        section = request.form["section"]
        father_name = request.form["father_name"]
        mobile = request.form["mobile"]
        email = request.form["email"]
        address = request.form["address"]

        sql = """
        INSERT INTO students
        (student_name, roll_number, class_name, section, father_name, mobile, email, address, photo)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """

        values = (student_name, roll_number, class_name, section, father_name, mobile, email, address, filename)

        cursor.execute(sql, values)
        db.commit()

        return redirect("/add_student")

    return render_template("add_student.html")

@app.route("/view_students")
def view_students():
    if "admin" not in session:
      return redirect("/login")
    search = request.args.get("search")

    if search:

        sql = """
        SELECT * FROM students
        WHERE student_name LIKE %s
        OR roll_number LIKE %s
        """

        value = ("%" + search + "%", "%" + search + "%")

        cursor.execute(sql, value)

    else:

        cursor.execute("SELECT * FROM students")

    students = cursor.fetchall()

    return render_template("view_students.html", students=students)

@app.route("/attendance")
def attendance():
    if "admin" not in session:
      return redirect("/login")
    cursor.execute("SELECT * FROM students")

    students = cursor.fetchall()

    return render_template("attendance.html", students=students)

@app.route("/edit_student/<int:id>", methods=["GET", "POST"])
def edit_student(id):
    if "admin" not in session:
       return redirect("/login")
    if request.method == "POST":

        student_name = request.form["student_name"]
        roll_number = request.form["roll_number"]
        class_name = request.form["class_name"]
        section = request.form["section"]
        father_name = request.form["father_name"]
        mobile = request.form["mobile"]
        email = request.form["email"]
        address = request.form["address"]

        sql = """
        UPDATE students
        SET
            student_name=%s,
            roll_number=%s,
            class_name=%s,
            section=%s,
            father_name=%s,
            mobile=%s,
            email=%s,
            address=%s
        WHERE id=%s
        """

        values = (
            student_name,
            roll_number,
            class_name,
            section,
            father_name,
            mobile,
            email,
            address,
            id
        )

        cursor.execute(sql, values)
        db.commit()

        return redirect("/view_students")

    cursor.execute("SELECT * FROM students WHERE id=%s", (id,))
    student = cursor.fetchone()

    return render_template("edit_student.html", student=student)


@app.route("/save_attendance", methods=["POST"])
def save_attendance():
    if "admin" not in session:
      return redirect("/login")
    student_ids = request.form.getlist("student_id")

    for student_id in student_ids:

        status = request.form.get(f"attendance_{student_id}")

        sql = """
        INSERT INTO attendance (student_id, attendance_date, status)
        VALUES (%s, CURDATE(), %s)
        """

        cursor.execute(sql, (student_id, status))

    db.commit()

    return redirect("/attendance")

@app.route("/reports", methods=["GET", "POST"])
def reports():

    if "admin" not in session:
        return redirect("/login") 
    
    if request.method == "POST":

        attendance_date = request.form["attendance_date"]

        sql = """
        SELECT
            students.student_name,
            students.roll_number,
            attendance.attendance_date,
            attendance.status
        FROM attendance
        INNER JOIN students
        ON attendance.student_id = students.id
        WHERE attendance.attendance_date = %s
        ORDER BY attendance.attendance_date DESC
        """

        cursor.execute(sql, (attendance_date,))
        records = cursor.fetchall()

    else:

        sql = """
        SELECT
            students.student_name,
            students.roll_number,
            attendance.attendance_date,
            attendance.status
        FROM attendance
        INNER JOIN students
        ON attendance.student_id = students.id
        ORDER BY attendance.attendance_date DESC
        """

        cursor.execute(sql)
        records = cursor.fetchall()

    return render_template("reports.html", records=records)

@app.route("/export_excel")
def export_excel():
    if "admin" not in session:
       return redirect("/login")
    sql = """
    SELECT
        students.student_name,
        students.roll_number,
        attendance.attendance_date,
        attendance.status
    FROM attendance
    INNER JOIN students
    ON attendance.student_id = students.id
    ORDER BY attendance.attendance_date DESC
    """

    cursor.execute(sql)
    records = cursor.fetchall()

    df = pd.DataFrame(
        records,
        columns=[
            "Student Name",
            "Roll Number",
            "Date",
            "Status"
        ]
    )

    filename = "Attendance_Report.xlsx"

    df.to_excel(filename, index=False)

    return send_file(
        filename,
        as_attachment=True
    )

@app.route("/export_pdf")
def export_pdf():

    if "admin" not in session:
        return redirect("/login")

    sql = """
    SELECT
        students.student_name,
        students.roll_number,
        attendance.attendance_date,
        attendance.status
    FROM attendance
    INNER JOIN students
    ON attendance.student_id = students.id
    ORDER BY attendance.attendance_date DESC
    """

    cursor.execute(sql)
    records = cursor.fetchall()

    data = [["Student Name", "Roll No", "Date", "Status"]]

    for row in records:
        data.append(list(row))

    filename = "Attendance_Report.pdf"

    pdf = SimpleDocTemplate(filename)

    table = Table(data)

    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
    ]))

    pdf.build([table])

    return send_file(filename, as_attachment=True)

@app.route("/delete_student/<int:id>")
def delete_student(id):
    if "admin" not in session:
        return redirect("/login")
    sql = "DELETE FROM students WHERE id = %s"

    cursor.execute(sql, (id,))
    db.commit()

    return redirect("/view_students")

@app.route("/logout")
def logout():

    session.pop("admin", None)

    return redirect("/login")

if __name__ == "__main__":
    app.run(debug=True)