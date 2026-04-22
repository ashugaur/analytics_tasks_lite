# %% Simulate data for sankey diagram

import pandas as pd
import random

def create_fill_dataframe(strength, stages, num_rows=10):
    """
    Creates a pandas DataFrame with specified fill stages and strength values.

    Args:
        strength (list): List of strength values.
        stages (list): List of fill stage names.
        num_rows (int): Number of rows to generate in the DataFrame.

    Returns:
        pandas.DataFrame: DataFrame with fill stages as columns and strength values as rows.
    """

    data = {}
    for stage in stages:
        data[stage] = []

    for _ in range(num_rows):
        row = {}
        for stage in stages:
            if stage == 'Fill1':
                row[stage] = random.choice([s for s in strength if s != 'NoFill'])
            else:
                row[stage] = random.choice(strength)
        for stage in stages:
            data[stage].append(row[stage])

    df = pd.DataFrame(data)
    df.insert(0, 'row_number', range(1, num_rows + 1))
    return df

# Example usage with your provided lists:
strength = ['NoFill', '0.8MG', '1.2MG', '1.7MG', '2.4MG', '3.0MG']
stages = ['Fill1', 'Fill2', 'Fill3', 'Fill4', 'Fill5']

df = create_fill_dataframe(strength, stages)
print(df)

# Example usage with more stages and rows:

stages_extended = ['Fill1', 'Fill2', 'Fill3', 'Fill4', 'Fill5', 'Fill6', 'Fill7', 'Fill8']
df_extended = create_fill_dataframe(strength, stages_extended, num_rows=10)
print(df_extended)


# %% Simulate complex data for sankey diagram

import pandas as pd
import random

def create_weighted_fill_dataframe(strength, stages, num_rows=4, weightage_factor=0.5):
    """
    Creates a pandas DataFrame with weighted fill stages and strength values.

    Args:
        strength (list): List of strength values.
        stages (list): List of fill stage names.
        num_rows (int): Number of rows to generate in the DataFrame.
        weightage_factor (float): Controls the weightage towards lower strengths.

    Returns:
        pandas.DataFrame: DataFrame with fill stages as columns and strength values as rows.
    """

    data = {}
    numeric_strengths = [float(s.replace('MG', '')) for s in strength if 'MG' in s]
    numeric_strengths.sort()

    def weighted_choice(stage_index):
        weights = []
        for s in strength:
            if 'MG' in s:
                num_strength = float(s.replace('MG', ''))
                weight = 1 / (num_strength * (stage_index * weightage_factor + 1))
            else:
                weight = stage_index * weightage_factor
            weights.append(weight)

        total_weight = sum(weights)
        normalized_weights = [w / total_weight for w in weights]
        return random.choices(strength, weights=normalized_weights, k=1)[0]

    for stage in stages:
        data[stage] = []

    for _ in range(num_rows):
        row = {}
        for i, stage in enumerate(stages):
            if stage == 'Fill1':
                # Fill1 has its own weightage - favor lower strengths
                weights_fill1 = []
                for s in strength:
                    if 'MG' in s:
                        num_strength = float(s.replace('MG', ''))
                        weight = 1 / num_strength  # Simpler weight for Fill1
                    else:
                        weight = 0.1 #low weight for NoFill in Fill1
                    weights_fill1.append(weight)
                total_weight_fill1 = sum(weights_fill1)
                normalized_weights_fill1 = [w / total_weight_fill1 for w in weights_fill1]
                row[stage] = random.choices(strength, weights=normalized_weights_fill1, k=1)[0]
            else:
                # Other Fill# columns use the weighted_choice with stage index
                row[stage] = weighted_choice(i)
        for stage in stages:
            data[stage].append(row[stage])

    df = pd.DataFrame(data)
    df.insert(0, 'row_number', range(1, num_rows + 1))
    return df

# Example usage:
strength = ['NoFill', '0.8MG', '1.2MG', '1.7MG', '2.4MG', '3.0MG']
stages = ['Fill1', 'Fill2', 'Fill3', 'Fill4', 'Fill5', 'Fill6']

df = create_weighted_fill_dataframe(strength, stages, num_rows=1000, weightage_factor=0.3)
#print(df)

#df.head(10).to_clipboard(index=False)


## Transpose
df_melted = pd.melt(df, id_vars=['row_number'], var_name='fill', value_name='strength')
#df_melted['seq'] = df_melted['fill'].str.replace('Fill', '').astype(int)
df_melted['seq'] = df_melted['fill']
df_melted = df_melted[['row_number', 'strength', 'seq']]
df_melted = df_melted.rename(columns={'strength':'fill'})
df_melted = df_melted.sort_values(by=['row_number', 'seq']).reset_index(drop=True)

#print(df_melted)
#df_melted.head(10).to_clipboard(index=False)



# %% Data cleaning

exec(open(_exploratory + r"\introspection\sql\pandasql\pandasql.py").read())

## 1. lodes_data
query_lodes = """ 
--DROP TABLE IF EXISTS lodes_data;
SELECT 
    row_number AS alluvium,
    seq AS stage,
    fill AS stratum,
    1 AS y,
    CAST(SUBSTRING(seq, 5) AS INTEGER) AS x
FROM 
    df
ORDER BY 
    row_number, x; """

lodes_data = qdfsql(df_melted, query_lodes)
lodes_data.to_csv(_vl + r'\flow\lodes_data_06x.csv', index=False)


## 2. stratum_totals
# Step 1: Create a Temporary Table for Stage Counts
query_stage_counts = """ 
--DROP TABLE IF EXISTS stage_counts;
--CREATE TABLE stage_counts AS
SELECT 
    seq AS stage,
    fill AS stratum,
    CAST(SUBSTRING(seq, 5) AS INTEGER) AS x,
    COUNT(*) AS value
FROM 
    df
GROUP BY 
    seq, fill; """

stage_counts = qdfsql(df_melted, query_stage_counts)


# Step 2: Create a Temporary Table for Stage Totals
query_stage_totals = """ 
--DROP TABLE IF EXISTS stage_totals;
--CREATE TABLE stage_totals AS
SELECT 
    stage,
    SUM(value) AS total_per_stage
FROM 
    df
GROUP BY 
    stage; """

stage_totals = qdfsql(stage_counts, query_stage_totals)


# Step 3: Combine and Calculate Percentages for stratum_totals
query_stratum_totals = """ 
--DROP TABLE IF EXISTS stratum_totals;
--CREATE TABLE stratum_totals AS
SELECT 
    sc.stage,
    sc.stratum,
    sc.value,
    sc.x,
    --ROUND((sc.value::FLOAT / st.total_per_stage) * 100, 1) AS percentage
    ROUND((CAST(sc.value AS REAL) / st.total_per_stage) * 100, 1) AS percentage
FROM 
    df1 sc
JOIN 
    df2 st ON sc.stage = st.stage
ORDER BY 
    sc.x, sc.stratum; """

stratum_totals = qdfssql({'df1': stage_counts, 'df2': stage_totals}, query_stratum_totals)

stratum_totals.to_csv(_vl + r'\flow\stratum_totals_06x.csv', index=False)

