import os
import re
import json
import logging
from PyPDF2 import PdfReader
import pandas as pd
from multiprocessing import Pool, cpu_count, Manager

# Konfiguracja logowania
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Funkcja do wczytania konfiguracji
def load_config(config_path):
    with open(config_path, 'r') as file:
        return json.load(file)

# Funkcja do wczytania kodów kolorów z pliku
def load_color_codes(color_config_path):
    color_codes = {}
    with open(color_config_path, 'r') as file:
        for line in file:
            line = line.strip()
            if line and "=" in line:
                code, color_name = line.split("=", 1)
                color_codes[code.strip()] = color_name.strip()
    return color_codes

# Funkcja do ekstrakcji danych z sekcji "Informacje dodatkowe"
def extract_data_from_section(text, color_codes):
    results = {color_name: 0.0 for color_name in color_codes.values()}
    lines = text.split("\n")
    start_extracting = False
    
    for line in lines:
        if "Informacje dodatkowe:" in line:
            start_extracting = True
            continue
        
        if start_extracting:
            match = re.match(r"(\d+)\s+[A-Za-z0-9\s]+\s+\d+\.\d+\s+\d+\.\d+\s+\d+\.\d+\s+\d+\s+(\d+\.\d+)\s+\d+", line)
            if match:
                code = match.group(1)
                mb_value = float(match.group(2))  # MB (metry bieżące)
                
                if code in color_codes:
                    color_name = color_codes[code]
                    
                    # Modyfikacja wartości według warunku
                    if mb_value == 0:
                        logging.warning(f"Wartość 0 dla kodu {code} ({color_name})")
                    elif mb_value < 100:
                        mb_value += 5
                    else:
                        mb_value += 10
                    
                    results[color_name] += mb_value
    return results

# Funkcja do przetwarzania pojedynczego pliku PDF
def process_pdf(file_path, color_codes):
    try:
        reader = PdfReader(file_path)
        full_text = "".join(page.extract_text() or "" for page in reader.pages)
        return extract_data_from_section(full_text, color_codes)
    except Exception as e:
        logging.error(f"Błąd podczas przetwarzania pliku {file_path}: {e}")
        return {}

# Funkcja do przetwarzania plików równolegle
def process_pdfs_parallel(pdf_files, color_codes):
    with Pool(processes=cpu_count()) as pool:
        results = pool.starmap(process_pdf, [(file, color_codes) for file in pdf_files])
    
    # Sumowanie wyników
    final_results = {color: 0.0 for color in color_codes.values()}
    for file_result in results:
        for color, value in file_result.items():
            final_results[color] += value
    
    return final_results

# Główna funkcja programu
def main():
    # Wczytaj konfigurację
    config_path = "config.json"
    color_config_path = "config.kolory.txt"
    config = load_config(config_path)
    color_codes = load_color_codes(color_config_path)

    input_folder = config["input_folder"]
    output_file = config["output_file"]
    
    pdf_files = [os.path.join(input_folder, f) for f in os.listdir(input_folder) if f.endswith('.pdf')]
    total_files = len(pdf_files)

    if not pdf_files:
        logging.info("Brak plików PDF w folderze wejściowym.")
        return

    logging.info(f"Rozpoczynam przetwarzanie {total_files} plików PDF równolegle...")
    final_results = process_pdfs_parallel(pdf_files, color_codes)

    # Zapisz wyniki do pliku Excel
    try:
        df = pd.DataFrame(list(final_results.items()), columns=["Kolor", "Suma (m)"])
        df.to_excel(output_file, index=False)
        logging.info(f"Zapisano dane do pliku: {output_file}")
    except Exception as e:
        logging.error(f"Błąd podczas zapisu pliku wyjściowego: {e}")

if __name__ == "__main__":
    main()
