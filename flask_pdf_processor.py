import os
import logging
from flask import Flask, render_template, request, jsonify, send_from_directory
import pandas as pd
from werkzeug.utils import secure_filename
from pdf_color_filterv2 import process_pdfs_parallel, load_config, load_color_codes

app = Flask(__name__)

# Konfiguracja folderów
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
ALLOWED_EXTENSIONS = {'pdf'}

# CHANGED: Tworzenie folderów przy starcie aplikacji
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

# CHANGED: Lepsza konfiguracja logowania przez Flask
app.logger.setLevel(logging.INFO)
handler = logging.FileHandler('app.log')
handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
app.logger.addHandler(handler)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    try:
        # CHANGED: Zbieranie informacji o błędnych plikach
        invalid_files = []
        filenames = []

        if 'files' not in request.files:
            app.logger.error("No files part in request")
            return jsonify({"message": "No files part"}), 400

        files = request.files.getlist('files')
        if not files or all(file.filename == '' for file in files):
            app.logger.error("No files uploaded")
            return jsonify({"message": "No files uploaded"}), 400

        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                filenames.append(filename)
            else:
                invalid_files.append(file.filename)

        if invalid_files:
            app.logger.error(f"Invalid files: {invalid_files}")
            return jsonify({"message": f"Invalid file formats: {', '.join(invalid_files)}"}), 400

        app.logger.info(f"Files uploaded: {', '.join(filenames)}")
        return jsonify({"message": f"Uploaded: {', '.join(filenames)}"}), 200

    except Exception as e:
        app.logger.error(f"Critical upload error: {str(e)}", exc_info=True)
        return jsonify({"message": "Server error during upload"}), 500

@app.route('/process', methods=['POST'])
def process_files():
    try:
        # CHANGED: Obsługa brakujących plików konfiguracyjnych
        config_path = "config.json"
        color_config_path = "config.kolory.txt"
        
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Config file {config_path} not found")
        if not os.path.exists(color_config_path):
            raise FileNotFoundError(f"Color config file {color_config_path} not found")

        config = load_config(config_path)
        color_codes = load_color_codes(color_config_path)

        pdf_files = [os.path.join(UPLOAD_FOLDER, f) for f in os.listdir(UPLOAD_FOLDER) if f.endswith('.pdf')]
        if not pdf_files:
            app.logger.warning("No PDFs to process")
            return jsonify({"message": "No PDF files found"}), 400

        app.logger.info(f"Processing {len(pdf_files)} files")

        # CHANGED: Dodatkowa walidacja wyników
        final_results = process_pdfs_parallel(pdf_files, color_codes)
        if not isinstance(final_results, dict):
            raise ValueError("Invalid results format from process_pdfs_parallel")

        final_results = {k: v for k, v in final_results.items() if v > 0}
        if not final_results:
            app.logger.info("No non-zero results")
            return jsonify({"message": "No data to save"}), 200  # CHANGED: 200 zamiast 400

        output_file = os.path.join(OUTPUT_FOLDER, "results.xlsx")
        df = pd.DataFrame(list(final_results.items()), columns=["Kolor", "Suma (m)"])
        df.to_excel(output_file, index=False)

        app.logger.info(f"Saved results to {output_file}")
        return jsonify({
            "message": "Processing complete",
            "download_url": "/download"
        }), 200

    except FileNotFoundError as e:
        app.logger.error(f"Config error: {str(e)}")
        return jsonify({"message": str(e)}), 404
    except Exception as e:
        app.logger.error(f"Processing failed: {str(e)}", exc_info=True)
        return jsonify({"message": f"Processing error: {str(e)}"}), 500

@app.route('/download')
def download_file():
    try:
        filename = 'results.xlsx'
        # CHANGED: Sprawdzenie istnienia pliku przed wysłaniem
        if not os.path.exists(os.path.join(OUTPUT_FOLDER, filename)):
            raise FileNotFoundError("File not generated yet")
        return send_from_directory(OUTPUT_FOLDER, filename, as_attachment=True)
    except FileNotFoundError:
        return jsonify({"message": "File not available"}), 404
    except Exception as e:
        app.logger.error(f"Download error: {str(e)}")
        return jsonify({"message": "Download failed"}), 500

@app.route('/list_files', methods=['GET'])
def list_files():
    try:
        files = os.listdir(UPLOAD_FOLDER)
        return jsonify({"files": files}), 200
    except Exception as e:
        app.logger.error(f"Listing error: {str(e)}")
        return jsonify({"message": "Cannot list files"}), 500

@app.route('/delete_file', methods=['POST'])
def delete_file():
    try:
        data = request.get_json()
        if not data or 'filename' not in data:
            return jsonify({"message": "Missing filename"}), 400

        # CHANGED: Dodatkowe zabezpieczenia
        filename = secure_filename(data['filename'])
        if not filename:
            raise ValueError("Invalid filename")

        file_path = os.path.join(UPLOAD_FOLDER, filename)
        if not os.path.exists(file_path):
            return jsonify({"message": "File not found"}), 404

        os.remove(file_path)
        app.logger.info(f"Deleted: {filename}")
        return jsonify({"message": f"Deleted {filename}"}), 200

    except Exception as e:
        app.logger.error(f"Delete error: {str(e)}")
        return jsonify({"message": "Deletion failed"}), 500

if __name__ == "__main__":
    # CHANGED: Bezpieczne uruchomienie (debug tylko lokalnie)
    app.run(host='0.0.0.0', port=5000, debug=os.environ.get('FLASK_DEBUG', 'False') == 'True')