import pandas as pd
import csv

if __name__ == "__main__":
    train_csv_path = "C:\\Users\\victor\\Documents\\licenta_victor\\varianta_ID3\\dataset\\train\\train.csv"
    
    
    ddos_data = pd.read_csv("C:\\Users\\victor\\Documents\\licenta_victor\\varianta_ID3\\sheet_ddos.txt", 
        sep=',', header=None, skiprows=1, nrows=10000
    )
    
    
    not_ddos_data = pd.read_csv("C:\\Users\\victor\\Documents\\licenta_victor\\varianta_ID3\\sheet_not_ddos.txt", 
                                sep=',', header=None, nrows=10000)
    
    first_line = pd.read_csv("C:\\Users\\victor\\Documents\\licenta_victor\\varianta_ID3\\final_dataset.csv", 
        sep=",", header=None, nrows=1
    )
    
    combined_data = pd.concat([first_line, ddos_data, not_ddos_data], ignore_index=True)
    
    train_data = combined_data
    
    #shuffle
    first_line_fixed = combined_data.iloc[:1]
    rest_of_data = combined_data.iloc[1:]
    
    rest_of_data_shuffled = rest_of_data.sample(frac=1, random_state=42).reset_index(drop=True)
    
    combined_data = pd.concat([first_line_fixed, rest_of_data_shuffled], ignore_index=True)
    
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
    
    header_row = combined_data.iloc[0]
    
    columns_to_remove = [col for col in combined_data.columns if header_row[col] in columns_to_drop]
    
    combined_data = combined_data.drop(columns=columns_to_remove)
    
    #remove first column
    combined_data = combined_data.drop(columns=combined_data.columns[0])
    
    combined_data.to_csv(train_csv_path, quoting=csv.QUOTE_NONE, escapechar=' ')
    
    
    combined_data = combined_data[1:].reset_index(drop=True)
    
    
    df_data_path = "C:\\Users\\victor\\Documents\\licenta_victor\\varianta_ID3\\DF.data"
    
    
    DF = pd.DataFrame(data=combined_data)
    
    
    with open(df_data_path, mode='w', newline='', encoding='utf-8') as f:
        pass
    
    for _, row in DF.iterrows():
        line = row.values.tolist()
        with open(df_data_path, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(line)
            
    #add spaces
    with open(df_data_path, mode='r', encoding='utf-8') as f:
        content = f.read()
        
    #verify if we have a value with nan or inf in the row of the dataset
    
    # Convert the content into a DataFrame to check for NaN or Inf values
    lines = content.splitlines()  # Split the file into lines

    # Parse lines and remove any that contain NaN or Inf
    cleaned_lines = []
    for line in lines:
        # Check if any value in the line is NaN or Inf
        if 'nan' not in line and 'inf' not in line:
            cleaned_lines.append(line)

    # Join the lines back into a single string
    cleaned_content = "\n".join(cleaned_lines)
    
    content_with_spaces = cleaned_content.replace(",", ", ")

    with open(df_data_path, mode='w', encoding='utf-8') as f:
        f.write(content_with_spaces)
    
    df_data_names_path = "C:\\Users\\victor\\Documents\\licenta_victor\\varianta_ID3\\DF.names"
    
    # Extract unique elements from the Protocol column
    protocol_column = list(train_data[6])
    unique_protocols = set(protocol_column)
    protocol_column = list(unique_protocols)
    
    if "Protocol" in protocol_column:
        protocol_column.remove("Protocol")
        protocol_column.insert(0, "Protocol")
        
    numeric_values = [x for x in protocol_column[1:] if isinstance(x, (int, float))] 
    sorted_numeric_values = sorted(numeric_values) 

    protocol_column = [protocol_column[0]] + sorted_numeric_values + [x for x in protocol_column[1:] if not isinstance(x, (int, float))]
    
    result = protocol_column[0] + ": " + ", ".join(str(x) for x in protocol_column[1:]) + "."
    
    with open(df_data_names_path, mode='w', newline='', encoding='utf-8') as f:
        pass
    
    with open(df_data_names_path, mode='w', newline='', encoding='utf-8') as f:
        f.write("Benign, ddos.\n\n")
        
        f.write(result)          
        f.write("\nTot Fwd Pkts: continuous.\n")
        f.write("Tot Bwd Pkts: continuous.\n")
        f.write("TotLen Fwd Pkts: continuous.\n")
        f.write("TotLen Bwd Pkts: continuous.\n")
        
        f.write("Flow Byts/s: continuous.\n")
        f.write("Flow Pkts/s: continuous.\n")
        
        f.write("Fwd Pkts/s: continuous.\n")
        f.write("Bwd Pkts/s: continuous.\n")
        
        f.write("SYN Flag Cnt: 0, 1.\n")
        f.write("RST Flag Cnt: 0, 1.\n")
        
        #f.write("Label: Benign, ddos.\n")
            
    print(result)
    
    """
    header2 = [
        'Flow ID', 'Src IP', 'Src Port', 'Dst IP', 'Dst Port', 'Protocol', 'Timestamp', 'Flow Duration', 'Tot Fwd Pkts',
        'Tot Bwd Pkts', 'TotLen Fwd Pkts', 'TotLen Bwd Pkts', 'Fwd Pkt Len Max', 'Fwd Pkt Len Min', 'Fwd Pkt Len Mean','Fwd Pkt Len Std',
        'Bwd Pkt Len Max', 'Bwd Pkt Len Min', 'Bwd Pkt Len Mean', 'Bwd Pkt Len Std', 'Flow Byts/s', 'Flow Pkts/s', 'Flow IAT Mean', 
        'Flow IAT Std', 'Flow IAT Max', 'Flow IAT Min', 'Fwd IAT Tot', 'Fwd IAT Mean', 'Fwd IAT Std', 'Fwd IAT Max', 'Fwd IAT Min',
        'Bwd IAT Tot', 'Bwd IAT Mean', 'Bwd IAT Std', 'Bwd IAT Max', 'Bwd IAT Min', 'Fwd PSH Flags', 'Bwd PSH Flags', 
        'Fwd URG Flags', 'Bwd URG Flags', 'Fwd Header Len', 'Bwd Header Len', 'Fwd Pkts/s', 'Bwd Pkts/s', 
        'Pkt Len Min', 'Pkt Len Max', 'Pkt Len Mean', 'Pkt Len Std', 'Pkt Len Var', 'FIN Flag Cnt',
        'SYN Flag Cnt', 'RST Flag Cnt', 'PSH Flag Cnt','ACK Flag Cnt', 'URG Flag Cnt', 
        'CWE Flag Count', 'ECE Flag Cnt', 'Down/Up Ratio', 'Pkt Size Avg', 
        'Fwd Seg Size Avg','Bwd Seg Size Avg', 'Fwd Byts/b Avg',
        'Fwd Pkts/b Avg', 'Fwd Blk Rate Avg', 'Bwd Byts/b Avg', 'Bwd Pkts/b Avg', 'Bwd Blk Rate Avg', 'Subflow Fwd Pkts',
        'Subflow Fwd Byts', 'Subflow Bwd Pkts', 'Subflow Bwd Byts', 'Init Fwd Win Byts', 'Init Bwd Win Byts', 'Fwd Act Data Pkts',
        'Fwd Seg Size Min', 'Active Mean', 'Active Std', 'Active Max', 'Active Min', 'Idle Mean','Idle Std', 'Idle Max',
        'Idle Min', 'Label'
    ]
    
    
    
    
    """