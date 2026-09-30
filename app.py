from datetime import datetime
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
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, session
from datetime import date
import mysql.connector
import requests
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")
# WhatsApp API Configuration
ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")

PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")

WHATSAPP_URL = f"https://graph.facebook.com/v23.0/{PHONE_NUMBER_ID}/messages"
def send_whatsapp_message(phone, student_name, attendance_date, attendance_time=None, template_name="student_present"):
    try:
        # 1. Phone number clean & format (10-digit number me automatically 91 country code lagana)
        clean_phone = str(phone).strip().replace("+", "").replace(" ", "").replace("-", "")
        if len(clean_phone) == 10:
            clean_phone = "91" + clean_phone

        # 2. Template ke hisab se dynamic parameters taiyar karna
        if template_name == "student_present":
            # Present template expects 3 parameters: Student Name, Date, Time
            parameters = [
                {"type": "text", "text": str(student_name)},
                {"type": "text", "text": str(attendance_date)},
                {"type": "text", "text": str(attendance_time) if attendance_time else ""}
            ]
        elif template_name == "student_absent":
            # Absent template expects 2 parameters: Student Name, Date
            parameters = [
                {"type": "text", "text": str(student_name)},
                {"type": "text", "text": str(attendance_date)}
            ]
        else:
            # Future templates ke liye generic fallback
            parameters = [
                {"type": "text", "text": str(student_name)},
                {"type": "text", "text": str(attendance_date)}
            ]
            if attendance_time:
                parameters.append({"type": "text", "text": str(attendance_time)})

        headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }

        data = {
            "messaging_product": "whatsapp",
            "to": clean_phone,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {
                    "code": "en"
                },
                "components": [
                    {
                        "type": "body",
                        "parameters": parameters
                    }
                ]
            }
        }

        print(f"\n📱 Sending WhatsApp [{template_name}] to {clean_phone} ({student_name})...")
        response = requests.post(WHATSAPP_URL, headers=headers, json=data, timeout=10)

        print("Status Code:", response.status_code)
        print("Response:", response.text)

        if response.status_code == 200:
            print(f"✅ WhatsApp Message Sent Successfully to {student_name}")
            return True
        else:
            print(f"❌ WhatsApp Message Failed: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Error sending WhatsApp message: {e}")
        return False
    
db = mysql.connector.connect(
    host=os.getenv("DB_HOST"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME")
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

        admin_username = os.getenv("ADMIN_USERNAME")
        admin_password = os.getenv("ADMIN_PASSWORD")

        if username == admin_username and password == admin_password:

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
        parent_mobile = request.form["parent_mobile"]
        mobile = request.form["mobile"]
        email = request.form["email"]
        address = request.form["address"]

        sql = """
        INSERT INTO students
        (student_name, roll_number, class_name, section, father_name, parent_mobile, mobile, email, address, photo)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """

        values = (student_name, roll_number, class_name, section, father_name, parent_mobile, mobile, email, address, filename)

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
        SELECT
            id,
            student_name,
            roll_number,
            class_name,
            section,
            father_name,
            parent_mobile,
            mobile,
            email,
            address,
            photo
        FROM students
        WHERE student_name LIKE %s
        OR roll_number LIKE %s
        """

        value = ("%" + search + "%", "%" + search + "%")
        cursor.execute(sql, value)

    else:

        cursor.execute("""
            SELECT
                id,
                student_name,
                roll_number,
                class_name,
                section,
                father_name,
                parent_mobile,
                mobile,
                email,
                address,
                photo
            FROM students
        """)

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
        parent_mobile = request.form["parent_mobile"]
        mobile = request.form["mobile"]
        email = request.form["email"]
        address = request.form["address"]

        photo = request.files["photo"]

        filename = None

        # New Photo Upload
        if photo.filename != "":

            filename = secure_filename(photo.filename)

            upload_folder = os.path.join(
                app.root_path,
                "static",
                "uploads"
            )

            os.makedirs(upload_folder, exist_ok=True)

            photo.save(
                os.path.join(upload_folder, filename)
            )

        # Photo bhi update karni hai
        if filename:

            sql = """
            UPDATE students
            SET
                student_name=%s,
                roll_number=%s,
                class_name=%s,
                section=%s,
                father_name=%s,
                parent_mobile=%s,
                mobile=%s,
                email=%s,
                address=%s,
                photo=%s
            WHERE id=%s
            """

            values = (
                student_name,
                roll_number,
                class_name,
                section,
                father_name,
                parent_mobile,
                mobile,
                email,
                address,
                filename,
                id
            )

        # Photo update nahi karni
        else:

            sql = """
            UPDATE students
            SET
                student_name=%s,
                roll_number=%s,
                class_name=%s,
                section=%s,
                father_name=%s,
                parent_mobile=%s,
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
                parent_mobile,
                mobile,
                email,
                address,
                id
            )

        cursor.execute(sql, values)
        db.commit()

        return redirect("/view_students")

    cursor.execute("""
        SELECT
            id,
            student_name,
            roll_number,
            class_name,
            section,
            father_name,
            parent_mobile,
            mobile,
            email,
            address,
            photo
        FROM students
        WHERE id=%s
    """, (id,))

    student = cursor.fetchone()

    return render_template(
        "edit_student.html",
        student=student
    )
@app.route("/save_attendance", methods=["POST"])
def save_attendance():

    if "admin" not in session:
        return redirect("/login")

    student_ids = request.form.getlist("student_id")

    for student_id in student_ids:

        status = request.form.get(f"attendance_{student_id}")

        # Check today's attendance and get old status
        cursor.execute("""
            SELECT id, status
            FROM attendance
            WHERE student_id=%s
            AND attendance_date=CURDATE()
        """, (student_id,))

        already = cursor.fetchone()

        old_status = None

        if not already:

            cursor.execute("""
                INSERT INTO attendance
                (student_id, attendance_date, status)
                VALUES (%s, CURDATE(), %s)
            """, (student_id, status))

            should_send_message = True

        else:

            old_status = already[1]

            cursor.execute("""
                UPDATE attendance
                SET status=%s
                WHERE student_id=%s
                AND attendance_date=CURDATE()
            """, (status, student_id))

            # Send message only if status actually changed
            should_send_message = old_status != status

        # Get student's name and parent's mobile number
        cursor.execute("""
            SELECT student_name, parent_mobile
            FROM students
            WHERE id=%s
        """, (student_id,))

        student_data = cursor.fetchone()

        if should_send_message and student_data and student_data[1]:

            student_name = student_data[0]
            parent_mobile = student_data[1]

            attendance_date = datetime.now().strftime("%d-%m-%Y")
            attendance_time = datetime.now().strftime("%I:%M %p")

            # Send WhatsApp according to attendance status
            if status == "Present":

                send_whatsapp_message(
                    parent_mobile,
                    student_name,
                    attendance_date,
                    attendance_time,
                    "student_present"
                )

            elif status == "Absent":

                send_whatsapp_message(
                    parent_mobile,
                    student_name,
                    attendance_date,
                    attendance_time,
                    "student_absent"
                )

    db.commit()

    return redirect("/attendance")
@app.route("/reports", methods=["GET", "POST"])
def reports():

    if "admin" not in session:
        return redirect("/login")

    if request.method == "POST":

        student_name = request.form.get("student_name")
        roll_number = request.form.get("roll_number")
        from_date = request.form.get("from_date")
        to_date = request.form.get("to_date")

        sql = """
        SELECT
           students.student_name,
           students.roll_number,
           attendance.attendance_date,
           attendance.status,
           attendance.attendance_time
        FROM attendance
        INNER JOIN students
        ON attendance.student_id = students.id
        WHERE 1=1
        """

        values = []

        if student_name:
           sql += " AND students.student_name LIKE %s"
           values.append("%" + student_name + "%")
        
        if roll_number:
          sql += " AND students.roll_number = %s"
          values.append(roll_number)

        if from_date and to_date:
           sql += """
              AND attendance.attendance_date
              BETWEEN %s AND %s
           """
           values.append(from_date)
           values.append(to_date)

        elif from_date:
           sql += " AND attendance.attendance_date >= %s"
           values.append(from_date)

        elif to_date:
           sql += " AND attendance.attendance_date <= %s"
           values.append(to_date)

        sql += " ORDER BY attendance.attendance_date DESC"

        cursor.execute(sql, tuple(values))
        records = cursor.fetchall()

    else:

        sql = """
        SELECT
            students.student_name,
            students.roll_number,
            attendance.attendance_date,
            attendance.status,
            attendance.attendance_time
        FROM attendance
        INNER JOIN students
        ON attendance.student_id = students.id
        ORDER BY attendance.attendance_date DESC
        """

        cursor.execute(sql)
        records = cursor.fetchall()

    summary_sql = """
    SELECT
        students.student_name,

        SUM(
            CASE
                WHEN attendance.status = 'Present' THEN 1
                ELSE 0
            END
        ) AS present,

        SUM(
            CASE
                WHEN attendance.status = 'Absent' THEN 1
                ELSE 0
            END
        ) AS absent,

        ROUND(
            (
                SUM(
                    CASE
                        WHEN attendance.status = 'Present' THEN 1
                        ELSE 0
                    END
                ) * 100
            ) /
            NULLIF(
                SUM(
                    CASE
                        WHEN attendance.status IN ('Present','Absent') THEN 1
                        ELSE 0
                    END
                ),
                0
            ),
            2
        ) AS percentage

    FROM students

    LEFT JOIN attendance
    ON students.id = attendance.student_id

    GROUP BY students.id
    """

    cursor.execute(summary_sql)
    rows = cursor.fetchall()

    summary = []

    for row in rows:

        name = row[0]
        present = row[1]
        absent = row[2]
        percentage = row[3]

        if percentage is None:
            percentage = 0

        if percentage >= 90:
            status = "🟢 Excellent"

        elif percentage >= 75:
            status = "🟡 Good"

        else:
            status = "🔴 Low"

        summary.append(
            (
                name,
                present,
                absent,
                percentage,
                status
            )
        )

    return render_template(
        "reports.html",
        records=records,
        summary=summary
    )

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

    # Pehle attendance delete karo
    cursor.execute("DELETE FROM attendance WHERE student_id = %s", (id,))

    # Phir student delete karo
    cursor.execute("DELETE FROM students WHERE id = %s", (id,))

    db.commit()

    return redirect("/view_students")

@app.route("/start_attendance")
def start_attendance():

    if "admin" not in session:
        return redirect("/login")
    cursor.execute("""
        SELECT is_closed
        FROM attendance_status
        WHERE attendance_date = CURDATE()
    """)

    status = cursor.fetchone()

    if status and status[0] == "Yes":
        return """
        <h2 style='color:red;text-align:center;margin-top:50px;'>
        Today's Attendance has already been Closed.
        </h2>
        <div style='text-align:center;'>
            <a href='/attendance'>Go Back</a>
        </div>
        """
   
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
              face_encoding,
              tolerance=0.5
            )       

            face_distances = face_recognition.face_distance(
              known_encodings,
              face_encoding
            )

            best_match_index = np.argmin(face_distances)

            print("Distances:", face_distances)
            print("Best Match:", known_names[best_match_index])
            print("Matches:", matches)  

            if matches[best_match_index]:
                print("Inside IF Block") 
                name = known_names[best_match_index]
                cursor.execute(
                    "SELECT id FROM students WHERE student_name=%s",
                    (name,)
                )

                student = cursor.fetchone()

                if student:

                    student_id = student[0]
                    print("Student ID:", student_id)
                    cursor.execute("""
                       SELECT status
                       FROM attendance
                       WHERE student_id=%s
                       AND attendance_date=CURDATE()
                    """, (student_id,))

                    already = cursor.fetchone()

                    # Agar attendance record nahi hai
                    if not already:

                        cursor.execute("""
                          INSERT INTO attendance
                          (student_id, attendance_date, attendance_time, status)
                          VALUES (%s, CURDATE(), CURTIME(), 'Present')
                        """, (student_id,))

                        db.commit()

                        attendance_saved = True

                        winsound.Beep(1000, 500)

                        print("New Attendance Saved")
                        cursor.execute(
                            """
                            SELECT parent_mobile
                            FROM students
                            WHERE id=%s
                            """,
                           (student_id,)
                        )

                        parent = cursor.fetchone()

                        if parent and parent[0]:

                         cursor.execute("""
                           SELECT
                             DATE_FORMAT(attendance_date, '%d-%m-%Y'),
                             TIME_FORMAT(attendance_time, '%h:%i %p')
                           FROM attendance
                           WHERE student_id=%s
                           AND attendance_date=CURDATE()
                         """, (student_id,))

                         attendance_data = cursor.fetchone()

                         attendance_date = attendance_data[0]
                         attendance_time = attendance_data[1]

                         send_whatsapp_message(
                           parent[0],
                           name,
                           attendance_date,
                           attendance_time,
                           "student_present"
                        )

                    # Agar Absent hai to Present bana do
                    elif already[0] == "Absent":

                      cursor.execute("""
                         UPDATE attendance
                         SET
                            status='Present',
                            attendance_time=CURTIME()
                        WHERE student_id=%s
                        AND attendance_date=CURDATE()
                      """, (student_id,))

                      db.commit()

                      attendance_saved = True

                      winsound.Beep(1000, 500)

                      print("Attendance Updated : Absent -> Present")
                      cursor.execute(
                        """
                        SELECT parent_mobile
                        FROM students
                        WHERE id=%s
                        """,
                        (student_id,)
                      )

                      parent = cursor.fetchone()

                      if parent and parent[0]:

                        cursor.execute("""
                          SELECT
                             DATE_FORMAT(attendance_date, '%d-%m-%Y'),
                             TIME_FORMAT(attendance_time, '%h:%i %p')
                          FROM attendance
                          WHERE student_id=%s
                          AND attendance_date=CURDATE()
                        """, (student_id,))

                        attendance_data = cursor.fetchone()

                        attendance_date = attendance_data[0]
                        attendance_time = attendance_data[1]

                        send_whatsapp_message(
                             parent[0],
                             name,
                             attendance_date,
                             attendance_time,
                             "student_present"
                        )
                     # Agar pehle se Present hai
                    else:

                     print("Attendance Already Present")
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
@app.route("/close_attendance")
def close_attendance():

    if "admin" not in session:
        return redirect("/login")

    return render_template("close_attendance.html")  
@app.route("/confirm_close_attendance")
def confirm_close_attendance():

    if "admin" not in session:
        return redirect("/login")

    # Sabhi students nikalo
    cursor.execute("SELECT id FROM students")
    students = cursor.fetchall()

    for student in students:

        student_id = student[0]

        # Check karo ki aaj attendance lagi hai ya nahi
        cursor.execute("""
            SELECT *
            FROM attendance
            WHERE student_id=%s
            AND attendance_date=CURDATE()
        """, (student_id,))

        already = cursor.fetchone()

        # Agar attendance nahi lagi hai
        if not already:

            cursor.execute("""
                INSERT INTO attendance
                (student_id, attendance_date, status, attendance_time)
                VALUES
                (%s, CURDATE(), 'Absent', CURTIME())
            """, (student_id,))
            db.commit()

            cursor.execute("""
                SELECT student_name, parent_mobile
                FROM students
                WHERE id=%s
            """, (student_id,))

            student_data = cursor.fetchone()

            if student_data and student_data[1]:

                student_name = student_data[0]
                parent_mobile = student_data[1]

                attendance_date = datetime.now().strftime("%d-%m-%Y")
                attendance_time = datetime.now().strftime("%I:%M %p")

                send_whatsapp_message(
                    parent_mobile,
                    student_name,
                    attendance_date,
                    attendance_time,
                    "student_absent"
                )

    # Attendance ko Closed mark karo
    cursor.execute("""
        INSERT INTO attendance_status
        (attendance_date, is_closed)
        VALUES
        (CURDATE(), 'Yes')
        ON DUPLICATE KEY UPDATE
        is_closed='Yes'
    """)

    db.commit()

    return redirect("/reports")
@app.route("/reopen_attendance")
def reopen_attendance():

    if "admin" not in session:
        return redirect("/login")

    cursor.execute("""
        DELETE FROM attendance_status
        WHERE attendance_date = CURDATE()
    """)

    db.commit()

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