import mysql.connector


class DatabaseInitializer:
    def __init__(self, host, user, password, database):
        self.host = host
        self.user = user
        self.password = password
        self.database = database

    def connect_to_database(self, db_name=None):
        return mysql.connector.connect(
            host=self.host,
            user=self.user,
            password=self.password,
            database=db_name if db_name else None
        )

    def create_database(self):
        conn = self.connect_to_database()
        cursor = conn.cursor()

        cursor.execute("CREATE DATABASE IF NOT EXISTS " + self.database)

        cursor.close()
        conn.close()

    def create_students_table(self):
        conn = self.connect_to_database(self.database)
        cursor = conn.cursor()

        query = """
        CREATE TABLE IF NOT EXISTS students (
            id BIGINT(20) UNSIGNED NOT NULL AUTO_INCREMENT,
            name VARCHAR(255) NOT NULL,
            student_number BIGINT(20) NOT NULL,
            created_at TIMESTAMP NULL DEFAULT NULL,
            updated_at TIMESTAMP NULL DEFAULT NULL,
            PRIMARY KEY (id)
        ) ENGINE=InnoDB AUTO_INCREMENT=995 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """

        cursor.execute(query)
        conn.commit()
        cursor.close()
        conn.close()

    def create_courses_table(self):
        conn = self.connect_to_database(self.database)
        cursor = conn.cursor()

        query = """
        CREATE TABLE IF NOT EXISTS courses (
            id BIGINT(20) UNSIGNED NOT NULL AUTO_INCREMENT,
            code VARCHAR(255) NOT NULL,
            course_number VARCHAR(255) NOT NULL,
            name VARCHAR(255) NOT NULL,
            hours INT(10) UNSIGNED NOT NULL,
            created_at TIMESTAMP NULL DEFAULT NULL,
            updated_at TIMESTAMP NULL DEFAULT NULL,
            PRIMARY KEY (id)
        ) ENGINE=InnoDB AUTO_INCREMENT=50 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """

        cursor.execute(query)
        conn.commit()
        cursor.close()
        conn.close()

    def create_student_courses_table(self):
        conn = self.connect_to_database(self.database)
        cursor = conn.cursor()

        query = """
        CREATE TABLE IF NOT EXISTS student_courses (
            id BIGINT(20) UNSIGNED NOT NULL AUTO_INCREMENT,
            student_id BIGINT(20) UNSIGNED NOT NULL,
            course_id BIGINT(20) UNSIGNED NOT NULL,
            created_at TIMESTAMP NULL DEFAULT NULL,
            updated_at TIMESTAMP NULL DEFAULT NULL,
            PRIMARY KEY (id),
            INDEX student_courses_student_id_idx (student_id),
            INDEX student_courses_course_id_idx (course_id),
            CONSTRAINT student_courses_student_id_fk FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE,
            CONSTRAINT student_courses_course_id_fk FOREIGN KEY (course_id) REFERENCES courses (id) ON DELETE CASCADE
        ) ENGINE=InnoDB AUTO_INCREMENT=8001 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """

        cursor.execute(query)
        conn.commit()
        cursor.close()
        conn.close()

    def initialize_database(self):
        self.create_database()
        self.create_students_table()
        self.create_courses_table()
        self.create_student_courses_table()

    def fetch_data_from_database(self):
        conn = self.connect_to_database(self.database)
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