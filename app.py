# Flask App for Inforums
# final project for CSCI 3172
# by Liam Moore and Kevin Shanks (group 54)

import os
import datetime
from zxcvbn import zxcvbn
from flask import Flask, render_template, request, redirect, url_for, flash, session, Markup
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, current_user, login_user, logout_user

# flask app initialization
app = Flask(__name__)
app.secret_key = "keep this secret"
login = LoginManager(app)

# local paths
app.config["AVATAR_UPLOAD"] = os.getcwd() + '/static/img/avatars/'
app.config["AVATARS"] = '../static/img/avatars/'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'
db = SQLAlchemy(app)

# helper methods (MIGHT NOT NEED)
def get_avatar_path(user_id):
    if os.path.exists(app.config["AVATARS"] + f"ava_{user_id}.jpg"):
        return f"../static/img/avatars/ava_{user_id}.jpg"
    if os.path.exists(app.config["AVATARS"] + f"ava_{user_id}.png"):
        return f"../static/img/avatars/ava_{user_id}.png"
    return "../static/img/avatars/ava_0.jpg"

# create relational database tables
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(12), unique=True, nullable=False)
    email = db.Column(db.String(12), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    avatar_path = db.Column(db.String(100), default=app.config["AVATARS"] + "ava_0.jpg")
    date = db.Column(db.String(32), nullable=False)
    posts = db.relationship('Post', backref='user')
    comments = db.relationship('Comment', backref='user')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    topic = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.String(63206), nullable=False)
    date = db.Column(db.String(25), nullable=False)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    content = db.Column(db.String(8000), nullable=False)
    date = db.Column(db.String(25), default=datetime.datetime.now().strftime("%m/%d/%Y, %-I:%M %p"))

# database initialization
if not os.path.exists('db.sqlite3'):
    db.create_all()

# index page
@app.route('/', methods = ['GET', 'POST'])
def index():
    # get all posts (and sorts by newest)
    new_posts = Post.query.all()[-3:][::-1]

    # topic-specific posts (sorts by newest)
    gaming_posts = Post.query.filter_by(topic=1)[::-1]
    coding_posts = Post.query.filter_by(topic=2)[::-1]
    science_posts = Post.query.filter_by(topic=3)[::-1]
    stock_posts = Post.query.filter_by(topic=4)[::-1]
    art_posts = Post.query.filter_by(topic=5)[::-1]

    # topic icon dictionary
    icon = {
        1: ["danger", "ni ni-controller"],
        2: ["success", "ni ni-laptop"],
        3: ["primary", "ni ni-atom"],
        4: ["info", "ni ni-chart-bar-32"],
        5: ["warning", "ni ni-palette"]
    }

    if current_user.is_authenticated:
        print(current_user.avatar_path)

    return render_template("index.html", new_posts=new_posts, gaming_posts=gaming_posts, coding_posts=coding_posts, science_posts=science_posts, stock_posts=stock_posts, art_posts=art_posts, icon=icon)

# user login loader function
@login.user_loader
def load_user(id):
    return User.query.get(int(id))

# login page
@app.route('/login', methods = ['GET', 'POST'])
def login():
    
    # user is already logged in
    if current_user.is_authenticated:
        flash("You are already logged in!", "success")
        return redirect(url_for('index'))

    if request.method == 'POST':
        # collect login form data
        email = request.form['email']
        password = request.form['password']
        print("Logging in with:", email, password)


        # create user object with given email
        user = User.query.filter_by(email=email).first()
        if user == None or not user.check_password(password):
            print("Email or password is incorrect")
            flash('Incorrect email or password', "danger")
            return redirect(url_for('login'))
        else:
            print("Login successful")

            # login the user
            login_user(user)
            flash(f"Welcome back {current_user.username}!", "success")
            return redirect(url_for('index'))

    return render_template("login.html")

@app.route('/logout')
def logout():
    logout_user()
    flash("You have logged out successfully", "success")
    return redirect(url_for('index'))

# register page
@app.route('/register', methods = ['GET', 'POST'])
def register():
    
    # user is already logged in
    if current_user.is_authenticated:
        flash("You already have an account", "danger")
        return redirect(url_for('index'))

    if request.method == 'POST':
        # collect register form data
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        print(username, email, password)

        # check if user can be created
        if User.query.filter_by(username=username).first() != None:
            flash('That username is already taken', "danger")
            redirect(url_for('register'))
        elif User.query.filter_by(email=email).first() != None:
            flash('Account with that email already exists', "danger")
            redirect(url_for('register'))
        else:
            # check if password is strong enough
            if zxcvbn(password)['score'] == 0 or zxcvbn(password)['score'] == 1:
                flash("Your password is too weak", "danger")
                redirect(url_for('register'))
            else:
                # create new row in database
                user = User(username=username, email=email, date=datetime.datetime.now().strftime("%B %-d, %Y"))
                user.set_password(password)
                db.session.add(user)
                db.session.commit()
                print("added user to db")

                flash("Your account has been created! Login", "success")
                return redirect(url_for('login'))

    return render_template("register.html")

# profile page
@app.route('/profile', methods = ['GET', 'POST'])
def profile():
    
    username = request.args.get('user')
    profile_user = User.query.filter_by(username=username).first()
    profile_user_posts = Post.query.filter_by(user_id=profile_user.id)[::-1]
    num_posts = len(profile_user_posts)
    # num_comments = len(Comments.query.filter_by(user_id=user.id))

    tips_recieved = 0
    tips_given = 0

    # topic icon dictionary
    icon = {
        1: ["danger", "ni ni-controller"],
        2: ["success", "ni ni-laptop"],
        3: ["primary", "ni ni-atom"],
        4: ["info", "ni ni-chart-bar-32"],
        5: ["warning", "ni ni-palette"]
    }

    # change profile picture
    if request.method == 'POST':
        avatar_file = request.files['avatar_upload']
        extension = avatar_file.filename[-4:]
        avatar_file.save(os.path.join(app.config["AVATAR_UPLOAD"], f"ava_{current_user.id}{extension}"))

        # update database
        current_user.avatar_path = app.config["AVATARS"] + f"ava_{current_user.id}{extension}"
        db.session.commit()
        flash("Your avatar has been updated!", "success")
        return render_template("profile.html", profile_user=profile_user, profile_user_posts=profile_user_posts, icon=icon, num_posts=num_posts, tips_recieved=tips_recieved, tips_given=tips_given)

    return render_template("profile.html", profile_user=profile_user, profile_user_posts=profile_user_posts, icon=icon, num_posts=num_posts, tips_recieved=tips_recieved, tips_given=tips_given)

# thread creation page
@app.route("/newthread", methods = ['GET', 'POST'])
def new_thread():
    # if user tries creating a thread without being logged in
    if not current_user.is_authenticated:
        flash("Login or create an account", "warning")
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        topic = request.args.get('topic')
        print("Title:", title)
        print("Content:", content)
        print("Topic:", topic)
        print(current_user.id)
        
        post = Post(user_id=current_user.id, topic=topic, title=title, content=content, date=datetime.datetime.now().strftime("%m/%d/%Y, %-I:%M %p"))
        db.session.add(post)
        db.session.commit()
        print("Added post to db")

        # http://localhost:5000/%7B%20url_for('thread',%20post_id=post.id)%20%7D

        # print(f'Your post has been created! You can view it <a href="{url_for('thread', post_id=post.id)}" class="alert-link">here.</a>')
        flash(Markup(f'Your post has been created! You can view it <a href="{url_for("thread", post_id=post.id)}" class="alert-link">here.</a>'), "success")
        return redirect(url_for('index'))
    
    return render_template("newthread.html", avatar_path=get_avatar_path(current_user.id))

@app.route("/thread", methods = ['GET', 'POST'])
def thread():

    post_id = request.args.get('post_id')
    post = Post.query.filter_by(id=post_id).first()
    content = post.content.split('\n')

    # return render_template("thread.html", avatar_path=get_avatar_path(current_user.id), user_id=post.user.id, poster_avatar_path=get_avatar_path(post.user.id), title=post.title, content=content, username=post.user.username, date=post.date)
    return render_template("thread.html", post=post, content=content)



# ====== REMOVE BEFORE DEPLOYMENT ====== #
@app.route('/elements', methods = ['GET', 'POST'])
def elements():
    return render_template("elements.html")


# run app
if __name__ == "__main__":
    app.run()