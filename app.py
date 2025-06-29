# Q&A Forum - Flask Full App with Login/Register Support
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'supersecret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///qs_forum.db'
db = SQLAlchemy(app)

# --- Models ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    reputation = db.Column(db.Integer, default=0)
    questions = db.relationship('Question', backref='author', lazy=True)
    answers = db.relationship('Answer', backref='author', lazy=True)

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    tags = db.relationship('Tag', secondary='question_tags', backref='questions')
    answers = db.relationship('Answer', backref='question', lazy=True)
    comments = db.relationship('Comment', backref='question', lazy=True)

class Answer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text, nullable=False)
    is_accepted = db.Column(db.Boolean, default=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    comments = db.relationship('Comment', backref='answer', lazy=True)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.String(500), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    answer_id = db.Column(db.Integer, db.ForeignKey('answer.id'), nullable=True)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=True)

class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

question_tags = db.Table('question_tags',
    db.Column('question_id', db.Integer, db.ForeignKey('question.id')),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'))
)

# --- Helper ---
def get_current_user():
    if 'user_id' in session:
        return User.query.get(session['user_id'])
    return None

# --- Routes ---
@app.route('/')
def index():
    questions = Question.query.order_by(Question.created_at.desc()).all()
    return render_template('index.html', questions=questions, current_user=get_current_user())

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        if User.query.filter_by(username=username).first():
            flash('Username already exists.')
            return redirect(url_for('register'))
        user = User(username=username, password=password)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful. Please log in.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            return redirect(url_for('index'))
        flash('Invalid credentials.')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Logged out successfully.')
    return redirect(url_for('index'))

@app.route('/ask', methods=['GET', 'POST'])
def ask():
    current_user = get_current_user()
    if not current_user:
        flash("Login required to ask a question.")
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form['title']
        body = request.form['body']
        tags = request.form['tags'].split(',')
        question = Question(title=title, body=body, user_id=current_user.id)
        for tag_name in tags:
            tag = Tag.query.filter_by(name=tag_name.strip()).first()
            if not tag:
                tag = Tag(name=tag_name.strip())
            question.tags.append(tag)
        db.session.add(question)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('ask.html', current_user=current_user)

@app.route('/question/<int:qid>', methods=['GET', 'POST'])
def question_detail(qid):
    question = Question.query.get_or_404(qid)
    current_user = get_current_user()

    if request.method == 'POST':
        if not current_user:
            flash("Login required to answer.")
            return redirect(url_for('login'))
        body = request.form['body']
        answer = Answer(body=body, question_id=qid, user_id=current_user.id)
        db.session.add(answer)
        db.session.commit()
        return redirect(url_for('question_detail', qid=qid))

    return render_template('question_detail.html', question=question, current_user=current_user)

@app.route('/search')
def search():
    query = request.args.get('q', '')
    if query:
        results = Question.query.filter(
            Question.title.contains(query) |
            Question.body.contains(query)
        ).all()
    else:
        results = []

    return render_template('search_results.html', query=query, questions=results, current_user=get_current_user())


# --- Main ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
