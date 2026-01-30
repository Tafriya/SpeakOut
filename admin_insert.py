from app import db, Admin, app
from werkzeug.security import generate_password_hash

with app.app_context():
    username = "Administrator"
    password = "112233" 

    hashed_password = generate_password_hash(password)
    admin = Admin(username=username, password=hashed_password)

    db.session.add(admin)
    db.session.commit()

    print("Admin created successfully!")
