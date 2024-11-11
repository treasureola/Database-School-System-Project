import mysql.connector as connection
from flask import Flask, session, render_template, redirect, url_for, request, flash
import time, random
from datetime import datetime, date
import re

app = Flask('app')
app.secret_key = 'SECRET_KEY'
letterID = 0
db = connection.connect(
    host="phase2-7.cgi21eqy7g91.us-east-1.rds.amazonaws.com",
    user="admin",
    password="phasetwo7",
    database="integration"
)

####################################################
#                    FUNCTIONS                     #
####################################################

# reconnect to database if to referesh any changes made from another device
def _reconnect():
    global db
    db = connection.connect(
        host="phase2-7.cgi21eqy7g91.us-east-1.rds.amazonaws.com",
        user="admin",
        password="phasetwo7",
        database="integration"
    )

# given a time string, return the start and end time
def _process_time(class_time):
    time_list = class_time.split("-")

    start_time = float(time_list[0][0:2])
    if str(time_list[0][3]) != '0':
        start_time += 0.5

    end_time = float(time_list[1][0:2])
    if str(time_list[1][3]) != '0':
        end_time += 0.5

    return start_time, end_time

# uses the current time to determine the current semester
def _get_curr_semester():
    seasons = {
            'Fall': ['August','September', 'October', 'November', 'December'],
            'Spring': ['January', 'February', 'March', 'April', 'May', 'June']
            }
    
    current_time = datetime.now()
    current_month = current_time.strftime('%B')
    current_year = int(current_time.strftime('%Y'))
    for season in seasons:
      if current_month in seasons[season]:
        return season, current_year
    return 'Invalid input month'

def _get_next_semester():
    seasons = {
            'Spring': ['August','September', 'October', 'November', 'December'],
            'Fall': ['January', 'February', 'March', 'April', 'May', 'June']
            }
    
    current_time = datetime.now()
    current_month = current_time.strftime('%B')
    current_year = int(current_time.strftime('%Y'))

    for season in seasons:
      if current_month in seasons[season]:
        if season == 'Spring':
          current_year += 1
        return season, current_year
    return 'Invalid input month'

def _calendar_map(class_time):
    times = _process_time(class_time)
    hour1 = times[0] - 12
    hour2 = times[1] - 12
    diff = hour2 - hour1

    return hour1, hour2, diff*2+1



def sessionStatus():
    return session['user_id']

def sessionType():
    return session['type']

def checkComplete():
  cursor = db.cursor(dictionary = True)
  cursor.execute("SELECT * FROM applications WHERE status = 'incomplete'")
  apps = cursor.fetchall()
  for i in range(len(apps)):
    app = apps[i]
    if(app["student_id"]!=None and app["semester"]!=None and app["s_year"]!=None and app["degree_type"]!=None and app["interest"]!=None and app["experience"]!=None):
      cursor.execute("UPDATE applications SET status = 'review' WHERE student_id = %s and semester = %s and s_year = %s", (app["student_id"], app["semester"], app["s_year"]))
      db.commit()
      
def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


####################################################
#                WEBSITE FUNCTIONS                 #
####################################################

# Reset the database
@app.route('/reset')
def reset():
  cur = db.cursor(dictionary=True)
  with open('phase2create.sql', 'r') as f:
    sql_scr = f.read()
  sql_c = sql_scr.split(';')
  for c in sql_c:
    cur.execute(c)
    db.commit()
  session.pop('username', None)
  session.pop('user_id', None)
  session.pop('fname', None)
  session.pop('lname', None)
  session.pop('type', None)
  session.clear()

  return redirect('/')




# Commits all the saved registered classes to the database
@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    # Commit data to enrollment table
    if request.method == 'POST':
        cursor = db.cursor(dictionary=True)
        semester = _get_next_semester()
        for cid in session["registration"]:
            cursor.execute("INSERT INTO student_courses (student_id, class_id, grade, csem, cyear) VALUES (%s, %s, 'IP', %s, %s)", (session['user_id'], cid, semester[0], semester[1]))
            db.commit()

        session["registration"] = []
        session.modified = True

        flash("You've successfully registered!", "success")

    return redirect('/register') 

# Route to add a class
@app.route('/add', methods=['GET', 'POST'])
def add():
  if request.method == 'POST':
      _reconnect()

      cursor = db.cursor(dictionary=True)

      # Retrieve form data
      cid = request.form["cid"]
      csem = request.form["csem"]
      cyear = request.form["cyear"]
      course = request.form["course"]
      day = request.form["day_of_week"]

      # 1. Check if class already in currently registered class
      if cid in session["registration"]:
          flash("You've already added that class", "error")
          return redirect('/register')


      # Check if already enrolled previously
      cursor.execute('''SELECT * FROM student_courses s 
      JOIN class_section c ON s.class_id = c.class_id AND s.csem = c.csem AND s.cyear = c.cyear
      JOIN course i ON c.course_id = i.id
      WHERE i.id = %s AND s.student_id = %s AND s.grade != "D" AND s.grade != "F" ''', (course, session['user_id']))
      data = cursor.fetchone()

      if data:
          if data['csem'] == csem and data['cyear'] == cyear:
            message = "You are currently enrolled in " + data['course_name'] + " for this semester"
          else:
            message = "You've already taken " + data['course_name'] +" in " + data['csem'] + " " + str(data['cyear'])
          flash(message, "error")
          return redirect('/register') 

      # Check prereq  
      cursor.execute('''SELECT p.prereq_id FROM class_section c
      JOIN course i ON c.course_id = i.id
      JOIN prerequisite p ON i.id = p.course_id
      WHERE c.class_id = %s''',(course, ))
      ids = cursor.fetchall()

      cursor.execute("SELECT * FROM student_courses s JOIN class_section c ON s.class_id = c.class_id JOIN course i ON c.course_id = i.id WHERE s.student_id = %s GROUP BY i.id", (session['user_id'],))
      taken = cursor.fetchall()
      
      for id in ids:
        # Check if the id appears in taken 
        if id['prereq_id'] not in taken:
          flash("You do not fulfill the prerequisites for this class", "error")
          return redirect('/register') 
        

      # Check schedule conflict
      my_time = request.form["class_time"]
      my_class_time = _process_time(my_time)
      
      print("time: ", my_class_time)

      # Retrieve all class times for currently registering year and semester for each class and check
      for class_id in session["registration"]:
          cursor.execute("SELECT class_time FROM class_section WHERE class_id = %s AND csem = %s \
                          AND cyear = %s", (class_id, csem, cyear))
          other_time = cursor.fetchone()['class_time']
          curr_class_time =  _process_time(other_time)

          if (my_class_time[0] > curr_class_time[0] - 0.5 and my_class_time[0] < curr_class_time[1] + 0.5) or (my_class_time[1] > curr_class_time[0] - 0.5 and my_class_time[1] < curr_class_time[1] + 0.5):
              flash("This class has a time conflict with a class you've already added", "error")
              return redirect('/register') 
        

      # Now we have to check for the classes that already got checked out but for current semester/year
      cursor.execute('''SELECT class_time FROM class_section cs JOIN student_courses e ON cs.class_id = e.class_id AND cs.csem = e.csem AND cs.cyear = e.cyear \
                      WHERE cs.csem = %s AND cs.cyear = %s AND cs.day_of_week = %s AND student_id = %s''', (csem, cyear, day ,session['user_id']))
      time_list = cursor.fetchall()
      for curr_class in time_list:
          curr_class_time = _process_time(curr_class['class_time'])
          print("test: ", curr_class_time)
          if (my_class_time[0] > curr_class_time[0] - 0.5 and my_class_time[0] < curr_class_time[1] + 0.5) or (my_class_time[1] > curr_class_time[0] - 0.5 and my_class_time[1] < curr_class_time[1] + 0.5):
            flash("This class has a time conflict with a class you've already registered for", "error")
            return redirect('/register') 
          

      # If no issue, then add to registered class
      session["registration"].append(cid)
      session.modified = True
      flash("Added class to cart", "success")

  return redirect('/register')

# Drop courses
@app.route('/drop', methods=['GET', 'POST'])
def drop():
    if request.method == 'POST':
        cursor = db.cursor(dictionary=True)
        stud_id = request.form['stud_id']
        cid = request.form["cid"]
        csem = request.form["csem"]
        cyear = request.form["cyear"]

        cursor.execute("DELETE FROM student_courses WHERE student_id = %s AND class_id = %s AND csem = %s AND cyear = %s", (stud_id, cid, csem, cyear))
        db.commit()

        flash("Successfully dropped the class", "success")


    return redirect('/register')

# Remove from registration 
@app.route('/remove', methods=['GET', 'POST'])
def remove():
    if request.method == 'POST':
        session["registration"].remove(request.form["cid"])
        session.modified = True

    return redirect('/register')

@app.route("/update_info", methods=['POST'])
def update_all():
  cursor = db.cursor(dictionary=True)
  user_id = request.form.get('user_id')

  # Check if user exists
  cursor.execute("SELECT * FROM user WHERE user_id = %s", (user_id, ))
  data = cursor.fetchone()

  # Update first name
  fname = request.form['fname']
  if fname != "":
    fname = fname.title()

  # Update last name
  lname = request.form['lname']
  if lname != "":
    lname = lname.title()

  # Update email
  email = request.form['email']
  if email != "":
    if validate_email(email) == False:
      flash("Invalid email. Please use the format: username@domain.com", "error")
      return redirect('/userloggedin')

  # Update phone number
  number = request.form['number']
  if number != "":
    if re.match(r'^\d{3}-\d{3}-\d{4}$', number) == None:
      flash("Invalid phone number. Please use the format: 123-456-7890", "error")
      return redirect('/userloggedin')

  # Update database
  if fname != "" and data['fname'] != fname:
    flash("Successfully updated first name", "success")
    cursor.execute("UPDATE user SET fname = %s WHERE user_id = %s", (fname, user_id))
    db.commit()

  if lname != "" and data['lname'] != lname:
    flash("Successfully updated last name", "success")
    cursor.execute("UPDATE user SET lname = %s WHERE user_id = %s", (lname, user_id))
    db.commit()

  if email != "" and data['email'] != email:
    flash("Successfully updated email", "success")
    cursor.execute("UPDATE user SET email = %s WHERE user_id = %s", (email, user_id))
    db.commit()
    

  if number != "" and data['user_phoneNUM'] != number:
    flash("Successfully updated phone number", "success")
    cursor.execute("UPDATE user SET user_phoneNUM = %s WHERE user_id = %s", (number, user_id))
    db.commit()
    
  return redirect('/userloggedin', message=message)


@app.route("/update_grade", methods=['GET', 'POST'])
def update_grade():
    if request.method == 'POST':
      cursor = db.cursor(dictionary=True)

      grade = str(request.form['grade'])
      student_id = request.form['student'] 
      class_id = request.form['class']
      csem = str(request.form['csem'])
      cyear = str(request.form['cyear'])
  
      cursor.execute("UPDATE student_courses SET grade = %s WHERE student_id = %s AND class_id = %s AND csem = %s AND cyear = %s", (grade, student_id, class_id, csem, cyear))
      db.commit()
      return redirect('/userloggedin')

####################################################
#                    HOME PAGE                     #
####################################################


@app.route('/')
def home_page():
  _reconnect()
  return render_template("home.html", title = 'Home Page', session = session)


####################################################
#                    LOGIN PAGE                    #
####################################################


@app.route('/userlogin', methods=['GET', 'POST'])
def login():
  _reconnect()

  if request.method == "GET":
    return render_template("login.html")

  if request.method == 'POST':

    # Connect to the database
    try:
      cur = db.cursor(dictionary = True)
      uname = (request.form["username"])
      passwrd = (request.form["password"])
    except:
      flash("Error connecting to database. Please try again", "error")
      return render_template('login.html')

    # Check if there's any input:
    if uname == "" or passwrd == "":
        flash("Please enter your username and password", "error")
        return render_template('login.html') 

    # Check if the username and password are correct
    try:
      cur.execute("SELECT username, user_password, user_type, user_id, fname, lname FROM user WHERE username = %s and user_password = %s", (uname, passwrd))
      data = cur.fetchone()
     
      if data:
        session['username'] = data['username']
        session['user_id'] = data['user_id']
        session['fname'] = data['fname']
        session['lname'] = data['lname']
        session['type'] = data['user_type']
        session['registration'] = []
        return redirect('/userloggedin')
      else:
        flash("Incorrect username and password", "error")
    except:
      flash("Error while logging in. Please try again", "error")

  return render_template('login.html')


####################################################
#                   CATALOG PAGE                   #
####################################################

@app.route('/catalog')
def catalog():
  _reconnect()
  
  # Get all departments from classes
  cursor = db.cursor(dictionary=True)
  cursor.execute("SELECT dept_name FROM course GROUP BY dept_name ORDER BY dept_name ASC")
  dept = cursor.fetchall()

  # Store all classes for each depatemtn in a dictionary
  course = {}
  for row in dept:
    cursor.execute("SELECT * FROM course WHERE dept_name = %s", (row["dept_name"],))
    course[row["dept_name"]] = cursor.fetchall()

  # Get all prerequisites
  cursor.execute("SELECT * FROM prerequisite p JOIN course c ON p.prereq_id = c.id ORDER BY c.course_num ASC")    
  prereq = cursor.fetchall()

  logged = False

  if 'user_id' in session:
    logged = True

  user = None
  if logged:
    cursor.execute("SELECT * FROM user WHERE user_id = %s", (session['user_id'],))
    user = cursor.fetchone()

  return render_template('catalog.html', dept=dept, course=course, prereq=prereq, logged=logged, user=user)

####################################################
#                  LOGIN REDIRECT                  #
####################################################

@app.route('/userloggedin', methods=['GET', 'POST'])
def user():
  _reconnect()
  if 'username' in session: 
    #check for the student logging in
    if(session['type'] == 5 or session['type'] == 4):
      return redirect('/studentlogging')
    
    #check for the alumni 
    elif(session['type'] == 2):
      return redirect('/alumnilogging')
    
    #check for admin 
    elif(session['type'] == 0):
      return redirect('/admin')

    #check for applicant 
    elif(session['type'] == 6):
      return redirect('/welcome')

    #check for applicant 
    elif(session['type'] == 7):
      return redirect('/cac')

    #check for faculty advisor
    elif(session['type'] == 1):
      return redirect('/faculty')

   #check for grad secretary 
    elif(session['type'] == 3):
      return redirect('/gradsec')
    
  return redirect('/')

####################################################
#                REGISTRATION PAGE                 #
####################################################

@app.route('/register', methods=['GET', 'POST'])
def register():
    _reconnect()

    # Connect to database
    cursor = db.cursor(dictionary=True)
    semester = _get_next_semester()
    query = "SELECT * FROM class_section cs \
            JOIN course c ON cs.course_id = c.id WHERE \
            cs.csem = %s AND cs.cyear = %s"
    params = [semester[0], semester[1]]

    # Display the courses
    if request.method == 'POST':   # If request = POST, query based on form data (i.e search function)
        dname = request.form["dname"]
        cnum = request.form["cnum"]
        cid = request.form["cid"]
        title = request.form["title"]  

        if dname != "":
            query += " AND c.dept_name LIKE  %s"
            params.append(f"%{dname}%")
        
        if cnum != "":
            query += " AND c.course_num = %s"
            params.append(cnum)

        if cid != "":
            query += " AND cs.class_id = %s"
            params.append(cid)

        if title != "":
            query += " AND c.course_name LIKE %s"
            params.append(f"%{title}%")
       
    query += " ORDER BY c.dept_name, c.course_num"

    cursor.execute(query, params)
    classes = cursor.fetchall()

    cursor.execute("SELECT * FROM class_section c JOIN course i ON c.course_id = i.id WHERE c.csem = %s AND c.cyear = %s", (semester[0], semester[1]))
    bulletin = cursor.fetchall()

    instructor_list = {}
    for each_class in classes:
        cursor.execute("SELECT fname, lname FROM user WHERE user_id = %s", (each_class['faculty_id'],))
        instructor_list[each_class['faculty_id']] = cursor.fetchone()

    cursor.execute("SELECT * FROM prerequisite p JOIN course c ON p.prereq_id = c.id")    
    prereqs = cursor.fetchall()

    renderer = {
        "cid": "Class ID",
        "csem": "Semester",
        "cyear": "Year",
        "day_of_week": "Day of week",
        "class_time": "Class Time",
        "fid": "Instructor",
        "dname": "Department",
        "cnum": "Course Number",
        "class_section": "Class Section",
        "title": "Title",
        "credits": "Credits",
    }
    cursor.execute('''SELECT * FROM student_courses s JOIN class_section c ON s.class_id = c.class_id 
    AND s.csem = c.csem AND s.cyear = c.cyear JOIN course i ON c.course_id = i.id 
    WHERE s.student_id = %s AND s.cyear = %s AND s.csem = %s ORDER BY c.class_time, CASE c.day_of_week 
    WHEN 'M' THEN 1 
    WHEN 'T' THEN 2 
    WHEN 'W' THEN 3 
    WHEN 'R' THEN 4
    ELSE 5 
    END''', (session['user_id'], semester[1], semester[0]))   
    schedule = cursor.fetchall()

    intervals = [("1:00", 1.0),("1:30", 1.5),
                 ("2:00", 2.0),("2:30", 2.5),
                 ("3:00", 3.0),("3:30", 3.5),
                 ("4:00", 4.0),("4:30", 4.5),
                 ("5:00", 5.0),("5:30", 5.5),
                 ("6:00", 6.0),("6:30", 6.5),
                 ("7:00", 7.0),("7:30", 7.5),
                 ("8:00", 8.0),("8:30", 8.5),
                 ("9:00", 9.0),("9:30", 9.5),]
    week = ['M', 'T', 'W', 'R', 'F']

    times = {}
    for row in schedule:
      time = _calendar_map(row['class_time'])
      times[row['class_id']] = [time[0], time[1], time[2], row['day_of_week']]

    cursor.execute("SELECT * FROM student_courses s JOIN class_section c ON s.class_id = c.class_id JOIN course i ON c.course_id = i.id WHERE s.student_id = %s GROUP BY i.id", (session['user_id'],))
    taken = cursor.fetchall()

    return render_template('registration.html', schedule=schedule, renderer=renderer, instructor_list=instructor_list,
                            classes=classes, prereqs=prereqs, session=session, semester=semester, times=times, 
                            intervals=intervals, week=week, taken=taken, bulletin=bulletin)



####################################################
#                  FACULTY PAGE                    #
####################################################


#faculty login 
@app.route('/faculty', methods=['GET', 'POST'])
def faculty():
  if sessionType() == 1:
    _reconnect()

    cur = db.cursor(dictionary = True)
    cur.execute("SELECT * FROM user u JOIN user_type t ON u.user_type = t.id JOIN faculty f ON u.user_id = f.faculty_id WHERE u.user_id = %s", (session['user_id'],))
    data = cur.fetchone()

    cur_sem = _get_curr_semester()
    next_sem = _get_next_semester()

    cur.execute("SELECT DISTINCT csem, cyear FROM student_courses ORDER BY cyear DESC, csem")
    semesters = cur.fetchall()
    
    new_semester = {'csem': next_sem[0], 'cyear': str(next_sem[1])}
    if new_semester not in semesters:
      semesters.append(new_semester)  
      semesters = sorted(semesters, key=lambda x: (-int(x['cyear']), x['csem']))

    cur.execute('''SELECT * FROM class_section c JOIN course i ON c.course_id = i.id 
    JOIN user u ON c.faculty_id = u.user_id WHERE u.user_id = %s''', (session['user_id'],))
    registration = cur.fetchall()

    cur.execute('''SELECT * FROM student_courses s 
    JOIN class_section c ON s.class_id = c.class_id 
    AND s.csem = c.csem AND s.cyear = c.cyear WHERE c.faculty_id = %s''', (session['user_id'],))
    classes = cur.fetchall()

    return render_template('dashboard.html', data=data, cur_sem=cur_sem, next_sem=next_sem, semesters=semesters, 
                           registration=registration, classes=classes)

  else:
    return redirect('/')

@app.route('/class/<class_id>/<csem>/<cyear>', methods=['GET', 'POST'])
def class_page(class_id, csem, cyear):
  cyear = str(cyear)
  _reconnect()

  cur = db.cursor(dictionary = True)
  cur.execute('''SELECT * FROM class_section c JOIN course i ON c.course_id = i.id 
  JOIN user u ON c.faculty_id = u.user_id WHERE u.user_id = %s AND c.class_id = %s AND c.csem = %s AND c.cyear = %s''', 
              (session['user_id'], class_id, csem, cyear))
  course = cur.fetchone()


  cur.execute('''SELECT * FROM student_courses s 
  JOIN class_section c ON s.class_id = c.class_id 
  AND s.csem = c.csem AND s.cyear = c.cyear
  JOIN user u ON s.student_id = u.user_id WHERE c.class_id = %s AND c.csem = %s AND c.cyear = %s''', (class_id, csem, cyear))
  classes = cur.fetchall()
  
  return render_template('class.html', course=course, classes=classes, session=session, csem=csem, cyear=cyear)


#alumni log in
@app.route('/alumnilogging')
def alumnilogging():
    _reconnect()
    if sessionType() == 2:
      cur = db.cursor(dictionary = True)
      cur.execute("SELECT * FROM user u JOIN user_type t ON u.user_type = t.id JOIN alumni a ON u.user_id = a.student_id JOIN degrees d ON a.degree_id = d.degree_id WHERE u.username = %s", (session['username'],))
      data = cur.fetchone()
      db.commit()
      return render_template("alumni.html", title = 'Alumni Logged In', data = data)
    else:
      return redirect('/')


#student log in 
@app.route('/studentlogging')
def studentlogging():
  _reconnect()

  if sessionType() == 4 or sessionType() == 5:
    cur = db.cursor(dictionary = True)
    cur.execute("SELECT * FROM user u JOIN user_type t ON u.user_type = t.id JOIN students s ON u.user_id = s.student_id JOIN degrees d ON s.degree_id = d.degree_id WHERE u.username = %s", (session['username'],))
    data = cur.fetchone()

    cur_sem = _get_curr_semester()
    next_sem = _get_next_semester()

    cur.execute("SELECT DISTINCT csem, cyear FROM student_courses ORDER BY cyear DESC, csem")
    semesters = cur.fetchall()

    new_semester = {'csem': next_sem[0], 'cyear': str(next_sem[1])}
    semesters.append(new_semester)  

    semesters = sorted(semesters, key=lambda x: (-int(x['cyear']), x['csem']))

    cur.execute('''SELECT * FROM student_courses s JOIN class_section c ON s.class_id = c.class_id 
    AND s.csem = c.csem AND s.cyear = c.cyear JOIN course i ON c.course_id = i.id JOIN user u ON c.faculty_id = u.user_id 
    WHERE student_id = %s''', (session['user_id'],))
    registration = cur.fetchall()

    # intervals = [("1:00", 1.0),("1:30", 1.5),
    #               ("2:00", 2.0),("2:30", 2.5),
    #               ("3:00", 3.0),("3:30", 3.5),
    #               ("4:00", 4.0),("4:30", 4.5),
    #               ("5:00", 5.0),("5:30", 5.5),
    #               ("6:00", 6.0),("6:30", 6.5),
    #               ("7:00", 7.0),("7:30", 7.5),
    #               ("8:00", 8.0),("8:30", 8.5),
    #               ("9:00", 9.0),("9:30", 9.5),]
    # week = ['M', 'T', 'W', 'R', 'F']
    # semester = _get_curr_semester()
    # cur.execute('''SELECT * FROM student_courses s JOIN class_section c ON s.class_id = c.class_id 
    #   AND s.csem = c.csem AND s.cyear = c.cyear JOIN course i ON c.course_id = i.id 
    #   WHERE s.student_id = %s AND s.cyear = %s AND s.csem = %s ORDER BY c.class_time, CASE c.day_of_week 
    #   WHEN 'M' THEN 1 
    #   WHEN 'T' THEN 2 
    #   WHEN 'W' THEN 3 
    #   WHEN 'R' THEN 4
    #   ELSE 5 
    #   END''', (session['user_id'], semester[1], semester[0]))   
    # schedule = cur.fetchall()
    
    # times = {}
    # for row in schedule:
    #   time = _calendar_map(row['class_time'])
    #   times[row['class_id']] = [time[0], time[1], time[2], row['day_of_week']]

    #cur.execute("SELECT status FROM student_status WHERE student_id = %s", (session['user_id'],))
    #checksuspended = cur.fetchone()
    #if checksuspended == None:
      #get the students grade
    cur.execute("SELECT grade FROM student_courses WHERE student_id = %s", (session['user_id'],))
    grades = cur.fetchall()
    invalid_grades = ['C', 'D', 'F']
    counter = 0
    for g in grades:
      #print(g)
      if g in invalid_grades:
        #print(g)
        #print(counter)
        counter += 1

    #three grades below a B
    if counter >= 3:
      cur.execute("INSERT into student_status (student_id, status) VALUES (%s, %s)", (session['user_id'], 'Suspended'))
      db.commit()
    else: 
      cur.execute("DELETE from student_status WHERE student_id = %s", (session['user_id'], ))
      db.commit()
        
    cur.execute("SELECT status FROM student_status WHERE student_id = %s", (session['user_id'],))
    suspended = cur.fetchone()
    db.commit()

    return render_template("student.html", title = 'Student Logged In', data = data, suspended = suspended, 
                           registration = registration, semesters = semesters, cur_sem = cur_sem)
  
  else:
    return redirect('/')


#admin log in 
@app.route('/admin')
def admin():
  _reconnect()
  if sessionType() == 0:
    cur = db.cursor(dictionary = True)
    cur.execute("SELECT * FROM user u JOIN user_type t ON u.user_type = t.id WHERE u.username = %s", (session['username'],))
    data = cur.fetchone()
    
    cur.execute("SELECT * FROM user u JOIN faculty f ON u.user_id = f.faculty_id WHERE user_type = %s", (1, ))
    faculty = cur.fetchall()

    cur.execute("SELECT * FROM user u JOIN alumni a ON u.user_id = a.student_id WHERE user_type = %s", (2, ))
    alumni = cur.fetchall()

    cur.execute("SELECT * FROM user WHERE user_type = %s", (3, ))
    grad = cur.fetchall()

    cur.execute("SELECT * FROM user u JOIN students s ON u.user_id = s.student_id WHERE user_type = %s", (4, ))
    master = cur.fetchall()

    cur.execute("SELECT * FROM user u JOIN students s ON u.user_id = s.student_id WHERE user_type = %s", (5, ))
    phd = cur.fetchall()

    cur.execute("SELECT * FROM phd_req WHERE thesisapproved = %s", ('False', ))
    notappr = cur.fetchall()

    return render_template("admin.html", title = 'Admin Logged In', data = data, faculty=faculty, 
                           alumni=alumni, grad=grad, master=master, phd=phd, notappr=notappr)
  else:
    return redirect('/')
  

#grad sec log in 
student_info = list()
@app.route('/gradsec', methods=['GET', 'POST'])
def gs_student_names():
  _reconnect()
  if sessionType() == 3:

    cur = db.cursor(dictionary = True, buffered = True)
    students = list()

    cur.execute("SELECT fname, lname, user_id FROM user WHERE user_type = %s OR user_type = %s", (4, 5))
    students = cur.fetchall()

    cur.execute("SELECT fname, lname, user_id FROM user WHERE user_type = %s", (6,))
    applicants = cur.fetchall()

    cur.execute("SELECT user_id, fname, lname, p_semester, p_year FROM review INNER JOIN user ON user_id = student_id WHERE status = 'seen'")
    reviews = cur.fetchall()

    cur.execute("SELECT user_id, fname, lname, a_semester, a_year FROM admitted INNER JOIN user on user.user_id = admitted.a_id WHERE accept = 'ACCEPT'")
    admits = cur.fetchall()
    
    return render_template("gradsec.html", students=students, applicants = applicants, admits = admits, reviews = reviews)
  
  else:
    return redirect('/')



@app.route('/viewform1/<id>')
def viewform1(id):
  _reconnect()
  if sessionType() == 0:
    cur = db.cursor(dictionary = True)
    cur.execute("SELECT courseID FROM form1answer WHERE student_id = %s", (id,))
    data = cur.fetchall()
    db.commit()

    cur.execute("SELECT * from course")
    courses = cur.fetchall()
    db.commit()

    return render_template("viewform1.html", data = data, courses = courses)

  else:
    return redirect('/')



@app.route('/updateinfo', methods=['GET', 'POST'])
def updateinfo():
  _reconnect()
  #connect to the database
  cur = db.cursor(dictionary = True)

  if request.method == 'POST':
    #update the sql database here
    if((request.form["lname"])):
      cur.execute("UPDATE user SET lname = %s WHERE user_id = %s", ( str((request.form["lname"])), session['user_id']))
      db.commit()

    if((request.form["fname"])):
      cur.execute("UPDATE user SET fname = %s WHERE user_id = %s", ( str((request.form["fname"])), session['user_id']))
      db.commit()

    if((request.form["email"])):
      cur.execute("UPDATE user SET email = %s WHERE user_id = %s", ( str((request.form["email"])), session['user_id']))
      db.commit()

    if((request.form["address"])):
      cur.execute("UPDATE user SET user_address = %s WHERE user_id = %s", ( str((request.form["address"])), session['user_id']))
      db.commit()

    if((request.form["phonenum"])):
      cur.execute("UPDATE user SET user_phoneNUM = %s WHERE user_id = %s", ( str((request.form["phonenum"])), session['user_id']))
      db.commit()
    

    #reset the session variables to change if the first and last name was updated
    cur.execute("SELECT username, user_password, user_id, fname, lname FROM user WHERE user_id = %s", (session['user_id'], ))
    data = cur.fetchone()
    db.commit()
    session['fname'] = data['fname']
    session['lname'] = data['lname']
    return redirect('/')




@app.route('/updategrade/<studID>/<courID>', methods=['GET', 'POST'])
def updategrade(studID, courID):
  _reconnect()
  #connect to the database
  cur = db.cursor(dictionary = True)

  if sessionType() == 0:

    if request.method == 'POST':
      #update grade
      if((request.form["grade"])):
        cur.execute("UPDATE student_courses SET grade = %s WHERE student_id = %s and class_id = %s", ( str((request.form["grade"])), studID, courID))
        db.commit()

    return redirect('/')

  else:
    return redirect('/')





@app.route('/signup', methods=['GET', 'POST'])
def signup():
  _reconnect()
  if request.method == "GET":
    return render_template("signup.html")
    
  if request.method == "POST":
    cur = db.cursor(dictionary = True)
    unm = (request.form["username"])
    passwrd = (request.form["password"])
    fname = (request.form["fname"])
    lname = (request.form["lname"])
    ssn =  (request.form["ssn"])
    email =  (request.form["email"])
    address =  (request.form["address"])
    phone =  (request.form["phone"])
    type = (request.form["dates"])

    if(type == "ms"):
      x = 4
      y = 20
    if(type == "phd"):
      x = 5
      y = 21
    
    while True:
      id = random.randint(10000000, 99999999)
      cur.execute("SELECT user_id FROM user WHERE user_id = %s", (id,))
      if not cur.fetchone():
        break


    cur.execute("SELECT username FROM user WHERE username = %s", (unm, ))
    data = cur.fetchone()
    if(data != None):
      return render_template("userexists.html")

    db.commit()

    db.commit()
    cur.execute("SELECT ssn FROM user WHERE ssn = %s", (ssn, ))
    data = cur.fetchone()
    if(data != None):
      return render_template("userexists.html")

    db.commit()
    cur.execute("SELECT email FROM user WHERE email = %s", (email, ))
    data = cur.fetchone()
    if(data != None):
      return render_template("userexists.html")
      
    cur.execute("INSERT into user (user_id, user_type, fname, lname, username, user_password, user_address, user_phoneNUM, ssn, email) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", (id, 6, fname, lname, unm, passwrd, address, phone, ssn, email))
    db.commit()
    #cur.execute("INSERT into students (student_id, degree_id) VALUES (%s, %s)", (id, y))
    #db.commit()
    #cur.execute("INSERT into need_advisor (student_id) VALUES (%s)", (id, ))
    #db.commit()
    #if(x == 5):
      #cur.execute("INSERT into phd_req (student_id, thesisapproved) VALUES (%s, %s)", (id, 'False'))
      #db.commit()


    cur.execute("SELECT username, user_password, user_id, fname, lname FROM user WHERE username = %s and user_password = %s", (unm, passwrd))
    data = cur.fetchone()
    db.commit()
  
    if data != None :
      session['username'] = data['username']
      session['user_id'] = data['user_id']
      session['fname'] = data['fname']
      session['lname'] = data['lname']
      return redirect('/welcome')





@app.route('/form1', methods=['GET', 'POST'])
def form():
  _reconnect()
  cur = db.cursor(dictionary = True)
  if sessionType() == 4 or sessionType() == 5:
    _reconnect()

    if request.method == "GET":
      _reconnect()
      return render_template("form1.html")

    if request.method == 'POST':
      _reconnect()
      cur = db.cursor(dictionary = True)
      req_courses_ctr = 0
      outside_courses_ctr = 0
      cs_courses_ctr = 0
      cs_credit_hours = 0
      studentid = session['user_id']
      for i in range(100, 122):
        checkboxes = request.form.getlist(str(i))
        for e in checkboxes:
          if(e == "yes"):
            if i == 100 or i == 101 or i == 102:
              req_courses_ctr = req_courses_ctr + 1
            if i == 119 or i == 120 or i == 121:
              outside_courses_ctr = outside_courses_ctr + 1
            if i != 119 or i != 120 or i != 121:
              cs_courses_ctr = cs_courses_ctr + 1
            if i == 120 or i == 121:
                cs_credit_hours += 2
            else:
              cs_credit_hours += 3
        
            


      cur.execute("SELECT * FROM course c JOIN class_section cs ON cs.course_id = c.id JOIN student_courses sc ON sc.class_id = cs.class_id AND sc.csem = cs.csem AND sc.cyear = cs.cyear WHERE sc.student_id = %s", (studentid, ))
      scourses = cur.fetchall()
      for s in scourses:
        if s['id'] == 100 or 101 or 102:
          req_courses_ctr = req_courses_ctr + 1


      degree = list()
      cur.execute("SELECT fname, lname, user_id, user_address, user_phoneNUM, email FROM user WHERE user_id = %s", (studentid, ))
      student_name = cur.fetchall()
      student_info.insert(0, student_name)
      eligible = {'eligible': 'True', 'reason': []}
      student_info.insert(1, eligible)

    # get degree_id
      cur.execute("SELECT degree_id FROM students WHERE student_id = %s", (studentid, ))
      degree = cur.fetchall()
      if not degree:
        degree = 0
      student_info.insert(2, degree[0])


      if(cs_credit_hours < 12):
        student_info[1]['eligible'] = 'False'
        student_info[1]['reason'].append('Less credit hours')
        flash(f'Form Submission Unsuccessful! You have registered for less than 12 credit hours.', category="danger")
        return redirect('/userloggedin')


      if student_info[2]['degree_id'] == 20:
        # check for required courses
        if req_courses_ctr < 3:
            student_info[1]['eligible'] = 'False'
            student_info[1]['reason'].append('Has not taken required courses')
            flash(f'Form Submission Unsuccessful! You have not taken the required courses for your Master Degree', category="danger")
            return redirect('/userloggedin')
           
            

      check = 0
      for i in range(100, 122):
        checkboxes = request.form.getlist(str(i))

        for checkbox in checkboxes:
          if(checkbox == "yes"):
            if (check == 0):
              #cur.execute("DELETE from student_courses WHERE grade = %s and student_id = %s", ('IP', session['user_id'] ))
              #db.commit()
              cur.execute("DELETE from form1answer WHERE student_id = %s", (session['user_id'], ))
              db.commit()
              check +=1

            #cur.execute("SELECT grade FROM student_courses WHERE class_id = %s and student_id = %s", (i,session['user_id']))
            #grade = cur.fetchone()
            #print(grade)
            

            #invalid_grades = ['D', 'F']
            #if grade != None:
              #if grade in invalid_grades:
                  #cur.execute("DELETE from student_courses WHERE class_id = %s", (i, ))
                  #db.commit()
                  #cur.execute("INSERT into student_courses (student_id, class_id, grade) VALUES (%s, %s, %s)", (session['user_id'], i, 'IP'))
                  #db.commit()

            #else:
              #print("reaches the else")
              #cur.execute("INSERT into student_courses (student_id, class_id, grade) VALUES (%s, %s, %s)", (session['user_id'], i, 'IP'))
              #db.commit()

              

            cur.execute("INSERT into form1answer (student_id, courseID) VALUES (%s, %s)", (session['user_id'], i))
            db.commit()

            #cur.execute("SELECT * from student_courses WHERE class_id = %s and student_id = %s", (i,session['user_id']))
            #data = cur.fetchall()
            
    flash(f'Form Submission Successful!', category="danger")
    return redirect('/userloggedin')

  else:
    return redirect('/')
    #return render_template("form1.html")



@app.route('/student_courseslist')
def studentcourse():
  _reconnect()
  if sessionType() == 0:
    cur = db.cursor(dictionary = True)

    cur.execute("SELECT class_id FROM student_courses WHERE student_id = %s", (session['user_id'], ))
    course_id = cur.fetchall()
    db.commit()
    return course_id

  else:
    return redirect('/')





@app.route('/approvethesis/<id>')
def approvethesis(id):
  _reconnect()
  if sessionType() == 0:
    cur = db.cursor(dictionary = True)
    cur.execute("UPDATE phd_req SET thesisapproved = %s WHERE student_id = %s", ('True', id))
    db.commit()
    return redirect('/')
  else:
    return redirect('/')


#beginning of sameen's part

@app.route('/user/<id>/<type>')
def userinfo(id, type):
  _reconnect()
  if sessionType() == 0:
    cur = db.cursor(dictionary = True)

    cur.execute("SELECT * FROM user u JOIN user_type t ON u.user_type = t.id WHERE user_id = %s", (id, ))
    data = cur.fetchone()
    studentcourses = None
    alumnicourses = None
    notappr = None
    suspended = None

    
    if type == '4' or type == '5':
      studentcourses = "student"
      cur.execute("SELECT * FROM phd_req WHERE thesisapproved = %s", ('False', ))
      notappr = cur.fetchall()
      cur.execute("SELECT grade FROM student_courses WHERE student_id = %s", (id,))
      grades = cur.fetchall()
      invalid_grades = ['C', 'D', 'F']
      counter = 0
      for g in grades:
        #print(g)
        if g in invalid_grades:
          #print(g)
          #print(counter)
          counter += 1

      #three grades below a B
      if counter >= 3:
        cur.execute("INSERT into student_status (student_id, status) VALUES (%s, %s)", (id, 'Suspended'))
        db.commit()
      else: 
        cur.execute("DELETE from student_status WHERE student_id = %s", (id, ))
        db.commit()
        
      cur.execute("SELECT status FROM student_status WHERE student_id = %s", (id,))
      suspended = cur.fetchone()
      db.commit()

 

    if type == '2': 
      alumnicourses = "alumni"
      db.commit()


    #advsior: get the advisees, option to view their form 1, see the phd studnets and approve their thesis

    return render_template("userinfo.html", data = data, alumnicourses = alumnicourses, studentcourses = studentcourses, notappr = notappr, suspended = suspended, id=id, type=type)
  
  else:
    return redirect('/')


@app.route('/updateuserinfo/<id>', methods=['GET', 'POST'])
def updateuserinfo(id):
  _reconnect()
  #connect to the database
  cur = db.cursor(dictionary = True)

  if request.method == 'POST':
    #update the sql database here

    if((request.form["lname"])):
      cur.execute("UPDATE user SET lname = %s WHERE user_id = %s", ( str((request.form["lname"])), id))
      db.commit()

    if((request.form["fname"])):
      cur.execute("UPDATE user SET fname = %s WHERE user_id = %s", ( str((request.form["fname"])), id))
      db.commit()

    if((request.form["email"])):
      cur.execute("UPDATE user SET email = %s WHERE user_id = %s", ( str((request.form["email"])), id))
      db.commit()
    if((request.form["address"])):
      cur.execute("UPDATE user SET user_address = %s WHERE user_id = %s", ( str((request.form["address"])), id))
      db.commit()
    if((request.form["phonenum"])):
      cur.execute("UPDATE user SET user_phoneNUM = %s WHERE user_id = %s", ( str((request.form["phonenum"])), id))
      db.commit()


    return redirect('/')



@app.route('/assigned', methods=['GET', 'POST'])
def assigned():
  _reconnect()
  if sessionType() == 0:
    if request.method == "POST":
      cur = db.cursor(dictionary = True)
      student = (int)(request.form["student"])
      advisor = (int)(request.form["advisor"])
      cur.execute("DELETE from student_advisors WHERE studentID = %s ", (student, ))
      db.commit()
      cur.execute("INSERT into student_advisors (studentID, advisorID) VALUES (%s, %s)", (student, advisor))
      db.commit()
      cur.execute("DELETE from need_advisor WHERE student_id = %s ", (student, ))
      return redirect('/')
  else:
    return redirect('/')



@app.route('/assignadvsior')
def assignadvisor():
  _reconnect()
  if sessionType() == 0:
    cur = db.cursor(dictionary = True)

    cur.execute("SELECT fname, lname, user_id from user where user_type = %s", (1, ))
    advisors = cur.fetchall()

    cur.execute("SELECT fname, lname, user_id from user where user_type = %s", (4, ))
    mstudents = cur.fetchall()

    cur.execute("SELECT fname, lname, user_id from user where user_type = %s", (5, ))
    pstudents = cur.fetchall()

    return render_template("assignadvisor.html", advisors = advisors, mstudents = mstudents, pstudents = pstudents)
  
  else:
    return redirect('/')






@app.route('/graduatethestudent/<id>/<type>', methods=['GET', 'POST'])
def graduatethestudent(id, type):
  _reconnect()
  if sessionType() == 0: 
    if request.method == "POST":
      cur = db.cursor(dictionary = True)
      cur.execute("UPDATE user SET user_type = %s WHERE user_id = %s", (2, id))
      db.commit()
      if(type == '4'):
        y = 20
      if(type == '5'):
        y = 21
      cur.execute("INSERT into alumni (student_id, degree_id, semester, grad_year) VALUES (%s, %s, %s, %s)", (id, y, 'Spring', 2023))
      db.commit()
      cur.execute("DELETE from student_advisors WHERE studentID = %s ", (id, ))
      db.commit()
      cur.execute("DELETE from students WHERE student_id = %s ", (id, ))
      db.commit()
      return redirect('/')
  
  else:
    return redirect('/')
    


@app.route('/remove/<id>/<type>', methods=['GET', 'POST'])
def removeuser(id, type):
  _reconnect()
  if sessionType() == 0:
    if request.method == "POST":
      cur = db.cursor(dictionary = True)
      if type == '3': 
        cur.execute("DELETE from user WHERE user_id = %s", (id, ))
        db.commit()
      elif type == '2': 
        cur.execute("DELETE from student_courses WHERE student_id = %s ", (id, ))
        db.commit()
        cur.execute("DELETE from student_status WHERE student_id = %s", (id, ))
        db.commit()
        cur.execute("DELETE from application WHERE student_id = %s", (id, ))
        db.commit()
        cur.execute("DELETE from alumni WHERE student_id = %s", (id, ))
        db.commit()
        cur.execute("DELETE from students WHERE student_id = %s ", (id, ))
        db.commit()
        cur.execute("DELETE from user WHERE user_id = %s", (id, ))
        db.commit()
      elif type == '4' or type == '5': 
        cur.execute("DELETE from student_courses WHERE student_id = %s ", (id, ))
        db.commit()
        cur.execute("DELETE from need_advisor WHERE student_id = %s", (id, ))
        db.commit()
        cur.execute("DELETE from applied_grad WHERE student_id = %s", (id, ))
        db.commit()
        cur.execute("DELETE from application WHERE student_id = %s", (id, ))
        db.commit()
        cur.execute("DELETE from student_status WHERE student_id = %s", (id, ))
        db.commit()
        cur.execute("DELETE from application WHERE student_id = %s", (id, ))
        db.commit()
        cur.execute("DELETE from student_advisors WHERE studentID = %s", (id, ))
        db.commit()
        cur.execute("DELETE from phd_req WHERE student_id = %s", (id, ))
        db.commit()
        cur.execute("DELETE from need_advisor WHERE student_id = %s", (id, ))
        db.commit()
        cur.execute("DELETE from students WHERE student_id = %s ", (id, ))
        db.commit()
        cur.execute("DELETE from user WHERE user_id = %s", (id, ))
        db.commit()
      elif type == '1':
        cur.execute("SELECT studentID FROM student_advisors WHERE advisorID = %s", (id, ))
        students = cur.fetchall()
        for s in students:
          #print(s)
          cur.execute("INSERT into need_advisor (student_id) VALUES (%s)", (s,))
          db.commit()

        cur.execute("DELETE from student_advisors WHERE advisorID = %s", (id, ))
        db.commit()
        cur.execute("DELETE from faculty WHERE faculty_id = %s", (id, ))
        db.commit()
        cur.execute("DELETE from user WHERE user_id = %s", (id, ))
        db.commit()

      return redirect('/')

  else:
    return redirect('/')





@app.route('/addthestudent', methods=['GET', 'POST'])
def addthestudent():
  _reconnect()
  if sessionType() == 0:
    if request.method == "GET":
      return render_template("addstudent.html")
    
    if request.method == "POST":
      cur = db.cursor(dictionary = True)
      unm = (request.form["username"])
      passwrd = (request.form["password"])
      fname = (request.form["fname"])
      lname = (request.form["lname"])
      ssn =  (request.form["ssn"])
      email =  (request.form["email"])
      address =  (request.form["address"])
      phone =  (request.form["phone"])
      type = (request.form["dates"])
      sem = (request.form["semester"])
      admit = (request.form["admityear"])

      if(type == "ms"):
        x = 4
        y = 20
      if(type == "phd"):
        x = 5
        y = 21
    
      while True:
        id = random.randint(10000000, 99999999)
        cur.execute("SELECT user_id FROM user WHERE user_id = %s", (id,))
        if not cur.fetchone():
          break


      cur.execute("SELECT username FROM user WHERE username = %s", (unm, ))
      data = cur.fetchone()
      if(data != None):
        return render_template("userexists.html")

      db.commit()

      db.commit()
      cur.execute("SELECT ssn FROM user WHERE ssn = %s", (ssn, ))
      data = cur.fetchone()
      if(data != None):
        return render_template("userexists.html")

      db.commit()
      cur.execute("SELECT email FROM user WHERE email = %s", (email, ))
      data = cur.fetchone()
      if(data != None):
        return render_template("userexists.html")
      
      cur.execute("INSERT into user (user_id, user_type, fname, lname, username, user_password, user_address, user_phoneNUM, ssn, email) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", (id, x, fname, lname, unm, passwrd, address, phone, ssn, email))
      db.commit()
      cur.execute("INSERT into students (student_id, degree_id, semester, admit_year) VALUES (%s, %s, %s, %s)", (id, y, sem, admit))
      db.commit()
      cur.execute("INSERT into need_advisor (student_id) VALUES (%s)", (id, ))
      db.commit()
      if(x == 5):
        cur.execute("INSERT into phd_req (student_id, thesisapproved) VALUES (%s, %s)", (id, 'False'))
        db.commit()

      return redirect('/')

  else:
    return redirect('/')



@app.route('/applygrad', methods=['GET', 'POST'])
def applygrad():
  _reconnect()
  if sessionType() == 4 or sessionType() == 5:
  #connect to the database
    cur = db.cursor(dictionary = True)
    if request.method == "GET":
      return render_template("applying.html")

    if request.method == "POST":
      type = (request.form["dates"])
      if(type == "ms"):
        x = 4
        y = 20
      if(type == "phd"):
        x = 5
        y = 21
      cur.execute("INSERT into applied_grad (student_id, dtype) VALUES (%s, %s)", (session['user_id'], y))
      db.commit()
      return render_template("applygrad.html")
  else:
    return redirect('/')



@app.route('/coursehist/<id>', methods=['GET', 'POST'])
def coursehist(id):
  _reconnect()
  if sessionType() == 0 or sessionType() == 4 or sessionType() == 5 or sessionType() == 2 or sessionType() == 3:
  #connect to the database
    _reconnect()

    cur = db.cursor(dictionary = True)

    cur.execute("SELECT * FROM students WHERE student_id = %s", (id,))
    check = cur.fetchone()

    if check == None:
      cur.execute("SELECT * FROM user u JOIN user_type t ON u.user_type = t.id JOIN alumni a ON u.user_id = a.student_id JOIN degrees d ON a.degree_id = d.degree_id WHERE u.user_id = %s", (id,))
    else:
      cur.execute("SELECT * FROM user u JOIN user_type t ON u.user_type = t.id JOIN students s ON u.user_id = s.student_id JOIN degrees d ON s.degree_id = d.degree_id WHERE u.user_id = %s", (id,))
    data = cur.fetchone()


  
    #cur.execute("SELECT class_id, grade FROM student_courses WHERE student_id = %s", (id, ))
    #data = cur.fetchall()
    #class_ids = [row['class_id'] for row in data]
    #print(data)
    #cur.execute("SELECT id, course_name, course_num, credit_hours from course")
    #cour = cur.fetchall()
    #db.commit()

    #cur.execute("SELECT c.dept_name, c.id, c.course_num, c.course_name, c.credit_hours FROM course c JOIN class_section cs ON cs.course_id = c.id JOIN student_courses sc ON sc.class_id = cs.class_id WHERE cs.class_id IN ({}) GROUP BY c.id".format(','.join(['%s']*len(class_ids))), class_ids)
    #answer = cur.fetchall()

    cur.execute("SELECT * FROM course c JOIN class_section cs ON cs.course_id = c.id JOIN student_courses sc ON sc.class_id = cs.class_id AND sc.csem = cs.csem AND sc.cyear = cs.cyear WHERE sc.student_id = %s", (id, ))
    courses = cur.fetchall()

    grade_points = 0
    num_courses = 0
    #credits = 0
    cur.execute("SELECT class_id, grade FROM student_courses WHERE student_id = %s", (id, ))
    student_grades = cur.fetchall()
    db.commit()

    #cur.execute("SELECT class_section.class_id, course_id FROM class_section JOIN student_courses ON class_section.class_id = student_courses.class_id WHERE student_courses.student_id = %s", (id,))
    #data2 = cur.fetchall()
    cur_sem = _get_curr_semester()
    next_sem = _get_next_semester()

    cur.execute("SELECT DISTINCT csem, cyear FROM student_courses ORDER BY cyear DESC, csem")
    semesters = cur.fetchall()

    # new_semester = {'csem': next_sem[0], 'cyear': str(next_sem[1])}
    # semesters.append(new_semester)  

    # semesters = sorted(semesters, key=lambda x: (-int(x['cyear']), x['csem']))

    for i in range(len(student_grades)):
      #cur.execute("SELECT credit_hours FROM course JOIN class_section ON course.id = class_section.course_id WHERE class_section.class_id = %s", (student_grades[i]['class_id'], ))
      #course_hours = cur.fetchone()
      #cur.execute("Select course_id from class_section where class_id = %s", (student_grades[i]['class_id'], ))
      #cur.execute("SELECT credit_hours FROM course WHERE id = %s", (student_grades[i]['class_id'], ))
      #course_hours = cur.fetchone()
      #credits += course_hours['credit_hours']
      grade = student_grades[i]['grade'] 
      #num_courses = num_courses + 1
      if grade == 'A':
          grade_points = grade_points + 4
          num_courses = num_courses + 1
      if grade == 'A-':
          grade_points = grade_points + 3.7
          num_courses = num_courses + 1
      if grade == 'B+':
          grade_points = grade_points + 3.3
          num_courses = num_courses + 1
      if grade == 'B':
          grade_points = grade_points + 3
          num_courses = num_courses + 1
      if grade == 'B-':
          grade_points = grade_points + 2.7
          num_courses = num_courses + 1
      if grade == 'C+':
          grade_points = grade_points + 2.3
          num_courses = num_courses + 1
      if grade == 'C':
          grade_points = grade_points + 2
          num_courses = num_courses + 1
      if grade == 'C-':
          grade_points = grade_points + 1.7
          num_courses = num_courses + 1
      if grade == 'F':
          grade_points = grade_points + 0
          num_courses = num_courses + 1
    if num_courses == 0:
      num_courses = 1
    gpa = grade_points / num_courses
    gpa = round(gpa, 2)
    return render_template("coursehist.html", id = id, gpa = gpa, courses = courses, data = data,
                            semesters = semesters, cur_sem = cur_sem, next_sem = next_sem, session=session)
  else:
    return redirect('/')



@app.route('/addfaculty' , methods=['GET', 'POST'])
def addfaculty():
  _reconnect()
  if sessionType() == 0:
    if request.method == "GET":
      return render_template("addfaculty.html")

    if request.method == "POST":
      cur = db.cursor(dictionary = True)
      unm = (request.form["username"])
      passwrd = (request.form["password"])
      fname = (request.form["fname"])
      lname = (request.form["lname"])
      ssn =  (request.form["ssn"])
      email =  (request.form["email"])
      address =  (request.form["address"])
      phone =  (request.form["phone"])
      type = (int)(request.form["type"])
      depart = request.form["depart"]

      count = 0
      inst = 0
      advi = 0
      rev = 0
      for i in range(0, 3):
        checkboxes = request.form.getlist(str(i))
        for e in checkboxes:
          if(e == "yes"):
            count += 1
            if(count == 1):
              inst = 1
            elif(count == 2):
              advi = 1
            elif(count == 3):
              rev = 1




      while True:
        id = random.randint(10000000, 99999999)
        cur.execute("SELECT user_id FROM user WHERE user_id = %s", (id,))
        if not cur.fetchone():
          break
    
      cur.execute("SELECT username FROM user WHERE username = %s", (unm, ))
      data = cur.fetchone()
      if(data != None):
        return render_template("userexists.html")

      db.commit()

      db.commit()
      cur.execute("SELECT ssn FROM user WHERE ssn = %s", (ssn, ))
      data = cur.fetchone()
      if(data != None):
        return render_template("userexists.html")

      db.commit()
      cur.execute("SELECT email FROM user WHERE email = %s", (email, ))
      data = cur.fetchone()
      if(data != None):
        return render_template("userexists.html")
      
      cur.execute("INSERT into user (user_id, user_type, fname, lname, username, user_password, user_address, user_phoneNUM, ssn, email) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", (id, type, fname, lname, unm, passwrd, address, phone, ssn, email))
      db.commit()
      cur.execute("INSERT into faculty (faculty_id, department, instructor, advisor, reviewr) VALUES (%s, %s, %s, %s, %s)", (id, depart, inst, advi, rev))
      db.commit()
      return redirect('/')

  else:
    return redirect('/')


@app.route('/addgradsec' , methods=['GET', 'POST'])
def addgradsec():
  _reconnect()
  if sessionType() == 0:
    if request.method == "GET":
      return render_template("addgradsec.html")

    if request.method == "POST":
      cur = db.cursor(dictionary = True)
      unm = (request.form["username"])
      passwrd = (request.form["password"])
      fname = (request.form["fname"])
      lname = (request.form["lname"])
      ssn =  (request.form["ssn"])
      email =  (request.form["email"])
      address =  (request.form["address"])
      phone =  (request.form["phone"])
      type = (int)(request.form["type"])

      while True:
        id = random.randint(10000000, 99999999)
        cur.execute("SELECT user_id FROM user WHERE user_id = %s", (id,))
        if not cur.fetchone():
          break
    
      cur.execute("SELECT username FROM user WHERE username = %s", (unm, ))
      data = cur.fetchone()
      if(data != None):
        return render_template("userexists.html")

      db.commit()

      db.commit()
      cur.execute("SELECT ssn FROM user WHERE ssn = %s", (ssn, ))
      data = cur.fetchone()
      if(data != None):
        return render_template("userexists.html")

      db.commit()
      cur.execute("SELECT email FROM user WHERE email = %s", (email, ))
      data = cur.fetchone()
      if(data != None):
        return render_template("userexists.html")
      
      cur.execute("INSERT into user (user_id, user_type, fname, lname, username, user_password, user_address, user_phoneNUM, ssn, email) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", (id, type, fname, lname, unm, passwrd, address, phone, ssn, email))
      db.commit()
      return redirect('/')

  else:
    return redirect('/')



@app.route('/addalumni' , methods=['GET', 'POST'])
def addalumni():
  _reconnect()
  if sessionType() == 0:
    if request.method == "GET":
      return render_template("addalumni.html")

    if request.method == "POST":
      cur = db.cursor(dictionary = True)
      unm = (request.form["username"])
      passwrd = (request.form["password"])
      fname = (request.form["fname"])
      lname = (request.form["lname"])
      ssn =  (request.form["ssn"])
      email =  (request.form["email"])
      address =  (request.form["address"])
      phone =  (request.form["phone"])
      type = (int)(request.form["type"])
      degree = (int)(request.form["dates"])
      sem = (request.form["semester"])
      year = (int)(request.form["gradyear"])

      while True:
        id = random.randint(10000000, 99999999)
        cur.execute("SELECT user_id FROM user WHERE user_id = %s", (id,))
        if not cur.fetchone():
          break
    
      cur.execute("SELECT username FROM user WHERE username = %s", (unm, ))
      data = cur.fetchone()
      if(data != None):
        return render_template("userexists.html")

      db.commit()

      db.commit()
      cur.execute("SELECT ssn FROM user WHERE ssn = %s", (ssn, ))
      data = cur.fetchone()
      if(data != None):
        return render_template("userexists.html")

      db.commit()
      cur.execute("SELECT email FROM user WHERE email = %s", (email, ))
      data = cur.fetchone()
      if(data != None):
        return render_template("userexists.html")
      
      cur.execute("INSERT into user (user_id, user_type, fname, lname, username, user_password, user_address, user_phoneNUM, ssn, email) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", (id, type, fname, lname, unm, passwrd, address, phone, ssn, email))
      db.commit()
      cur.execute("INSERT into alumni (student_id, degree_id, semester, grad_year) VALUES (%s, %s, %s, %s)", (id, degree, sem, year))
      db.commit()
      return redirect('/')

  else:
    return redirect('/')





@app.route('/logout')
def logout():
  _reconnect()
  session.pop('username', None)
  session.pop('user_id', None)
  session.pop('fname', None)
  session.pop('lname', None)
  session.pop('type', None)
  session.clear()
  return redirect('/')




#Faculty in department and can review Form 1
#For phD students they have to approve (pass) the phd thesis
#they can view their advisees' transcript but cannot update transcript.


@app.route('/faculty/login', methods=['GET', 'POST'])
def faculty_login():
    _reconnect()
    print(f'method is: ', request.method)


    if request.method == "GET":
        return render_template('faculty_login.html')
            
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        
        
        # try to login user 
        if len(username) < 1 : 
            flash("Username cannot be blank", category="danger")
            return redirect('login')
        elif len(password) < 1: 
            flash("Password cannot be blank", category="danger")
            return redirect('login')
        else:
            try:
                sql = '''SELECT * from user where username=%s AND user_password=%s '''
                
          
                cursor= db.cursor(dictionary=True)
                cursor.execute(sql, (username, password))
                result = cursor.fetchone()
                if result != None: 
                    set_session(user=result)
                    flash(f'Welcome {username}. \n You have been succesfully logged in', category='success')
                    return redirect('dashboard')
                    
                else:
                    flash(f'Username and password do not match', category='danger')
                    return redirect('login')
                
            except connection.Error as e: 
                print(f'Error: {e}')





@app.route('/faculty/dashboard', methods=['GET', 'POST'])
def faculty_dashboard():
  _reconnect()
  if sessionType() == 1:
    if request.method == "GET":
      return render_template('dashboard.html')
      
    if request.method == "POST": 
        user = get_session['user']
        return render_template('dashboard.html',  user=user)

  else:
    return redirect('/')
    



@app.route('/faculty/advisees/')
def faculty_advisees():
  _reconnect()
  if sessionType() == 1:
    if session.get('user_id') == None:
      return redirect(url_for('login'))
      # check if the user is logged in and is a faculty advisor
    
    else:
      return render_template('students.html')
  
  else:
    return redirect('/')


@app.route('/faculty/advisees/phd')
def phd_students():
  _reconnect()
  if sessionType() == 1:
    if session.get('user_id') == None:
      return redirect(url_for('login'))
    # check if the user is logged in and is a faculty advisor
    
    else:
    # get advisor id from login session 
      adv_id = session['user_id']
    # lets write a query to fetch all PhD students that belong to this particular advisor
      query = '''select user.user_id, user.user_type, user.fname, user.lname, user.email, student_advisors.studentID, student_advisors.advisorID, students.student_id, students.degree_id, 
            user_type.id, user_type.name as degree_name
            from user 
            JOIN student_advisors ON  user.user_id = student_advisors.studentID
            JOIN students ON  student_advisors.studentID = students.student_id
            JOIN user_type ON user.user_type = user_type.id
            where student_advisors.advisorID =%s AND user_type.id = 5'''


      cursor= db.cursor(dictionary=True)

      cursor.execute(query,(adv_id,) )
      result =cursor.fetchall()

      return render_template('phd_students.html', students=result)

  else:
    return redirect('/')



@app.route('/faculty/advisees/<transcript_id>')
def faculty_transcript(transcript_id): 
  _reconnect()
  if sessionType() == 1:
    if session.get('user_id') == None:
      return redirect(url_for('login'))
    # check if the user is lgged in and is a faculty advisor
    
    else:
      if transcript_id != None:
        transcript_id = int(transcript_id)
        cursor= db.cursor(dictionary=True)
        cursor.execute("select fname, lname, email from user where user_id = %s", (transcript_id, ))
        userdata = cursor.fetchone()

        query = '''
       SELECT DISTINCT c.dept_name, c.id, c.course_num, c.course_name, c.credit_hours, sc.class_id, sc.grade FROM course c JOIN class_section cs ON cs.course_id = c.id JOIN student_courses sc ON sc.class_id = cs.class_id WHERE sc.student_id = %s
        '''

        
       
        

        cursor.execute(query,(transcript_id,) )
        result =cursor.fetchall()


        grade_points = 0
        num_courses = 0
      #credits = 0
        cursor.execute("SELECT class_id, grade FROM student_courses WHERE student_id = %s", (transcript_id, ))
        student_grades = cursor.fetchall()
        db.commit()

      #cur.execute("SELECT class_section.class_id, course_id FROM class_section JOIN student_courses ON class_section.class_id = student_courses.class_id WHERE student_courses.student_id = %s", (id,))
      #data2 = cur.fetchall()

      

        for i in range(len(student_grades)):
        #cur.execute("SELECT credit_hours FROM course JOIN class_section ON course.id = class_section.course_id WHERE class_section.class_id = %s", (student_grades[i]['class_id'], ))
        #course_hours = cur.fetchone()
        #cur.execute("Select course_id from class_section where class_id = %s", (student_grades[i]['class_id'], ))
        #cur.execute("SELECT credit_hours FROM course WHERE id = %s", (student_grades[i]['class_id'], ))
        #course_hours = cur.fetchone()
        #credits += course_hours['credit_hours']
          grade = student_grades[i]['grade'] 
        #num_courses = num_courses + 1
          if grade == 'A':
            grade_points = grade_points + 4
            num_courses = num_courses + 1
          if grade == 'A-':
            grade_points = grade_points + 3.7
            num_courses = num_courses + 1
          if grade == 'B+':
            grade_points = grade_points + 3.3
            num_courses = num_courses + 1
          if grade == 'B':
            grade_points = grade_points + 3
            num_courses = num_courses + 1
          if grade == 'B-':
            grade_points = grade_points + 2.7
            num_courses = num_courses + 1
          if grade == 'C+':
            grade_points = grade_points + 2.3
            num_courses = num_courses + 1
          if grade == 'C':
            grade_points = grade_points + 2
            num_courses = num_courses + 1
          if grade == 'C-':
            grade_points = grade_points + 1.7
            num_courses = num_courses + 1
          if grade == 'F':
            grade_points = grade_points + 0
            num_courses = num_courses + 1
        if num_courses == 0:
          num_courses = 1
        gpa = grade_points / num_courses
        gpa = round(gpa, 2)


    return render_template('student_transcript.html', transcript=result, userdata = userdata, gpa = gpa)

  else:
    return redirect('/')



@app.route('/faculty/advisees/formone/<user_id>', methods=['GET', 'POST'])
def faculty_form(user_id): 
  _reconnect()
    
  if sessionType() == 1:
    if session.get('user_id') == None:
      return redirect(url_for('login'))
    # check if the user is logged in and is a faculty advisor
    
    else:
      if request.method =="GET":
        if user_id != None:
            user_id = int(user_id)

            query = '''
              SELECT
              user.user_id,  
              user.fname, user.lname, user.email,
              course.id AS class_id,
              course.course_name,
              course.course_num, 
              course.dept_name,
              course.credit_hours,
              phd_req.student_id, phd_req.thesisapproved
            FROM
              user
              JOIN student_advisors ON user.user_id = student_advisors.studentID
              JOIN students ON student_advisors.studentID = students.student_id
              JOIN form1answer ON user.user_id = form1answer.student_id
              JOIN course ON course.id = form1answer.courseID
              JOIN phd_req ON phd_req.student_id = students.student_id

            WHERE
              user.user_id = %s; 
          '''
        
          
            cursor= db.cursor(dictionary=True)

            cursor.execute(query,(user_id,) )
            result =cursor.fetchall()

            q = '''
              SELECT
              user.user_id,  
              phd_req.thesisapproved
            FROM
              user
              JOIN student_advisors ON user.user_id = student_advisors.studentID
              JOIN students ON student_advisors.studentID = students.student_id
              JOIN phd_req ON phd_req.student_id = students.student_id

            WHERE
              user.user_id = %s; 
          '''
            cursor.execute(q,(user_id,) )
            phdapp =cursor.fetchall()

  

            return render_template('review_formone.html', form_one=result, phdapp = phdapp)


      elif request.method == "POST":
      # get the form values 
        

        student= int(request.form['student_id'])
        if request.form['status'] == None:
          flash(f"Please approve to continue", category="danger")
          return render_template('review_formone.html', form_one=result)
        else:
          strstatus = request.form['status']
          if strstatus == "True": 
            status = True
          else:
            status = False
          print(f'student: {student}, thesis: {status}')
          query= "UPDATE phd_req SET thesisapproved = %s WHERE student_id = %s"


          cursor= db.cursor()
          cursor.execute(query, (strstatus, student))


          db.commit()
        # result =cursor.fetchall()


          query = '''
              SELECT
              user.user_id,  
              user.fname, user.lname, user.email,
              course.id AS class_id,
              course.course_name,
              course.course_num, 
              course.dept_name,
              course.credit_hours,
              phd_req.student_id, phd_req.thesisapproved
            FROM
              user
              JOIN student_advisors ON user.user_id = student_advisors.studentID
              JOIN students ON student_advisors.studentID = students.student_id
              JOIN form1answer ON user.user_id = form1answer.student_id
              JOIN course ON course.id = form1answer.courseID
              JOIN phd_req ON phd_req.student_id = students.student_id

            WHERE
              user.user_id = %s; 
          '''
        
         
          
          cursor= db.cursor(dictionary=True)

          cursor.execute(query,(user_id,) )
          result =cursor.fetchall()

          q = '''
              SELECT
              user.user_id,  
              phd_req.thesisapproved
            FROM
              user
              JOIN student_advisors ON user.user_id = student_advisors.studentID
              JOIN students ON student_advisors.studentID = students.student_id
              JOIN phd_req ON phd_req.student_id = students.student_id

            WHERE
              user.user_id = %s; 
          '''
          cursor.execute(q,(user_id,) )
          phdapp =cursor.fetchall()
   
          db.commit()
          flash(f'Student Thesis has been approved!', category="success")

          return render_template('review_formone.html', form_one=result, phdapp = phdapp)
  else:
    return redirect('/')

      


@app.route('/faculty/advisees/formone/masters/<user_id>', methods=['GET', 'POST'])
def faculty_form_masters(user_id): 
  _reconnect()
    
  if sessionType() == 1:
    if session.get('user_id') == None:
      return redirect(url_for('login'))
    # check if the user is logged in and is a faculty advisor
    
    else:
      if request.method =="GET":
        if user_id != None:
            user_id = int(user_id)

            query = '''
              SELECT
              user.user_id,  
              user.fname, user.lname, user.email,
              course.id AS class_id,
              course.course_name,
              course.course_num,
              course.dept_name,
              course.credit_hours
            FROM
              user
              JOIN student_advisors ON user.user_id = student_advisors.studentID
              JOIN students ON student_advisors.studentID = students.student_id
              JOIN form1answer ON user.user_id = form1answer.student_id
              JOIN course ON course.id = form1answer.courseID

            WHERE
              user.user_id = %s; 
          '''
        
          
            cursor= db.cursor(dictionary=True)

            cursor.execute(query,(user_id,) )
            result =cursor.fetchall()
     

            return render_template('review_formone_masters.html', form_one=result)
  else:
    return redirect('/')



@app.route('/faculty/advisees/masters')
def master_students():
  _reconnect()

  if sessionType() == 1:
    if session.get('user_id') == None:
      return redirect(url_for('login'))
    # check if the user is logged in and is a faculty advisor
    
    else:
    # get advisor id from login session 
      adv_id = session['user_id']
    # lets write a query to fetch all PhD students that belong to this particular advisor
      query = '''select user.user_id, user.user_type, user.fname, user.lname, user.email, student_advisors.studentID, student_advisors.advisorID, students.student_id, students.degree_id, 
            user_type.id, user_type.name as degree_name
            from user 
            JOIN student_advisors ON  user.user_id = student_advisors.studentID
            JOIN students ON  student_advisors.studentID = students.student_id
            JOIN user_type ON user.user_type = user_type.id
            where student_advisors.advisorID =%s AND user_type.id = 4'''


      cursor= db.cursor(dictionary=True)

      cursor.execute(query,(adv_id,) )
      result =cursor.fetchall()

      return render_template('master_students.html', students=result)
  else:
      return redirect('/')




@app.route('/student/<student_id>', methods=['GET', 'POST'])
def gs_student_data(student_id):
  _reconnect()
  if request.method == "POST":
    if sessionType() == 3:

      cur = db.cursor(dictionary = True)

      degree = list()

      cur.execute("SELECT fname, lname, user_id, user_address, user_phoneNUM, email FROM user WHERE user_id = %s", (student_id, ))
      student_name = cur.fetchall()
      student_info.insert(0, student_name)
      eligible = {'eligible': 'True', 'reason': []}
      student_info.insert(1, eligible)

    # get degree_id
      cur.execute("SELECT degree_id FROM students WHERE student_id = %s", (student_id, ))
      degree = cur.fetchall()
      if not degree:
        degree = 0
      student_info.insert(2, degree[0])

    # get courses and grades
      cur.execute("SELECT class_id, grade FROM student_courses WHERE student_id = %s", (student_id, ))
      student_grades = cur.fetchall()
      if not student_grades:
        student_grades = list()
      student_info.insert(3, student_grades)

      #db.commit()
    # get gpa and credit hours
    # counters for grades
      grade_points = 0
      total_credit_hours = 0
      num_courses = 0
      bad_grade_ctr = 0
      req_courses_ctr = 0
      outside_courses_ctr = 0
      cs_courses_ctr = 0
      cs_credit_hours = 0

      for i in range(len(student_grades)):
        #cur.execute("SELECT DISTINCT c.dept_name, c.id, c.course_num, c.course_name, c.credit_hours, sc.class_id, sc.grade FROM course c JOIN class_section cs ON cs.course_id = c.id JOIN student_courses sc ON sc.class_id = cs.class_id WHERE sc.student_id = %s", (id, ))
        #courses = cur.fetchall()
        cur.execute("SELECT DISTINCT credit_hours FROM course JOIN class_section ON course.id = class_section.course_id WHERE class_section.class_id = %s", (student_grades[i]['class_id'], ))
        course_hours = cur.fetchone()
 
        
        #db.commit()
        cur.execute("SELECT DISTINCT course_id FROM class_section AS cs WHERE cs.class_id = %s", (student_grades[i]['class_id'], ))
        course_id = cur.fetchone()
        #course_id = c['course_id']



        db.commit()
        if course_id == 100 or course_id == 101 or course_id == 102:
          req_courses_ctr = req_courses_ctr + 1
        if course_id == 119 or course_id == 120 or course_id == 121:
          outside_courses_ctr = outside_courses_ctr + 1
        if course_id != 119 or course_id != 120 or course_id != 121:
          cs_courses_ctr = cs_courses_ctr + 1
          cs_credit_hours = cs_credit_hours + course_hours['credit_hours']
        total_credit_hours = total_credit_hours + course_hours['credit_hours']
        grade = student_grades[i]['grade'] 
        
        if grade == 'A':
          grade_points = grade_points + 4
          num_courses = num_courses + 1
        if grade == 'A-':
          grade_points = grade_points + 3.7
          num_courses = num_courses + 1
        if grade == 'B+':
          grade_points = grade_points + 3.3
          num_courses = num_courses + 1
        if grade == 'B':
          grade_points = grade_points + 3
          num_courses = num_courses + 1
        if grade == 'B-':
          grade_points = grade_points + 2.7
          bad_grade_ctr = bad_grade_ctr + 1
          num_courses = num_courses + 1
        if grade == 'C+':
          grade_points = grade_points + 2.3
          bad_grade_ctr = bad_grade_ctr + 1
          num_courses = num_courses + 1
        if grade == 'C':
          grade_points = grade_points + 2
          bad_grade_ctr = bad_grade_ctr + 1
          num_courses = num_courses + 1
        if grade == 'C-':
          grade_points = grade_points + 1.7
          bad_grade_ctr = bad_grade_ctr + 1
          num_courses = num_courses + 1
        if grade == 'F':
          grade_points = grade_points + 0
          bad_grade_ctr = bad_grade_ctr + 1
          num_courses = num_courses + 1
      if num_courses == 0:
        num_courses = 1
      gpa = grade_points / num_courses
      gpa = round(gpa, 2)
      gpa_dict = {'gpa': gpa}
      total_credit_hours_dict = {'total_credit_hours': total_credit_hours}
      student_info.insert(4, gpa_dict)
      student_info.insert(5, total_credit_hours_dict)
      if bad_grade_ctr >= 3:
        cur.execute("INSERT INTO student_status VALUES (%s, %s)", (student_id, "suspended"))
        gs_all_suspended()

    # check if they've applied for graduation
      gradcheck = 0
      cur.execute("SELECT * FROM applied_grad WHERE student_id = %s", (student_id, ))
      applied = cur.fetchall()
      if not applied:
        student_info[1]['eligible'] = 'False'
        student_info[1]['reason'].append('Has not applied to graduate')

    # requirements for master's students
      if student_info[2]['degree_id'] == 20:
        # check gpa
        if student_info[4]['gpa'] < 3.0:
            student_info[1]['eligible'] = 'False'
            student_info[1]['reason'].append('Has not met GPA requirement')
            gradcheck = 1
        # check credit hours
        if student_info[5]['total_credit_hours'] < 30:
            student_info[1]['eligible'] = 'False'
            student_info[1]['reason'].append('Has not met credit hour requirement')
            gradcheck = 1
        # check for grades below a B
        if bad_grade_ctr > 2:
            student_info[1]['eligible'] = 'False'
            student_info[1]['reason'].append('Has 2+ grades below a B')
            gradcheck = 1
        # check for required courses
        if req_courses_ctr < 3:
            student_info[1]['eligible'] = 'False'
            student_info[1]['reason'].append('Has not taken required courses')
            gradcheck = 1
        # check for outside courses
        if outside_courses_ctr < 2:
            student_info[1]['eligible'] = 'False'
            student_info[1]['reason'].append('Has not taken enough classes outside of CS')
            gradcheck = 1

    # requirements for phd students
      if student_info[2]['degree_id'] == 21:
        # check gpa
        if student_info[4]['gpa'] < 3.5:
            student_info[1]['eligible'] = 'False'
            student_info[1]['reason'].append('Has not met GPA requirement')
            gradcheck = 1
        # check credit hours
        if student_info[5]['total_credit_hours'] < 36:
            student_info[1]['eligible'] = 'False'
            student_info[1]['reason'].append('Has not met credit hour requirement')
            gradcheck = 1
        # check for grades below a B
        if bad_grade_ctr > 1:
            student_info[1]['eligible'] = 'False'
            student_info[1]['reason'].append('Has 1+ grades below a B')
            gradcheck = 1
        # check for 30 credits of CS courses
        if cs_credit_hours < 30:
            student_info[1]['eligible'] = 'False'
            student_info[1]['reason'].append('Has not met CS course credit requirement')
            gradcheck = 1

    # check if thesis is approved for phd 
      if student_info[2]['degree_id'] == 21:
        cur.execute("SELECT thesisapproved FROM phd_req WHERE student_id = %s", (student_id, ))
        approved = cur.fetchall()
        student_info.append(approved)
        if approved[0]['thesisapproved'] == 'False':
          student_info[1]['eligible'] = 'False'
          student_info[1]['reason'].append('Thesis has not been approved')
          gradcheck = 1


      if gradcheck == 1:
        cur.execute("DELETE FROM applied_grad WHERE student_id = %s", (student_id, ))

    # get advisor
      cur.execute("SELECT advisorID FROM student_advisors WHERE studentID = %s", (student_id, ))
      advisor_id = cur.fetchall()



      if not advisor_id:
        advisor_name = [{'fname': "N/A"}]
        student_info.insert(6, advisor_name)
        return render_template ("student_data.html", student_info=student_info)
    
      cur.execute("SELECT fname, lname FROM user WHERE user_id = %s", (advisor_id[0]['advisorID'], ))
      advisor_name = cur.fetchall()
      student_info.insert(6, advisor_name)
    
      cur_sem = _get_curr_semester()
      next_sem = _get_next_semester()

      cur.execute("SELECT DISTINCT csem, cyear FROM student_courses ORDER BY cyear DESC, csem")
      semesters = cur.fetchall()
      
      new_semester = {'csem': next_sem[0], 'cyear': str(next_sem[1])}
      if new_semester not in semesters:
        semesters.append(new_semester)  
        semesters = sorted(semesters, key=lambda x: (-int(x['cyear']), x['csem']))

      cur.execute("SELECT * FROM student_courses s JOIN class_section c ON s.class_id = c.class_id AND s.csem = c.csem AND s.cyear = c.cyear JOIN course i ON c.course_id = i.id WHERE s.student_id = %s ORDER BY c.cyear DESC, c.csem", (student_id, ))
      schedule=cur.fetchall()

      return render_template ("student_data.html", student_info=student_info, student_id = student_id, 
                              cur_sem=cur_sem, next_sem=next_sem, semesters=semesters, schedule=schedule)
  
    else:
      return redirect('/')


@app.route('/graduate/<student_id>')
def gs_graduate(student_id):
  _reconnect()
  if sessionType() == 3:
    data = list()
    data.insert(0, student_id)

    cur = db.cursor(dictionary = True)

    # get degree_id
    cur.execute("SELECT degree_id FROM students WHERE student_id = %s", (student_id, ))
    degree_id = cur.fetchall()
    data.insert(1, degree_id)

    cur.execute("SELECT fname, lname, user_id FROM user WHERE user_id = %s", (student_id, ))
    name = cur.fetchall()
    data.insert(2, name)

    # gets current year
    today = datetime.date.today()
    year = today.year

    cur.execute("INSERT INTO alumni (student_id, degree_id, semester, grad_year) VALUES (%s, %s, %s, %s)", (student_id, data[1][0]['degree_id'], 'Spring', year))
    cur.execute("DELETE FROM students WHERE student_id = %s", (student_id, ))
    cur.execute("UPDATE user SET user_type = %s WHERE user_id = %s", (2, student_id))

    return render_template("graduate.html", data=data)

  else:
    return redirect('/')



@app.route('/all_suspended')
def gs_all_suspended():
  _reconnect()
  if sessionType() == 3:
    cur = db.cursor(dictionary = True)
    suspended_students_names = list()

    cur.execute("SELECT student_id FROM student_status")
    all_suspended = cur.fetchall()

    for x in range(len(all_suspended)):
        cur.execute("SELECT fname, lname FROM user WHERE user_id = %s", (all_suspended[x]['student_id'], ))
        name = cur.fetchall()
        suspended_students_names.append(name)

    return render_template("suspension.html", suspended_students_names=suspended_students_names)
  else:
    return redirect('/')



@app.route('/assign_advisor/<student_id>', methods=['GET', 'POST'])
def gs_assign_advisor(student_id):
  _reconnect()
  if sessionType() == 3:
    cur = db.cursor(dictionary = True)

    if request.method == "POST":
        advisor_id = request.form.get("advisor_id")
        cur.execute("INSERT INTO student_advisors VALUES (%s, %s)", (student_id, advisor_id))

    # get student name
    cur.execute("SELECT fname, lname, user_id, user_address, user_phoneNUM, email FROM user WHERE user_id = %s", (student_id, ))
    student = cur.fetchall()

    # get advisor names
    cur.execute("SELECT fname, lname, user_id FROM user WHERE user_type = %s", (1, ))
    advisors = cur.fetchall()

    return render_template("assign_advisor.html", advisors=advisors, student=student)

  else:
    return redirect('/')


####################################################
#                  APPLICATION                    #
####################################################

@app.route('/welcome')
def welcome():
    _reconnect()
    cursor = db.cursor(dictionary = True)
    
    cursor.execute("SELECT fname FROM user WHERE user_id = %s", (session['user_id'],))
    name = cursor.fetchone()
    print(name)

    cursor.execute("SELECT fname, student_id, semester, s_year FROM applications INNER JOIN user ON applications.student_id = user.user_ID WHERE status = 'review'")
    apps = cursor.fetchall()
    print(apps)

    return render_template("applicant.html", apps = apps, name = name['fname'])

@app.route('/view', methods=['POST', 'GET'])
def view():
 _reconnect()
 cursor = db.cursor(dictionary=True, buffered = True)
 this = session["user_id"]
 cursor.execute("SELECT * FROM user INNER JOIN applications on user_id = student_id where user_id = %s;", (this,))
 data = cursor.fetchall()
 cursor.execute("SELECT semester,s_year FROM applications WHERE student_id = %s", (session["user_id"],))
 just = cursor.fetchone()
 print(just)
 cursor.execute("SELECT * FROM Rapplications WHERE Rstudent_id = %s AND Rsemester = %s AND Rs_year = %s", (session["user_id"], just['semester'], just['s_year']))
 rejec = cursor.fetchone()
 if request.method == "POST": 
    print("this")
    cursor = db.cursor(dictionary=True, buffered = True)
    fee = request.form.getlist('fee')
    fee = fee[0]
    print(fee)
    student = request.form.getlist('student')
    student = student[0]
    print(student)
    cursor.execute("INSERT INTO admitted VALUES (%s,%s,%s,%s,%s,'')", (this, just['semester'],just['s_year'],student,fee))
    db.commit()
    return redirect('/welcome')
 return render_template("view.html", content = data, this = this, rejec = rejec)

@app.route('/application', methods=['GET', 'POST'])
def application():
   _reconnect()
   cursor = db.cursor(dictionary=True) 
   cursor.execute("SELECT * FROM user WHERE user_id = %s", (session['user_id'],))
   info = cursor.fetchone()
   if request.method == 'POST':
       cursor = db.cursor(dictionary=True, buffered = True)
       prior_bac_deg_gpa = request.form["prior_bac_deg_gpa"]
       prior_bac_deg_major = request.form["prior_bac_deg_major"]
       prior_bac_deg_year = request.form["prior_bac_deg_year"]
       prior_bac_deg_university = request.form["prior_bac_deg_university"]
       prior_ms_deg_gpa = request.form["prior_ms_deg_gpa"]
       prior_ms_deg_major = request.form["prior_ms_deg_major"]
       prior_ms_deg_year = request.form["prior_ms_deg_year"]
       prior_ms_deg_university = request.form["prior_ms_deg_university"]
       gre_verbal = request.form["GRE_verbal"]
       gre_year = request.form["GRE_year"]
       gre_quantitative = request.form["GRE_quantitative"]
       gre_advanced_score = request.form["GRE_advanced_score"]
       gre_advanced_subject = request.form["GRE_advanced_subject"]
       toefl_score = request.form["TOEFL_score"]
       toefl_date = request.form["TOEFL_date"]
       interest = request.form["interest"]
       experience = request.form["experience"]
       semester = request.form["semester"]
       degree_type = request.form["degree_type"]
       s_year = request.form["s_year"]
       this = session["user_id"]
       transcript = request.form["transcript"]
       cursor.execute("INSERT INTO applications VALUES ('review', %s, %s, %s, %s, '', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, '', %s, %s, %s, %s,CURDATE(),%s,'not decided')", 
                      (this, semester, s_year, degree_type, prior_bac_deg_gpa, prior_bac_deg_major, prior_bac_deg_year, prior_bac_deg_university, gre_verbal, 
                       gre_year, gre_quantitative, gre_advanced_score, gre_advanced_subject, toefl_score, toefl_date, interest, experience, prior_ms_deg_gpa, prior_ms_deg_major, prior_ms_deg_year, prior_ms_deg_university,transcript))
       db.commit()
      #  cursor.execute("INSERT INTO review (student_id, review_id, p_semester, p_year, rev_rating, deficiency_course, reason_reject, GAS_comment, decision, recom_advisor,status) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s,'submitted')", (this, '', semester,s_year, '', '', '', '', '', ''))
      #  db.commit()
       
       print(111, this)
       print(111, semester)
       print(111, s_year)
       cursor.execute("SELECT student_id, semester,s_year FROM applications WHERE student_id = %s AND semester = %s AND s_year = %s",(this,semester,s_year,))
       those = cursor.fetchone()
       
       print(transcript)
       if transcript == 'Request':
        print("this1")
        school = request.form["schools"]
        print("this2")
        email =  request.form["emails"]
        cursor.execute("INSERT INTO transcript (t_id,t_semester,t_year,school, email,decision) VALUES (%s,%s,%s,%s,%s,'Requested' )", (those['student_id'], those['semester'], those['s_year'], school,email,)) 
        db.commit()

       if transcript == 'Upload':
        school = request.form["schools"]
        email =  request.form["emails"]
        cursor.execute("INSERT INTO transcript (t_id,t_semester,t_year,school, email,decision) VALUES (%s,%s,%s,%s,%s,'Uploaded' )", (those['student_id'], those['semester'], those['s_year'], school,email,)) 
        db.commit()
       cursor.execute("SELECT decision FROM transcript WHERE t_id = %s AND t_semester = %s AND t_year = %s",(this,semester,s_year,))
       decide = cursor.fetchone()
    
       uid = session["user_id"]
       
       rname = request.form["field_rName"]
       affil = request.form["field_affil"]
       email = request.form["field_email"]

       rname1 = request.form["field_rName1"]
       affil1 = request.form["field_affil1"]
       email1 = request.form["field_email1"]

       rname2 = request.form["field_rName2"]
       affil2 = request.form["field_affil2"]
       email2 = request.form["field_email2"]
       

       cursor.execute("INSERT INTO letter (user_id, l_semester,l_year,letter_id,recommenderName, recommenderAffil, recommenderEmail) VALUES (%s,%s,%s, '', %s, %s,%s)", (those['student_id'], those['semester'], those['s_year'], rname, affil, email,)) 
       db.commit()
       cursor.execute("INSERT INTO letter1 (user_id,l_semester,l_year,letter_id,recommenderName1, recommenderAffil1, recommenderEmail1) VALUES (%s,%s,%s, '', %s, %s,%s)", (those['student_id'], those['semester'], those['s_year'], rname1, affil1, email1,)) 
       db.commit()
       cursor.execute("INSERT INTO letter2 (user_id,l_semester,l_year,letter_id,recommenderName2, recommenderAffil2, recommenderEmail2) VALUES (%s,%s,%s, '', %s, %s,%s)", (those['student_id'], those['semester'], those['s_year'], rname2, affil2, email2,)) 
       db.commit()
       cursor.execute("SELECT recommenderName FROM letter INNER JOIN user on user.user_id = letter.user_id WHERE letter.user_id = %s", (uid,))
       data = cursor.fetchone()
       db.commit()
       return render_template("complete.html",data = data,those = those, decide = decide)
   return render_template("application.html", info = info)


@app.route('/infoViewer')
def infoViewer():
  _reconnect()
  if(session['type'] == 6):
    cur = db.cursor(dictionary = True)
    cur.execute("SELECT email, user_address, user_id, user_phoneNUM FROM user WHERE username = %s", (session['username'],))
    data = cur.fetchone()
    return render_template("updateinfo.html", data = data)
  else:
    return redirect('/')

@app.route('/incomplete',  methods = ["POST", "GET"])
def incomplete():
   _reconnect()
   cursor = db.cursor(dictionary=True, buffered = True) 
   cursor.execute("SELECT * FROM user WHERE user_id = %s", (session['user_id'],))
   info = cursor.fetchone()
   if request.method == 'POST':
       cursor = db.cursor(dictionary=True, buffered = True)
       prior_bac_deg_gpa = request.form["prior_bac_deg_gpa"]
       prior_bac_deg_major = request.form["prior_bac_deg_major"]
       prior_bac_deg_year = request.form["prior_bac_deg_year"]
       prior_bac_deg_university = request.form["prior_bac_deg_university"]
       prior_ms_deg_gpa = request.form["prior_ms_deg_gpa"]
       prior_ms_deg_major = request.form["prior_ms_deg_major"]
       prior_ms_deg_year = request.form["prior_ms_deg_year"]
       prior_ms_deg_university = request.form["prior_ms_deg_university"]
       gre_verbal = request.form["GRE_verbal"]
       gre_year = request.form["GRE_year"]
       gre_quantitative = request.form["GRE_quantitative"]
       gre_advanced_score = request.form["GRE_advanced_score"]
       gre_advanced_subject = request.form["GRE_advanced_subject"]
       toefl_score = request.form["TOEFL_score"]
       toefl_date = request.form["TOEFL_date"]
       interest = request.form["interest"]
       experience = request.form["experience"]
       semester = request.form["semester"]
       degree_type = request.form["degree_type"]
       s_year = request.form["s_year"]
       this = session["user_id"]
       transcript = request.form["transcript"]
       cursor.execute("INSERT INTO applications VALUES ('incomplete', %s, %s, %s, %s, '', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, '', %s, %s, %s, %s,CURDATE(),'sent','not decided')", 
                      (this, semester, s_year, degree_type, prior_bac_deg_gpa, prior_bac_deg_major, prior_bac_deg_year, prior_bac_deg_university, gre_verbal, 
                       gre_year, gre_quantitative, gre_advanced_score, gre_advanced_subject, toefl_score, toefl_date, interest, experience, prior_ms_deg_gpa, prior_ms_deg_major, prior_ms_deg_year, prior_ms_deg_university))      
       db.commit()

      #  cursor.execute("SELECT student_id, semester,s_year FROM applications WHERE student_id = %s",(this,))
      #  those = cursor.fetchone()

       print(111, this)
       print(111, semester)
       print(111, s_year)
       cursor.execute("SELECT student_id, semester,s_year FROM applications WHERE student_id = %s AND semester = %s AND s_year = %s",(this,semester,s_year,))
       those = cursor.fetchone()
       
       if transcript == 'Request':
        print("this1")
        school = request.form["schools"]
        print("this2")
        email =  request.form["emails"]
        cursor.execute("INSERT INTO transcript (t_id,t_semester,t_year,school, email,decision) VALUES (%s,%s,%s,%s,%s,'Requested' )", (those['student_id'], those['semester'], those['s_year'], school,email,)) 
        db.commit()

       if transcript == 'Upload':
        school = request.form["schools"]
        email =  request.form["emails"]
        cursor.execute("INSERT INTO transcript (t_id,t_semester,t_year,school, email,decision) VALUES (%s,%s,%s,%s,%s,'Uploaded' )", (those['student_id'], those['semester'], those['s_year'], school,email,)) 
        db.commit()
       cursor.execute("SELECT decision FROM transcript WHERE t_id = %s AND t_semester = %s AND t_year = %s",(this,semester,s_year,))
       decide = cursor.fetchone()

       uid = session["user_id"]
       
       rname = request.form["field_rName"]
       affil = request.form["field_affil"]
       email = request.form["field_email"]

       rname1 = request.form["field_rName1"]
       affil1 = request.form["field_affil1"]
       email1 = request.form["field_email1"]

       rname2 = request.form["field_rName2"]
       affil2 = request.form["field_affil2"]
       email2 = request.form["field_email2"]
       

       cursor.execute("INSERT INTO letter (user_id, l_semester,l_year,letter_id,recommenderName , recommenderEmail, recommenderAffil) VALUES (%s,%s,%s, '', %s, %s,%s)", (those['student_id'], those['semester'], those['s_year'], rname,email, affil,)) 
       db.commit()
       cursor.execute("INSERT INTO letter1 (user_id,l_semester,l_year,letter_id,recommenderName1 , recommenderEmail1, recommenderAffil1) VALUES (%s,%s,%s, '', %s, %s,%s)", (those['student_id'], those['semester'], those['s_year'], rname1,email1, affil1,)) 
       db.commit()
       cursor.execute("INSERT INTO letter2 (user_id,l_semester,l_year,letter_id,recommenderName2, recommenderEmail2 , recommenderAffil2) VALUES (%s,%s,%s, '', %s, %s,%s)", (those['student_id'], those['semester'], those['s_year'], rname2,email2, affil2,)) 
       db.commit()
       return redirect('/welcome')
   return render_template("application.html", info = info)


@app.route('/updateapplication', methods=['GET', 'POST'])
def updateapplication():
   _reconnect()
   cursor = db.cursor(dictionary=True) 
   cursor.execute("SELECT * FROM user WHERE user_id = %s", (session['user_id'],))
   info = cursor.fetchone()
   if request.method == 'POST':
       cursor = db.cursor(dictionary=True, buffered=True)
       prior_bac_deg_gpa = request.form["prior_bac_deg_gpa"]
       prior_bac_deg_major = request.form["prior_bac_deg_major"]
       prior_bac_deg_year = request.form["prior_bac_deg_year"]
       prior_bac_deg_university = request.form["prior_bac_deg_university"]
       prior_ms_deg_gpa = request.form["prior_ms_deg_gpa"]
       prior_ms_deg_major = request.form["prior_ms_deg_major"]
       prior_ms_deg_year = request.form["prior_ms_deg_year"]
       prior_ms_deg_university = request.form["prior_ms_deg_university"]
       gre_verbal = request.form["GRE_verbal"]
       gre_year = request.form["GRE_year"]
       gre_quantitative = request.form["GRE_quantitative"]
       gre_advanced_score = request.form["GRE_advanced_score"]
       gre_advanced_subject = request.form["GRE_advanced_subject"]
       toefl_score = request.form["TOEFL_score"]
       toefl_date = request.form["TOEFL_date"]
       interest = request.form["interest"]
       experience = request.form["experience"]
       semester = request.form["semester"]
       degree_type = request.form["degree_type"]
       s_year = request.form["s_year"]
       this = session["user_id"]
       transcript = request.form["transcript"]
       cursor.execute("UPDATE applications SET status = 'review', student_id = %s, semester = %s, s_year = %s, degree_type = %s, prior_bac_deg_name = '', prior_bac_deg_gpa = %s, prior_bac_deg_major = %s, prior_bac_deg_year = %s, prior_bac_deg_university = %s, GRE_verbal = %s, GRE_year = %s, GRE_quatitative = %s, GRE_advanced_score = %s, GRE_advanced_subject = %s, TOEFL_score = %s, TOEFL_date = %s, interest = %s, experience = %s, prior_ms_deg_name = '', prior_ms_deg_gpa = %s, prior_ms_deg_major = %s, prior_ms_deg_year = %s, prior__deg_university = %s, transcript= 'sent', student = 'not decided' WHERE student_id = %s AND semester = %s AND s_year = %s", 
                    (this, semester, s_year, degree_type, prior_bac_deg_gpa, prior_bac_deg_major, prior_bac_deg_year, prior_bac_deg_university, gre_verbal, 
                    gre_year, gre_quantitative, gre_advanced_score, gre_advanced_subject, toefl_score, toefl_date, interest, experience, prior_ms_deg_gpa, prior_ms_deg_major, prior_ms_deg_year, prior_ms_deg_university,this,semester, s_year))
       db.commit()
       cursor.execute("SELECT student_id, semester,s_year FROM applications WHERE student_id = %s",(this,))
       those = cursor.fetchone()

       if transcript == 'Request':
        school = request.form["schools"]
        email =  request.form["emails"]
        cursor.execute("INSERT INTO transcript (t_id,t_semester,t_year,school, email,decision) VALUES (%s,%s,%s,%s,%s,'Requested' )", (those['student_id'], those['semester'], those['s_year'], school,email,)) 
        db.commit()

       if transcript == 'Upload':
        cursor.execute("INSERT INTO transcript (t_id,t_semester,t_year,school, email,decision) VALUES (%s,%s,%s,%s,%s,'Uploaded' )", (those['student_id'], those['semester'], those['s_year'], '','',)) 
        db.commit()
       cursor.execute("SELECT decision FROM transcript WHERE t_id = %s AND t_semester = %s AND t_year = %s",(this,semester,s_year,))
       decide = cursor.fetchone()

       uid = session["user_id"]
       
       rname = request.form["field_rName"]
       affil = request.form["field_affil"]
       email = request.form["field_email"]

       rname1 = request.form["field_rName1"]
       affil1 = request.form["field_affil1"]
       email1 = request.form["field_email1"]

       rname2 = request.form["field_rName2"]
       affil2 = request.form["field_affil2"]
       email2 = request.form["field_email2"]
       

       cursor.execute("UPDATE letter SET user_id = %s, l_semester = %s, l_year = %s, recommenderName = %s, recommenderAffil = %s, recommenderEmail = %s WHERE user_id = %s AND l_semester = %s AND l_year = %s", (those['student_id'], those['semester'], those['s_year'], rname, affil, email,those['student_id'], those['semester'], those['s_year'],))
       db.commit()
       cursor.execute("UPDATE letter1 SET user_id = %s, l_semester = %s, l_year = %s, recommenderName1 = %s, recommenderAffil1 = %s, recommenderEmail1 = %s WHERE user_id = %s AND l_semester = %s AND l_year = %s", (those['student_id'], those['semester'], those['s_year'], rname1, affil1, email1,those['student_id'], those['semester'], those['s_year'],))
       db.commit()
       cursor.execute("UPDATE letter2 SET user_id = %s, l_semester = %s, l_year = %s,recommenderName2 = %s, recommenderAffil2 = %s, recommenderEmail2 = %s WHERE user_id = %s AND l_semester = %s AND l_year = %s", (those['student_id'], those['semester'], those['s_year'], rname2, affil2, email2,those['student_id'], those['semester'], those['s_year'],))
       db.commit()
       cursor.execute("SELECT recommenderName FROM letter INNER JOIN user on user.user_id = letter.user_id WHERE letter.user_id = %s", (uid,))
       data = cursor.fetchone()
       db.commit()
       return render_template("complete.html",data = data,those = those,decide = decide)
   return render_template("editApp.html", info = info)

@app.route('/updateincomplete',  methods = ["POST", "GET"])
def updateincomplete():
   _reconnect()
   cursor = db.cursor(dictionary=True,buffered = True) 
   cursor.execute("SELECT * FROM user WHERE user_id = %s", (session['user_id'],))
   info = cursor.fetchone()
   if request.method == 'POST':
       cursor = db.cursor(dictionary=True,buffered = True)
       prior_bac_deg_gpa = request.form["prior_bac_deg_gpa"]
       prior_bac_deg_major = request.form["prior_bac_deg_major"]
       prior_bac_deg_year = request.form["prior_bac_deg_year"]
       prior_bac_deg_university = request.form["prior_bac_deg_university"]
       prior_ms_deg_gpa = request.form["prior_ms_deg_gpa"]
       prior_ms_deg_major = request.form["prior_ms_deg_major"]
       prior_ms_deg_year = request.form["prior_ms_deg_year"]
       prior_ms_deg_university = request.form["prior_ms_deg_university"]
       gre_verbal = request.form["GRE_verbal"]
       gre_year = request.form["GRE_year"]
       gre_quantitative = request.form["GRE_quantitative"]
       gre_advanced_score = request.form["GRE_advanced_score"]
       gre_advanced_subject = request.form["GRE_advanced_subject"]
       toefl_score = request.form["TOEFL_score"]
       toefl_date = request.form["TOEFL_date"]
       interest = request.form["interest"]
       experience = request.form["experience"]
       semester = request.form["semester"]
       degree_type = request.form["degree_type"]
       s_year = request.form["s_year"]
       this = session["user_id"]
       transcript = request.form["transcript"]
       cursor.execute("SELECT semester, s_year FROM applications WHERE student_id = %s AND status = 'incomplete'", (this,))
       just = cursor.fetchone()
       justs = []
       for data in just:
        justs.extend(data)
        print(0, data)
        print(4, just)
        cursor.execute("UPDATE applications SET status = 'incomplete', student_id = %s, semester = %s, s_year = %s, degree_type = %s, prior_bac_deg_name = '', prior_bac_deg_gpa = %s, prior_bac_deg_major = %s, prior_bac_deg_year = %s, prior_bac_deg_university = %s, GRE_verbal = %s, GRE_year = %s, GRE_quatitative = %s, GRE_advanced_score = %s, GRE_advanced_subject = %s, TOEFL_score = %s, TOEFL_date = %s, interest = %s, experience = %s, prior_ms_deg_name = '', prior_ms_deg_gpa = %s, prior_ms_deg_major = %s, prior_ms_deg_year = %s, prior__deg_university = %s, transcript= 'sent', student = 'not decided' WHERE student_id = %s AND semester = %s AND s_year = %s", 
                     (this, just['semester'], just['s_year'], degree_type, prior_bac_deg_gpa, prior_bac_deg_major, prior_bac_deg_year, prior_bac_deg_university, gre_verbal, 
                    gre_year, gre_quantitative, gre_advanced_score, gre_advanced_subject, toefl_score, toefl_date, interest, experience, prior_ms_deg_gpa, prior_ms_deg_major, prior_ms_deg_year, prior_ms_deg_university,this,just['semester'], just['s_year'],))
        db.commit()

       cursor.execute("SELECT student_id, semester,s_year FROM applications WHERE student_id = %s AND semester = %s AND s_year = %s",(this,semester,s_year,))
       those = cursor.fetchone()
       if those == None:
        print(this)
       
       if transcript == 'Request':
        print("this1")
        school = request.form["schools"]
        print("this2")
        email =  request.form["emails"]
        cursor.execute("INSERT INTO transcript (t_id,t_semester,t_year,school, email,decision) VALUES (%s,%s,%s,%s,%s,'Requested' )", (those['student_id'], those['semester'], those['s_year'], school,email,)) 
        db.commit()

       if transcript == 'Upload':
        school = request.form["schools"]
        email =  request.form["emails"]
        cursor.execute("INSERT INTO transcript (t_id,t_semester,t_year,school, email,decision) VALUES (%s,%s,%s,%s,%s,'Uploaded' )", (those['student_id'], those['semester'], those['s_year'], school,email,)) 
        db.commit()
       cursor.execute("SELECT decision FROM transcript WHERE t_id = %s AND t_semester = %s AND t_year = %s",(this,semester,s_year,))
       decide = cursor.fetchone()

       uid = session["user_id"]
       
       rname = request.form["field_rName"]
       affil = request.form["field_affil"]
       email = request.form["field_email"]

       rname1 = request.form["field_rName1"]
       affil1 = request.form["field_affil1"]
       email1 = request.form["field_email1"]

       rname2 = request.form["field_rName2"]
       affil2 = request.form["field_affil2"]
       email2 = request.form["field_email2"]
       

       cursor.execute("UPDATE letter SET user_id = %s, l_semester = %s, l_year = %s, recommenderName = %s, recommenderEmail = %s, recommenderAffil = %s WHERE user_id = %s AND l_semester = %s AND l_year = %s", (those['student_id'], those['semester'], those['s_year'], rname,email, affil,those['student_id'], those['semester'], those['s_year'],))
       db.commit()
       cursor.execute("UPDATE letter1 SET user_id = %s, l_semester = %s, l_year = %s, recommenderName1 = %s, recommenderEmail1 = %s, recommenderAffil1 = %s WHERE user_id = %s AND l_semester = %s AND l_year = %s", (those['student_id'], those['semester'], those['s_year'], rname1,email1, affil1,those['student_id'], those['semester'], those['s_year'],))
       db.commit()
       cursor.execute("UPDATE letter2 SET user_id = %s, l_semester = %s, l_year = %s,recommenderName2 = %s, recommenderEmail2 = %s, recommenderAffil2 = %s WHERE user_id = %s AND l_semester = %s AND l_year = %s", (those['student_id'], those['semester'], those['s_year'], rname2,email2, affil2, those['student_id'], those['semester'], those['s_year'],))
       db.commit()
       return redirect('/welcome')
   return render_template("editApp.html", info = info)


@app.route('/complete/<user_id>/<l_semester>/<l_year>',methods = ["POST", "GET"])
def complete(user_id,l_semester,l_year):
  _reconnect()
  if request.method == 'POST':
    cursor = db.cursor(dictionary=True,buffered = True)
    content = request.form["content"]
    content1 = request.form["content1"]
    content2 = request.form["content2"]
    cursor.execute("SELECT decision FROM transcript where t_id = %s AND t_semester = %s AND t_year = %s", (user_id,l_semester,l_year,) )
    upload = cursor.fetchone()
    if upload == None:
      print("this")
    else:
      if upload['decision'] == 'Requested':
        tcontent = request.form["tcontent"]
        cursor.execute("UPDATE transcript SET contents = %s WHERE t_id = %s AND t_semester = %s AND t_year = %s",(tcontent,user_id,l_semester,l_year))
        db.commit()
    
    
    cursor.execute("UPDATE letter SET contents = %s WHERE user_id = %s AND l_semester = %s AND l_year = %s",(content,user_id,l_semester,l_year))
    db.commit()
    cursor.execute("UPDATE letter1 SET contents = %s WHERE user_id = %s AND l_semester = %s AND l_year = %s",(content1,user_id,l_semester,l_year))
    db.commit()
    cursor.execute("UPDATE letter2 SET contents = %s WHERE user_id = %s AND l_semester = %s AND l_year = %s",(content2,user_id,l_semester,l_year))
    db.commit()
    return redirect('/welcome')
  return render_template("complete.html")

@app.route('/editApp/<semester>/<s_year>')
def editApp(semester, s_year):
  _reconnect()
  cursor = db.cursor(dictionary=True)
  print(22, semester)
  print(33, s_year)
  cursor.execute("SELECT * FROM user WHERE user_id = %s", (session['user_id'],))
  info = cursor.fetchone()
  cursor.execute("SELECT * FROM applications WHERE student_id = %s AND semester = %s AND s_year = %s", (session['user_id'], semester, s_year))
  app = cursor.fetchone()
  cursor.execute("SELECT * FROM letter WHERE user_id = %s AND l_semester = %s AND l_year = %s", (session['user_id'], semester, s_year))
  letter = cursor.fetchone()
  cursor.execute("SELECT * FROM letter1 WHERE user_id = %s AND l_semester = %s AND l_year = %s", (session['user_id'], semester, s_year))
  letter1 = cursor.fetchone()
  cursor.execute("SELECT * FROM letter2 WHERE user_id = %s AND l_semester = %s AND l_year = %s", (session['user_id'], semester, s_year))
  letter2 = cursor.fetchone()
  return render_template('editApp.html', info = info, app = app,letter = letter, letter1 = letter1, letter2 = letter2)

@app.route('/reviews')
def reviews():
   _reconnect()
   cursor = db.cursor(buffered = True)

   cursor.execute("SELECT user_id from user where user_type = 6")
   appinfo = cursor.fetchall()
   
   justs = []
   for data in appinfo:
        justs.extend(data)
   cursor.execute("SELECT student_id, semester, s_year FROM applications WHERE (student_id,semester,s_year) NOT IN (SELECT student_id,p_semester,p_year FROM review WHERE student_id = %s AND review_id = %s) AND status ='review'", (justs[0],session["user_id"],))
   infos = cursor.fetchall()
   print(justs)
   return render_template("review.html", applicants = infos)

@app.route('/reviews/<student_id>/<semester>/<s_year>', methods=['GET','POST'])
def review(student_id,semester,s_year):
    _reconnect()
    cursor = db.cursor(buffered = True)
    cursor.execute("SELECT student_id, semester, s_year FROM applications WHERE student_id = %s", (student_id,))
    info = cursor.fetchone()
    cursor.execute("SELECT letter.contents, letter1.contents, letter2.contents FROM letter INNER JOIN letter1 ON letter.user_id = letter1.user_id INNER JOIN letter2 ON letter2.user_id = letter1.user_id WHERE letter.user_id = %s AND letter.l_semester = %s AND letter.l_year = %s AND letter1.user_id = %s AND letter1.l_semester = %s AND letter1.l_year = %s AND letter2.user_id = %s AND letter2.l_semester = %s AND letter2.l_year = %s", (student_id, semester, s_year, student_id, semester, s_year, student_id, semester, s_year,))
    letter = cursor.fetchone()
    if request.method == 'POST':
        cursor = db.cursor(dictionary = True, buffered = True)
        if session["type"] == 7:
          fdecision = request.form.getlist('fdecision')
          fdecision = fdecision[0]
          print(fdecision)
          cursor.execute("UPDATE applications SET status = %s WHERE student_id = %s AND semester = %s AND s_year = %s", (fdecision, student_id,semester,s_year))
          db.commit()
        decision = request.form.getlist('decision')
        decision = decision[0]
        print(decision)
        deficiency_course = request.form["dcourse"]
        reason_reject = request.form['reason']
        GAS_comment = request.form['comment']
        advisor = request.form['radvisor']
        cursor.execute("INSERT INTO review (student_id, review_id, p_semester, p_year, rev_rating, deficiency_course, reason_reject, GAS_comment, decision, recom_advisor,status) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s,'seen')", (student_id, session['user_id'], semester,s_year, "1", deficiency_course, reason_reject, GAS_comment, decision, advisor))
        # cursor.execute("UPDATE review SET student_id = %s, review_id = %s, p_semester = %s, p_year = %s, rev_rating = %s, deficiency_course = %s, reason_reject = %s, GAS_comment = %s, decision = %s, recom_advisor = %s, status = 'seen' WHERE student_id = %s AND p_semester = %s AND p_year = %s", (student_id, session['user_id'], semester,s_year, "1", deficiency_course, reason_reject, GAS_comment, decision, advisor,student_id,semester,s_year))
        db.commit()
        # cursor.execute("UPDATE applications SET status = %s WHERE student_id = %s AND semester = %s AND s_year = %s", (fdecision, student_id,semester,s_year))
        return redirect('/')
    cursor = db.cursor(buffered = True)
    cursor.execute("SELECT * FROM applications WHERE student_id = %s AND semester = %s AND s_year = %s", (student_id,semester,s_year))
    appinfo = cursor.fetchall()
    cursor.execute("SELECT fname, lname FROM user WHERE user_id = %s", (student_id,))
    names = cursor.fetchone()
    info = []
    for data in appinfo:
        info.extend(data)
    info.extend(names)
    print(appinfo)
    print(info)
    return render_template("appreview.html", appinfo = info, names = names, letter = letter)

@app.route('/gsview/<student_id>')
def gsview(student_id):
   _reconnect()
   print(student_id)
   cursor = db.cursor(buffered = True)
   cursor.execute("SELECT * from user INNER JOIN applications ON user_id = student_id WHERE user_type = 6 AND user_id = %s",(student_id,))
   appinfo = cursor.fetchone()
  #  cursor.execute("SELECT letter.content, letter1.content, letter2.content FROM letter INNER JOIN letter1 ON letter.user_id = letter1.user_id INNER JOIN letter2 ON letter2.user_id = letter1.user_id")
  #  data = cursor.fetchall()
   return render_template("gsview.html", appinfo = appinfo)

@app.route('/finalDecision/<student_id>/<semester>/<s_year>', methods = ["POST", "GET"])
def finalDecision(student_id,semester,s_year):
  _reconnect()
  print(1,s_year)
  cursor = db.cursor(dictionary = True, buffered = True)
  this0 = student_id
  this1 = semester
  this2 = s_year
  cursor.execute("SELECT decision FROM transcript WHERE t_id = %s AND t_semester = %s AND t_year = %s", (student_id,semester,s_year,))
  decide = cursor.fetchone()
  print(decide)
  if request.method == "POST": 
    cursor = db.cursor(dictionary=True, buffered = True)
    decision = request.form.getlist('Decision')
    decision = decision[0]
    print(decision)
    # if decide["decision"] == "Requested":
    #   print(decide["decision"])
    #   Transcript = request.form.getlist('Transcript')
    #   Transcript = Transcript[0]
    #   print(Transcript)
    #   cursor.execute("UPDATE applications SET status = %s, transcript = %s WHERE student_id = %s AND semester = %s AND s_year = %s", (decision, Transcript, student_id,semester,s_year))
    #   print(student_id)
    #   db.commit()
    cursor.execute("UPDATE applications SET status = %s, transcript = %s WHERE student_id = %s AND semester = %s AND s_year = %s", (decision, 'Requested', student_id,semester,s_year))
    print(student_id)
    db.commit()
    cursor.execute("SELECT * FROM applications WHERE student_id = %s AND semester = %s AND s_year = %s ", (student_id,semester,s_year))
    data = cursor.fetchone()
    print(2, data)
    print(22, data['degree_type'])
    if decision == 'Reject':
      cursor.execute("INSERT INTO Rapplications VALUES ('Reject', %s, %s, %s, %s, '', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, '', %s, %s, %s, %s,CURDATE(),'sent','not decided')", 
                      (student_id, semester, s_year, data['degree_type'], data['prior_bac_deg_gpa'], data['prior_bac_deg_major'], data['prior_bac_deg_year'], data['prior_bac_deg_university'], '', '', '', '', '', '', '', data['interest'], data['experience'], data['prior_ms_deg_gpa'], data['prior_ms_deg_major'], data['prior_ms_deg_year'], ''))
      db.commit()
      cursor.execute("DELETE FROM applications WHERE student_id = %s AND semester = %s AND s_year = %s AND status = 'Reject'", (student_id,semester,s_year))      
      db.commit()
    cursor.execute("UPDATE review SET status = 'done' WHERE student_id = %s AND p_semester = %s AND p_year = %s", (student_id, semester,s_year))
    db.commit()
    return redirect("/gradsec")
  return render_template("final.html",this0 = this0, this1 = this1, this2 = this2, decide = decide )
  
@app.route('/Decision/<student_id>/<semester>/<s_year>', methods = ["POST", "GET"])
def Decision(student_id,semester,s_year):
  _reconnect()
  cursor = db.cursor(dictionary = True, buffered = True)
  cursor.execute("SELECT student_id, semester, s_year FROM applications WHERE student_id = %s", (student_id,))
  info = cursor.fetchall()
  print(student_id)
  if request.method == "POST": 
    print("this")
    cursor = db.cursor(dictionary=True, buffered = True)
    fee = request.form.getlist('Fee')
    fee = fee[0]
    print(fee)
    student = request.form.getlist('student')
    student = student[0]
    print(student)
    cursor.execute("UPDATE admitted SET accept = 'done' WHERE a_id = %s AND a_semester = %s AND a_year = %s", (student_id,semester,s_year))
    if student == 'ACCEPT':
      cursor.execute("SELECT degree_id FROM degrees WHERE degree_name = 'MS Degree' ")
      one = cursor.fetchone()
      cursor.execute("SELECT degree_id FROM degrees WHERE degree_name = 'PhD Degree' ")
      two = cursor.fetchone()
      if(one['degree_id'] == 20):
        y = 20
        cursor.execute("INSERT into students (student_id, degree_id, admit_year) VALUES (%s, %s, CURDATE())", (student_id, y))
        db.commit()
        cursor.execute("UPDATE user SET user_type = %s WHERE user_id = %s", (4,student_id,))
        db.commit()
      if(one['degree_id'] == 21):
        y = 21
        cursor.execute("INSERT into students (student_id, degree_id, admit_year) VALUES (%s, %s, CURDATE())", (student_id, y))
        db.commit()
        cursor.execute("UPDATE user SET user_type = %s WHERE user_id = %s", (5,student_id,))
        db.commit()
      cursor.execute("INSERT into need_advisor (student_id) VALUES (%s)", (student_id, ))
      db.commit()
      if(one['degree_id'] == 21):
        cursor.execute("INSERT into phd_req (student_id, thesisapproved) VALUES (%s, %s)", (student_id, 'False'))
        db.commit()
      cursor.execute("UPDATE admitted SET accept = 'done' WHERE a_id = %s AND a_semester = %s AND a_year = %s", (student_id,semester,s_year))


    print(student_id)
    db.commit()

    return redirect("/gradsec")
  return render_template("decision.html",info = info )

@app.route('/queryone', methods = ["POST", "GET"])
def queryone():
  _reconnect()
  cursor = db.cursor(dictionary = True, buffered = True)
  cursor.execute("SELECT lname, user_id FROM user where user_type = 6")
  name = cursor.fetchall()
  if request.method == "POST":
    cursor = db.cursor(dictionary = True, buffered = True)
    lname = request.form["lname"]
    ID = request.form["user_id"]
    print(lname,ID)
    cursor.execute("SELECT fname, lname, user_id FROM user WHERE lname = %s OR user_id = %s", (lname,ID,))
    print(lname,ID)
    appinfo = cursor.fetchone()
    if appinfo == None:
      flash("NO RESULTS","error")
      return redirect("/queryone")
    return render_template("queryapp.html", appinfo = appinfo)
  return render_template("query.html", name = name)

@app.route('/queryinfo/<student_id>')
def queryinfo(student_id):
   _reconnect()
   cursor = db.cursor(buffered = True)
   cursor.execute("SELECT * from user INNER JOIN applications ON user_id = student_id WHERE user_type = 6 AND user_id = %s", (student_id,))
   appinfo = cursor.fetchone()
   return render_template("queryinfo.html", appinfo = appinfo)

@app.route('/querytwo', methods = ["POST", "GET"])
def querytwo():
  _reconnect()
  cursor = db.cursor(dictionary = True, buffered = True)
  if request.method == "POST":
    cursor = db.cursor(dictionary = True, buffered = True)
    semester = request.form["semester"]
    year = request.form["year"]
    deg = request.form["degree_type"]
    cursor.execute("SELECT fname, lname,user_id FROM user INNER JOIN applications ON user_id = student_id WHERE semester = %s OR s_year = %s OR degree_type = %s", (semester,year,deg,))
    appinfo = cursor.fetchone()
    if appinfo == None:
      flash("NO RESULTS","error")
      return redirect("/queryone")
    return render_template("queryapp.html", appinfo = appinfo)
  return render_template("query.html", name = name)

@app.route('/querythree', methods = ["POST", "GET"])
def querythree():
  _reconnect()
  cursor = db.cursor(dictionary = True, buffered = True)
  if request.method == "POST":
    cursor = db.cursor(dictionary = True, buffered = True)
    semester = request.form["semester"]
    year = request.form["year"]
    deg = request.form["degree_type"]
    cursor.execute("SELECT fname, lname,user_id FROM user INNER JOIN applications ON user_id = student_id WHERE status = 'Admit' OR status = 'Admit with aid' ")
    appinfo = cursor.fetchone()
    if appinfo == None:
      flash("NO RESULTS","error")
      return redirect("/queryone")
    return render_template("queryapp.html", appinfo = appinfo)
  return render_template("query.html", name = name)

@app.route('/queryfour', methods = ["POST", "GET"])
def queryfour():
  cursor = db.cursor(dictionary = True, buffered = True)
  if request.method == "POST":
    cursor = db.cursor(dictionary = True, buffered = True)
    semester = request.form["semester"]
    year = request.form["year"]
    deg = request.form["degree_type"]
    cursor.execute("SELECT COUNT(user_id) AS Applicants FROM user WHERE user_type = 6")
    appinfo = cursor.fetchone()
    cursor.execute("SELECT COUNT(student_id) AS Applicants FROM applications WHERE status = 'Admit'")
    appinfo1 = cursor.fetchone()
    cursor.execute("SELECT COUNT(student_id) AS Applicants FROM applications WHERE status = 'Reject'")
    appinfo2 = cursor.fetchone()
    cursor.execute("SELECT COUNT(student_id) AS Applicants FROM applications WHERE status = 'Admit with Aid'")
    appinfo3 = cursor.fetchone()
    cursor.execute("SELECT AVG(GRE_verbal) AS Applicants FROM applications")
    appinfo4 = cursor.fetchone()
    cursor.execute("SELECT AVG(GRE_quatitative) AS Applicants FROM applications")
    appinfo5 = cursor.fetchone()
    cursor.execute("SELECT AVG(GRE_advanced_score) AS Applicants FROM applications")
    appinfo6 = cursor.fetchone()
    cursor.execute("SELECT AVG(TOEFL_score) AS Applicants FROM applications")
    appinfo7 = cursor.fetchone()
    if appinfo == None:
      flash("NO RESULTS","error")
      return redirect("/queryone")
    return render_template("queryfour.html", appinfo = appinfo, appinfo1 = appinfo1, appinfo2 = appinfo2,appinfo3 = appinfo3,appinfo4 = appinfo4,appinfo5 = appinfo5,appinfo6 = appinfo6,appinfo7 = appinfo7)
  return render_template("query.html", name = name)

@app.route('/cac')
def cac():
  _reconnect()
  return redirect('/reviews')
  # cursor = db.cursor(buffered = True)
  # cursor.execute("SELECT fname, lname, user_id FROM user WHERE user_type = %s", (6,))
  # applicants = cursor.fetchall()
  # cursor.execute("SELECT user_id, fname, lname, p_semester, p_year FROM review INNER JOIN user on user.user_id = review.review_id")
  # reviews = cursor.fetchall()
  # return render_template("cac.html", applicants = applicants, reviews = reviews)


@app.route('/cacview')
def cacview():
  _reconnect()
  cursor = db.cursor(buffered = True)
  cursor.execute("SELECT user_id from user where user_type = 6")
  info = cursor.fecthall()
  cursor.execute("SELECT * from user INNER JOIN applications ON user_id = student_id WHERE user_id = %s", (info["user_id"],))
  appinfo = cursor.fetchall()
  return render_template("cacview.html", appinfo = appinfo)


app.run(host='0.0.0.0', port=8080)
