import pandas as pd
import csv

# Function to drop specified columns and remove the first placeholder column
def drop_and_format(df, header_row, columns_to_drop):
    # Find original columns to remove by header name
    cols_to_remove = [col for col in df.columns if header_row[col] in columns_to_drop]
    df = df.drop(columns=cols_to_remove)
    # Drop the now-unused first placeholder column (original index)
    df = df.drop(columns=df.columns[0])
    return df

if __name__ == "__main__":
    # Paths
    base = r"C:\Users\victor\Documents\licenta_victor\varianta_ID3"
    train_csv_path = base + r"\dataset\train\train.csv"
    test_csv_path  = base + r"\dataset\test\test.csv"
    
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
    
    # --- CREATE TRAIN SET ---
    # Read header and sample slices
    header_orig = pd.read_csv(base + r"\final_dataset.csv", sep=",", header=None, nrows=1, low_memory=False)
    ddos_data    = pd.read_csv(base + r"\sheet_ddos.txt", sep=",", header=None, skiprows=1, nrows=10000, low_memory=False)
    not_ddos     = pd.read_csv(base + r"\sheet_not_ddos.txt", sep=",", header=None, nrows=10000, low_memory=False)
    
    # Combine and shuffle (keep header in first row)
    combined = pd.concat([header_orig, ddos_data, not_ddos], ignore_index=True)
    header_row = combined.iloc[0]
    data_rows  = combined.iloc[1:].sample(frac=1, random_state=42).reset_index(drop=True)
    combined   = pd.concat([combined.iloc[:1], data_rows], ignore_index=True)
    
    # Drop and format
    train_clean = drop_and_format(combined, header_row, columns_to_drop)
    
    # Remove the header row
    train_clean = train_clean.iloc[1:].reset_index(drop=True)
    
    # Export without header/index, comma separator (same format as test.csv)
    train_clean.to_csv(train_csv_path, sep=",", header=False, index=False, quoting=csv.QUOTE_NONE)


    # --- CREATE TEST SET ---
    final_full = pd.read_csv(base + r"\final_dataset.csv", sep=",", header=None, low_memory=False, dtype=str)
    header_f   = final_full.iloc[:1]
    data_f     = final_full.iloc[1:]
    sampled    = data_f.sample(n=min(40000, len(data_f)), random_state=42).reset_index(drop=True)
    combined_t = pd.concat([header_f, sampled], ignore_index=True)

    header_row_t = combined_t.iloc[0]
    test_clean   = drop_and_format(combined_t, header_row_t, columns_to_drop)
    # ** sTERGEM PRIMUL RaND (header-ul) **
    test_clean = test_clean.iloc[1:].reset_index(drop=True)
    test_clean.to_csv(test_csv_path, sep=",", header=False, index=False, quoting=csv.QUOTE_NONE)
