import mysql.connector
import pandas as pd


class Database:
    def connect_to_database(self):
        return mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="pharma_collage"
        )

    def fetch_data_from_database(self):
        conn = self.connect_to_database()
        cursor = conn.cursor()

        # Fetch courses
        cursor.execute("SELECT id, course_number, name, code FROM courses")
        courses = cursor.fetchall()

        # Fetch students
        cursor.execute("SELECT id, student_number, name FROM students")
        students = cursor.fetchall()

        # Fetch student_courses
        cursor.execute("SELECT id, course_id, student_id FROM student_courses")
        student_courses = cursor.fetchall()

        cursor.close()
        conn.close()

        return courses, students, student_courses