from flask import Blueprint, jsonify, request
from auth import login_required
from models import User, Permission
import json

api = Blueprint('api', __name__)

@api.route('/api/problems', methods=['GET'])
@login_required
def get_problems():
    """
    Get all problems accessible to the user
    ---
    tags:
      - Problems
    security:
      - Bearer: []
    responses:
      200:
        description: List of problems
    """
    user_id = request.user_id
    problems = load_problems()
    
    # Filter problems based on permissions
    accessible_problems = [
        p for p in problems['problems']
        if has_permission(user_id, p['id'], 'read')
    ]
    
    return jsonify(accessible_problems)

@api.route('/api/problems/<int:problem_id>', methods=['GET'])
@login_required
def get_problem(problem_id):
    """
    Get a specific problem
    ---
    tags:
      - Problems
    parameters:
      - name: problem_id
        in: path
        type: integer
        required: true
    security:
      - Bearer: []
    responses:
      200:
        description: Problem details
      404:
        description: Problem not found
    """
    user_id = request.user_id
    
    if not has_permission(user_id, problem_id, 'read'):
        return jsonify({'error': 'Access denied'}), 403
    
    problems = load_problems()
    problem = next(
        (p for p in problems['problems'] if p['id'] == problem_id),
        None
    )
    
    if not problem:
        return jsonify({'error': 'Problem not found'}), 404
    
    return jsonify(problem)

# Add more API endpoints... 