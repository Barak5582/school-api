import requests
from requests.auth import HTTPBasicAuth
from fastapi.responses import JSONResponse, FileResponse
from xml.etree import ElementTree as ET
from fastapi import FastAPI
import logging
import matplotlib.pyplot as plt
import base64
from io import BytesIO
import csv
import pandas as pd
import os


app = FastAPI()

USERNAME = 'shadif@nelson-si.com'
PASSWORD = 'J79$Qjnw4&acpM2y'

# Consts
CSVFIELDS = {"children": ['first_name', 'last_name', 'email', 'hobbies'],
             "teachers": ['name', 'email', 'phones', 'subject']}


@app.get("/teachers")
async def get_teachers():
    url = 'https://apigw-pod1.dm-us.informaticacloud.com/t/alfh1gf7rvmitxjlvzgs29.com/GetTeachers'
    response = requests.post(url, auth=HTTPBasicAuth(USERNAME, PASSWORD))

    teachers_list = []

    if response.status_code == 200:
        root = ET.fromstring(response.text)
        for teacher in root.findall('Teacher'):

            name = teacher.find('Name').text
            email = teacher.find('Email').text
            subject = teacher.find("Subject").text

            # Handle multiple phone numbers
            phone_numbers = []
            for phone in teacher.findall('Phone'):
                phone_type = phone.attrib.get('type', 'unknown')
                phone_number = phone.text
                phone_info = {
                     phone_type: phone_number
                }
                phone_numbers.append(phone_info)

            teacher_dict = {
                "name": name,
                "email": email,
                "phones": phone_numbers,
                "subject": subject
            }
            teachers_list.append(teacher_dict)

        return teachers_list
    else:
        return JSONResponse(content={"error": "Could not fetch data"}, status_code=500)


@app.get("/children")
async def get_children():
    logging.info("http request to get all children started")
    url = 'https://apigw-pod1.dm-us.informaticacloud.com/t/alfh1gf7rvmitxjlvzgs29.com/GetChildren'
    response = requests.post(url, auth=HTTPBasicAuth(USERNAME, PASSWORD))

    # initialize new list
    children_list = []

    if response.status_code == 200:
        root = ET.fromstring(response.text)
        for child in root.findall('Child'):
            person_details = child.find('PersonDetails')
            name = person_details.find('Name')
            first_name = name.find('First').text
            last_name = name.find('Last').text
            email = person_details.find('Email').text
            hobbies = [hobby.text for hobby in child.findall('Hobby')]

            child_dict = {
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "hobbies": hobbies
            }
            children_list.append(child_dict)

        return children_list
    else:
        return JSONResponse(content={"error": "Could not fetch data"}, status_code=500)


def get_dict_of_subjects(teachers: dict) -> dict:
    # initialize dict to collect data
    subjects = {}

    # Find all the subjects in school
    for teacher in teachers:
        subjects[teacher.get("subject")] = 0

    return subjects


def get_teachers_by_subjects(children: list, teachers: dict):
    dict_of_subjects = get_dict_of_subjects(teachers)

    for child in children:
        if child.get("hobbies"):
            for sub in child.get('hobbies'):
                dict_of_subjects[sub] += 1

    for teacher in teachers:
        if dict_of_subjects[teacher.get('subject')] > 0:
            dict_of_subjects[teacher.get('subject')] = teacher

    dict_to_return = {}
    for subject, teacher in dict_of_subjects.items():
        if teacher:
            dict_to_return[subject] = teacher

    return dict_to_return


def get_school_analytics(children, teachers):

    class_occupancy = get_dict_of_subjects(teachers)
    print(class_occupancy)

    # count how many students in each class
    for children in children:
        for subject in children.get("hobbies"):
            class_occupancy[subject] += 1

    # Create a plot
    fig, ax = plt.subplots(figsize=(12, 6))
    bars = ax.bar(class_occupancy.keys(), class_occupancy.values())

    # set labels
    ax.set_xticklabels(class_occupancy.keys(), fontsize=12)
    ax.set_yticklabels(ax.get_yticks(), fontsize=12)

    # Add the values inside the bars
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2.0, height / 2, str(int(height)),
                va='center', ha='center', color='white', fontsize=12)

    # Render the plot to a BytesIO object
    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)

    # Encode as base64
    img = base64.b64encode(buffer.read()).decode()

    return img


def handle_manager_view(children: dict = None, teachers: dict = None):
    student_by_sub = get_dict_of_subjects(teachers)

    for subject in student_by_sub:
        student_by_sub[subject] = []

    for subject in student_by_sub:
        for child in children:
            if subject.lower() in child.get('hobbies'):
                student_by_sub[subject].append(child)

    return student_by_sub, teachers, len(children)


def get_unregistered_students(children: dict) -> list:
    unregistered_students = []
    for child in children:
        if not child.get("hobbies"):
            unregistered_students.append(child)
    return unregistered_students


def download_csv(files: dict):
    # for filetype, data in files.items():
    #     filename = f"{filetype}.csv"
    #     with open(filename, 'w', newline='') as csvfile:
    #         fieldnames = CSVFIELDS.get(filetype)
    #         writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    #         writer.writeheader()
    #         for record in data:
    #             writer.writerow(record)
    #
    #     return FileResponse(filename, headers={"Content-Disposition": f"attachment; filename={filename}"})
    with pd.ExcelWriter('school_insights.xlsx', engine='openpyxl') as writer:
        # Loop through each data type to create a DataFrame
        for filetype, data in files.items():
            df = pd.DataFrame(data)

            # Save the DataFrame to the Excel writer object
            df.to_excel(writer, sheet_name=filetype, index=False)

        # Return the Excel file as a download
    return FileResponse(
        'school_insights.xlsx',
        headers={"Content-Disposition": f"attachment; filename=school_insights.xlsx"}
    )

