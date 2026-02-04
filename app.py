from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, flash, session
import json
from datetime import datetime, timedelta
import os
import threading
import schedule
import time
import pandas as pd
from io import BytesIO
import pytz
from weasyprint import HTML
import calendar
from auth import login_required, admin_required, generate_token, verify_token
from models import User, Permission, Group
from backup import start_backup_scheduler
from api import api

app = Flask(__name__)

# Ensure data directory exists
if not os.path.exists('data'):
    os.makedirs('data')

# Initialize problems.json if it doesn't exist
if not os.path.exists('data/problems.json'):
    with open('data/problems.json', 'w') as f:
        json.dump({"problems": []}, f)

def load_problems():
    with open('data/problems.json', 'r') as f:
        return json.load(f)

def save_problems(problems):
    with open('data/problems.json', 'w') as f:
        json.dump(problems, f, indent=4)

def send_reminder_email(problem):
    # TODO: Implement actual email sending
    print(f"Sending reminder for problem: {problem['title']}")

def check_reminders():
    problems = load_problems()['problems']
    today = datetime.now().date()
    
    for problem in problems:
        due_date = datetime.strptime(problem['due_date'], '%Y-%m-%d').date()
        days_until_due = (due_date - today).days
        
        if days_until_due in [7, 3, 1] and problem['status'] != 'closed':
            send_reminder_email(problem)

# Start reminder checker in background
def run_schedule():
    while True:
        schedule.run_pending()
        time.sleep(60)

schedule.every().day.at("09:00").do(check_reminders)
reminder_thread = threading.Thread(target=run_schedule, daemon=True)
reminder_thread.start()

@app.route('/')
def dashboard():
    problems = load_problems()
    return render_template('dashboard.html', problems=problems['problems'])

@app.route('/add_problem', methods=['GET', 'POST'])
@login_required
def add_problem():
    if request.method == 'POST':
        data = load_problems()
        new_problem = {
            'id': len(data['problems']) + 1,
            'title': request.form['title'],
            'category': request.form['category'],
            'description': request.form['description'],
            'status': 'open',
            'created_date': datetime.now().strftime('%Y-%m-%d'),
            'due_date': request.form['due_date'],
            'tags': request.form.getlist('tags'),
            'owner_id': session['user_id'],
            'group_id': request.form.get('group_id'),
            'visibility': request.form.get('visibility', 'private'),
            'history': [{
                'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'action': 'created',
                'details': 'בעיה נוצרה'
            }]
        }
        data['problems'].append(new_problem)
        save_problems(data)
        return jsonify({'success': True})
    
    user_groups = Group.load_user_groups(session['user_id'])
    return render_template('problem_form.html', groups=user_groups)

@app.route('/delete_problem/<int:problem_id>', methods=['POST'])
def delete_problem(problem_id):
    data = load_problems()
    data['problems'] = [p for p in data['problems'] if p['id'] != problem_id]
    save_problems(data)
    return jsonify({'success': True})

@app.route('/edit_problem/<int:problem_id>', methods=['GET', 'POST'])
def edit_problem(problem_id):
    data = load_problems()
    problem = next((p for p in data['problems'] if p['id'] == problem_id), None)
    
    if request.method == 'POST':
        old_status = problem['status']
        new_status = request.form['status']
        
        # Create history entry
        history_entry = {
            'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'action': 'edited',
            'details': f'שדות שעודכנו: {", ".join(request.form.keys())}'
        }
        
        if old_status != new_status:
            history_entry['details'] = f'סטטוס שונה מ-{old_status} ל-{new_status}'
        
        problem.update({
            'title': request.form['title'],
            'category': request.form['category'],
            'description': request.form['description'],
            'status': new_status,
            'due_date': request.form['due_date'],
            'tags': request.form.getlist('tags')
        })
        
        if 'history' not in problem:
            problem['history'] = []
        problem['history'].append(history_entry)
        
        save_problems(data)
        return jsonify({'success': True})
    
    return render_template('problem_form.html', problem=problem, edit_mode=True)

@app.route('/filter_problems')
def filter_problems():
    category = request.args.get('category')
    status = request.args.get('status')
    search = request.args.get('search', '').lower()
    
    problems = load_problems()['problems']
    
    if category and category != 'all':
        problems = [p for p in problems if p['category'] == category]
    if status and status != 'all':
        problems = [p for p in problems if p['status'] == status]
    if search:
        problems = [p for p in problems if search in p['title'].lower() or search in p['description'].lower()]
    
    return jsonify(problems)

@app.route('/problem_stats')
def problem_stats():
    problems = load_problems()['problems']
    
    total = len(problems)
    by_status = {}
    by_category = {}
    overdue = 0
    total_time_spent = 0
    today = datetime.now().date()
    
    for problem in problems:
        # Status stats
        status = problem['status']
        by_status[status] = by_status.get(status, 0) + 1
        
        # Category stats
        category = problem['category']
        by_category[category] = by_category.get(category, 0) + 1
        
        # Overdue problems
        due_date = datetime.strptime(problem['due_date'], '%Y-%m-%d').date()
        if due_date < today and problem['status'] != 'closed':
            overdue += 1
            
        # Add time tracking stats
        total_time_spent += problem.get('total_time', 0)
    
    return jsonify({
        'total': total,
        'by_status': by_status,
        'by_category': by_category,
        'overdue': overdue,
        'total_time_spent': total_time_spent,
        'avg_time_per_problem': total_time_spent / total if total > 0 else 0
    })

@app.route('/add_subtask/<int:problem_id>', methods=['POST'])
def add_subtask(problem_id):
    data = load_problems()
    problem = next((p for p in data['problems'] if p['id'] == problem_id), None)
    
    if problem:
        new_subtask = {
            'id': len(problem.get('subtasks', [])) + 1,
            'title': request.form['title'],
            'status': 'pending',
            'created_date': datetime.now().strftime('%Y-%m-%d'),
            'completed_date': None
        }
        
        if 'subtasks' not in problem:
            problem['subtasks'] = []
        
        problem['subtasks'].append(new_subtask)
        
        # Add to history
        history_entry = {
            'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'action': 'subtask_added',
            'details': f'נוספה משימת משנה: {new_subtask["title"]}'
        }
        problem['history'].append(history_entry)
        
        save_problems(data)
        return jsonify({'success': True, 'subtask': new_subtask})
    
    return jsonify({'success': False}), 404

@app.route('/toggle_subtask/<int:problem_id>/<int:subtask_id>', methods=['POST'])
def toggle_subtask(problem_id, subtask_id):
    data = load_problems()
    problem = next((p for p in data['problems'] if p['id'] == problem_id), None)
    
    if problem and 'subtasks' in problem:
        subtask = next((s for s in problem['subtasks'] if s['id'] == subtask_id), None)
        if subtask:
            subtask['status'] = 'completed' if subtask['status'] == 'pending' else 'pending'
            subtask['completed_date'] = datetime.now().strftime('%Y-%m-%d') if subtask['status'] == 'completed' else None
            
            save_problems(data)
            return jsonify({'success': True})
    
    return jsonify({'success': False}), 404

@app.route('/timeline')
def timeline():
    problems = load_problems()['problems']
    timeline_data = []
    
    for problem in problems:
        timeline_data.append({
            'id': problem['id'],
            'title': problem['title'],
            'start_date': problem['created_date'],
            'end_date': problem['due_date'],
            'status': problem['status'],
            'category': problem['category']
        })
    
    return render_template('timeline.html', timeline_data=timeline_data)

@app.route('/export/<format>')
def export_data(format):
    problems = load_problems()['problems']
    
    if format == 'excel':
        # Create a more detailed Excel report
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Problems sheet
            df_problems = pd.DataFrame(problems)
            df_problems.to_excel(writer, sheet_name='Problems', index=False)
            
            # Solutions sheet
            solutions_data = []
            for problem in problems:
                for solution in problem.get('solutions', []):
                    solution_data = {
                        'problem_id': problem['id'],
                        'problem_title': problem['title'],
                        **solution
                    }
                    solutions_data.append(solution_data)
            
            if solutions_data:
                df_solutions = pd.DataFrame(solutions_data)
                df_solutions.to_excel(writer, sheet_name='Solutions', index=False)
            
            # Time logs sheet
            time_logs_data = []
            for problem in problems:
                for log in problem.get('time_logs', []):
                    log_data = {
                        'problem_id': problem['id'],
                        'problem_title': problem['title'],
                        **log
                    }
                    time_logs_data.append(log_data)
            
            if time_logs_data:
                df_time_logs = pd.DataFrame(time_logs_data)
                df_time_logs.to_excel(writer, sheet_name='Time Logs', index=False)
            
            # Add some basic charts
            workbook = writer.book
            problems_sheet = writer.sheets['Problems']
            
            # Status distribution pie chart
            status_counts = df_problems['status'].value_counts()
            chart1 = workbook.add_chart({'type': 'pie'})
            chart1.add_series({
                'categories': ['Problems', 1, 0, len(status_counts), 0],
                'values': ['Problems', 1, 1, len(status_counts), 1],
                'name': 'Status Distribution'
            })
            problems_sheet.insert_chart('K2', chart1)
        
        output.seek(0)
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='problems_detailed_export.xlsx'
        )
    
    return jsonify({'error': 'Invalid format'}), 400

@app.route('/add_comment/<int:problem_id>', methods=['POST'])
def add_comment(problem_id):
    data = load_problems()
    problem = next((p for p in data['problems'] if p['id'] == problem_id), None)
    
    if problem:
        new_comment = {
            'id': len(problem.get('comments', [])) + 1,
            'text': request.form['text'],
            'created_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'user': 'אנונימי',  # Will be replaced with actual user when auth is added
            'mentions': extract_mentions(request.form['text'])
        }
        
        if 'comments' not in problem:
            problem['comments'] = []
            
        problem['comments'].append(new_comment)
        
        # Add to history
        history_entry = {
            'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'action': 'comment_added',
            'details': 'נוספה תגובה חדשה'
        }
        problem['history'].append(history_entry)
        
        save_problems(data)
        return jsonify({'success': True, 'comment': new_comment})
    
    return jsonify({'success': False}), 404

@app.route('/log_time/<int:problem_id>', methods=['POST'])
def log_time(problem_id):
    data = load_problems()
    problem = next((p for p in data['problems'] if p['id'] == problem_id), None)
    
    if problem:
        time_entry = {
            'id': len(problem.get('time_logs', [])) + 1,
            'minutes': int(request.form['minutes']),
            'description': request.form['description'],
            'logged_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'user': 'אנונימי'
        }
        
        if 'time_logs' not in problem:
            problem['time_logs'] = []
            
        problem['time_logs'].append(time_entry)
        
        # Update total time spent
        problem['total_time'] = sum(log['minutes'] for log in problem['time_logs'])
        
        save_problems(data)
        return jsonify({'success': True, 'time_entry': time_entry})
    
    return jsonify({'success': False}), 404

def extract_mentions(text):
    """Extract @mentions from text"""
    mentions = []
    words = text.split()
    for word in words:
        if word.startswith('@'):
            mentions.append(word[1:])
    return mentions

@app.route('/kanban')
def kanban_view():
    problems = load_problems()['problems']
    columns = {
        'open': [],
        'in_progress': [],
        'review': [],
        'closed': []
    }
    
    for problem in problems:
        columns[problem['status']].append(problem)
    
    return render_template('kanban.html', columns=columns)

@app.route('/gantt')
def gantt_view():
    problems = load_problems()['problems']
    return render_template('gantt.html', problems=problems)

@app.route('/update_status/<int:problem_id>', methods=['POST'])
def update_status(problem_id):
    data = load_problems()
    problem = next((p for p in data['problems'] if p['id'] == problem_id), None)
    
    if problem:
        new_status = request.form['status']
        old_status = problem['status']
        problem['status'] = new_status
        
        history_entry = {
            'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'action': 'status_changed',
            'details': f'סטטוס שונה מ-{old_status} ל-{new_status}'
        }
        problem['history'].append(history_entry)
        
        save_problems(data)
        return jsonify({'success': True})
    
    return jsonify({'success': False}), 404

@app.route('/add_solution/<int:problem_id>', methods=['POST'])
def add_solution(problem_id):
    data = load_problems()
    problem = next((p for p in data['problems'] if p['id'] == problem_id), None)
    
    if problem:
        solution = {
            'id': len(problem.get('solutions', [])) + 1,
            'description': request.form['description'],
            'steps': request.form['steps'].split('\n'),
            'created_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'effectiveness': request.form.get('effectiveness', 0),
            'implemented': False
        }
        
        if 'solutions' not in problem:
            problem['solutions'] = []
            
        problem['solutions'].append(solution)
        
        history_entry = {
            'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'action': 'solution_added',
            'details': 'נוסף פתרון חדש'
        }
        problem['history'].append(history_entry)
        
        save_problems(data)
        return jsonify({'success': True, 'solution': solution})
    
    return jsonify({'success': False}), 404

@app.route('/implement_solution/<int:problem_id>/<int:solution_id>', methods=['POST'])
def implement_solution(problem_id, solution_id):
    data = load_problems()
    problem = next((p for p in data['problems'] if p['id'] == problem_id), None)
    
    if problem and 'solutions' in problem:
        solution = next((s for s in problem['solutions'] if s['id'] == solution_id), None)
        if solution:
            solution['implemented'] = True
            solution['implementation_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            history_entry = {
                'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'action': 'solution_implemented',
                'details': f'פתרון {solution_id} יושם'
            }
            problem['history'].append(history_entry)
            
            save_problems(data)
            return jsonify({'success': True})
    
    return jsonify({'success': False}), 404

@app.route('/tags/autocomplete')
def tags_autocomplete():
    query = request.args.get('q', '').lower()
    problems = load_problems()['problems']
    
    # Collect all unique tags
    all_tags = set()
    for problem in problems:
        all_tags.update(tag.lower() for tag in problem.get('tags', []))
    
    # Filter tags by query
    matching_tags = [tag for tag in all_tags if query in tag]
    return jsonify(matching_tags)

@app.route('/reports')
def reports():
    problems = load_problems()['problems']
    today = datetime.now().date()
    
    # Calculate various metrics
    metrics = {
        'total_problems': len(problems),
        'avg_resolution_time': 0,
        'overdue_percentage': 0,
        'completion_rate': 0,
        'category_distribution': {},
        'monthly_trends': {},
        'tag_usage': {},
        'solution_effectiveness': {}
    }
    
    closed_problems = [p for p in problems if p['status'] == 'closed']
    if closed_problems:
        # Average resolution time
        resolution_times = []
        for problem in closed_problems:
            created = datetime.strptime(problem['created_date'], '%Y-%m-%d').date()
            history = problem.get('history', [])
            closed_entry = next((h for h in reversed(history) if h['action'] == 'status_changed' and 'סגור' in h['details']), None)
            if closed_entry:
                closed_date = datetime.strptime(closed_entry['date'].split()[0], '%Y-%m-%d').date()
                resolution_times.append((closed_date - created).days)
        
        if resolution_times:
            metrics['avg_resolution_time'] = sum(resolution_times) / len(resolution_times)
    
    # Overdue percentage
    overdue = sum(1 for p in problems if datetime.strptime(p['due_date'], '%Y-%m-%d').date() < today and p['status'] != 'closed')
    metrics['overdue_percentage'] = (overdue / len(problems)) * 100 if problems else 0
    
    # Completion rate
    metrics['completion_rate'] = (len(closed_problems) / len(problems)) * 100 if problems else 0
    
    # Category distribution
    for problem in problems:
        category = problem['category']
        metrics['category_distribution'][category] = metrics['category_distribution'].get(category, 0) + 1
    
    # Monthly trends
    for problem in problems:
        month = problem['created_date'][:7]  # YYYY-MM
        metrics['monthly_trends'][month] = metrics['monthly_trends'].get(month, 0) + 1
    
    # Tag usage
    for problem in problems:
        for tag in problem.get('tags', []):
            metrics['tag_usage'][tag] = metrics['tag_usage'].get(tag, 0) + 1
    
    # Solution effectiveness
    for problem in problems:
        for solution in problem.get('solutions', []):
            if solution.get('implemented'):
                effectiveness = solution.get('effectiveness', 0)
                metrics['solution_effectiveness'][problem['id']] = effectiveness
    
    return render_template('reports.html', metrics=metrics)

@app.route('/calendar')
def calendar_view():
    year = int(request.args.get('year', datetime.now().year))
    month = int(request.args.get('month', datetime.now().month))
    
    # Get calendar data
    cal = calendar.monthcalendar(year, month)
    month_name = calendar.month_name[month]
    
    # Get problems for this month
    problems = load_problems()['problems']
    problem_dates = {}
    
    for problem in problems:
        due_date = datetime.strptime(problem['due_date'], '%Y-%m-%d').date()
        if due_date.year == year and due_date.month == month:
            day = due_date.day
            if day not in problem_dates:
                problem_dates[day] = []
            problem_dates[day].append(problem)
    
    return render_template('calendar.html',
                         calendar=cal,
                         month_name=month_name,
                         year=year,
                         month=month,
                         problem_dates=problem_dates)

@app.route('/notifications')
def get_notifications():
    problems = load_problems()['problems']
    today = datetime.now().date()
    notifications = []
    
    # Due date notifications
    for problem in problems:
        if problem['status'] != 'closed':
            due_date = datetime.strptime(problem['due_date'], '%Y-%m-%d').date()
            days_until_due = (due_date - today).days
            
            if days_until_due <= 7:
                notifications.append({
                    'type': 'due_date',
                    'problem_id': problem['id'],
                    'title': problem['title'],
                    'message': f'יש לך {days_until_due} ימים לסיים את הבעיה',
                    'priority': 'high' if days_until_due <= 3 else 'medium',
                    'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
    
    # Inactive problems notifications
    for problem in problems:
        if problem['status'] not in ['closed', 'review']:
            last_activity = max(
                datetime.strptime(entry['date'].split()[0], '%Y-%m-%d').date()
                for entry in problem.get('history', [{'date': problem['created_date'] + ' 00:00:00'}])
            )
            days_inactive = (today - last_activity).days
            
            if days_inactive >= 7:
                notifications.append({
                    'type': 'inactive',
                    'problem_id': problem['id'],
                    'title': problem['title'],
                    'message': f'לא הייתה פעילות בבעיה זו {days_inactive} ימים',
                    'priority': 'medium',
                    'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
    
    # Sort notifications by priority and date
    priority_order = {'high': 0, 'medium': 1, 'low': 2}
    notifications.sort(key=lambda x: (priority_order[x['priority']], x['date']))
    
    return jsonify(notifications)

@app.route('/search')
def advanced_search():
    query = request.args.get('q', '').lower()
    category = request.args.get('category')
    status = request.args.get('status')
    tags = request.args.getlist('tags')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    problems = load_problems()['problems']
    
    if query:
        problems = [p for p in problems if
                   query in p['title'].lower() or
                   query in p['description'].lower() or
                   any(query in comment['text'].lower() for comment in p.get('comments', [])) or
                   any(query in solution['description'].lower() for solution in p.get('solutions', []))]
    
    if category:
        problems = [p for p in problems if p['category'] == category]
    
    if status:
        problems = [p for p in problems if p['status'] == status]
    
    if tags:
        problems = [p for p in problems if all(tag in p.get('tags', []) for tag in tags)]
    
    if date_from:
        date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
        problems = [p for p in problems if datetime.strptime(p['created_date'], '%Y-%m-%d').date() >= date_from]
    
    if date_to:
        date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
        problems = [p for p in problems if datetime.strptime(p['due_date'], '%Y-%m-%d').date() <= date_to]
    
    return jsonify(problems)

@app.route('/activity_log')
def activity_log():
    problems = load_problems()['problems']
    activities = []
    
    for problem in problems:
        for entry in problem.get('history', []):
            activities.append({
                'problem_id': problem['id'],
                'problem_title': problem['title'],
                'date': entry['date'],
                'action': entry['action'],
                'details': entry['details']
            })
    
    # Sort activities by date (newest first)
    activities.sort(key=lambda x: x['date'], reverse=True)
    
    return render_template('activity_log.html', activities=activities)

@app.route('/templates')
def problem_templates():
    """View problem templates"""
    templates = load_templates()
    return render_template('templates.html', templates=templates['templates'])

@app.route('/save_as_template/<int:problem_id>', methods=['POST'])
def save_as_template(problem_id):
    """Save problem as template"""
    data = load_problems()
    problem = next((p for p in data['problems'] if p['id'] == problem_id), None)
    
    if problem:
        template = {
            'id': generate_template_id(),
            'name': request.form.get('template_name', problem['title']),
            'category': problem['category'],
            'description': problem['description'],
            'subtasks': problem.get('subtasks', []),
            'tags': problem.get('tags', []),
            'created_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        templates = load_templates()
        templates['templates'].append(template)
        save_templates(templates)
        
        return jsonify({'success': True})
    
    return jsonify({'success': False}), 404

@app.route('/create_from_template/<int:template_id>')
def create_from_template(template_id):
    """Create new problem from template"""
    templates = load_templates()
    template = next((t for t in templates['templates'] if t['id'] == template_id), None)
    
    if template:
        return render_template('problem_form.html', template=template)
    
    return redirect(url_for('dashboard'))

@app.route('/reminders')
def reminders():
    """View and manage reminders"""
    problems = load_problems()['problems']
    reminders_list = []
    today = datetime.now().date()
    
    for problem in problems:
        if problem['status'] != 'closed':
            due_date = datetime.strptime(problem['due_date'], '%Y-%m-%d').date()
            days_until_due = (due_date - today).days
            
            if days_until_due <= 7:
                reminder = {
                    'problem_id': problem['id'],
                    'title': problem['title'],
                    'due_date': problem['due_date'],
                    'days_left': days_until_due,
                    'category': problem['category'],
                    'priority': 'high' if days_until_due <= 3 else 'medium'
                }
                reminders_list.append(reminder)
    
    return render_template('reminders.html', reminders=reminders_list)

@app.route('/save_reminder_settings', methods=['POST'])
def save_reminder_settings():
    """Save reminder settings"""
    settings = {
        'days_before': request.form.getlist('days_before[]'),
        'notification_types': request.form.getlist('notification_types[]')
    }
    
    # Save settings to file
    with open(os.path.join('data', 'reminder_settings.json'), 'w') as f:
        json.dump(settings, f, indent=4)
    
    return jsonify({'success': True})

@app.route('/tags/suggest')
def suggest_tags():
    """Suggest tags based on problem content"""
    text = request.args.get('text', '').lower()
    
    # Load all existing tags for reference
    problems = load_problems()['problems']
    existing_tags = set()
    for problem in problems:
        existing_tags.update(tag.lower() for tag in problem.get('tags', []))
    
    # Simple keyword-based suggestions
    keywords = {
        'תקציב': ['כספים', 'הוצאות', 'חיסכון'],
        'כסף': ['כספים', 'תשלום', 'הוצאות'],
        'בריאות': ['רפואה', 'טיפול', 'בדיקות'],
        'עבודה': ['קריירה', 'משרה', 'מקצועי'],
        'משפחה': ['הורים', 'ילדים', 'זוגיות'],
        'דחוף': ['קריטי', 'חשוב', 'מיידי']
    }
    
    suggested_tags = set()
    
    # Add matching keywords
    for key, values in keywords.items():
        if key in text:
            suggested_tags.update(values)
    
    # Add similar existing tags
    for tag in existing_tags:
        if any(word in tag for word in text.split()):
            suggested_tags.add(tag)
    
    return jsonify(list(suggested_tags))

@app.route('/advanced_reports')
def advanced_reports():
    """Generate advanced reports and analytics"""
    problems = load_problems()['problems']
    today = datetime.now().date()
    
    # Calculate advanced metrics
    metrics = {
        'resolution_times': [],
        'category_success_rates': {},
        'tag_correlations': {},
        'monthly_workload': {},
        'problem_complexity': {}
    }
    
    for problem in problems:
        # Resolution time analysis
        if problem['status'] == 'closed':
            created = datetime.strptime(problem['created_date'], '%Y-%m-%d').date()
            history = problem.get('history', [])
            closed_entry = next((h for h in reversed(history) if h['action'] == 'status_changed' and 'סגור' in h['details']), None)
            if closed_entry:
                closed_date = datetime.strptime(closed_entry['date'].split()[0], '%Y-%m-%d').date()
                resolution_time = (closed_date - created).days
                metrics['resolution_times'].append({
                    'problem': problem['title'],
                    'days': resolution_time,
                    'category': problem['category']
                })
        
        # Category success rate
        category = problem['category']
        if category not in metrics['category_success_rates']:
            metrics['category_success_rates'][category] = {'total': 0, 'solved': 0}
        metrics['category_success_rates'][category]['total'] += 1
        if problem['status'] == 'closed':
            metrics['category_success_rates'][category]['solved'] += 1
        
        # Tag correlation analysis
        tags = problem.get('tags', [])
        for tag1 in tags:
            for tag2 in tags:
                if tag1 < tag2:
                    key = f"{tag1}-{tag2}"
                    metrics['tag_correlations'][key] = metrics['tag_correlations'].get(key, 0) + 1
        
        # Monthly workload
        month = problem['created_date'][:7]
        metrics['monthly_workload'][month] = metrics['monthly_workload'].get(month, 0) + 1
        
        # Problem complexity score
        complexity_score = 0
        complexity_score += len(problem.get('subtasks', [])) * 2
        complexity_score += len(problem.get('comments', []))
        complexity_score += len(problem.get('time_logs', [])) * 0.5
        metrics['problem_complexity'][problem['title']] = complexity_score
    
    return render_template('advanced_reports.html', metrics=metrics)

def load_templates():
    """Load templates from JSON file"""
    templates_file = os.path.join('data', 'templates.json')
    if not os.path.exists(templates_file):
        with open(templates_file, 'w') as f:
            json.dump({"templates": []}, f)
    
    with open(templates_file, 'r') as f:
        return json.load(f)

def save_templates(templates):
    """Save templates to JSON file"""
    with open(os.path.join('data', 'templates.json'), 'w') as f:
        json.dump(templates, f, indent=4)

def generate_template_id():
    """Generate a new template ID"""
    templates = load_templates()
    if not templates['templates']:
        return 1
    return max(t['id'] for t in templates['templates']) + 1

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        users = User.load_users()
        user = users.get(username)
        
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = username
            session['is_admin'] = user['role'] == 'admin'
            
            # Update last login
            user['last_login'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            User.save_users(users)
            
            return redirect(url_for('dashboard'))
        
        flash('שם משתמש או סיסמה שגויים', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        users = User.load_users()
        if username in users:
            flash('שם המשתמש כבר קיים', 'error')
            return render_template('register.html')
        
        users[username] = {
            'email': email,
            'password_hash': generate_password_hash(password),
            'role': 'user',
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'last_login': None,
            'settings': {}
        }
        
        User.save_users(users)
        flash('ההרשמה הושלמה בהצלחה', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/share_problem/<int:problem_id>', methods=['POST'])
@login_required
def share_problem(problem_id):
    """Share a problem with another user"""
    target_username = request.form['username']
    permission_type = request.form['permission_type']
    
    users = User.load_users()
    if target_username not in users:
        return jsonify({'error': 'User not found'}), 404
    
    permissions = Permission.load_permissions()
    
    # Add new permission
    permission = {
        'user_id': target_username,
        'resource_id': problem_id,
        'permission_type': permission_type,
        'granted_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    if str(problem_id) not in permissions:
        permissions[str(problem_id)] = []
    
    permissions[str(problem_id)].append(permission)
    Permission.save_permissions(permissions)
    
    return jsonify({'success': True})

def has_permission(user_id, resource_id, required_permission):
    """Check if user has required permission"""
    if session.get('is_admin'):
        return True
        
    permissions = Permission.load_permissions()
    resource_permissions = permissions.get(str(resource_id), [])
    
    user_permission = next(
        (p for p in resource_permissions if p['user_id'] == user_id),
        None
    )
    
    if not user_permission:
        return False
    
    permission_levels = {
        'read': 1,
        'write': 2,
        'admin': 3
    }
    
    required_level = permission_levels[required_permission]
    actual_level = permission_levels[user_permission['permission_type']]
    
    return actual_level >= required_level

@app.route('/groups')
@login_required
def groups():
    """View and manage groups"""
    user_groups = Group.load_user_groups(session['user_id'])
    return render_template('groups.html', groups=user_groups)

@app.route('/create_group', methods=['POST'])
@login_required
def create_group():
    """Create a new group"""
    name = request.form['name']
    description = request.form['description']
    
    group = {
        'id': generate_group_id(),
        'name': name,
        'description': description,
        'creator_id': session['user_id'],
        'members': [session['user_id']],  # Creator is automatically a member
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'open_problems': 0,
        'solved_problems': 0
    }
    
    groups = Group.load_groups()
    groups['groups'].append(group)
    Group.save_groups(groups)
    
    return jsonify({'success': True, 'group': group})

def generate_group_id():
    """Generate a new group ID"""
    groups = Group.load_groups()
    if not groups['groups']:
        return 1
    return max(g['id'] for g in groups['groups']) + 1

@app.route('/invite_to_group/<int:group_id>', methods=['POST'])
@login_required
def invite_to_group(group_id):
    """Invite a user to a group"""
    email = request.form['email']
    groups = Group.load_groups()
    group = next((g for g in groups['groups'] if g['id'] == group_id), None)
    
    if group:
        # TODO: Send actual email invitation
        if email not in group['members']:
            group['members'].append(email)
            Group.save_groups(groups)
            return jsonify({'success': True})
    
    return jsonify({'success': False}), 404

@app.route('/add_member_to_group/<int:group_id>', methods=['POST'])
@login_required
def add_member_to_group(group_id):
    """Add a member to a group"""
    username = request.form['username']
    groups = Group.load_groups()
    group = next((g for g in groups['groups'] if g['id'] == group_id), None)
    
    if group and username not in group['members']:
        group['members'].append(username)
        Group.save_groups(groups)
        return jsonify({'success': True})
    
    return jsonify({'success': False}), 404

@app.route('/delete_group/<int:group_id>', methods=['POST'])
@login_required
def delete_group(group_id):
    """Delete a group"""
    groups = Group.load_groups()
    group = next((g for g in groups['groups'] if g['id'] == group_id), None)
    
    if group and group['creator_id'] == session['user_id']:
        groups['groups'] = [g for g in groups['groups'] if g['id'] != group_id]
        Group.save_groups(groups)
        return jsonify({'success': True})
    
    return jsonify({'success': False}), 403

if __name__ == '__main__':
    app.run(debug=True) 