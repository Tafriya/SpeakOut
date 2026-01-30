from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from models import db,User, Admin, Grievance, Comment, Like, Department, Notice
from werkzeug.security import generate_password_hash, check_password_hash
from flask import session
from werkzeug.utils import secure_filename
import os 
import json
from PIL import Image
import uuid


app = Flask(__name__)
app.secret_key = "tafriya"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///./speakout.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

db.init_app(app)

with app.app_context():
    db.create_all()

def is_image_file(file):
    try:
        file.seek(0)
        img = Image.open(file)
        img.verify() 
        file.seek(0)   
        return True
    except (UnidentifiedImageError, Exception):
        file.seek(0)   
        return False  

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        role = request.form["role"]
        username = request.form["username"]
        password = request.form["password"]

        if role == "user":
            user = User.query.filter_by(username=username).first()
            if user and check_password_hash(user.password, password):
                session["user_id"] = user.id
                session["username"] = user.username
                session["profile_pic"] = user.profile_pic or 'default_profile.png'
                session["role"] = "user"
                flash("Logged in as user!", "success")
                return redirect(url_for("index"))  
            else:
                flash("Invalid user credentials", "danger")
                return redirect(url_for("login"))

        elif role == "admin":
            admin = Admin.query.filter_by(username=username).first()
            if admin and check_password_hash(admin.password, password):
                session["admin_id"] = admin.id
                session["username"] = admin.username
                session["role"] = "admin"
                flash("Logged in as admin!", "success")
                return redirect(url_for("a_dashboard")) 
            else:
                flash("Invalid admin credentials", "danger")
                return redirect(url_for("login"))

        elif role == "department":
            dept = Department.query.filter_by(username=username).first()
            if dept and check_password_hash(dept.password, password):
                session["department_id"] = dept.id
                session["username"] = dept.username
                session["profile_pic"] = dept.profile_pic or "default_department.png"
                session["role"] = "department"
                flash(f"Logged in as {dept.name} Department!", "success")
                return redirect(url_for("d_dashboard"))
            else:
                flash("Invalid department credentials", "danger")
                return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        location = request.form.get("location").strip().lower()
        confirm = request.form["confirm_password"]

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash("Username already exists!", "warning")
            return redirect(url_for("register"))

        if password == confirm:
            hashed_password = generate_password_hash(password)
            new_user = User(username=username, email=email, password=hashed_password,location=location)
            db.session.add(new_user)
            db.session.commit()
            flash("Registration successful! Please login.", "success")
            return redirect(url_for("login"))
        else:
            flash("Passwords do not match!", "danger")

    return render_template("user/register.html")

@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/u_dashboard')
def u_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    department_id = request.args.get('department_id')
    query = Grievance.query.filter_by(user_id=session['user_id'])
    

    if department_id:
        query = query.filter_by(department_id=department_id)

    grievances = query.all()
    departments = Department.query.all()

    return render_template(
        'user/u_dashboard.html',
        grievances=grievances,
        departments=departments
    )


@app.route('/submit_grievance', methods=['GET', 'POST'])
def submit_grievance():
    if 'username' not in session:
        flash("Please log in to submit a grievance.", "warning")
        return redirect(url_for('login'))

    departments = Department.query.all()
    allowed_locations = {"kasaragod", "mangalore", "bangalore"}

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        department_id = request.form.get('department_id')
        location = request.form.get("location").strip().lower()
        user_id = session['user_id']
        image_file = request.files.get('image')
        image_filename = None

        if location not in allowed_locations:
            flash("Invalid location selected.", "danger")
            return redirect(url_for('submit_grievance'))

        if image_file and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image_file.save(image_path)
            image_filename = filename

        new_grievance = Grievance(
            title=title,
            description=description,
            location=location,
            user_id=user_id,
            image=image_filename,
            department_id=int(department_id) if department_id else None 
        )

        db.session.add(new_grievance)
        db.session.commit()
        flash("Grievance submitted successfully!", "success")
        return redirect(url_for('u_dashboard'))

    return render_template('user/submit_grievance.html', departments=departments)

@app.route('/edit_grievance/<int:grievance_id>', methods=['GET', 'POST'])
def edit_grievance(grievance_id):
    grievance = Grievance.query.get_or_404(grievance_id)

    if grievance.user_id != session.get('user_id'):
        flash("You are not authorized to edit this grievance.", "danger")
        return redirect(url_for('u_dashboard'))

    if request.method == 'POST':
        grievance.title = request.form['title']
        grievance.description = request.form['description']
        grievance.category = request.form['category']
        location = request.form.get("location").strip().lower()
        db.session.commit()
        flash("Grievance updated successfully!", "success")
        return redirect(url_for('view_grievance', id=grievance.id))

    return render_template("user/edit_grievance.html", grievance=grievance)


@app.route('/delete_grievance/<int:grievance_id>', methods=['POST'])
def delete_grievance(grievance_id):
    grievance = Grievance.query.get_or_404(grievance_id)

    if grievance.user_id != session.get('user_id'):
        flash("You are not authorized to delete this grievance.", "danger")
        return redirect(url_for('u_dashboard'))

    
    Comment.query.filter_by(grievance_id=grievance.id).delete()
    
    db.session.delete(grievance)
    db.session.commit()
    flash("Grievance deleted successfully.", "success")
    return redirect(url_for('u_dashboard'))


# @app.route('/view_grievance/<int:id>', methods=['GET', 'POST'])
# def view_grievance(id):
#     if 'user_id' not in session:
#         flash("Please log in to view the grievance.", "warning")
#         return redirect(url_for('login'))

#     grievance = Grievance.query.get_or_404(id)
#     has_liked = Like.query.filter_by(user_id=session['user_id'], grievance_id=id).first() is not None

#     if not grievance:
#         flash("Grievance not found or access denied.", "danger")
#         return redirect(url_for('u_dashboard'))

#     if request.method == 'POST':
#         if 'like' in request.form:
#             if not has_liked:
#                 like = Like(user_id=session['user_id'], grievance_id=id)
#                 db.session.add(like)
#                 db.session.commit()
#                 flash("You liked this grievance.", "success")
#             return redirect(url_for('view_grievance', id=id))

        
#         message = request.form.get('message', '').strip()
#         if message:
#             new_comment = Comment(
#                 grievance_id=grievance.id,
#                 user_id=session['user_id'],
#                 message=message
#             )
#             db.session.add(new_comment)
#             db.session.commit()
#             flash("Comment posted successfully.", "success")
#             return redirect(url_for('view_grievance', id=id))

#     comments = Comment.query.filter_by(grievance_id=grievance.id).order_by(Comment.timestamp.desc()).all()
#     like_count = Like.query.filter_by(grievance_id=id).count()
#     departments = Department.query.all()

#     return render_template("user/view_grievance.html",
#                            grievance=grievance,
#                            comments=comments,
#                            has_liked=has_liked,
#                            like_count=like_count,
#                            departments=departments)

@app.route('/view_grievance/<int:id>', methods=['GET', 'POST'])
def view_grievance(id):
    if 'user_id' not in session:
        flash("Please log in to view the grievance.", "warning")
        return redirect(url_for('login'))

    grievance = Grievance.query.get_or_404(id)
    if not grievance:
        flash("Grievance not found or access denied.", "danger")
        return redirect(url_for('u_dashboard'))

    # check if user has already liked
    existing_like = Like.query.filter_by(user_id=session['user_id'], grievance_id=id).first()
    has_liked = True if existing_like else False

    if request.method == 'POST':
        if 'like' in request.form:
            if has_liked:
                # Unlike → remove record
                db.session.delete(existing_like)
                db.session.commit()
                flash("You unliked this grievance.", "info")
            else:
                # Like → add new record
                like = Like(user_id=session['user_id'], grievance_id=id)
                db.session.add(like)
                db.session.commit()
                flash("You liked this grievance.", "success")
            return redirect(url_for('view_grievance', id=id))

        # Handle comments
        message = request.form.get('message', '').strip()
        if message:
            new_comment = Comment(
                grievance_id=grievance.id,
                user_id=session['user_id'],
                message=message
            )
            db.session.add(new_comment)
            db.session.commit()
            flash("Comment posted successfully.", "success")
            return redirect(url_for('view_grievance', id=id))

    comments = Comment.query.filter_by(grievance_id=grievance.id).order_by(Comment.timestamp.desc()).all()
    like_count = Like.query.filter_by(grievance_id=id).count()
    departments = Department.query.all()

    return render_template("user/view_grievance.html",
                           grievance=grievance,
                           comments=comments,
                           has_liked=has_liked,
                           like_count=like_count,
                           departments=departments)



@app.route('/edit_comment/<int:comment_id>', methods=['GET', 'POST'])
def edit_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)

    
    if comment.user_id != session.get('user_id'):
        flash("You are not authorized to edit this comment.", "danger")
        return redirect(url_for('view_grievance', id=comment.grievance_id))

    if request.method == 'POST':
        new_message = request.form['message'].strip()
        if new_message:
            comment.message = new_message
            db.session.commit()
            flash("Comment updated successfully.", "success")
        return redirect(url_for('view_grievance', id=comment.grievance_id))

    return render_template("user/edit_comment.html", comment=comment)


@app.route('/delete_comment/<int:comment_id>', methods=['POST'])
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)

   
    if comment.user_id != session.get('user_id'):
        flash("You are not authorized to delete this comment.", "danger")
        return redirect(url_for('view_grievance', id=comment.grievance_id))

    db.session.delete(comment)
    db.session.commit()
    flash("Comment deleted successfully.", "success")
    return redirect(url_for('view_grievance', id=comment.grievance_id))

@app.route('/profile')
def profile():
    if 'username' not in session:
        flash("Please log in to view your profile.", "warning")
        return redirect(url_for('login'))

    user_id = session['user_id']
    user = User.query.get(user_id)

    grievance_count = Grievance.query.filter_by(user_id=user_id).count()
    comment_count = Comment.query.filter_by(user_id=user_id).count()

    return render_template('user/profile.html',
                           user=user,
                           grievance_count=grievance_count,
                           comment_count=comment_count)

@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'user_id' not in session:
        flash("Please log in to edit your profile.", "warning")
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        # Update username
        new_username = request.form.get('username', '').strip()
        if new_username:
            user.username = new_username

        # Update email
        new_email = request.form.get('email', '').strip()
        if new_email:
            user.email = new_email

        # Update location
        new_location = request.form.get('location', '').strip().lower()
        if new_location:
            user.location = new_location

        # Handle profile picture
        profile_pic = request.files.get('profile_pic')
        if profile_pic and profile_pic.filename.strip():
            if not allowed_file(profile_pic.filename):
                flash("Invalid file extension. Only png, jpg, jpeg, gif are allowed.", "danger")
                return redirect(url_for('edit_profile'))

            if not is_image_file(profile_pic):
                flash("Invalid image file. Only real images are allowed.", "danger")
                return redirect(url_for('edit_profile'))

            # Save new profile pic with UUID
            filename = f"{uuid.uuid4().hex}_{secure_filename(profile_pic.filename)}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            profile_pic.save(filepath)

            # Delete old profile pic if not default
            if user.profile_pic and user.profile_pic != "default_profile.png":
                old_path = os.path.join(app.config['UPLOAD_FOLDER'], user.profile_pic)
                if os.path.exists(old_path):
                    os.remove(old_path)

            user.profile_pic = filename

        # ✅ Commit changes
        db.session.commit()

        # ✅ Update session after commit
        session['username'] = user.username
        session['location'] = user.location
        session['email'] = user.email
        session['profile_pic'] = user.profile_pic or 'default_profile.png'

        flash("Profile updated successfully!", "success")
        return redirect(url_for('profile'))

    return render_template('user/edit_profile.html', user=user)

# @app.route('/edit_profile', methods=['GET', 'POST'])
# def edit_profile():
#     if 'user_id' not in session:
#         flash("Please log in to edit your profile.", "warning")
#         return redirect(url_for('login'))

#     user = User.query.get(session['user_id'])

#     if request.method == 'POST':
#         # Update username
#         new_username = request.form.get('username', '').strip()
#         if new_username:
#             user.username = new_username

#         # Update email
#         new_email = request.form.get('email', '').strip()
#         if new_email:
#             user.email = new_email


#         # Update location
#         new_location = request.form.get('location', '').strip().lower()
#         if new_location:
#             user.location = new_location

#         # Handle profile picture
#         profile_pic = request.files.get('profile_pic')
#         if profile_pic and profile_pic.filename.strip():
#             if not allowed_file(profile_pic.filename):
#                 flash("Invalid file extension. Only png, jpg, jpeg, gif are allowed.", "danger")
#                 return redirect(url_for('edit_profile'))

#             if not is_image_file(profile_pic):
#                 flash("Invalid image file. Only real images are allowed.", "danger")
#                 return redirect(url_for('edit_profile'))

#             # Save new profile pic with UUID
#             filename = f"{uuid.uuid4().hex}_{secure_filename(profile_pic.filename)}"
#             filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
#             profile_pic.save(filepath)

#             # Delete old profile pic if not default
#             if user.profile_pic and user.profile_pic != "default_profile.png":
#                 old_path = os.path.join(app.config['UPLOAD_FOLDER'], user.profile_pic)
#                 if os.path.exists(old_path):
#                     os.remove(old_path)

#             user.profile_pic = filename
#             flash("Profile picture updated successfully!", "success")
#             return redirect(url_for('profile'))
#         else:
#             flash("Profile updated successfully (no new picture uploaded).", "success")
#             return redirect(url_for('profile'))

#         # Commit changes
#         db.session.commit()

#         # Update session safely
#         session['username'] = user.username
#         session['location'] = user.location
#         session['email'] = user.email
#         session['profile_pic'] = user.profile_pic or 'default_profile.png'

#         return redirect(url_for('edit_profile'))

#     return render_template('user/edit_profile.html', user=user)



@app.route('/grievances')
def all_grievances():
    if 'user_id' not in session:
        flash("Please log in to view all grievances.", "warning")
        return redirect(url_for('login'))

    search_query = request.args.get('search', '').strip().lower()
    department_id = request.args.get('department_id', '')
    status = request.args.get('status', '')
    location = request.args.get('location', '').strip().lower()
    sort = request.args.get('sort', 'latest')

    grievances = Grievance.query

    
    if search_query:
        grievances = grievances.filter(
            (Grievance.title.ilike(f"%{search_query}%")) |
            (Grievance.description.ilike(f"%{search_query}%"))
        )

    
    if department_id:
        grievances = grievances.filter_by(department_id=department_id)

    
    if status:
        grievances = grievances.filter_by(status=status)

   
    if location:
        grievances = grievances.filter_by(location=location)

    
    if sort == 'likes':
        grievances = grievances.outerjoin(Like).group_by(Grievance.id).order_by(db.func.count(Like.id).desc())
    else:
        grievances = grievances.order_by(Grievance.created_at.desc())

    grievances = grievances.all()

    user_likes = Like.query.filter_by(user_id=session['user_id']).all()
    liked_ids = {like.grievance_id for like in user_likes}
    like_counts = {g.id: Like.query.filter_by(grievance_id=g.id).count() for g in grievances}
    
    departments = Department.query.all()

    return render_template('user/all_grievances.html',
                           grievances=grievances,
                           liked_ids=liked_ids,
                           like_counts=like_counts,
                           departments=departments,
                           department_id=department_id)

@app.route('/toggle_like/<int:grievance_id>', methods=['POST'])
def toggle_like(grievance_id):
    if 'user_id' not in session:
        flash("Please log in to like grievances.", "warning")
        return redirect(url_for('login'))

    existing_like = Like.query.filter_by(user_id=session['user_id'], grievance_id=grievance_id).first()

    if existing_like:
        db.session.delete(existing_like)
        db.session.commit()
        flash("Like removed.", "info")
    else:
        new_like = Like(user_id=session['user_id'], grievance_id=grievance_id)
        db.session.add(new_like)
        db.session.commit()
        flash("Grievance liked.", "success")

    return redirect(url_for('all_grievances'))


@app.route("/user/u_notices")
def u_notices():
    if "user_id" not in session or session.get("role") != "user":
        flash("Please log in as a user.", "warning")
        return redirect(url_for("login"))

    user = User.query.get(session["user_id"])
    if not user or not user.location:
        notices = []
    else:
        notices = (Notice.query
                   .filter(func.lower(Notice.location) == user.location.lower())
                   .order_by(Notice.timestamp.desc())
                   .all())

    return render_template("user/u_notices.html", notices=notices)

from sqlalchemy import func

@app.route('/d_dashboard')
def d_dashboard():
    if 'department_id' not in session or session.get('role') != 'department':
        flash("Please log in as a department.", "warning")
        return redirect(url_for('login'))

    dept_id = session['department_id']
    department = Department.query.get_or_404(dept_id)

    grievances = Grievance.query.filter_by(department_id=dept_id).all()
    total_grievances = len(grievances)
    pending_count = Grievance.query.filter_by(department_id=dept_id, status="Pending").count() or 0
    inprogress_count = Grievance.query.filter_by(department_id=dept_id, status="In Progress").count() or 0
    resolved_count = Grievance.query.filter_by(department_id=dept_id, status="Resolved").count() or 0

    priority_grievances = (
        db.session.query(Grievance, func.count(Like.id).label("like_count"))
        .outerjoin(Like, Like.grievance_id == Grievance.id)
        .filter(Grievance.department_id == dept_id, Grievance.status != "Resolved")
        .group_by(Grievance.id)
        .order_by(func.count(Like.id).desc())
        .all()
    )

    return render_template(
        'department/d_dashboard.html',
        department=department,
        grievances=grievances,  
        priority_grievances=priority_grievances,
        total_grievances=total_grievances,
        pending_count=pending_count,
        inprogress_count=inprogress_count,
        resolved_count=resolved_count
    )


@app.route("/dashboard/status-data")
def status_data():
    dept_id = session.get("department_id")   
    status_counts = (
        db.session.query(Grievance.status, func.count(Grievance.id))
        .filter(Grievance.department_id == dept_id)   
        .group_by(Grievance.status)
        .all()
    )

    labels = [row[0] for row in status_counts]
    values = [row[1] for row in status_counts]

    all_statuses = ["Pending", "In Progress", "Resolved"]
    for i, s in enumerate(all_statuses):
        if s not in labels:
            labels.insert(i, s)
            values.insert(i, 0)

    return jsonify({"labels": labels, "values": values})

@app.route("/dashboard/location-data")
def location_data():
    dept_id = session.get("department_id")   
    data = (
        db.session.query(Grievance.location, func.count(Grievance.id))
        .filter(Grievance.department_id == dept_id)
        .group_by(func.lower(Grievance.location))
        .order_by(func.lower(Grievance.location))
        .all()
    )

    labels = [row[0].title() for row in data]
    values = [row[1] for row in data]

    return jsonify({"labels": labels, "values": values})


@app.route("/department/update_status/<int:grievance_id>", methods=["POST"])
def update_grievance_status(grievance_id):
    if "department_id" not in session or session.get("role") != "department":
        flash("Unauthorized access!", "danger")
        return redirect(url_for("login"))

    grievance = Grievance.query.get_or_404(grievance_id)

    if grievance.department_id != session["department_id"]:
        flash("You cannot update grievances from another department!", "danger")
        return redirect(url_for("d_dashboard"))

    new_status = request.form["status"]
    grievance.status = new_status
    db.session.commit()

    flash("Grievance status updated!", "success")
    next_page = request.form.get("next")
    return redirect(next_page or url_for("d_dashboard"))


@app.route('/department/all_grievances')
def d_all_grievances():
    if 'department_id' not in session:
        return redirect(url_for('login'))

    department_id = session['department_id']

    search = request.args.get('search', '').strip()
    status = request.args.get('status', '').strip()
    location = request.args.get('location', '').strip().lower()

    query = Grievance.query.filter_by(department_id=department_id)

    if search:
        query = query.filter(
            (Grievance.title.ilike(f"%{search}%")) |
            (Grievance.id.cast(db.String).ilike(f"%{search}%"))
        )

    if status:
        query = query.filter(Grievance.status == status)

    if location:
        query = query.filter(Grievance.location.ilike(f"%{location}%"))

    grievances = query.all()

    grievance_data = []
    for g in grievances:
        grievance_data.append({
            "grievance": g,
            "like_count": Like.query.filter_by(grievance_id=g.id).count(),
            "comment_count": Comment.query.filter_by(grievance_id=g.id).count()
        })

    return render_template("department/d_all_grievances.html", grievance_data=grievance_data)



@app.route('/department/view_grievance/<int:id>')
def d_view_grievance(id):
    if 'department_id' not in session or session.get('role') != 'department':
        flash("Please log in as a department.", "warning")
        return redirect(url_for('login'))

    grievance = Grievance.query.get_or_404(id)

    if grievance.department_id != session['department_id']:
        flash("You cannot access grievances from another department!", "danger")
        return redirect(url_for('d_dashboard'))

    comments = Comment.query.filter_by(grievance_id=grievance.id).order_by(Comment.timestamp.desc()).all()
    like_count = Like.query.filter_by(grievance_id=id).count()

    return render_template(
        'department/d_view_grievance.html',
        grievance=grievance,
        comments=comments,
        like_count=like_count
    )



@app.route("/department/update_profile", methods=["GET", "POST"])
def update_profile():
    if "department_id" not in session or session.get("role") != "department":
        flash("Please log in as a department.", "warning")
        return redirect(url_for("login"))

    dept_id = session["department_id"]
    department = Department.query.get_or_404(dept_id)

    if request.method == "POST":
        name = request.form["name"]
        username = request.form["username"]

        if "profile_pic" in request.files:
            file = request.files["profile_pic"]
            if file and file.filename != "":
                filename = secure_filename(file.filename)
                filepath = os.path.join("static/uploads/departments", filename)
                file.save(filepath)
                department.profile_pic = filename

        department.name = name
        department.username = username
        db.session.commit()

        flash("Profile updated successfully!", "success")
        return redirect(url_for("d_dashboard"))

    return render_template("department/update_profile.html", department=department)


@app.route("/department/d_notices", methods=["GET", "POST"])
def d_notices():
    if "department_id" not in session or session.get("role") != "department":
        flash("Unauthorized access!", "danger")
        return redirect(url_for("login"))

    if request.method == "POST":
        title = request.form.get("title")
        message = request.form.get("message")
        location = request.form.get("location").strip().lower()

        new_notice = Notice(
            title=title,
            message=message,
            location=location,
            department_id=session["department_id"]
        )
        db.session.add(new_notice)
        db.session.commit()
        flash("Notice sent successfully!", "success")
        return redirect(url_for("d_notices"))

    dept_id = session["department_id"]
    notices = Notice.query.filter_by(department_id=dept_id).order_by(Notice.timestamp.desc()).all()
    return render_template("department/d_notices.html", notices=notices)

@app.route("/department/notices")
def d_view_notices():
    if "department_id" not in session or session.get("role") != "department":
        flash("Please log in as a department.", "warning")
        return redirect(url_for("login"))

    department_id = session["department_id"]
    notices = Notice.query.filter_by(department_id=department_id).order_by(Notice.timestamp.desc()).all()
    return render_template("department/d_view_notices.html", notices=notices)


@app.route("/department/delete_notice/<int:notice_id>", methods=["POST"])
def d_delete_notice(notice_id):
    if "department_id" not in session or session.get("role").lower() != "department":
        flash("Please log in as a department user.", "warning")
        return redirect(url_for("login"))

    notice = Notice.query.get_or_404(notice_id)
    db.session.delete(notice)
    db.session.commit()
    flash("Notice deleted successfully.", "success")
    return redirect(url_for("d_notices"))

@app.route('/a_dashboard')
def a_dashboard():
    if 'admin_id' not in session:
        return redirect(url_for('login'))

    total_users = User.query.count()
    total_departments = Department.query.count()
    total_grievances = Grievance.query.count()

    recent_grievances = (
        Grievance.query
        .order_by(Grievance.created_at.desc())
        .limit(5)
        .all()
    )

    priority_grievance = (
        db.session.query(Grievance, func.count(Like.id).label("like_count"))
        .outerjoin(Like, Like.grievance_id == Grievance.id)
        .filter(Grievance.status != "Resolved")
        .group_by(Grievance.id)
        .order_by(func.count(Like.id).desc())
        .limit(5)
        .all()
    )

    return render_template("admin/a_dashboard.html",
        total_users=total_users,
        total_departments=total_departments,
        total_grievances=total_grievances,
        recent_grievances=recent_grievances,
        priority_grievance=priority_grievance
    )

@app.route("/dashboard/department-data")
def department_data():
    data = (
        db.session.query(Department.name, func.count(Grievance.id))
        .outerjoin(Grievance, Grievance.department_id == Department.id)
        .group_by(Department.id, Department.name)
        .all()
    )

    aliases = {
        "Police": "Police",
        "Water Supply": "Water",
        "Electricity Board": "Electricity",
        "Municipality": "Municipality",
        "Transport Department": "Transport",
        "Revenue Department": "Revenue",
        "Health Department": "Health",
        "Education Department": "Education",
        "Public Works Department": "PWD",
        "Women & Child Welfare": "WCD",
        "Environment Department": "Environment",
        "Fire Department": "Fire",
    }

    labels = [aliases.get(row[0], row[0]) for row in data]
    values = [row[1] for row in data]

    return jsonify({"labels": labels, "values": values})




@app.route('/admin/grievance_stats')
def admin_grievance_stats():
    if 'admin_id' not in session:
        return jsonify({"error": "Unauthorized"}), 403

    grievance_status_counts = (
        db.session.query(Grievance.status, db.func.count(Grievance.id))
        .group_by(Grievance.status)
        .all()
    )
    status_labels = [s[0] for s in grievance_status_counts]
    status_counts = [s[1] for s in grievance_status_counts]

    return jsonify({
        "labels": status_labels,
        "counts": status_counts
    })

@app.route("/a_location_data")
def a_location_data():
    data = (
        db.session.query(Grievance.location, func.count(Grievance.id))
        .group_by(func.lower(Grievance.location))
        .order_by(func.lower(Grievance.location))
        .all()
    )

    labels = [row[0].title() for row in data]
    values = [row[1] for row in data]

    return jsonify({"labels": labels, "values": values})


@app.route('/a_manage_users')
def a_manage_users():
    if 'admin_id' not in session:
        return redirect(url_for('login'))

    users = User.query.all()
    return render_template('admin/a_manage_users.html', users=users)

@app.route("/admin/view_user/<int:id>")
def a_view_users(id):
    user = User.query.get_or_404(id)
    grievances_count = Grievance.query.filter_by(user_id=user.id).count()
    comments_count = Comment.query.filter_by(user_id=user.id).count()
    likes_count = Like.query.filter_by(user_id=user.id).count()
    return render_template("admin/a_view_users.html", user=user,
        grievances_count=grievances_count,
        comments_count=comments_count,
        likes_count=likes_count)


@app.route('/a_delete_user/<int:id>', methods=['POST','GET'])
def a_delete_user(id):
    user = User.query.get_or_404(id)
    db.session.delete(user)
    db.session.commit()
    flash("User deleted successfully!", "success")
    return redirect(url_for('admin/a_view_users.html'))

@app.route("/a_view_grievances")
def a_view_grievances():
    search       = request.args.get("search", "").strip()
    status       = request.args.get("status", "").strip()
    department_id= request.args.get("department", "").strip()
    location     = request.args.get("location", "").strip().lower()

    query = Grievance.query

    if search:
        query = query.filter(
            (Grievance.title.ilike(f"%{search}%")) |
            (Grievance.description.ilike(f"%{search}%"))
        )

    if status:
        query = query.filter(Grievance.status == status) 

    if department_id:
        query = query.filter(Grievance.department_id == department_id)

    if location:
        query = query.filter(func.lower(Grievance.location) == location.lower())

    grievances   = query.order_by(Grievance.created_at.desc()).all()
    departments  = Department.query.order_by(Department.name).all()

    locations = ["mangalore", "bangalore", "kasaragod"]

    return render_template(
        "admin/a_view_grievances.html",
        grievances=grievances,
        departments=departments,
        locations=locations
    )

@app.route("/admin/open_grievance/<int:id>")
def a_open_grievance(id):
    grievance = Grievance.query.get_or_404(id)
    like_count = Like.query.filter_by(grievance_id=grievance.id).count()
    comments = Comment.query.filter_by(grievance_id=grievance.id).all()
    return render_template("admin/a_open_grievance.html", grievance=grievance, like_count=like_count, comments=comments)

@app.route('/a_delete_grievance/<int:id>', methods=['POST', 'GET'])
def a_delete_grievance(id):
    grievance = Grievance.query.get_or_404(id)
    db.session.delete(grievance)
    db.session.commit()
    flash("Grievance deleted successfully!", "success")
    return redirect(url_for('a_grievances'))


import os
from flask import current_app, url_for

@app.route("/a_manage_departments")
def a_manage_departments():
    departments = Department.query.all()
    dept_data = []
    for dept in departments:
        filename = dept.profile_pic if dept.profile_pic else "default_department.jpg"
        filepath = os.path.join(current_app.static_folder, "uploads/departments", filename)

        
        if not os.path.exists(filepath):
            filename = "default_department.jpg"

        dept_data.append({
            "id": dept.id,
            "name": dept.name,
            "profile_pic": filename
        })

    return render_template("admin/a_manage_departments.html", departments=dept_data)



@app.route("/a_view_departments/<int:id>")
def a_view_departments(id):
    dept = Department.query.get_or_404(id)

    total_grievances = Grievance.query.filter_by(department_id=id).count()
    handled = Grievance.query.filter_by(department_id=id, status="Resolved").count()
    pending = Grievance.query.filter_by(department_id=id, status="Pending").count()
    inprogress = Grievance.query.filter_by(department_id=id, status="In Progress").count()

    return render_template(
        "admin/a_view_departments.html",
        dept=dept,
        total_grievances=total_grievances,
        handled=handled,
        pending=pending,
        inprogress=inprogress
    )


@app.route("/a_delete_department/<int:id>", methods=["POST", "GET"])
def a_delete_department(id):
    dept = Department.query.get_or_404(id)

    try:
        db.session.delete(dept)
        db.session.commit()
        flash("Department deleted successfully!", "success")
    except:
        db.session.rollback()
        flash("Error deleting department. Try again.", "danger")

    return redirect(url_for("a_view_departments"))

from werkzeug.security import generate_password_hash

@app.route("/a_add_department", methods=["GET", "POST"])
def a_add_department():
    if request.method == "POST":
        name = request.form.get("name")
        username = request.form.get("username")
        password = request.form.get("password")
        pic_file = request.files.get("profile_pic")

        hashed_password = generate_password_hash(password)

        pic_filename = None
        if pic_file and pic_file.filename != "":
            pic_filename = secure_filename(pic_file.filename)
            pic_file.save(os.path.join("static/uploads", pic_filename))

        new_dept = Department(
            name=name,
            username=username,
            password=hashed_password,
            profile_pic=pic_filename
        )
        db.session.add(new_dept)
        db.session.commit()

        flash("Department added successfully!", "success")
        return redirect(url_for("a_manage_departments"))

    return render_template("admin/a_add_department.html")




@app.route('/a_view_notices')
def a_view_notices():
    if 'admin_id' not in session:
        return redirect(url_for('login'))

    notices = Notice.query.order_by(Notice.timestamp.desc()).all()
    return render_template('admin/a_view_notices.html', notices=notices)

@app.route('/a_delete_notice/<int:id>', methods=['POST', 'GET'])
def a_delete_notice(id):
    notice = Notice.query.get_or_404(id)
    db.session.delete(notice)
    db.session.commit()
    flash("Notice deleted successfully!", "success")
    return redirect(url_for('a_view_notices'))


@app.route('/logout')
def logout():
    session.clear()  
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


if __name__ == "__main__":
    app.run(debug=True)