from flask import Flask, request, jsonify, send_file, render_template
import os
import shutil
import pandas as pd
from werkzeug.utils import secure_filename

# Konfiguracja aplikacji Flask
app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
RESULT_FOLDER = 'results'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)

# Funkcja do przetwarzania plików PDF (tu podłącz swój kod przetwarzania)
def process_pdfs():
    # Tu można podpiąć kod przetwarzania PDF-ów
    # Na razie tylko tworzymy pusty plik wynikowy
    output_file = os.path.join(RESULT_FOLDER, 'output.xlsx')
    df = pd.DataFrame({"Kolor": ["18 szary", "14 szary"], "Suma (m)": [40.8, 51.4]})
    df.to_excel(output_file, index=False)
    return output_file

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'files' not in request.files:
        return jsonify({'error': 'Brak plików'}), 400
    
    files = request.files.getlist('files')
    for file in files:
        if file.filename == '':
            continue
        filename = secure_filename(file.filename)
        file.save(os.path.join(UPLOAD_FOLDER, filename))
    
    return jsonify({'message': 'Pliki przesłane'}), 200

@app.route('/list_files', methods=['GET'])
def list_files():
    files = os.listdir(UPLOAD_FOLDER)
    return jsonify({'files': files})

@app.route('/delete_file', methods=['POST'])
def delete_file():
    data = request.json
    filename = data.get('filename')
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        return jsonify({'message': 'Plik usunięty'}), 200
    return jsonify({'error': 'Plik nie istnieje'}), 400

@app.route('/process', methods=['POST'])
def process_files():
    if not os.listdir(UPLOAD_FOLDER):
        return jsonify({'error': 'Brak plików do przetworzenia'}), 400
    
    output_file = process_pdfs()
    return jsonify({'message': 'Przetwarzanie zakończone', 'output_file': output_file})

@app.route('/download', methods=['GET'])
def download_file():
    output_file = os.path.join(RESULT_FOLDER, 'output.xlsx')
    if os.path.exists(output_file):
        return send_file(output_file, as_attachment=True)
    return jsonify({'error': 'Plik wynikowy nie istnieje'}), 400

@app.route('/clear_uploads', methods=['POST'])
def clear_uploads():
    shutil.rmtree(UPLOAD_FOLDER)
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    return jsonify({'message': 'Folder uploads wyczyszczony'}), 200

if __name__ == '__main__':
    app.run(debug=True)
