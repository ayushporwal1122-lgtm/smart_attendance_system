import time
import winsound
import face_recognition
import pickle
import cv2
import numpy as np
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

@app.route("/generate_encodings")
def generate_encodings():

    if "admin" not in session:
        return redirect("/login")

    cursor.execute("SELECT student_name, photo FROM students")
    students = cursor.fetchall()

    known_encodings = []
    known_names = []

    for student in students:

        name = student[0]
        photo = student[1]
        if not photo:
          print(name, "Photo not found in database")
          continue
        image_path = os.path.join("static", "uploads", photo)

        if not os.path.exists(image_path):
            print(photo, "Not Found")
            continue

        image = face_recognition.load_image_file(image_path)
        print("Loading:", image_path)
        encodings = face_recognition.face_encodings(image)
        print("Faces Found:", len(encodings))

        if len(encodings) > 0:
            known_encodings.append(encodings[0])
            known_names.append(name)
            print(name, "Encoding Generated")
        else:
            print("Face not found in", photo)

    data = {
        "encodings": known_encodings,
        "names": known_names
    }

    os.makedirs("encodings", exist_ok=True)

    with open("encodings/encodings.pkl", "wb") as f:
        pickle.dump(data, f)

    return "Encodings Generated Successfully!"

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

        # Check if attendance already exists today
        cursor.execute("""
            SELECT id
            FROM attendance
            WHERE student_id=%s
            AND attendance_date=CURDATE()
        """, (student_id,))

        already = cursor.fetchone()

        if not already:

            cursor.execute("""
                INSERT INTO attendance
                (student_id, attendance_date, status)
                VALUES (%s, CURDATE(), %s)
            """, (student_id, status))

        else:

            cursor.execute("""
                UPDATE attendance
                SET status=%s
                WHERE student_id=%s
                AND attendance_date=CURDATE()
            """, (status, student_id))

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

@app.route("/start_attendance")
def start_attendance():

    if "admin" not in session:
        return redirect("/login")

    with open("encodings/encodings.pkl", "rb") as f:
        data = pickle.load(f)

    known_encodings = data["encodings"]
    known_names = data["names"]

    cap = cv2.VideoCapture(0)

    while True:

        ret, frame = cap.read()

        if not ret:
            break

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        face_locations = face_recognition.face_locations(rgb)
        face_encodings = face_recognition.face_encodings(rgb, face_locations)

        attendance_saved = False

        for face_encoding, face_location in zip(face_encodings, face_locations):

            matches = face_recognition.compare_faces(
                known_encodings,
                face_encoding
            )

            if True in matches:

                index = matches.index(True)
                name = known_names[index]

                cursor.execute(
                    "SELECT id FROM students WHERE student_name=%s",
                    (name,)
                )

                student = cursor.fetchone()

                if student:

                    student_id = student[0]

                    cursor.execute("""
                        SELECT *
                        FROM attendance
                        WHERE student_id=%s
                        AND attendance_date=CURDATE()
                    """, (student_id,))

                    already = cursor.fetchone()

                    if not already:

                        cursor.execute("""
                            INSERT INTO attendance
                            (student_id, attendance_date, status)
                            VALUES (%s, CURDATE(), 'Present')
                        """, (student_id,))

                        db.commit()

                        attendance_saved = True

                        winsound.Beep(1000, 500)

                top, right, bottom, left = face_location

                cv2.rectangle(
                    frame,
                    (left, top),
                    (right, bottom),
                    (0,255,0),
                    2
                )

                cv2.putText(
                    frame,
                    name,
                    (left, top-10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0,255,0),
                    2
                )

                if attendance_saved:

                    cv2.circle(
                        frame,
                        (right+20, top+20),
                        18,
                        (0,255,0),
                        -1
                    )

                    cv2.line(
                        frame,
                        (right+15, top+20),
                        (right+20, top+25),
                        (255,255,255),
                        2
                    )

                    cv2.line(
                        frame,
                        (right+20, top+25),
                        (right+30, top+12),
                        (255,255,255),
                        2
                    )

                    cv2.putText(
                        frame,
                        "Attendance Marked Successfully",
                        (40,40),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.8,
                        (0,255,0),
                        2
                    )

                    cv2.imshow("Smart Attendance", frame)

                    cv2.waitKey(2000)

                    cap.release()
                    cv2.destroyAllWindows()

                    return redirect("/attendance_success")

        cv2.imshow("Smart Attendance", frame)

        if cv2.waitKey(1) & 0xFF == 27:
            break

    cap.release()
    cv2.destroyAllWindows()

    return redirect("/attendance")    
@app.route("/logout")
def logout():

    session.pop("admin", None)

    return redirect("/login")

@app.route("/attendance_success")
def attendance_success():
    return render_template("attendance_success.html")
if __name__ == "__main__":
    app.run(debug=True)