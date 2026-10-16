import pandas as pd
import itertools
import numpy as np

def find_min_columns(file_path, tolerance=0.05):
    # 1. Load the CSV
    # Assumes the first column contains the thread counts (1, 2, 4, ... 64)
    df = pd.read_csv(file_path, index_col=0)
    
    # 2. Clean up columns
    # Remove any existing "Average" or summary columns to avoid skewing results
    data_cols = [col for col in df.columns if 'average' not in col.lower() and 'mean' not in col.lower()]
    df_data = df[data_cols].astype(float)
    
    # 3. Calculate true row-wise averages (across all 1 to 10 columns)
    true_averages = df_data.mean(axis=1)
    
    total_cols = len(data_cols)
    print(f"📋 Found {total_cols} data columns to analyze: {data_cols}")
    print(f"🎯 Target tolerance: {tolerance * 100}%\n")
    
    # 4. Find the minimum subset
    for r in range(1, total_cols + 1):
        found_subsets = []
        # Test all combinations of size r
        for subset in itertools.combinations(data_cols, r):
            subset_list = list(subset)
            subset_averages = df_data[subset_list].mean(axis=1)
            
            # Calculate maximum percentage deviation across all thread rows
            # Using absolute relative difference
            pct_diffs = np.abs((subset_averages - true_averages) / true_averages)
            max_deviation = pct_diffs.max()
            
            if max_deviation < tolerance:
                found_subsets.append((subset_list, max_deviation))
        
        # If we found any valid subsets of size r, print the best one and stop
        if found_subsets:
            # Sort by lowest maximum deviation
            found_subsets.sort(key=lambda x: x[1])
            best_subset, best_deviation = found_subsets[0]
            
            eliminated = list(set(data_cols) - set(best_subset))
            
            print(f"🎉 SUCCESS! Found optimal column reduction.")
            print(f"--------------------------------------------------")
            print(f"⚡ Minimum number of columns needed: {r} (out of {total_cols})")
            print(f"✅ Columns to KEEP:                  {best_subset}")
            print(f"❌ Columns you can ELIMINATE:        {eliminated}")
            print(f"📈 Maximum deviation across rows:    {best_deviation * 100:.2f}%")
            print(f"--------------------------------------------------")
            return
            
    print("❌ No subset of columns can maintain the average within 5% tolerance across all rows.")

# Run the analysis
if __name__ == "__main__":
    # Replace 'results.csv' with your actual filename if it differs
    find_min_columns('results.csv', tolerance=0.15)

