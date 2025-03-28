
import os
import subprocess
import shlex
import json
from flask import Flask, render_template, request, jsonify, session, Response, session
import uuid
import traceback
from werkzeug.utils import secure_filename
from datetime import datetime


SESSION_MODE = False


app = Flask(__name__, static_url_path='/static')
app.secret_key = 'your_secret_key'

CONURE_PATH = os.environ.get('CONURE_PATH')
if CONURE_PATH is None:
    print("CONURE_PATH is not set!")
else:
    print(f"CONURE_PATH is set to: {CONURE_PATH}")
    ARTWORK_GENERATOR_PATH = CONURE_PATH + "/artwork_generator/artwork_generator.py"

WORKSPACE_PATH = "/projects/bitstream/emon/conure_workspace/sessions/"
SWEEP_GENERATOR_PATH = CONURE_PATH + "/sweep/sweep.py"
SIMULATOR_CONFIG_PATH = CONURE_PATH + "/simulator/config.json"

#CONURE_PATH = "/projects/bitstream/emon/projects/conure"
#CONURE_PATH = "/home/emon/Documents/Projects/conure"





@app.route('/get_app_mode', methods=['POST'])
def get_app_mode():
    return jsonify({"session_mode": SESSION_MODE})

@app.route('/get_session_path', methods=['GET'])
def get_session_path():
    if "session_path" in session:
        return {'session_path': session["session_path"]}, 200
    else:
        return {'error': 'Session path not found'}, 404




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
def create_project_public():
    """
    Create a new project directory and store project data in a JSON file.
    Also change the server's working directory to the new project directory.

    Returns:
        A JSON response indicating the success or failure of the operation.
    """
    
    print("PUBLIC SESSION")

    if SESSION_MODE == True:
        if 'session_id' not in session:
            session['session_id'] = str(uuid.uuid4())  # Generate a unique session ID
            print("NEW SESSION WITH ID ", session['session_id'])
    else:
        session['session_id'] = data.get('directoryPath')
        print("NEW SESSION WITH ID ", session['session_id'])


    
    data = request.json
    print(data)
    print(data["projectName"])

    #session_path = data.get('directoryPath')
    session_path = WORKSPACE_PATH + session['session_id']
    PROJECT_PATH = session_path
    session["session_path"] = WORKSPACE_PATH + session['session_id']
    print("SESSION PATH IS  ", session["session_path"])

    if session_path:
        try:
            # Expand the user path to handle the tilde (~) symbol
            session_path = os.path.expanduser(session_path)
            
            # Create directory if it doesn't exist
            os.makedirs(session_path, exist_ok=True)
            
            # Store directory path in session
            session['session_path'] = session_path
            
            # Define project.json content (example template)
            project_data = {
                'name': data["projectName"],
                'description': 'This is a sample project.',
                'created_by': 'Your Name',
                'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            
            # Write project.json file inside the created directory
            json_file_path = os.path.join(session_path, 'project.json')
            with open(json_file_path, 'w') as json_file:
                json.dump(project_data, json_file, indent=4)
            
            # Change the server's working directory to the new project directory
            os.chdir(session_path)
            
            return jsonify({'success': True})
        
        except Exception as e:
            print(e)  # Log the error for debugging purposes
            return jsonify({'success': False, 'error': str(e)})
    
    return jsonify({'success': False, 'error': 'Invalid directory path'})





# @app.route('/save_json', methods=['POST'])
# def save_json():
#     """
#     Save JSON data to a specified file path.

#     Returns:
#         A JSON response indicating the success or failure of the operation.
#     """
#     data = request.json
#     data_to_save = data.get('data')  # Making it more generic
#     save_path = data.get('savePath')
#     save_name = data.get('saveName')

#     if data_to_save and save_path and save_name:
#         try:
#             # Construct full file path
#             file_path = os.path.join(save_path, save_name)
 
#             # Save data to specified file path
#             with open(file_path, 'w') as json_file:
#                 json.dump(data_to_save, json_file, indent=4)

#             # Print the full path of the saved file
#             print(f"File saved successfully at: {file_path}")

#             return jsonify({'success': True})
        
#         except Exception as e:
#             print(e)  # Log the error for debugging purposes
#             return jsonify({'success': False, 'error': str(e)})
    
#     return jsonify({'success': False, 'error': 'Missing data or save path/name'})


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

    if not data_to_save:
        return jsonify({'success': False, 'error': 'No data to save provided'}), 400
    if not save_path:
        return jsonify({'success': False, 'error': 'No save path provided'}), 400
    if not save_name:
        return jsonify({'success': False, 'error': 'No save name provided'}), 400

    try:
        # Expand user path to handle tilde (~) symbol
        save_path = os.path.expanduser(save_path)
        
        # Ensure the path is absolute to prevent directory traversal attacks
        if not os.path.isabs(save_path):
            return jsonify({'success': False, 'error': 'Invalid save path provided'}), 400

        # Create directory if it doesn't exist
        os.makedirs(save_path, exist_ok=True)

        # Construct full file path
        file_path = os.path.join(save_path, save_name)
 
        # Save data to specified file path
        with open(file_path, 'w') as json_file:
            json.dump(data_to_save, json_file, indent=4)

        # Print the full path of the saved file
        print(f"File saved successfully at: {file_path}")

        return jsonify({'success': True, 'filePath': file_path})
    
    except Exception as e:
        print(f"Exception occurred while saving file: {e}")  # Log the error for debugging purposes
        return jsonify({'success': False, 'error': str(e)}), 500
    
    



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
            # Log the received path
            #print(f"Received JSON path: {json_path}")
            
            # Expand user path to handle tilde (~) symbol
            json_path = os.path.expanduser(json_path)
            
            # Ensure the path is absolute to prevent directory traversal attacks
            if not os.path.isabs(json_path):
                return jsonify({'success': False, 'message': 'Invalid JSON path provided.'}), 400
            
            with open(json_path, 'r') as json_file:
                data_to_load = json.load(json_file)
            
            return jsonify({'success': True, 'data': data_to_load})
        except FileNotFoundError:
            print(f"File not found: {json_path}")
            return jsonify({'success': False, 'message': 'File not found.'}), 404
        except json.JSONDecodeError:
            print(f"Invalid JSON file: {json_path}")
            return jsonify({'success': False, 'message': 'Invalid JSON file.'}), 400
        except Exception as e:
            print(f"Exception occurred: {e}")  # Log the error for debugging purposes
            return jsonify({'success': False, 'message': str(e)}), 500
    return jsonify({'success': False, 'message': 'No JSON path provided.'}), 400






@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files or 'uploadFolder' not in request.form:
        return 'No file or folder part', 400
    
    file = request.files['file']
 
    print("PROJECT PATH BEFIORE UPLOADING", session["session_path"])
    upload_folder = request.form['uploadFolder']

    
    print("UPLOAD FOLDER", upload_folder)


    if file.filename == '':
        return 'No selected file', 400
    
    if file:
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)
        file.save(os.path.join(upload_folder, file.filename))
        return 'File uploaded successfully', 200
    

@app.route('/delete_file', methods=['POST'])
def delete_file():
    file_path = request.form['filePath']
    full_path = os.path.expanduser(file_path)
    
    if os.path.exists(full_path):
        os.remove(full_path)
        return 'File deleted successfully', 200
    else:
        return 'File not found', 400


# @app.route('/generate_preview', methods=['POST'])
# def generate_preview():
#     data = request.json
#     artwork_generator_path = "python artwork_generator/artwork_generator.py"
#     ADFPath = data.get('ADF', '')
#     outputPath = data.get('outputPath', '')
#     outputName = data.get('outputName', '')
#     #command = ADFPath + outputPath + outputName
#     ADFPath = "artwork_library/Inductors/Coplanar/Inductor_Coplanar_5.json"

#     #command = artwork_generator_path + " -a " + ADFPath +  " -o " + outputPath +  " -n " + outputName
#     command = f"{artwork_generator_path} -a {ADFPath} -o {outputPath} -n {outputName}"
#     print(command)

#         # Call the command as a subprocess
#     try:
#         result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
#         output = result.stdout
#         error = result.stderr
#     except subprocess.CalledProcessError as e:
#         output = e.output
#         error = str(e)

#     return jsonify({"status": "success", "command": command, "output": output, "error": error})






@app.route('/generate_preview', methods=['POST'])
def generate_preview():
    data = request.json


    
    ARTWORK_GENERATOR_PATH = CONURE_PATH + "/artwork_generator/artwork_generator.py"
    #ARTWORK_GENERATOR_PATH = "/home/emon/Documents/Projects/conure/artwork_generator/artwork_generator.py"

    ADFPath = os.path.expanduser(data.get('ADF'))
    outputPath = os.path.expanduser(data.get('outputPath', ''))
    outputName = data.get('outputName', '')

    command = f"python {ARTWORK_GENERATOR_PATH} -a {ADFPath} -o {outputPath} -n {outputName} --svg"
    command_list = shlex.split(command)

    print(f"Command: {command}")
    #print(f"Current Working Directory: {os.getcwd()}")
    #print(f"Environment Variables: {os.environ}")

    # Call the command as a subprocess
    try:
        process = subprocess.run(command_list)
        #result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        #result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        output = process.stdout
        error = process.stderr

        print("Subprocess Output:\n", output)
        if error:
            print("Subprocess Error:\n", error)

    except subprocess.CalledProcessError as e:
        print("PREVIEW ERROR")
        output = e.output
        #error = str(e)
        error = e.stderr
        print("Subprocess Error Output:\n", error)

    return jsonify({"status": "success", "command": command, "output": output, "error": error})



@app.route('/sweep_generate', methods=['POST'])
def sweep_generate():
    data = request.json
    

    ADFPath = os.path.expanduser(data.get('ADFPath'))
    sweepConfigPath = os.path.expanduser(data.get('sweepConfigPath'))
    outputPath = os.path.expanduser(data.get('outputPath', ''))
    outputName = data.get('uniqueSweepName', '')
    enableSimulation = data.get('enableSimulation', False)
    enableSVGinSweep = data.get('enableSVGinSweep', False)

    #command = f"python {SWEEP_GENERATOR_PATH} -a {ADFPath} --sweep {sweepConfigPath} --layout -o {outputPath} -n {outputName}"

    # Base command
    command = f"python {SWEEP_GENERATOR_PATH} -a {ADFPath} --sweep {sweepConfigPath} --layout -o {outputPath} -n {outputName}"

    # Add simulation arguments if enableSimulation is True
    if enableSimulation:
        command += f" --simulate --pack_sim -c {SIMULATOR_CONFIG_PATH} --sim emx"

    # Add SVG argument if enableSVGinSweep is True
    if enableSVGinSweep:
        command += " --svg"


    print("COMMAND: ",command )

    command_list = shlex.split(command)


    #print(f"Command: {command}")
    try:
        process = subprocess.run(command_list)
        output = process.stdout
        error = process.stderr
    except subprocess.CalledProcessError as e:
        print("SWEEP ERROR")
        output = e.output
        # error = str(e)
        error = e.stderr

    return jsonify({"status": "success", "command": command, "output": output, "error": error})


@app.route('/get_svg', methods=['GET'])
def get_svg():
    svg_path = request.args.get('path')
    try:
        # Expand user tilde to the full path
        svg_path = os.path.expanduser(svg_path)
        
        if not os.path.exists(svg_path):
            raise FileNotFoundError(f"The file {svg_path} does not exist.")
        
        with open(svg_path, 'r') as svg_file:
            svg_content = svg_file.read()
        return Response(svg_content, mimetype='image/svg+xml')
    except FileNotFoundError as fnf_error:
        print(f"File not found error: {fnf_error}")
        return jsonify({"status": "error", "message": str(fnf_error)}), 404
    except Exception as e:
        print(f"Error reading SVG file: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500



if __name__ == '__main__':
    app.run(host="0.0.0.0",port=8080, debug=True)
