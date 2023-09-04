from fastapi import FastAPI, Request, HTTPException
import logging
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from utils import (app, get_children, get_teachers, get_school_analytics, download_csv,
                   handle_manager_view, get_unregistered_students, get_teachers_by_subjects, get_hobby_pair_analytics)


app.mount("/stylesheets", StaticFiles(directory="stylesheets"), name="static")
templates = Jinja2Templates(directory="templates")

# Consts
USERS = ["Teacher", "Parent", "School Manager"]


# Home page
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    """Render the home page."""
    return templates.TemplateResponse("home.html", {"request": request, "user_types": USERS})


# initialized the first page for each userType
@app.get("/user", response_class=HTMLResponse)
async def user_first_page(request: Request, userType: str):
    """Render first page for a given user type."""
    if userType == "Teacher":
        return templates.TemplateResponse("teacher_subject_page.html", {"request": request})
    elif userType == "Parent":
        return templates.TemplateResponse("parent_first_page.html", {"request": request})
    elif userType == "School Manager":
        return templates.TemplateResponse("school_manager_first_page.html", {"request": request})
    else:
        return HTTPException(status_code=404, detail="User type not found")


# Second page for teacher. Fetch only the students that taking their class.
@app.get("/teacher-action", response_class=HTMLResponse)
async def teacher_page(request: Request, subject: str = None, action: str = None):
    """Handle teacher actions - viewing or downloading data."""
    logging.info(f"fetching students of {subject} class")
    children_data = await get_children()

    # Filter children data based on subject
    if subject:
        children_data = [child for child in children_data if subject.lower() in child.get('hobbies')]
    if action == 'View':
        return templates.TemplateResponse("teacher_view_page.html",
                                          {"request": request, "children": children_data, "subject": subject})
    if action == 'Download':
        return download_csv(files={"children": children_data})
    else:
        return HTTPException(status_code=404, detail="Invalid action")


# Second page for parent. Fetch only the family members.
@app.get("/parent-action", response_class=HTMLResponse)
async def parent_page(request: Request, family: str = None, action: str = None):
    """Handle parent actions - viewing or downloading data."""

    # Get children and teacher data
    children_data = await get_children()
    teacher_data = await get_teachers()

    # Filter children data based on family name
    if family:
        children_data = [child for child in children_data if family.lower() == child.get("last_name").lower()]

    # Get teachers for the given students and subjects
    teachers = get_teachers_by_subjects(children=children_data, teachers=teacher_data)

    if action == 'View':
        return templates.TemplateResponse("parent_view_page.html",
                                          {"request": request,
                                           "children": children_data,
                                           "family": family,
                                           "teachers": teachers})
    if action == 'Download':
        return download_csv(files={"children": children_data, "teachers": teachers.values()})
    else:
        return HTTPException(status_code=404, detail="Invalid action")


# Second page for manager.
@app.get("/manager-action", response_class=HTMLResponse)
async def manager_page(request: Request, action: str = None):
    """Handle school manager actions - viewing or downloading data."""

    # Get children and teacher data
    children_data = await get_children()
    teachers_data = await get_teachers()

    # Get list of unregistered students
    unregistered_students = get_unregistered_students(children_data)
    students_by_subjects, num_of_students = handle_manager_view(children=children_data,
                                                                teachers=teachers_data)

    if action == 'View':
        school_analytics = get_school_analytics(children=children_data, teachers=teachers_data)
        return templates.TemplateResponse("school_manager_page.html",
                                          {"request": request,
                                           "children": students_by_subjects,
                                           "teachers": teachers_data,
                                           "school_analytics": school_analytics,
                                           "unregistered_students": unregistered_students,
                                           "num_of_students": num_of_students,
                                           "hobby_pairs": get_hobby_pair_analytics(children_data)})

    if action == 'Download':
        files_to_download = {"teachers": teachers_data,
                             "children": children_data,
                             "unregistered_students": unregistered_students}
        files_to_download.update(students_by_subjects)
        return download_csv(files=files_to_download)
    else:
        return HTTPException(status_code=404, detail="Invalid action")
