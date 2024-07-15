
import os
import json
from flask import Flask, render_template, request, jsonify, session
import traceback


app = Flask(__name__, static_url_path='/static')
app.secret_key = 'your_secret_key'

@app.route('/')
def index():
    """
    Render the index.html template.

    Returns:
        The rendered index.html template.
    """
    return render_template('index.html')  # Load initial SPA template

@app.route('/project')
def project():
    """
    Render the project.html template.

    Returns:
        The rendered project.html template.
    """
    return render_template('project.html')  # Load Project tab content

@app.route('/artwork')
def artwork():
    """
    Render the artwork.html template.

    Returns:
        The rendered artwork.html template.
    """
    return render_template('artwork.html')  # Load Artwork tab content

@app.route('/sweep')
def sweep():
    """
    Render the sweep.html template.

    Returns:
        The rendered sweep.html template.
    """
    return render_template('sweep.html')  # Load Sweep tab content

@app.route('/create_project', methods=['POST'])
def create_project():
    """
    Create a new project directory and store project data in a JSON file.

    Returns:
        A JSON response indicating the success or failure of the operation.
    """
    data = request.json
    directory_path = data.get('directoryPath')
    
    if directory_path:
        try:
            # Create directory if it doesn't exist
            os.makedirs(directory_path, exist_ok=True)
            
            # Store directory path in session
            session['directory_path'] = directory_path
            
            # Define project.json content (example template)
            project_data = {
                'name': 'My Project',
                'description': 'This is a sample project.',
                'created_by': 'Your Name',
                'created_at': '2024-07-10',
            }
            
            # Write project.json file inside the created directory
            json_file_path = os.path.join(directory_path, 'project.json')
            with open(json_file_path, 'w') as json_file:
                json.dump(project_data, json_file, indent=4)
            
            return jsonify({'success': True})
        
        except Exception as e:
            print(e)  # Log the error for debugging purposes
            return jsonify({'success': False})
    
    return jsonify({'success': False})


@app.route('/save_json', methods=['POST'])
def save_json():
    """
    Save JSON data to a specified file path.

    Returns:
        A JSON response indicating the success or failure of the operation.
    """
    data = request.json
    data_to_save = data.get('data')  # Making it more generic
    save_path = data.get('savePath')
    save_name = data.get('saveName')

    if data_to_save and save_path and save_name:
        try:
            # Construct full file path
            file_path = os.path.join(save_path, save_name)
 
            # Save data to specified file path
            with open(file_path, 'w') as json_file:
                json.dump(data_to_save, json_file, indent=4)

            # Print the full path of the saved file
            print(f"File saved successfully at: {file_path}")

            return jsonify({'success': True})
        
        except Exception as e:
            print(e)  # Log the error for debugging purposes
            return jsonify({'success': False, 'error': str(e)})
    
    return jsonify({'success': False, 'error': 'Missing data or save path/name'})


@app.route('/load_json', methods=['POST'])
def load_json():
    """
    Load JSON data from a specified file path.

    Returns:
        A JSON response containing the loaded data or an error message.
    """
    data = request.json
    json_path = data.get('path')
    if json_path:
        try:
            with open(json_path, 'r') as json_file:
                data_to_load = json.load(json_file)
                #print(data_to_load)
            return jsonify({'success': True, 'data': data_to_load})
        except FileNotFoundError:
            return jsonify({'success': False, 'message': 'File not found.'})
        except Exception as e:
            print(e)  # Log the error for debugging purposes
            return jsonify({'success': False, 'message': str(e)})
    return jsonify({'success': False, 'message': 'No JSON path provided.'})


if __name__ == '__main__':
    app.run(port=8080, debug=True)
