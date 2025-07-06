import pandas as pd
import csv
import os
import time
import random
from datetime import datetime
from pathlib import Path

# Citirea globala a datasetului pentru a evita reincarcarea repetata
global_df = None

def initialize_dataset(dataset_path: Path):
    """
    Incarca datasetul global o singura data si il pastreaza in memorie
    """
    global global_df
    print("Incarcare dataset...")
    global_df = pd.read_csv(dataset_path)
    print(f"Dataset incarcat: {len(global_df)} inregistrari")


def create_log_file(logs_dir: Path) -> Path:
    """
    Selecteaza un subset aleatoriu de randuri din datasetul global,
    elimina coloanele nedorite, curata datele (fara NaN sau Inf),
    si scrie intr-un fisier de log cu timestamp.
    Returneaza calea catre fisierul de log creat.
    """
    global global_df
    
    logs_dir.mkdir(parents=True, exist_ok=True)

    # Nume de fisier cu timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = logs_dir / f"log_{timestamp}.data"

    # Verifica daca datasetul global este incarcat
    if global_df is None:
        raise ValueError("Datasetul global nu a fost initializat")
    
    # Numar aleatoriu de randuri intre 10 si 20
    num_rows = random.randint(10, 20)
    
    # Esantionare fara inlocuire
    sampled = global_df.sample(n=num_rows, random_state=None)

    # Coloanele care trebuie eliminate
    columns_to_drop = [
        'Flow ID', 'Src IP', 'Src Port','Dst IP','Dst Port', 'Timestamp', 'Flow Duration', 'Fwd Pkt Len Max', 'Fwd Pkt Len Min', 
        'Fwd Pkt Len Mean','Fwd Pkt Len Std',
        'Bwd Pkt Len Max', 'Bwd Pkt Len Min', 'Bwd Pkt Len Mean', 'Bwd Pkt Len Std',
        'Fwd PSH Flags', 'Bwd PSH Flags', 'Fwd URG Flags', 'Bwd URG Flags', 'Fwd Header Len', 'Bwd Header Len',
        'Pkt Len Min', 'Pkt Len Max', 'Pkt Len Mean', 'Pkt Len Std', 'Pkt Len Var',
        'Init Fwd Win Byts', 'Init Bwd Win Byts',
        'Subflow Fwd Pkts', 'Subflow Fwd Byts', 'Subflow Bwd Pkts', 'Subflow Bwd Byts',
        'ECE Flag Cnt', 'CWE Flag Count',
        'Down/Up Ratio', 'Pkt Size Avg', 'Fwd Pkts/b Avg', 'Fwd Blk Rate Avg', 'Bwd Blk Rate Avg', 'Fwd Act Data Pkts',
        'Idle Mean','Idle Std', 'Idle Max',
        'Idle Min', 'Active Mean', 'Active Std', 'Active Max', 'Active Min', 'Fwd Seg Size Min', 'Fwd Seg Size Avg',
        'Bwd Seg Size Avg', 'Fwd Byts/b Avg', 'Bwd Byts/b Avg', 'Bwd Pkts/b Avg', 'Flow IAT Mean', 'Flow IAT Std',
        'Flow IAT Max', 'Flow IAT Min', 'Fwd IAT Tot', 'Fwd IAT Mean', 'Fwd IAT Std', 'Fwd IAT Max', 'Fwd IAT Min', 
        'Bwd IAT Tot', 'Bwd IAT Mean', 'Bwd IAT Std', 'Bwd IAT Max', 'Bwd IAT Min',
        'FIN Flag Cnt', 'PSH Flag Cnt', 'ACK Flag Cnt', 'URG Flag Cnt',
        'SYN Flag Cnt', 'RST Flag Cnt', 'Bwd Pkts/s'
    ]
    
    # Optimizare: foloseste doar coloanele care exista in dataset
    existing_columns = [col for col in columns_to_drop if col in sampled.columns]
    filtered = sampled.drop(columns=existing_columns, errors='ignore')

    # Curata datele: elimina randurile cu NaN sau Inf
    filtered = filtered.replace([float('inf'), -float('inf')], pd.NA).dropna()

    # Scrie in fisier cu separator virgula + spatiu
    with log_file.open('w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        for row in filtered.itertuples(index=False):
            writer.writerow(row)

    # Post-procesare: asigura-te ca virgulele au spatiu
    content = log_file.read_text(encoding='utf-8')
    spaced = content.replace(',', ', ')
    log_file.write_text(spaced, encoding='utf-8')

    print(f"Fisier log creat: {log_file}")
    return log_file


def main():
    # Ajusteaza aceste cai dupa cum este necesar
    base_dir = Path(r"C:/Users/victor/Documents/licenta_victor/varianta_ID3")
    dataset_path = Path("C:\\Users\\victor\\Documents\\licenta_victor\\varianta_ID3\\dataset\\test\\test.csv")
    logs_dir = base_dir / "logs"

    initialize_dataset(dataset_path)

    print("Pornire generator de log-uri. Generare la fiecare 10 secunde...")
    try:
        while True:
            start_time = time.time()
            create_log_file(logs_dir)
            
            # Calculeaza timpul necesar pentru a genera log-ul
            elapsed_time = time.time() - start_time
            
            # Asteapta restul din cele 10 secunde daca procesarea s-a terminat mai repede
            if elapsed_time < 10:
                time.sleep(10 - elapsed_time)
            else:
                print(f"Atentie: Generarea log-ului a durat {elapsed_time:.2f} secunde, mai mult de 10 secunde")
                # Nu asteptam deloc in acest caz si incepem urmatoarea iteratie imediat
            
    except KeyboardInterrupt:
        print("Oprit de utilizator.")


if __name__ == '__main__':
    main()