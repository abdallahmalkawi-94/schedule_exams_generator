import numpy as np
from datetime import timedelta
import pandas as pd
from collections import defaultdict
import random
from multiprocessing import Pool


class GenerateExamsByExcel:
    def calculate_conflict_chunk(self, student_course_chunk, course_id_to_index, n_courses):
        print(f"Processing chunk with {len(student_course_chunk)} entries")
        conflict_matrix = np.zeros((n_courses, n_courses), dtype=int)
        student_course_dict = defaultdict(list)
        for sc in student_course_chunk:
            student_course_dict[sc[2]].append(sc[1])
        for student_id, course_ids in student_course_dict.items():
            if len(course_ids) > 1:
                for i in range(len(course_ids)):
                    for j in range(i + 1, len(course_ids)):
                        idx_i, idx_j = course_id_to_index[course_ids[i]], course_id_to_index[course_ids[j]]
                        conflict_matrix[idx_i, idx_j] += 1
                        conflict_matrix[idx_j, idx_i] += 1
        print(f"Chunk conflict matrix sum: {np.sum(conflict_matrix)}")
        return conflict_matrix

    def calculate_conflict_matrix(self, courses, student_courses):
        n_courses = len(courses)
        course_id_to_index = {course[0]: idx for idx, course in enumerate(courses)}
        print(f"Number of courses: {n_courses}")
        print(f"Course ID to index mapping: {course_id_to_index}")
        chunk_size = len(student_courses) // 4
        chunks = [student_courses[i:i + chunk_size] for i in range(0, len(student_courses), chunk_size)]
        print(f"Created {len(chunks)} chunks of size {chunk_size}")
        with Pool(processes=4) as pool:
            results = pool.starmap(self.calculate_conflict_chunk,
                                   [(chunk, course_id_to_index, n_courses) for chunk in chunks])
        conflict_matrix = np.sum(results, axis=0)
        print(f"Final conflict matrix shape: {conflict_matrix.shape}, sum: {np.sum(conflict_matrix)}")
        return conflict_matrix

    def generate_time_slots(self, start_date, end_date, slots_per_day, max_exams_per_day=5, exclude_days=None):
        if exclude_days is None:
            exclude_days = [5, 6]
        time_slots = []
        current_date = start_date
        while current_date <= end_date:
            if current_date.weekday() not in exclude_days:
                for slot in range(min(slots_per_day, max_exams_per_day)):
                    time_slots.append((current_date, slot))
            current_date += timedelta(days=1)
        return time_slots

    def assign_courses(self, courses, conflict_matrix, time_slots, student_courses):
        n_courses = len(courses)
        n_slots = len(time_slots)
        print(f"n_courses={n_courses}, n_slots={n_slots}")
        schedule = np.zeros((n_courses, n_slots), dtype=int)
        print(f"schedule shape={schedule.shape}")
        courses_sorted = sorted(range(n_courses), key=lambda x: -sum(conflict_matrix[x]))
        student_assignments = defaultdict(set)  # Tracks slots per student
        course_students = defaultdict(list)  # Tracks students per course
        student_daily_exams = defaultdict(lambda: defaultdict(int))  # Tracks exams per day per student

        for sc in student_courses:
            course_students[sc[1]].append(sc[2])

        for course_idx in courses_sorted:
            best_slot = None
            min_score = float('inf')
            slot_order = list(range(n_slots))
            random.shuffle(slot_order)
            for slot in slot_order:
                date, slot_num = time_slots[slot]
                if schedule[course_idx, slot] == 1:
                    continue
                conflicts = 0
                for other_course in range(n_courses):
                    if schedule[other_course, slot] == 1 and conflict_matrix[course_idx, other_course] > 0:
                        conflicts += conflict_matrix[course_idx, other_course]

                course_id = courses[course_idx][0]
                # Check for same-slot conflicts
                conflict_found = any(slot in student_assignments[student_id]
                                     for student_id in course_students[course_id])
                if conflict_found:
                    continue

                # Check for max 2 exams per day
                can_assign = True
                for student_id in course_students[course_id]:
                    if student_daily_exams[student_id][date] >= 2:
                        can_assign = False
                        break
                if not can_assign:
                    continue

                # Lookahead for same-day conflicts
                lookahead_conflicts = 0
                temp_schedule = schedule.copy()
                temp_schedule[course_idx, slot] = 1
                for other_idx in courses_sorted:
                    if other_idx <= course_idx or temp_schedule[other_idx].sum() > 0:
                        continue
                    valid_slots = [s for s in range(n_slots) if not any(
                        temp_schedule[oc, s] and conflict_matrix[other_idx, oc]
                        for oc in range(n_courses))]
                    if not valid_slots:
                        min_slot_conflict = float('inf')
                    else:
                        min_slot_conflict = min(
                            sum(temp_schedule[other_course, s] * conflict_matrix[other_idx, other_course]
                                for other_course in range(n_courses))
                            for s in valid_slots)
                    lookahead_conflicts += min_slot_conflict

                # Penalize same-day conflicts
                same_day_penalty = 0
                for student_id in course_students[course_id]:
                    student_slots = {s for s in student_assignments[student_id] if time_slots[s][0] == date}
                    if len(student_slots) >= 1:  # Already has 1 exam on this day
                        same_day_penalty += 100  # High penalty to discourage 2nd exam

                slot_penalty = sum(schedule[:, slot]) * 10
                total_score = conflicts + slot_penalty + lookahead_conflicts * 0.5 + same_day_penalty
                if total_score < min_score:
                    min_score = total_score
                    best_slot = slot

            if best_slot is not None:
                schedule[course_idx, best_slot] = 1
                date, slot_num = time_slots[best_slot]
                for student_id in course_students[courses[course_idx][0]]:
                    student_assignments[student_id].add(best_slot)
                    student_daily_exams[student_id][date] += 1
            else:
                print(f"No valid slot for course_idx={course_idx}")

        return schedule

    def analyze_student_conflicts(self, courses, student_courses, schedule, time_slots):
        student_course_dict = defaultdict(list)
        for sc in student_courses:
            student_course_dict[sc[2]].append(sc[1])
        course_id_to_index = {course[0]: idx for idx, course in enumerate(courses)}
        conflicts = {"same_slot": defaultdict(list), "same_day": defaultdict(list), "consecutive": defaultdict(list)}
        for student_id, course_ids in student_course_dict.items():
            exams_per_slot = defaultdict(list)
            exams_per_day = defaultdict(list)
            for course_id in course_ids:
                course_idx = course_id_to_index[course_id]
                for slot_idx, assigned in enumerate(schedule[course_idx]):
                    if assigned:
                        full_code = courses[course_idx][3] + courses[course_idx][1]
                        date, slot = time_slots[slot_idx]
                        exams_per_day[date].append((full_code, courses[course_idx][1][0]))
                        exams_per_slot[(date, slot)].append(full_code)

            for (date, slot), courses_in_slot in exams_per_slot.items():
                if len(courses_in_slot) >= 2:
                    conflicts["same_slot"][student_id].append(
                        (date, slot, [course[0] for course in courses_in_slot], 3))

            for date, courses_in_day in exams_per_day.items():
                if len(courses_in_day) >= 2 and not conflicts["same_slot"][student_id]:
                    conflicts["same_day"][student_id].append((date, [course[0] for course in courses_in_day], 2))

            sorted_dates = sorted(exams_per_day.keys())
            for i in range(len(sorted_dates) - 1):
                date1, date2 = sorted_dates[i], sorted_dates[i + 1]
                if (date2 - date1).days == 1:
                    # Get courses for date1 and date2
                    courses_day1 = exams_per_day[date1]
                    courses_day2 = exams_per_day[date2]

                    # Filter courses to include only those in the same year
                    same_year_courses_day1 = [course[0] for course in courses_day1]
                    same_year_courses_day2 = [course[0] for course in courses_day2]

                    # Check if there are any courses in the same year on consecutive days
                    print("same_year_courses_day1: ", courses_day1[0][1])
                    print("same_year_courses_day2: ", courses_day2[0][1])
                    if same_year_courses_day1 and same_year_courses_day2:
                        if courses_day1[0][1] == courses_day2[0][1]:
                            conflicts["consecutive"][student_id].append(
                                (date1, date2, same_year_courses_day1, same_year_courses_day2))
        return conflicts

    def export_to_excel(self, exam_schedule_df, same_day_conflicts_df, same_slot_conflicts_df,
                        consecutive_day_conflicts_df):
        with pd.ExcelWriter("exam_schedule.xlsx") as writer:
            exam_schedule_df.to_excel(writer, sheet_name="Exam Schedule", index=False)
            same_day_conflicts_df.to_excel(writer, sheet_name="Same Day Conflicts", index=False)
            same_slot_conflicts_df.to_excel(writer, sheet_name="Same Slot Conflicts", index=False)
            consecutive_day_conflicts_df.to_excel(writer, sheet_name="Consecutive Day Conflicts", index=False)

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
            for date, courses_in_day, severity in conflicts:
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
            for date, slot, courses_in_slot, severity in conflicts:
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

    def read_data_from_excel(self, file_path):
        try:
            df = pd.read_excel(file_path)
            required_columns = {'code', 'course_number', 'course_name', 'student_number', 'student_name'}
            if not required_columns.issubset(df.columns):
                raise ValueError(f"Excel file must contain columns: {required_columns}")

            # Deduplicate courses and students
            courses = df[['code', 'course_number', 'course_name']].drop_duplicates().values.tolist()
            courses = [(i, course[1], course[2], course[0]) for i, course in enumerate(courses, start=1)]
            students = df[['student_number', 'student_name']].drop_duplicates().values.tolist()
            students = [(i, student[0], student[1]) for i, student in enumerate(students, start=1)]

            student_number_to_id = {student[1]: student[0] for student in students}
            course_code_to_id = {course[3] + course[1]: course[0] for course in
                                 courses}  # Use full code (e.g., PHAR446A)

            # Deduplicate student_courses only for identical courses
            student_courses = []
            seen = defaultdict(set)  # Track (student_id, course_full_code) pairs
            for idx, row in df.iterrows():
                student_id = student_number_to_id.get(row['student_number'])
                course_full_code = row['code'] + row['course_number']  # e.g., PHAR446A
                course_id = course_code_to_id.get(course_full_code)
                if student_id is None or course_id is None:
                    raise ValueError(f"Invalid data at row {idx + 2}: student_number or code not found")
                key = (student_id, course_full_code)
                if key not in seen[student_id]:  # Allow multiple different courses
                    seen[student_id].add(course_full_code)
                    student_courses.append((idx + 1, course_id, student_id))
                else:
                    print(
                        f"Duplicate enrollment found: student {student_id}, course {course_full_code} at row {idx + 2}")

            return courses, students, student_courses
        except FileNotFoundError:
            raise FileNotFoundError(f"Excel file not found at: {file_path}")
        except Exception as e:
            raise Exception(f"Error reading Excel file: {str(e)}")

    def main(self, start_date, end_date, slots_per_day, max_exams_per_day, exclude_days, file):
        print("Starting main...")
        time_slots = self.generate_time_slots(start_date, end_date, slots_per_day, max_exams_per_day, exclude_days)
        print(f"Generated {len(time_slots)} time slots")
        courses, students, student_courses = self.read_data_from_excel(file)
        print(f"Read {len(courses)} courses, {len(students)} students, {len(student_courses)} student_courses")
        conflict_matrix = self.calculate_conflict_matrix(courses, student_courses)
        print("Conflict matrix calculated:", conflict_matrix.shape)
        schedule = self.assign_courses(courses, conflict_matrix, time_slots, student_courses)
        print("Schedule generated:", schedule.shape)
        conflicts = self.analyze_student_conflicts(courses, student_courses, schedule, time_slots)
        print("Conflicts analyzed")
        student_info = {student[0]: (student[1], student[2]) for student in students}
        schedule_df = self.schedule_df(time_slots, courses, schedule)
        print("Schedule DF created")
        same_day_df = self.same_day_conflicts_df(conflicts["same_day"], student_info)
        same_slot_df = self.same_slot_conflicts_df(conflicts["same_slot"], student_info)
        consecutive_df = self.consecutive_day_conflicts_df(conflicts["consecutive"], student_info)
        print("All conflict DFs created")
        return {
            "schedule": self.convert_to_serializable(schedule_df),
            "same_day_conflicts": self.convert_to_serializable(same_day_df),
            "same_slot_conflicts": self.convert_to_serializable(same_slot_df),
            "consecutive_day_conflicts": self.convert_to_serializable(consecutive_df),
        }
