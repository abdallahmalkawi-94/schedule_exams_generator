import mysql.connector
import numpy as np
from datetime import datetime, timedelta
import pandas as pd
from collections import defaultdict
import random

from database import Database


class ReCalculateConflictsExams():
    # Function to analyze student conflicts
    from collections import defaultdict

    def analyze_student_conflicts(self, student_courses, schedule):
        # Create a dictionary to map student_id to list of course_ids
        student_course_dict = defaultdict(list)
        for sc in student_courses:
            student_course_dict[sc[2]].append(sc[1])  # sc[2] = student_id, sc[1] = course_id

        # Track conflicts
        same_day_conflicts = defaultdict(list)  # {student_id: [(date, [course_codes])]}
        same_slot_conflicts = defaultdict(list)  # {student_id: [(date, slot, [course_codes])]}

        for student_id, course_ids in student_course_dict.items():
            # Track exams per day and per slot
            exams_per_day = defaultdict(list)
            exams_per_slot = defaultdict(list)

            for course_id in course_ids:
                # Find the exam for this course in the schedule
                exam = next((exam for exam in schedule if exam['course_id'] == course_id), None)
                if exam:
                    date = datetime.strptime(exam['exam_date'], '%Y-%m-%d')
                    slot = exam['slot']
                    full_code = exam['full_code']

                    # Add to exams_per_day and exams_per_slot
                    exams_per_day[date].append(full_code)
                    exams_per_slot[(date, slot)].append(full_code)

            # Check for same-day conflicts
            for date, courses_in_day in exams_per_day.items():
                if len(courses_in_day) >= 2:
                    same_day_conflicts[student_id].append((date, courses_in_day))

            # Check for same-slot conflicts
            for (date, slot), courses_in_slot in exams_per_slot.items():
                if len(courses_in_slot) >= 2:
                    same_slot_conflicts[student_id].append((date, slot, courses_in_slot))

        return same_day_conflicts, same_slot_conflicts

    def same_day_conflicts_df(self, same_day_conflicts, student_info):
        same_day_conflicts_data = []
        for student_id, conflicts in same_day_conflicts.items():
            student_number, student_name = student_info.get(student_id, ("N/A", "N/A"))
            for date, courses_in_day in conflicts:
                same_day_conflicts_data.append({
                    'student_id': student_id,
                    'student_number': student_number,
                    'student_name': student_name,
                    'date': date.strftime('%Y-%m-%d'),
                    'no_of_exam': len(courses_in_day),
                    'courses': ", ".join(courses_in_day),
                })
        same_day_conflicts_data.sort(key=lambda x: (x['date'], x['no_of_exam']))
        return same_day_conflicts_data

    def same_slot_conflicts_df(self, same_slot_conflicts, student_info):
        same_slot_conflicts_data = []
        for student_id, conflicts in same_slot_conflicts.items():
            student_number, student_name = student_info.get(student_id, ("N/A", "N/A"))
            for date, slot, courses_in_slot in conflicts:
                same_slot_conflicts_data.append({
                    'student_id': student_id,
                    'student_number': student_number,
                    'student_name': student_name,
                    'date': date.strftime('%Y-%m-%d'),
                    'slot': slot + 1,
                    'no_of_exam': len(courses_in_slot),
                    'courses': ", ".join(courses_in_slot),
                })

        same_slot_conflicts_data.sort(key=lambda x: (x['date'], x['slot'], x['no_of_exam']))
        return same_slot_conflicts_data

    def convert_to_serializable(self, data):
        """Convert numpy data types to native Python data types."""
        if isinstance(data, list):
            return [self.convert_to_serializable(item) for item in data]
        elif isinstance(data, dict):
            return {key: self.convert_to_serializable(value) for key, value in data.items()}
        elif isinstance(data, np.integer):
            return int(data)
        elif isinstance(data, np.floating):
            return float(data)
        elif isinstance(data, np.ndarray):
            return data.tolist()
        else:
            return data

    def connect_to_database(self):
        return mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="pharma_collage"
        )

    def main(self, newSchedule, time_slots):
        db = Database()
        # Fetch data from the database
        courses, students, student_courses = db.fetch_data_from_database()
        same_day_conflicts, same_slot_conflicts = self.analyze_student_conflicts(student_courses, newSchedule)

        print(same_day_conflicts)
        # Create a dictionary to map student_id to student details
        student_info = {student[0]: (student[1], student[2]) for student in students}

        same_day_conflicts_df = self.same_day_conflicts_df(same_day_conflicts, student_info)
        same_slot_conflicts_df = self.same_slot_conflicts_df(same_slot_conflicts, student_info)

        return {
            "same_day_conflicts": self.convert_to_serializable(same_day_conflicts_df),
            "same_slot_conflicts": self.convert_to_serializable(same_slot_conflicts_df),
            "schedule": self.convert_to_serializable(newSchedule),
        }


    # if __name__ == "__main__":
    #     main()
