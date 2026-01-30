from app import app, db
from models import Department  
from werkzeug.security import generate_password_hash

with app.app_context():
    departments = [
        {"name": "Police", "username": "police_dept", "password": "police123", "profile_pic": "police.png"},
        {"name": "Municipality", "username": "municipality_dept", "password": "municipality123", "profile_pic": "municipality.png"},
        {"name": "Water Supply", "username": "water_dept", "password": "water123", "profile_pic": "water.png"},
        {"name": "Electricity Board", "username": "electricity_dept", "password": "electricity123", "profile_pic": "electricity.png"},
        {"name": "Health Department", "username": "health_dept", "password": "health123", "profile_pic": "health.png"},
        {"name": "Transport Department", "username": "transport_dept", "password": "transport123", "profile_pic": "transport.png"},
        {"name": "Education Department", "username": "education_dept", "password": "education123", "profile_pic": "education.png"},
        {"name": "Women & Child Welfare", "username": "womenchild_dept", "password": "womenchild123", "profile_pic": "womenchild.png"},
        {"name": "Environment Department", "username": "environment_dept", "password": "environment123", "profile_pic": "environment.png"},
        {"name": "Public Works Department", "username": "pwd_dept", "password": "pwd123", "profile_pic": "pwd.png"},
        {"name": "Revenue Department", "username": "revenue_dept", "password": "revenue123", "profile_pic": "revenue.png"},
    ]

    for dept in departments:
        existing = Department.query.filter_by(username=dept["username"]).first()
        if not existing:
            new_dept = Department(
                name=dept["name"],
                username=dept["username"],
                password=generate_password_hash(dept["password"]),
                profile_pic=dept["profile_pic"]
            )
            db.session.add(new_dept)
            print(f"Inserted {dept['name']} ✅")
        else:
            print(f"{dept['name']} already exists ❌")

    db.session.commit()
    print("All departments inserted successfully 🎉")
