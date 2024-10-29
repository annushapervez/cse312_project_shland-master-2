import os.path

from flask import Flask, request, render_template, make_response, abort, redirect, send_from_directory, session, url_for
from pymongo import MongoClient
import json
import bcrypt
import secrets
import hashlib
import sys
from bson import ObjectId
import time
from flask_socketio import SocketIO, join_room, leave_room, send, emit
import random
from string import ascii_uppercase

'''
Resources:
https://testdriven.io/tips/e3ecc90d-0612-4d48-bf51-2323e913e17b/#:~:text=Flask%20automatically%20creates%20a%20static,.0.1%3A5000%2Flogo.

'''

# DB AND ALLOWED IMAGE SET UP -----------------------------------------
mongo_client = MongoClient("mongodb://mongo:27017")  # Docker testing
# mongo_client = MongoClient("mongodb://localhost:27017")  # local testing
db = mongo_client["cse312"]
user_collection = db["users"]
post_collection = db["posts"]
quiz_collection = db["quiz"]
ans_collection = db["answers"]

# print('hello, printing mongo collections (local testing)')
# print(db.list_collection_names())

# are we still using this?
allowed_images = ["eagle.jpg", "flamingo.jpg", "apple.jpg", "quiztime.jpg"]
UPLOADS = 'uploads'

# create instance of the class
# __name__ is convenient shortcut to pass application's module/package
app = Flask(__name__, template_folder='public/templates')
app.config['SECRET_KEY'] = 'asdfghj'  # keep in order to use sessions
socketio = SocketIO(app)

app.config['UPLOADS'] = UPLOADS
os.makedirs(app.config['UPLOADS'], exist_ok=True)

print("Checking for 'uploads' directory...")

if os.path.exists('uploads') and os.path.isdir('uploads'):
    print("The 'uploads' directory exists.")
else:
    print("The 'uploads' directory does not exist or is not a directory.")


# HELPER FUNCS --------------------------------------------------------
def escape_html(message):
    escaped_message = message.replace("&", "&amp;")
    escaped_message = escaped_message.replace(">", "&gt;")
    escaped_message = escaped_message.replace('"', "&quot;")
    escaped_message = escaped_message.replace("'", "&#39")
    escaped_message = escaped_message.replace("<", "&lt;")

    return escaped_message


def grade_answer(questionId, answerId):
    """
    grade_answer: updates answer record with grade and outputs int 1 (correct) or 0 (incorrect)
    questionId: ObjectId corresponding to the record of the question being answered
    answerId: ObjectId corresponding to the record of the answer being graded
    """

    q_record = quiz_collection.find_one({"_id": questionId})
    a_record = ans_collection.find_one({"_id": answerId})
    grade = 0

    if q_record and a_record:
        correct = q_record["correct_answer"]
        user_choice = a_record["user_choice"]
        if user_choice == correct:
            grade = 1

        ans_collection.update_one({"_id": answerId}, {"$set": {"grade": grade}})

    return grade


def generate_filename(filename):
    timestamp = str(int(time.time()))
    alphabet = 'abcdefghijklmnopqrstuvwxyz'
    capAlpha = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    randomStr = ''.join(random.choices(alphabet + capAlpha, k=5))
    filename, file_extension = os.path.splitext(filename)
    uniqueName = f"{timestamp}_{randomStr}{file_extension}"
    return uniqueName


# PATHS (TEMPLATE/IMAGE RENDERING) ------------------------------------

# CODE FOR WEBSOCKETS -------------------------------

quizQ = {}
rooms = {}

def generate_unique_code(length):
    code = ''
    while True:
        for _ in range(length):
            code += random.choice(ascii_uppercase)
        if code not in rooms:
            break
    return code


# route() func tells Flask what URL should trigger the function
@app.route('/', methods=['GET'])
@app.route('/index', methods=['GET'])
@app.route('/index.html', methods=['GET'])
def index():
    session.clear()
    if request.headers.get("Cookie") is not None:
        # print("cookies exist", file=sys.stderr)
        if "auth_token" in request.headers.get("Cookie"):
            # print("name is not guest", file=sys.stderr)

            cookie_kvps = {}
            cookies_as_list = request.headers.get("Cookie").split(";")
            for lines in cookies_as_list:
                cookie_kvp = lines.split("=")
                cookie_kvps[cookie_kvp[0].strip()] = cookie_kvp[1].strip()

            existing_auth_token = cookie_kvps["auth_token"]

            hashed_token = hashlib.sha256(existing_auth_token.encode("utf-8")).hexdigest()

            user = user_collection.find_one({"auth_token": hashed_token})

            if user:
                username = user["username"]
            else:
                username = "Guest"
        else:
            username = "Guest"
    else:
        # print("user is guest", file=sys.stderr)
        username = "Guest"

    posts = db.posts.find()
    quiz = db.quiz.find()

    response = make_response(render_template('index.html', name=username, posts=posts, quiz=quiz))
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Type"] = "text/html; charset=utf-8"
    # response.headers["Content-Length"] = str(len(open("public/templates/index.html").read()))

    return response


@app.route('/style', methods=['GET'])
@app.route('/style.css', methods=['GET'])
def style():
    response = make_response(render_template('style.css'))
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Type"] = "text/css; charset=utf-8"
    # response.headers["Content-Length"] = str(len(open("public/templates/style.css").read()))

    return response


@app.route('/quiz.css', methods=['GET'])
def quiz_style():
    response = make_response(render_template('quiz.css'))
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Type"] = "text/css; charset=utf-8"
    # response.headers["Content-Length"] = str(len(open("public/templates/style.css").read()))

    return response


@app.route('/grades.css', methods=['GET'])
def grades_style():
    response = make_response(render_template('grades.css'))
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Type"] = "text/css; charset=utf-8"

    return response


@app.route('/javascript', methods=['GET'])
@app.route('/functions.js', methods=['GET'])
def javascript():
    response = make_response(render_template('functions.js'))
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Type"] = "text/javascript; charset=utf-8"
    # response.headers["Content-Length"] = str(len(bytes(open("public/templates/functions.js").read(), 'utf-8')))

    return response

@app.route('/room.js', methods=['GET'])
def room_javascript():
    response = make_response(render_template('room.js'))
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Type"] = "text/javascript; charset=utf-8"
    # response.headers["Content-Length"] = str(len(bytes(open("public/templates/functions.js").read(), 'utf-8')))

    return response

@app.route('/quiz.js', methods=['GET'])
def quiz_javascript():
    response = make_response(render_template('quiz.js'))
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Type"] = "text/javascript; charset=utf-8"
    # response.headers["Content-Length"] = str(len(bytes(open("public/templates/functions.js").read(), 'utf-8')))

    return response


@app.route('/static/<image>', methods=['GET'])
def send_image(image):
    if (image not in allowed_images):
        abort(404)

    image_bytes = open(f"public/static/{image}", "rb").read()
    response = make_response(image_bytes)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Type"] = "image/jpeg"
    # image_length = str(len((open(f"public/static/{image}", "rb").read())))
    # response.headers["Content-Length"] = image_length

    return response


@app.route('/visit-counter', methods=['GET'])
def send_cookie():
    new_cookie = request.headers.get("Cookie", "visits=0")
    # print("Existing cookie", file=sys.stderr)
    # print(new_cookie, file=sys.stderr)

    cookie_kvps = {}
    if "Cookie" in request.headers and "visits" in new_cookie:

        cookie_as_list = new_cookie.split(";")

        for lines in cookie_as_list:
            cookie_kvp = lines.split("=")
            cookie_kvps[cookie_kvp[0].strip()] = cookie_kvp[1].strip()

        cookie_number = cookie_kvps["visits"]
        cookie_number = int(cookie_number) + 1

        cookie_kvps["visits"] = cookie_number

        new_cookie = ""

        for key_piece in cookie_kvps:
            new_cookie += " "
            new_cookie += key_piece
            new_cookie += "="
            new_cookie += str(cookie_kvps[key_piece])
            new_cookie += ";"

        new_cookie = new_cookie.rstrip(new_cookie[-1])
    else:
        # print("cookie does not exist")

        # cookie_as_list = new_cookie.split(";")
        # print("cookies as list")
        # print(cookie_as_list)

        # for lines in cookie_as_list:
        #     cookie_kvp = lines.split("=")
        #     # print("lines")
        #     # print(cookie_kvp)
        #     cookie_kvps[cookie_kvp[0].strip()] = cookie_kvp[1].strip()

        # print("new cookie kvp's")
        # print(cookie_kvps)
        new_cookie = "visits=1"

        cookie_number = 1
    # print("new_visit_count")
    # print(cookie_number)
    # print("new_cookie")
    # print(new_cookie)
    new_cookie = new_cookie + '; Max-Age=3600; Path=/visit-counter'

    response = make_response(str(cookie_number))
    response.mimetype = "text/plain; charset=utf-8"
    response.headers["Set-Cookie"] = new_cookie
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Length"] = str(len(str(cookie_number)))

    return response


@app.route('/register', methods=['POST'])
def register():
    # user_collection = db["users"]
    # print("registering")

    username = request.form.get("username_reg")
    password = request.form.get("password_reg")

    username = escape_html(username)

    found_user = user_collection.find_one({"username": username})

    if found_user is not None:
        # print("users exist:")
        # print(found_user)
        abort(401, 'user already exists')

    # print("username")
    # print(type(username))
    # print(username)
    # print("password")
    # print(password)

    if username and password:
        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
        user_and_pass = {"username": username, "password": hashed}
        # print("user and pass")
        # print(user_and_pass)
        user_collection.insert_one(user_and_pass)

    # print("made it past database")
    return redirect('http://localhost:8080', code=301)


@app.route('/login', methods=['POST'])
def login():
    # print("logging in")

    username = request.form.get("username_login")
    password = request.form.get("password_login")

    username = escape_html(username)

    checking_cookie = request.headers.get("Cookie")
    if "Cookie" in request.headers and "auth_token" in checking_cookie:
        abort(401, 'Already logged in as a user')

    if username and password:
        db_pass = user_collection.find_one({"username": username})  # finds a specific user

        if db_pass:  # if that user exists

            hash_pass = db_pass["password"]  # grab what's stored as their password
            if bcrypt.checkpw(password.encode("utf-8"), hash_pass):  # if the passwords match
                auth_token = secrets.token_urlsafe(32)
                hashed_token = hashlib.sha256(auth_token.encode("utf-8")).hexdigest()
                user_collection.update_one({"username": username}, {"$set": {"auth_token": hashed_token}})

                response = redirect("/", code=302)
                token_cookie = f"auth_token={auth_token}; Max-Age=3600; HttpOnly"
                response.headers["Set-Cookie"] = token_cookie

                get_quiz()

                return response

            else:
                abort(400, "Incorrect Password")

        else:
            abort(400, "No password provided")

    else:
        abort(406, 'missing username or password')

@app.route('/answer-question', methods=['POST'])
def answer_question():
    authCookie = request.headers.get("Cookie")
    if not authCookie or "auth_token" not in authCookie:
        abort(401, "Only authenticated users can create posts")

    authToken = None
    cookies = {}
    if authCookie:
        pairs = authCookie.split(';')
        for cookie in pairs:
            key, value = cookie.strip().split("=", 1)
            cookies[key] = value

    if "auth_token" in cookies:
        authToken = cookies["auth_token"]
    else:
        abort(401, "User authentication failed")

    hashedToken = hashlib.sha256(authToken.encode("utf-8")).hexdigest()
    user = user_collection.find_one({"auth_token": hashedToken})

    # since grabbing username from DB, is it enough to get away with security check?
    if user:
        username = user['username']
    else:
        abort(401, "User authentication failed")
    body = request.get_json(force=True)
    # print('BODYYYYY0-------------------')
    # print(body)
    title = body['title']
    desc = body['description']
    grade = body['grade']
    id = body['_id']
    data = {'username': username, 'qtitle': title, 'qdesc': desc, 'grade': grade, '_id': id}
    ans_collection.insert_one(data)

    return redirect('/quiz')


@app.route('/create-post', methods=['POST'])
def create_post():
    authCookie = request.headers.get("Cookie")
    if not authCookie or "auth_token" not in authCookie:
        abort(401, "Only authenticated users can create posts")

    authToken = None
    cookies = {}
    if authCookie:
        pairs = authCookie.split(';')
        for cookie in pairs:
            key, value = cookie.strip().split("=", 1)
            cookies[key] = value

    if "auth_token" in cookies:
        authToken = cookies["auth_token"]
    else:
        abort(401, "User authentication failed")

    hashedToken = hashlib.sha256(authToken.encode("utf-8")).hexdigest()
    user = user_collection.find_one({"auth_token": hashedToken})

    # since grabbing username from DB, is it enough to get away with security check?
    if user:
        username = user['username']
    else:
        abort(401, "User authentication failed")

    title = escape_html(request.form.get('title'))
    description = escape_html(request.form.get("description"))

    post = {
        'title': title,
        'description': description,
        'username': username,  # may change to 'poster'
        'likecount': 0,  # added like count
        'likers': []  # list of objects i.e., {'name': True/False}
    }

    db.posts.insert_one(post)

    # get id (I don't think we need this rn)
    # cursor = db.posts.find(post)
    # objectID = cursor['_id']
    # print(str(objectID))

    return redirect('http://localhost:8080', code=301)


@app.route('/get-posts', methods=['GET'])
def get_posts():
    # print('yooo')
    posts = list(db.posts.find())
    for post in posts:
        print(post)
        post['_id'] = str(post['_id'])
    return json.dumps(posts), 200, {'Content-Type': 'application/json', "X-Content-Type-Options": "nosniff"}


@app.route('/like-post', methods=['POST'])
def like_post():
    # authenticate user
    authCookie = request.headers.get("Cookie")
    if not authCookie or "auth_token" not in authCookie:
        # print('hello')
        abort(401, "Only authenticated users can like posts")

    authToken = None
    cookies = {}
    if authCookie:
        pairs = authCookie.split(';')
        for cookie in pairs:
            key, value = cookie.strip().split("=", 1)
            cookies[key] = value

    if "auth_token" in cookies:
        authToken = cookies["auth_token"]
    else:
        abort(401, "User authentication failed")

    hashedToken = hashlib.sha256(authToken.encode("utf-8")).hexdigest()
    user = user_collection.find_one({"auth_token": hashedToken})

    if user:
        username = user['username']
        # get post id (from request body) and db.posts.find_one({"_id": postID})
        body = request.get_json(force=True)  # body is dict
        postID = ObjectId(body['_id'])
        post = db.posts.find_one({"_id": postID})

        # if username in likers of post: decrement like count and remove username from likers
        # else increment like count and add username to likers
        if post:
            # print("post found", file=sys.stderr)    # debugging
            count = post['likecount']
            likers = post['likers']
            if username in likers:
                count -= 1
                likers.remove(username)
                # print("username in likers", file=sys.stderr)    # debugging
            else:
                count += 1
                likers.append(username)
                # print("username not in likers", file=sys.stderr)    # debugging

            # db.posts.update_one with the new like count and likers
            db.posts.update_one({'_id': postID}, {"$set": {'likers': likers, 'likecount': count}})

    else:
        abort(401, "User authentication failed")

    return redirect('http://localhost:8080', code=301)


@app.route('/create-quiz', methods=['POST'])
def create_quiz():
    authCookie = request.headers.get("Cookie")
    if not authCookie or "auth_token" not in authCookie:
        abort(401, "Only authenticated users can create quiz questions")
    authToken = None
    cookies = {}
    if authCookie:
        pairs = authCookie.split(';')
        for cookie in pairs:
            key, value = cookie.strip().split("=", 1)
            cookies[key] = value

    if "auth_token" in cookies:
        authToken = cookies["auth_token"]
    else:
        abort(401, "User authentication failed")

    hashedToken = hashlib.sha256(authToken.encode("utf-8")).hexdigest()
    user = user_collection.find_one({"auth_token": hashedToken})
    if user:
        username = user['username']
    else:
        abort(401, "User authentication failed")
    title = escape_html(request.form.get("quiz-title"))
    description = escape_html(request.form.get('description'))
    choices = [escape_html(answer) for answer in request.form.getlist("answers[]")]

    image = request.files.get('quizImage')
    image_name = None
    if image:
        image_name = generate_filename(image.filename)
        image_path = os.path.join(app.config['UPLOADS'], image_name)
        image.save(image_path)

    answer = int(escape_html(request.form.get('correct_answer')))

    quizQ = {
        'title': title,
        'description': description,
        'choices': choices,
        'image': image_name,
        'correct_answer': answer,
        'username': username
    }
    db.quiz.insert_one(quizQ)

    del quizQ["_id"]
    # return redirect('http://localhost:8080', code=301)
    # return Response(status=200)
    return redirect('/room')


@app.route('/get-quiz', methods=['GET'])
def get_quiz():
    questions = list(db.quiz.find())
    for question in questions:
        question['_id'] = str(question['_id'])
    return json.dumps(questions), 200, {'Content-Type': 'application/json', "X-Content-Type-Options": "nosniff"}


@app.route('/get-userquiz', methods=['GET'])
def get_userquiz():
    authToken = request.cookies.get("auth_token")
    if not authToken:
        abort(401, "User authentication failed, only logged in users can play quizzes")
    hashedToken = hashlib.sha256(authToken.encode("utf-8")).hexdigest()
    user_record = user_collection.find_one({"auth_token": hashedToken})

    if user_record:
        # user authenticated
        user = user_record["username"]
        questions = []
        question_creator = ''

        # make created questions dict from database collections
        question_records = quiz_collection.find()  # questions created by user

        for question in question_records: 
            print(question)
            question_creator = question['username']
            postID = ObjectId(question['_id'])

            if question_creator != user:
                dic = {'question': question['title'], 'answers': question['choices'], 'correct_answer': question['correct_answer'], 'description': question['description'], '_id': str(question['_id'])}
                questions.append(dic)
        
        print('YOOOOOO')
        print(questions)
        # make response with html variables replaced
        return json.dumps(questions), 200, {'Content-Type': 'application/json', "X-Content-Type-Options": "nosniff"}

    else:
        abort(401, "User authentication failed, user not found")

@app.route('/uploads/<filename>', methods=['GET'])
def upload_file(filename):
    return send_from_directory(app.config['UPLOADS'], filename)


@app.route('/obj2', methods=['GET', 'POST'])
def foo():
    if request.method == 'POST':

        authCookie = request.headers.get("Cookie")

        if not authCookie or "auth_token" not in authCookie:
            abort(401, "Only authenticated users can join the lobby")

        authToken = None
        cookies = {}
        if authCookie:
            pairs = authCookie.split(';')
            for cookie in pairs:
                key, value = cookie.strip().split("=", 1)
                cookies[key] = value

        if "auth_token" in cookies:
            authToken = cookies["auth_token"]
        else:
            abort(401, "User authentication failed")

        hashedToken = hashlib.sha256(authToken.encode("utf-8")).hexdigest()
        user = user_collection.find_one({"auth_token": hashedToken})

        if user:
            name = user['username']
            code = request.form.get('code')
            join = request.form.get('join', False)
            create = request.form.get('create', False)
        else:
            abort(401, "User authentication failed")

        if join == False and create == False:
            return render_template('quizhome.html', error='Create or enter a room', code=code, name=name)

        # name = request.form.get('name')
        code = request.form.get('code')
        join = request.form.get('join', False)
        create = request.form.get('create', False)

        # if not name:
        #     return render_template('quizhome.html', error='Please enter a name', code=code, name=name)

        if join != False and not code:
            return render_template('quizhome.html', error='Please enter a room code', code=code, name=name)

        room = code
        if create != False:
            room = generate_unique_code(4)
            rooms[room] = {'creator': name, "members": []}

        elif code not in rooms:
            return render_template('quizhome.html', error='Quiz does not exist', code=code, name=name)

        session['room'] = room
        session['name'] = name
        print("session")
        print(session)

        # code = session.get("room")

        return redirect(url_for("room"))

        # for dict in rooms:
        #     print("wtf")
        #     print(rooms[dict]['members'])
        #     print(rooms[dict]['creator'])
        #     owner_name = rooms[dict]["creator"]
        #     if name == owner_name:
        #         # return render_template("room.html", code=code, name=name)
        #         return redirect(url_for("room"))  # , code=code, name=name)
        #
        #     if rooms[dict["members"]]:
        #         if name in rooms[dict["members"]]:
        #             return redirect(url_for("room"))  # , code=code, name=name)

                # return redirect('/room', code=302)

        return render_template('quizhome.html')

        # else:
        #     return redirect('/room', code=302)

    return render_template('quizhome.html')


@app.route('/room')
def room():
    room = session.get('room')
    # if room is None or session.get('name') is None or room not in rooms:
    #     return redirect('/obj2')
    quiz = db.quiz.find()

    response = make_response(render_template('room.html',code=room, quiz=quiz))
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Type"] = "text/html; charset=utf-8"
    # response.headers["Content-Length"] = str(len(open("public/templates/index.html").read()))

    return response
    # return render_template('room.html', code=room, quiz=quiz)

@app.route('/quiz')
def quiz():
    return render_template('quiz.html')


@socketio.on('connect')
def connect(auth):
    # send("User has connected")
    # print("user connected", file=sys.stderr)
    room = session.get('room')
    name = session.get('name')  # might change to username
    if not room or not name:
        return
    if room not in rooms:
        leave_room(room)
        return

    join_room(room)
    send({'name': name, 'message': 'has entered the room'}, to=room)
    rooms[room]['members'].append(name)  # def change to username here, given auth key
    print(str(name) + ' joined room ' + str(room), file=sys.stderr)


@socketio.on('disconnect')
def disconnect():
    room = session.get('room')
    name = session.get('name')
    leave_room(room)

    if room in rooms:
        rooms[room]['members'].remove(name)
        if len(rooms[room]['members']) <= 0:
            del rooms[room]

    send({'name': name, 'message': 'has left the room'}, to=room)
    print(str(name) + ' has left room ' + str(room), file=sys.stderr)



@app.route('/grades', methods=['GET'])
@app.route('/grades.html', methods=['GET'])
def gradebook():
    """
    variables to replace in html file:
        user: str - username of logged-in user
        created_questions: dict(tuple(title:str, description:str)->list(tuple(username:str, grade:int)))
            - maps each question title, desc to list of all answers for that question
        own_answers: list(tuple(title, description, grade))
            - list of all grades for questions answered by user, with corresponding question title and desc
    """

    authToken = request.cookies.get("auth_token")
    if not authToken:
        abort(401, "User authentication failed, only logged in users can see grades")
    hashedToken = hashlib.sha256(authToken.encode("utf-8")).hexdigest()
    user_record = user_collection.find_one({"auth_token": hashedToken})

    if user_record:
        # user authenticated
        user = user_record["username"]
        created_questions = {}
        own_answers = []

        # make created questions dict from database collections
        question_records = quiz_collection.find({"username": user})  # questions created by user
        if question_records:
            for record in question_records:
                answer_records = ans_collection.find({"questionID": record["_id"]})
                key = (record["title"], record["description"])
                val = []
                if answer_records:
                    for rec in answer_records:
                        data = (rec["username"], rec["grade"])
                        val.append(data)
                created_questions[key] = val

        # make own_answers from answer collection
        answer_records = ans_collection.find({"username": user})
        if answer_records:
            for record in answer_records:
                print('answer records')
                print(record)
                data = (record["qtitle"], record["qdesc"], record["grade"])
                own_answers.append(data)

        # make response with html variables replaced
        response = make_response(
            render_template('grades.html', user=user, created_questions=created_questions, own_answers=own_answers))
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Type"] = "text/html; charset=utf-8"
        return response
    else:
        abort(401, "User authentication failed, user not found")

    


# def handle_join_room_event(data):
#     print("message_received:" + str(data), file=sys.stderr)
#     app.logger.info("{} has joined the Quiz app".format(data['username']))
#     join_room("Quiz app")
#     socketio.emit('join_room_announcement', data)

if __name__ == "__main__":
    # Please do not set debug=True in production
    socketio.run(app, host="0.0.0.0", port=8080, debug=True)
