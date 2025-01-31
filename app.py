from flask import Flask, render_template, request, jsonify, send_file

from database import database
from generate_exams import GenerateExams
from datetime import datetime

from recalculate_conflicts_exams import ReCalculateConflictsExams

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

if __name__ == '__main__':
    database.initialize_database()
    app.run(debug=True)