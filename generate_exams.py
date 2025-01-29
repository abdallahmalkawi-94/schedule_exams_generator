import numpy as np
from datetime import datetime, timedelta
import pandas as pd
from collections import defaultdict
import random

from database import Database


class GenerateExams():
    # Function to calculate the conflict matrix
    def calculate_conflict_matrix(self, courses, student_courses):
        n_courses = len(courses)
        conflict_matrix = np.zeros((n_courses, n_courses), dtype=int)

        # Create a dictionary to map course_id to index
        course_id_to_index = {course[0]: idx for idx, course in enumerate(courses)}

        # Create a dictionary to map student_id to list of course_ids
        student_course_dict = defaultdict(list)
        for sc in student_courses:
            student_course_dict[sc[2]].append(sc[1])

        # Calculate conflicts
        for student_id, course_ids in student_course_dict.items():
            for i in range(len(course_ids)):
                for j in range(i + 1, len(course_ids)):
                    course_idx_i = course_id_to_index[course_ids[i]]
                    course_idx_j = course_id_to_index[course_ids[j]]
                    conflict_matrix[course_idx_i, course_idx_j] += 1
                    conflict_matrix[course_idx_j, course_idx_i] += 1

        return conflict_matrix

    # Function to generate time slots
    def generate_time_slots(self, start_date, end_date, slots_per_day, weekdays):
        time_slots = []
        current_date = start_date
        while current_date <= end_date:
            if current_date.weekday() not in weekdays:
                for slot in range(slots_per_day):
                    time_slots.append((current_date, slot))
            current_date += timedelta(days=1)
        return time_slots

    # Function to assign courses to time slots using a greedy algorithm
    def assign_courses(self, courses, conflict_matrix, time_slots, student_courses):
        n_courses = len(courses)
        n_slots = len(time_slots)

        # Sort courses by the number of students enrolled (descending)
        courses_sorted = sorted(range(n_courses), key=lambda x: -sum(conflict_matrix[x]))

        # Initialize schedule
        schedule = np.zeros((n_courses, n_slots), dtype=int)

        # Track student assignments
        student_assignments = defaultdict(set)  # {student_id: {slot1, slot2, ...}}

        # Create a dictionary to map course_id to list of student_ids
        course_students = defaultdict(list)
        for sc in student_courses:
            course_students[sc[1]].append(sc[2])

        for course_idx in courses_sorted:
            best_slot = None
            min_conflicts = float('inf')

            # Shuffle slots to avoid bias
            slot_order = list(range(n_slots))
            random.shuffle(slot_order)

            for slot in slot_order:
                date, slot_num = time_slots[slot]

                # Check if the slot is already assigned to this course
                if schedule[course_idx, slot] == 1:
                    continue

                # Check for conflicts with other courses in the same slot
                conflicts = 0
                for other_course in range(n_courses):
                    if schedule[other_course, slot] == 1 and conflict_matrix[course_idx, other_course] > 0:
                        conflicts += conflict_matrix[course_idx, other_course]

                # Check if any student in this course is already assigned to this slot
                course_id = courses[course_idx][0]
                students_in_course = course_students[course_id]
                conflict_found = False
                for student_id in students_in_course:
                    if slot in student_assignments[student_id]:
                        conflict_found = True
                        break

                if conflict_found:
                    continue  # Skip this slot if it causes a conflict

                # Check for conflicts with other courses on the same day
                for other_slot in range(n_slots):
                    if other_slot != slot and time_slots[other_slot][0] == date:
                        for other_course in range(n_courses):
                            if schedule[other_course, other_slot] == 1 and conflict_matrix[
                                course_idx, other_course] > 0:
                                conflicts += conflict_matrix[course_idx, other_course]

                # Add a penalty for overloading specific slots
                slot_penalty = sum(schedule[:, slot]) * 10  # Penalize slots with more courses
                total_score = conflicts + slot_penalty

                # Choose the slot with the minimum total score
                if total_score < min_conflicts:
                    min_conflicts = total_score
                    best_slot = slot

            # Assign the course to the best slot
            if best_slot is not None:
                schedule[course_idx, best_slot] = 1

                # Update student assignments
                course_id = courses[course_idx][0]
                students_in_course = course_students[course_id]
                for student_id in students_in_course:
                    student_assignments[student_id].add(best_slot)

        return schedule

    # Function to analyze student conflicts
    def analyze_student_conflicts(self, courses, student_courses, schedule, time_slots):
        # Create a dictionary to map student_id to list of course_ids
        student_course_dict = defaultdict(list)
        for sc in student_courses:
            student_course_dict[sc[2]].append(sc[1])

        # Create a dictionary to map course_id to index
        course_id_to_index = {course[0]: idx for idx, course in enumerate(courses)}

        # Track conflicts
        same_day_conflicts = defaultdict(list)  # {student_id: [(date, [course_codes])]}
        same_slot_conflicts = defaultdict(list)  # {student_id: [(date, slot, [course_codes])]}
        consecutive_day_conflicts = defaultdict(list)  # {student_id: [(date1, date2, [course_codes1], [course_codes2])]}

        for student_id, course_ids in student_course_dict.items():
            # Track exams per day and per slot
            exams_per_day = defaultdict(list)
            exams_per_slot = defaultdict(list)

            for course_id in course_ids:
                course_idx = course_id_to_index[course_id]
                for slot_idx, assigned in enumerate(schedule[course_idx]):
                    if assigned == 1:
                        full_code = courses[course_idx][3] + courses[course_idx][1]
                        date, slot = time_slots[slot_idx]
                        exams_per_day[date].append((full_code, courses[course_idx][1][0]))  # Course Full code and year
                        exams_per_slot[(date, slot)].append((full_code, courses[course_idx][1][0]))  # Course Full code and year

            # Check for same-day conflicts
            for date, courses_in_day in exams_per_day.items():
                if len(courses_in_day) >= 2:
                    same_day_conflicts[student_id].append((date, [course[0] for course in courses_in_day]))

            # Check for same-slot conflicts
            for (date, slot), courses_in_slot in exams_per_slot.items():
                if len(courses_in_slot) >= 2:
                    same_slot_conflicts[student_id].append((date, slot, [course[0] for course in courses_in_slot]))

            # Check for consecutive-day conflicts (only if courses are in the same year)
            sorted_dates = sorted(exams_per_day.keys())
            for i in range(len(sorted_dates) - 1):
                date1 = sorted_dates[i]
                date2 = sorted_dates[i + 1]
                if (date2 - date1).days == 1:  # Check if dates are consecutive
                    # Get courses for date1 and date2
                    courses_day1 = exams_per_day[date1]
                    courses_day2 = exams_per_day[date2]

                    # Filter courses to include only those in the same year
                    same_year_courses_day1 = [course[0] for course in courses_day1]
                    same_year_courses_day2 = [course[0] for course in courses_day2]

                    # Check if there are any courses in the same year on consecutive days
                    if same_year_courses_day1 and same_year_courses_day2:
                        if courses_day1[0][1] == courses_day2[0][1]:
                            consecutive_day_conflicts[student_id].append((date1, date2, same_year_courses_day1, same_year_courses_day2))

        return same_day_conflicts, same_slot_conflicts, consecutive_day_conflicts

    # Function to export results to Excel
    def export_to_excel(self, exam_schedule_df, same_day_conflicts_df, same_slot_conflicts_df, consecutive_day_conflicts_df):
        # Export to Excel
        with pd.ExcelWriter("exam_schedule.xlsx") as writer:
            exam_schedule_df.to_excel(writer, sheet_name="Exam Schedule", index=False)
            same_day_conflicts_df.to_excel(writer, sheet_name="Same Day Conflicts", index=False)
            same_slot_conflicts_df.to_excel(writer, sheet_name="Same Slot Conflicts", index=False)
            consecutive_day_conflicts_df.to_excel(writer, sheet_name="Consecutive Day Conflicts", index=False)

        print("Excel file 'exam_schedule.xlsx' has been created.")

    def schedule_df(self, time_slots, courses, schedule):
        exam_schedule_data = []
        for course_idx, slots in enumerate(schedule):
            course_name = courses[course_idx][2]
            course_full_code = courses[course_idx][3] + courses[course_idx][1]
            for slot_idx, assigned in enumerate(slots):
                if assigned == 1:
                    date, slot = time_slots[slot_idx]
                    exam_schedule_data.append({
                        'course_id': courses[course_idx][0],
                        'course_name': course_name,
                        'full_code': course_full_code,
                        'exam_date': date.strftime('%Y-%m-%d'),
                        'slot': slot + 1,
                    })

        exam_schedule_data.sort(key=lambda x: (x['exam_date'], x['slot']))
        return exam_schedule_data

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

    def consecutive_day_conflicts_df(self, consecutive_day_conflicts, student_info):
        consecutive_day_conflicts_data = []
        for student_id, conflicts in consecutive_day_conflicts.items():
            student_number, student_name = student_info.get(student_id, ("N/A", "N/A"))
            for date1, date2, courses_day1, courses_day2 in conflicts:
                consecutive_day_conflicts_data.append({
                    'student_id': student_id,
                    'student_number': student_number,
                    'student_name': student_name,
                    'date1': date1.strftime('%Y-%m-%d'),
                    'date2': date2.strftime('%Y-%m-%d'),
                    'courses_day1': ", ".join(courses_day1),
                    'courses_day2': ", ".join(courses_day2),
                })

        consecutive_day_conflicts_data.sort(key=lambda x: (x['date1'], x['date2']))
        return consecutive_day_conflicts_data

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

    def main(self, time_slots):
        db = Database()
        # Fetch data from the database
        courses, students, student_courses = db.fetch_data_from_database()

        # Calculate conflict matrix
        conflict_matrix = self.calculate_conflict_matrix(courses, student_courses)

        # Assign courses to time slots
        schedule = self.assign_courses(courses, conflict_matrix, time_slots, student_courses)

        # Sheet 1: Exam Schedule
        schedule_df = self.schedule_df(time_slots, courses, schedule)
        # Analyze student conflicts
        same_day_conflicts, same_slot_conflicts, consecutive_day_conflicts = self.analyze_student_conflicts(courses, student_courses, schedule, time_slots)

        # Create a dictionary to map student_id to student details
        student_info = {student[0]: (student[1], student[2]) for student in students}

        # Sheet 2: Students with Two or More Exams on the Same Day
        same_day_conflicts_df = self.same_day_conflicts_df(same_day_conflicts, student_info)

        # Sheet 3: Students with Two or More Exams in the Same Time Slot
        same_slot_conflicts_df = self.same_slot_conflicts_df(same_slot_conflicts, student_info)

        # Sheet 4: Students with Exams on Consecutive Days (Same Year)
        consecutive_day_conflicts_df = self.consecutive_day_conflicts_df(consecutive_day_conflicts, student_info)

        # Export results to Excel
        # self.export_to_excel(
        #     pd.DataFrame(schedule_df),
        #     pd.DataFrame(same_day_conflicts_df),
        #     pd.DataFrame(same_slot_conflicts_df),
        #     pd.DataFrame(consecutive_day_conflicts_df)
        # )

        return {
            "same_day_conflicts": self.convert_to_serializable(same_day_conflicts_df),
            "same_slot_conflicts": self.convert_to_serializable(same_slot_conflicts_df),
            "consecutive_day_conflicts": self.convert_to_serializable(consecutive_day_conflicts_df),
            "schedule": self.convert_to_serializable(schedule_df),
        }