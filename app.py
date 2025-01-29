from flask import Flask, render_template, request, jsonify, send_file
from generate_exams import GenerateExams
from datetime import datetime

from recalculate_conflicts_exams import ReCalculateConflictsExams

# import json
# from final_code import (
#     create_schedule,
#     get_course_data,
#     analyze_student_conflicts,
#     export_schedule_to_excel
# )

app = Flask(__name__)


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    data = request.get_json()
    start_date = datetime.strptime(data.get("start_date"), '%Y-%m-%d')
    end_date = datetime.strptime(data.get("end_date"), '%Y-%m-%d')
    slots = int(data.get("time_periods"))
    weekdays = [int(day) for day in data.get('weekdays')]

    generateExams = GenerateExams()

    time_slots = generateExams.generate_time_slots(start_date, end_date, slots, weekdays)
    return jsonify(generateExams.main(time_slots))


@app.route('/re_calculate_conflicts', methods=['POST'])
def re_calculate_conflicts():
    data = request.get_json()
    newSchedule = data.get("scheduleData")
    start_date = datetime.strptime(data.get("start_date"), '%Y-%m-%d')
    end_date = datetime.strptime(data.get("end_date"), '%Y-%m-%d')
    slots = int(data.get("time_periods"))
    weekdays = [int(day) for day in data.get('weekdays')]

    generateExams = GenerateExams()

    time_slots = generateExams.generate_time_slots(start_date, end_date, slots, weekdays)

    reCalculate = ReCalculateConflictsExams()

    return jsonify(reCalculate.main(newSchedule, time_slots))

# @app.route('/api/generate-schedule', methods=['POST'])
# def generate_schedule_api():
#     data = request.json
#     start_date = datetime.strptime(data['startDate'], '%Y-%m-%d')
#     end_date = datetime.strptime(data['endDate'], '%Y-%m-%d')
#
#     schedule, slot_assignments, days_dict = create_schedule(start_date, end_date)
#     courses_data = get_course_data()
#
#     # Generate conflict summary
#     conflict_summary = analyze_student_conflicts(courses_data, slot_assignments, days_dict)
#
#     # Format schedule data for frontend
#     schedule_data = []
#     for (date, slot), courses in slot_assignments.items():
#         # Check if courses is a list of tuples or just course codes
#         for course in courses:
#             if isinstance(course, tuple):
#                 course_idx, course_code = course
#             else:
#                 course_code = course  # If it's just the course code
#
#             schedule_data.append({
#                 'date': date.strftime('%Y-%m-%d'),
#                 'slot': str(slot),  # Convert slot to string
#                 'courseCode': str(course_code)  # Convert course code to string
#             })
#
#     # Ensure conflict summary values are JSON serializable
#     if isinstance(conflict_summary, dict):
#         conflict_summary = {
#             'sameDay': len(conflict_summary.get('same_day', [])),
#             'consecutive': len(conflict_summary.get('consecutive', [])),
#             'details': {
#                 'sameDay': list(conflict_summary.get('same_day', [])),
#                 'consecutive': list(conflict_summary.get('consecutive', []))
#             }
#         }
#     else:
#         conflict_summary = {
#             'sameDay': 0,
#             'consecutive': 0,
#             'details': {
#                 'sameDay': [],
#                 'consecutive': []
#             }
#         }
#
#     return jsonify({
#         'schedule': schedule_data,
#         'conflicts': conflict_summary
#     })


# @app.route('/api/move-course', methods=['POST'])
# def move_course_api():
#     data = request.json
#     course_code = data['courseCode']
#     new_date = datetime.strptime(data['newDate'], '%Y-%m-%d')
#     new_slot = int(data['newSlot'])
#
#     # Get current schedule
#     schedule, slot_assignments, days_dict = create_schedule()
#     courses_data = get_course_data()
#
#     # Find and move the course
#     moved = False
#     for (date, slot), courses in list(slot_assignments.items()):
#         for i, course in enumerate(courses):
#             if isinstance(course, tuple):
#                 _, c_code = course
#             else:
#                 c_code = course
#
#             if str(c_code) == str(course_code):
#                 courses.pop(i)
#                 if (new_date, new_slot) not in slot_assignments:
#                     slot_assignments[(new_date, new_slot)] = []
#                 slot_assignments[(new_date, new_slot)].append(course)
#                 moved = True
#                 break
#         if moved:
#             break
#
#     # Recalculate conflicts
#     conflict_summary = analyze_student_conflicts(courses_data, slot_assignments, days_dict)
#
#     # Format the new schedule for frontend
#     schedule_data = []
#     for (date, slot), courses in slot_assignments.items():
#         for course in courses:
#             if isinstance(course, tuple):
#                 _, course_code = course
#             else:
#                 course_code = course
#             schedule_data.append({
#                 'date': date.strftime('%Y-%m-%d'),
#                 'slot': str(slot),
#                 'courseCode': str(course_code)
#             })
#
#     return jsonify({
#         'success': True,
#         'newSchedule': schedule_data,
#         'newConflicts': {
#             'sameDay': len(conflict_summary.get('same_day', [])),
#             'consecutive': len(conflict_summary.get('consecutive', [])),
#             'details': {
#                 'sameDay': list(conflict_summary.get('same_day', [])),
#                 'consecutive': list(conflict_summary.get('consecutive', []))
#             }
#         }
#     })


# @app.route('/api/export-excel', methods=['POST'])
# def export_excel_api():
#     schedule, slot_assignments, days_dict = create_schedule()
#     export_schedule_to_excel(schedule, slot_assignments, get_course_data(), days_dict)
#     return send_file('exam_schedule_7.xlsx')
#

if __name__ == '__main__':
    app.run(debug=True)