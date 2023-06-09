# SOLVE: It doesn't load the comment list in the post.html!!

from flask import Flask, render_template, redirect, url_for, flash, abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, RegisterForm, CommentForm, LoginForm
from flask_gravatar import Gravatar
import os
from dotenv import load_dotenv

SECRET_KEY = os.getenv("SECRET_KEY")

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
ckeditor = CKEditor(app)
Bootstrap(app)
login_manager = LoginManager(app)
gravatar = Gravatar(app, size=100, rating='g', default='retro', force_default=False, force_lower=False)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Database Tables
class User(UserMixin, db.Model):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), nullable=False)
    email = db.Column(db.String(250), unique=True, nullable=False)
    password = db.Column(db.String(250), nullable=False)
    posts = relationship("BlogPost", back_populates="author")
    comments = relationship("Comment", back_populates="comment_author")

class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    author = relationship("User", back_populates="posts")
    post_comments = relationship("Comment", back_populates="comment_post")

class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(250), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    comment_author = relationship("User", back_populates="comments")
    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    comment_post = relationship("BlogPost", back_populates="post_comments")

with app.app_context():
    db.create_all()  
    
def admin_only(f):
    def wrapper(*args, **kwargs):
        if current_user.id == 1:
            return f(*args, **kwargs)
        else:
            return abort(403)
    # Renaming the function name to avoid AssertionError
    wrapper.__name__ = f.__name__
    return wrapper

@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts, logged_in=current_user.is_authenticated)

@app.route('/register', methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        new_user = User(
        name = form.name.data,
        email = form.email.data,
        password = generate_password_hash(
            password=form.password.data,
            method= "pbkdf2:sha256",
            salt_length=16
        )
        )
        check_user = db.session.query(User).filter_by(email=form.email.data).first()
        if check_user:
            message = flash("Already registered email.")
            return redirect(url_for("register", message=message))
        else:
            db.session.add(new_user)
            db.session.commit()
            login()
            return redirect(url_for("get_all_posts"))
    return render_template("register.html", form=form, logged_in=current_user.is_authenticated)

@login_manager.user_loader
def load_user(user_id):
    return db.session.query(User).filter_by(id=user_id).first()

@app.route('/login', methods=["GET", "POST"])
def login():
    form  = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        user = db.session.query(User).filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for("get_all_posts"))
        else:
            message = flash("Invalid email or password.")
            return redirect(url_for("login", message=message))
    return render_template("login.html", form=form, logged_in=current_user.is_authenticated)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))

@app.route("/post/<int:post_id>", methods=["GET", "POST"])
def show_post(post_id):
    form = CommentForm()
    requested_post = BlogPost.query.get(post_id)
    if form.validate_on_submit():
        if current_user.is_authenticated:
            new_comment = Comment(
                text=form.comment.data,
                comment_author=current_user,
                comment_post=requested_post
                )
            db.session.add(new_comment)
            db.session.commit()
            return redirect(url_for("show_post", post_id=post_id))
        else:
            message = flash("You need to login to comment.")
            return redirect(url_for("login", message=message))
    return render_template("post.html", post=requested_post, form=form, current_user=current_user, logged_in=current_user.is_authenticated)

@app.route("/about")
def about():
    return render_template("about.html", logged_in=current_user.is_authenticated)

@app.route("/contact")
def contact():
    return render_template("contact.html", logged_in=current_user.is_authenticated)

@app.route("/new-post", methods=["GET", "POST"])
@login_required
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form, logged_in=current_user.is_authenticated)

@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@login_required
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=current_user,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form, logged_in=current_user.is_authenticated)

@app.route("/delete/<int:post_id>")
@login_required
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)