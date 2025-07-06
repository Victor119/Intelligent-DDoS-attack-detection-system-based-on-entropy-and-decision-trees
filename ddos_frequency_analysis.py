import pandas as pd
import numpy as np
import glob
import random
import re
import threading
import time
import subprocess
import os

from anytree import Node, RenderTree
from anytree.exporter import UniqueDotExporter

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from tree_visualizer import visualize_binary_tree, highlight_path_for_data_line

def calculate_entropy(a, b):
    n = a
    m = b
    if n == 0 and m == 0:
        return 0
    elif n == 0:
        return (m / (n + m)) * np.log2((n + m) / m)
    elif m == 0:
        return (n / (n + m)) * np.log2((n + m) / n)
    else:
        return (n / (n + m)) * np.log2((n + m) / n) + (m / (n + m)) * np.log2((n + m) / m)
    
def parse_n_m(s):
    match = re.match(r"\[(\d+)\+,(\d+)-]", s)
    if match:
        return int(match.group(1)), int(match.group(2))
    else:
        return (0, 0)

# Functia generalizata care proceseaza saved_H0
def total_entropy(saved_H0):
    # Extrage totalul din primul element (ex: "[9916+,10000-]Protocol")
    parent_str = saved_H0[0].split("]")[0] + "]"  # Izolam "[9916+,10000-]"
    total_benign, total_ddos = parse_n_m(parent_str)
    total = total_benign + total_ddos

    # Calculeaza entropiile si sumele partiale
    entropies = []
    counts = []
    for child_str in saved_H0[1:]:  # Ignoram primul element (eticheta)
        n, m = parse_n_m(child_str)
        entropies.append(calculate_entropy(n, m))
        counts.append(n + m)

    # Calculeaza suma ponderata
    total_sum_H = 0
    for i in range(len(entropies)):
        total_sum_H += (counts[i] / total) * entropies[i]
        
    return total_sum_H

# Functie pentru construirea structurii H pentru o coloana data
def build_H(frequency_table: pd.DataFrame, col: str):
    # Calculam totalurile pentru clasele 'benign' si 'ddos' (la nivel global)
    total_benign = frequency_table[frequency_table['Class'] == 'benign'].shape[0]
    total_ddos = frequency_table[frequency_table['Class'] == 'ddos'].shape[0]
    
    # Extragem lista de valori unice din coloana specificata
    values = frequency_table[col].unique().tolist()
    
    # Numarim aparitiile pentru fiecare valoare in functie de clasa
    value_counts = {}
    for value in values:
        benign_count = frequency_table[(frequency_table[col] == value) & (frequency_table['Class'] == 'benign')].shape[0]
        ddos_count = frequency_table[(frequency_table[col] == value) & (frequency_table['Class'] == 'ddos')].shape[0]
        value_counts[value] = (benign_count, ddos_count)
    
    # Construim structura H:
    # Primul element contine totalurile globale si eticheta coloanei,
    # urmatoarele elemente sunt siruri in formatul "[benign+,ddos-]" pentru fiecare valoare unica.
    H = [[f"[{total_benign}+,{total_ddos}-]{col}"] +
        [f"[{value_counts[value][0]}+,{value_counts[value][1]}-]" for value in values]]
    
    return H, value_counts, values

def process_columns(f_table: pd.DataFrame, exclude_cols=None):
    
    entropy_results = {}
    H_structures = {}
    for col in f_table.columns:
        if col in exclude_cols:
            continue
        
        print("\n======================")
        print(f"Prelucrare coloana: {col}")
        H, counts_dict, unique_vals = build_H(f_table, col)
        
        
        # Salvam structura H initiala
        saved_H = list(H[0])
        H_structures[col] = saved_H
        print("Structura H initiala:", saved_H)
        
        # Inlocuim etichetele cu entropiile calculate pentru fiecare valoare
        H[0][1:] = [calculate_entropy(counts_dict[val][0], counts_dict[val][1]) for val in unique_vals]
        print("Structura H cu entropie pentru fiecare valoare:", H[0])
        
        tot_ent = total_entropy(saved_H)
        print(f"Entropia totala pentru coloana {col}: {tot_ent}")
        
        entropy_results[col] = tot_ent
    return entropy_results, H_structures

def process_entropy_results(entropy_results):
    #Pas1: Sortam entropiile calculate pentru fiecare coloana
    sorted_entropy = sorted(entropy_results.items(), key=lambda x: x[1])
    
    #Pas2: Selectie aleatorie intre coloanele cu valoare minima, in cazul in care sunt mai multe
    
    #primul element are intotdeauna cea mai mica entropie
    min_val = sorted_entropy[0][1]
    
    #construim o lista cu toate coloanele care au entropia egala cu valoarea minima (min_val)
    min_value_columns = [col for col, ent in sorted_entropy if ent == min_val]
    
    node = random.choice(min_value_columns)  # selectia se face random daca sunt mai multe coloane
    
    return node

def find_binary_split(df: pd.DataFrame, col: str):
    vals = df[col].unique()
    if len(vals) <= 1:
        return None
    if len(vals) == 2:
        return vals[0]
    
    nums = sorted(df[col].astype(float).unique())
    best_ent = float('inf')
    best_split = None
    for i in range(len(nums)-1):
        split = (nums[i] + nums[i+1])/2
        left = df[df[col].astype(float) <= split]
        right = df[df[col].astype(float) > split]
        if left.empty or right.empty:
            continue
        l_b = (left['Class'] == 'benign').sum()
        l_d = (left['Class'] == 'ddos').sum()
        r_b = (right['Class'] == 'benign').sum()
        r_d = (right['Class'] == 'ddos').sum()
        total = l_b + l_d + r_b + r_d
        w_ent = ((l_b + l_d)/total)*calculate_entropy(l_b, l_d) + ((r_b + r_d)/total)*calculate_entropy(r_b, r_d)
        if w_ent < best_ent:
            best_ent = w_ent
            best_split = split
    return best_split if best_split is not None else nums[0]

def build_binary_decision_tree(df, max_depth, min_samples, depth=0, ignored=None):
    if ignored is None:
        ignored = ['Class']
    total = len(df)
    b_count = (df['Class'] == 'benign').sum()
    d_count = (df['Class'] == 'ddos').sum()
    
    if total <= min_samples or b_count == 0 or d_count == 0 or depth >= max_depth:
        return {'Class': 'benign' if b_count >= d_count else 'ddos'}
    
    entropy_results, _ = process_columns(df, exclude_cols=ignored)
    
    if not entropy_results:
        return {'Class': 'benign' if b_count >= d_count else 'ddos'}
    
    best_col = process_entropy_results(entropy_results)
    best_split = find_binary_split(df, best_col)
    
    if best_split is None:
        return {'Class': 'benign' if b_count >= d_count else 'ddos'}
    
    if isinstance(best_split, (int, float)):
        left_df = df[df[best_col].astype(float) <= best_split]
        right_df = df[df[best_col].astype(float) > best_split]
    else:
        left_df  = df[df[best_col] == best_split]
        right_df = df[df[best_col] != best_split]
    
    return {
        'attribute': best_col,
        'split_value': best_split,
        'left': build_binary_decision_tree(left_df, max_depth, min_samples, depth+1, ignored + [best_col]),
        'right': build_binary_decision_tree(right_df, max_depth, min_samples, depth+1, ignored + [best_col])
    }

def binary_to_anytree(tree, parent=None):
    if 'Class' in tree:
        return Node(f"Class: {tree['Class']}", parent)
    attribute = tree['attribute']
    split_value = tree['split_value']
    if isinstance(split_value, (int, float)):
        name = f"{attribute} <= {split_value:.2f}"
    else:
        name = f"{attribute} <= {split_value}"
    node = Node(name, parent)
    binary_to_anytree(tree['left'], node)
    binary_to_anytree(tree['right'], node)
    return node

def highlight_tree_path_for_data_line(data_line, column_names):
    """
    Function to highlight the path in the decision tree for a given data line.
    
    Args:
        data_line: String containing comma-separated values from a data file
        column_names: List of column names in order
    """
    try:
        # Parse the data line
        data_values = [val.strip() for val in data_line.split(',')]
        
        print(f"\nHighlighting path for data: {data_values}")
        print(f"Column mapping:")
        for i, col in enumerate(column_names):
            if i < len(data_values):
                print(f"  {col}: {data_values[i]}")
        
        # Call the visualization function to highlight the path
        highlight_path_for_data_line(data_values, column_names)
        
        print("Path highlighted in tree visualization!")
        print("Press 'C' in the visualization window to clear highlighting.")
        
    except Exception as e:
        print(f"Error highlighting path: {e}")

def process_data_file(file_path, column_names):
    """
    Procesează un fișier .data și evidențiază calea pentru fiecare linie
    """
    print(f"\n{'='*50}")
    print(f"PROCESARE FIȘIER NOU: {file_path}")
    print(f"{'='*50}")
    
    try:
        with open(file_path, 'r') as f:
            for line_number, line in enumerate(f, start=1):
                line = line.strip()
                if line:  # Verifică dacă linia nu este goală
                    print(f"\nLinia {line_number}: {line}")
                    highlight_tree_path_for_data_line(line, column_names)
                    
                    # Adaugă o pauză scurtă pentru a permite vizualizarea
                    time.sleep(0.5)
                    
    except Exception as e:
        print(f"Eroare la procesarea fișierului {file_path}: {e}")

class DataFileHandler(FileSystemEventHandler):
    """
    Handler pentru monitorizarea fișierelor .data noi
    """
    def __init__(self, column_names, processed_files):
        self.column_names = column_names
        self.processed_files = processed_files
    
    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith('.data'):
            file_path = event.src_path
            
            # Verifică dacă fișierul nu a fost deja procesat
            if file_path not in self.processed_files:
                print(f"\n Fișier nou detectat: {file_path}")
                
                # Așteaptă puțin pentru ca fișierul să fie complet scris
                time.sleep(1)
                
                # Procesează fișierul
                process_data_file(file_path, self.column_names)
                
                # Marchează fișierul ca procesat
                self.processed_files.add(file_path)
    
    def on_modified(self, event):
        # Dacă fișierul este modificat, îl procesăm din nou
        if not event.is_directory and event.src_path.endswith('.data'):
            file_path = event.src_path
            print(f"\n Fișier modificat detectat: {file_path}")
            
            time.sleep(1)  # Așteaptă ca modificarea să fie completă
            process_data_file(file_path, self.column_names)

def monitor_logs_folder(logs_dir, column_names):
    """
    Monitorizeaza folderul logs pentru fisiere .data noi
    """
    # Set pentru a ține evidenta fișierelor deja procesate
    processed_files = set()
    
    # Procesează fișierele existente
    existing_files = glob.glob(os.path.join(logs_dir, '*.data'))
    if existing_files:
        print(f"\nFișiere existente găsite: {len(existing_files)}")
        for file_path in existing_files:
            process_data_file(file_path, column_names)
            processed_files.add(file_path)
    else:
        print("\nNu au fost găsite fișiere .data existente în folderul 'logs'.")
    
    # Configurează monitorizarea pentru fișiere noi
    event_handler = DataFileHandler(column_names, processed_files)
    observer = Observer()
    observer.schedule(event_handler, logs_dir, recursive=False)
    
    # Pornește monitorizarea
    observer.start()
    print(f"\n Monitorizare activă pentru folderul: {logs_dir}")
    print("Programul va procesa automat fișierele .data noi care apar...")
    print("Apasă Ctrl+C pentru a opri monitorizarea.")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n Oprire monitorizare...")
        observer.stop()
    
    observer.join()
    print("Monitorizare oprită.")

def optimize_tree_with_flag(tree_dict):
    """
    Optimizează arborele în mod iterativ până când nu mai sunt posibile optimizări.
    Folosește un flag pentru a detecta când s-au făcut modificări și repetă procesul
    până când o parcurgere completă nu mai face nicio schimbare.
    
    Args:
        tree_dict: Dicționarul care reprezintă arborele de decizie
        
    Returns:
        dict: Arborele complet optimizat
    """
    
    def optimize_single_pass(tree, flag_ref):
        """
        Funcție internă care face o singură parcurgere DFS și optimizează arborele.
        
        Args:
            tree: Arborele curent
            flag_ref: Lista cu un element care conține flag-ul (pentru referință)
            
        Returns:
            dict: Arborele optimizat după o parcurgere
        """
        # Dacă este un nod frunză, returnează-l așa cum este
        if 'Class' in tree:
            return tree
        
        # Recursiv optimizează subarborii stâng și drept
        left_optimized = optimize_single_pass(tree['left'], flag_ref)
        right_optimized = optimize_single_pass(tree['right'], flag_ref)
        
        # Verifică dacă ambele noduri copil sunt frunze cu aceeași clasă
        if ('Class' in left_optimized and 'Class' in right_optimized and 
            left_optimized['Class'] == right_optimized['Class']):
            
            print(f" Optimizare gasita: Nodul cu atributul '{tree['attribute']}' si split-ul '{tree['split_value']}' "
                  f"este inlocuit cu clasa '{left_optimized['Class']}' "
                  f"(ambele noduri copil aveau aceeasi clasa)")
            
            # Setează flag-ul la 1 pentru a indica că s-a făcut o modificare
            flag_ref[0] = 1
            
            # Returnează un nod frunză cu clasa comună
            return {'Class': left_optimized['Class']}
        
        # Altfel, returnează nodul cu subarborii optimizați
        return {
            'attribute': tree['attribute'],
            'split_value': tree['split_value'],
            'left': left_optimized,
            'right': right_optimized
        }
    
    # Inițializează flag-ul la 0
    flag = [0]  # Folosim o listă pentru a putea modifica valoarea prin referință
    iteration = 0
    
    print(" INCEPE OPTIMIZAREA ITERATIVA A ARBORELUI")
    
    # Continuă optimizarea până când flag-ul rămâne 0 după o parcurgere completă
    while True:
        iteration += 1
        print(f"\n ITERATIA {iteration}:")
        
        # Resetează flag-ul la 0 la începutul fiecărei iterații
        flag[0] = 0
        print(f"Flag resetat la: {flag[0]}")
        
        # Efectuează o parcurgere DFS și optimizează
        tree_dict = optimize_single_pass(tree_dict, flag)
        
        print(f"Flag la sfarsitul iteratiei: {flag[0]}")
        
        # Dacă flag-ul este încă 0, înseamnă că nu s-au făcut modificări
        if flag[0] == 0:
            print(f"\n OPTIMIZARE COMPLETA!")
            print(f"Numarul total de iteratii: {iteration}")
            print(f"Nu mai sunt posibile optimizari suplimentare")
            break
        else:
            print(f"S-au gasit optimizari - continua cu urmatoarea iteratie...")
    
    print(" ARBORELE A FOST COMPLET OPTIMIZAT!")

    return tree_dict

if __name__ == '__main__':
    path = r"C:\Users\victor\Documents\licenta_victor\varianta_ID3\DF.data"
    data = pd.read_csv(path, header=None)
    data.columns = ['Protocol', 'Tot Fwd Pkts', 'Tot Bwd Pkts', 'TotLen Fwd Pkts', 
                    'TotLen Bwd Pkts', 'Flow Byts/s', 'Flow Pkts/s', 
                    'Fwd Pkts/s', 'Class']
    data['Class'] = data['Class'].str.strip().str.lower()
    
    for col in data.columns:
        if col != 'Class':
            try: data[col] = pd.to_numeric(data[col])
            except: pass
    
    max_depth = len(data.columns) - 1
    tree_dict = build_binary_decision_tree(data, max_depth=max_depth, min_samples=1)
    
    tree_dict = optimize_tree_with_flag(tree_dict)
    
    root = binary_to_anytree(tree_dict)
    for pre, _, node in RenderTree(root):
        print(f"{pre}{node.name}")
    
    dot_file = 'binary_tree.dot'
    UniqueDotExporter(root).to_dotfile(dot_file)
    subprocess.run(["dot", dot_file, "-Tpng", "-o", "binary_tree.png"], check=False)
    
    # Start OpenGL visualization in a separate thread
    def viz_thread():
        print("Starting OpenGL visualization...")
        visualize_binary_tree(root, "Binary Decision Tree")
        print("Visualization thread finished.")

    thread = threading.Thread(target=viz_thread, daemon=True)
    thread.start()

    # Wait a moment for the visualization to initialize
    time.sleep(2)

    # Code after starting visualization
    print("This will print immediately after launching visualization thread.")
    
    logs_dir = r"C:/Users/victor/Documents/licenta_victor/varianta_ID3/logs"
    
    # Pornește monitorizarea folderului logs
    monitor_logs_folder(logs_dir, data.columns.tolist())
    
    print("All threads complete. Exiting main program.")