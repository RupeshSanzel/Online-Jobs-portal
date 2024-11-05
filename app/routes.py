# app/routes.py
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import User, Job, Application
from app.forms import RegistrationForm, LoginForm, JobPostForm, ApplicationForm

main = Blueprint('main', __name__)
auth = Blueprint('auth', __name__)
jobs = Blueprint('jobs', __name__)

@main.route('/')
def home():
    recent_jobs = Job.query.order_by(Job.posted_date.desc()).limit(5).all()
    return render_template('home.html', jobs=recent_jobs)

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data, is_employer=form.is_employer.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful!')
        return redirect(url_for('auth.login'))
    return render_template('register.html', form=form)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.home'))
        flash('Invalid email or password')
    return render_template('login.html', form=form)

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.home'))

@jobs.route('/jobs')
def job_list():
    page = request.args.get('page', 1, type=int)
    jobs = Job.query.order_by(Job.posted_date.desc()).paginate(page=page, per_page=10)
    return render_template('jobs.html', jobs=jobs)

@jobs.route('/job/<int:job_id>')
def job_detail(job_id):
    job = Job.query.get_or_404(job_id)
    form = ApplicationForm()
    return render_template('job_detail.html', job=job, form=form)

@jobs.route('/post-job', methods=['GET', 'POST'])
@login_required
def post_job():
    if not current_user.is_employer:
        flash('Only employers can post jobs')
        return redirect(url_for('main.home'))
    form = JobPostForm()
    if form.validate_on_submit():
        job = Job(
            title=form.title.data,
            company=form.company.data,
            location=form.location.data,
            salary=form.salary.data,
            description=form.description.data,
            requirements=form.requirements.data,
            employer=current_user
        )
        db.session.add(job)
        db.session.commit()
        flash('Job posted successfully!')
        return redirect(url_for('jobs.job_list'))
    return render_template('post_job.html', form=form)

@jobs.route('/apply/<int:job_id>', methods=['POST'])
@login_required
def apply_job(job_id):
    if current_user.is_employer:
        flash('Employers cannot apply for jobs')
        return redirect(url_for('jobs.job_detail', job_id=job_id))
    
    job = Job.query.get_or_404(job_id)
    form = ApplicationForm()
    
    if form.validate_on_submit():
        application = Application(
            job=job,
            applicant=current_user,
            resume=form.resume.data,
            cover_letter=form.cover_letter.data
        )
        db.session.add(application)
        db.session.commit()
        flash('Application submitted successfully!')
        return redirect(url_for('jobs.job_detail', job_id=job_id))
    
    return redirect(url_for('jobs.job_detail', job_id=job_id))

@jobs.route('/my-applications')
@login_required
def my_applications():
    applications = Application.query.filter_by(user_id=current_user.id).all()
    return render_template('applications.html', applications=applications)
# app/routes.py (add these new routes)

@jobs.route('/manage-applications')
@login_required
def manage_applications():
    if not current_user.is_employer:
        flash('Access denied. Employer privileges required.')
        return redirect(url_for('main.home'))
    
    # Get all jobs posted by the employer
    employer_jobs = Job.query.filter_by(employer_id=current_user.id).all()
    
    # Get all applications for these jobs
    applications_by_job = {}
    for job in employer_jobs:
        applications = Application.query.filter_by(job_id=job.id)\
            .order_by(Application.applied_date.desc()).all()
        applications_by_job[job.id] = applications
    
    return render_template('manage_applications.html', 
                         jobs=employer_jobs, 
                         applications_by_job=applications_by_job)

@jobs.route('/update-application-status/<int:application_id>', methods=['POST'])
@login_required
def update_application_status(application_id):
    if not current_user.is_employer:
        return jsonify({'error': 'Access denied'}), 403

    application = Application.query.get_or_404(application_id)
    
    # Verify that the employer owns the job
    if application.job.employer_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403

    status = request.form.get('status')
    feedback = request.form.get('feedback')
    
    if status not in ['pending', 'viewed', 'selected', 'rejected']:
        return jsonify({'error': 'Invalid status'}), 400

    application.status = status
    application.feedback = feedback
    db.session.commit()

    return jsonify({
        'success': True,
        'status': status,
        'feedback': feedback
    })