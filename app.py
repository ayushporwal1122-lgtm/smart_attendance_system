from flask import Flask, render_template, request, redirect
import mysql.connector

app = Flask(__name__)

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Ayush@888",
    database="smart_attendence_db"
)

cursor = db.cursor()

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@app.route("/add_student", methods=["GET", "POST"])
def add_student():

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
        INSERT INTO students
        (student_name, roll_number, class_name, section, father_name, mobile, email, address)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """

        values = (student_name, roll_number, class_name, section, father_name, mobile, email, address)

        cursor.execute(sql, values)
        db.commit()

        return redirect("/add_student")

    return render_template("add_student.html")

@app.route("/view_students")
def view_students():

    cursor.execute("SELECT * FROM students")

    students = cursor.fetchall()

    return render_template("view_students.html", students=students)

@app.route("/edit_student/<int:id>", methods=["GET", "POST"])
def edit_student(id):

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
@app.route("/delete_student/<int:id>")
def delete_student(id):

    sql = "DELETE FROM students WHERE id = %s"

    cursor.execute(sql, (id,))
    db.commit()

    return redirect("/view_students")

if __name__ == "__main__":
    app.run(debug=True)