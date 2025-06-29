# Save as create_user.py and run it once
from app import db, User
from flask import Flask

app = Flask(__name__)
app.app_context().push()

user = User(username='user1')
db.session.add(user)
db.session.commit()
print(f'User created with ID {user.id}')
