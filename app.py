import pandas as pd
from flask import Flask, render_template, request, jsonify

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
    data = generateExams.main(time_slots)

    return jsonify(data)


@app.route('/re_calculate_conflicts', methods=['POST'])
def re_calculate_conflicts():
    data = request.get_json()
    newSchedule = data.get("scheduleData")
    start_date = datetime.strptime(data.get("start_date"), '%Y-%m-%d')
    end_date = datetime.strptime(data.get("end_date"), '%Y-%m-%d')
    slots = int(data.get("time_periods"))
    weekdays = [int(day) for day in data.get('weekdays')]
    print(start_date, end_date, slots, weekdays)
    generateExams = GenerateExams()

    time_slots = generateExams.generate_time_slots(start_date, end_date, slots, weekdays)

    reCalculate = ReCalculateConflictsExams()
    return jsonify(reCalculate.main(newSchedule, time_slots))


@app.route('/calculate_conflicts', methods=['GET'])
def calculate_conflicts():
    return render_template('calculate_existing.html')


@app.route('/calculate_conflicts_by_excel', methods=['POST'])
def calculate_conflicts_by_excel():
    # Check if the file is present in the request
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    # Read the uploaded Excel file
    df = pd.read_excel(file)

    # # Get additional form data
    start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d')
    end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d')
    slots = int(request.form.get('time_periods'))
    weekdays = request.form.getlist('weekdays[]')
    weekdays = [int(day) for day in weekdays]

    generateExams = GenerateExams()
    time_slots = generateExams.generate_time_slots(start_date, end_date, slots, weekdays)

    df["exam_date"] = df["exam_date"].astype(str)
    newSchedule = df.to_dict(orient="records")
    reCalculate = ReCalculateConflictsExams()
    return jsonify(reCalculate.main(newSchedule, time_slots))


if __name__ == '__main__':
    database.initialize_database()
    app.run(debug=True)
