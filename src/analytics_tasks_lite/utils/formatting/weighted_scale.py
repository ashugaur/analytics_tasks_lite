import pandas as pd

def weighted_scale(df, column, scale=(0, 100)):
    """
    Scales the values of a column proportionally between a 
    specified min and max range.
    """
    col_min = df[column].min()
    col_max = df[column].max()
    scale_min, scale_max = scale
    
    # The Min-Max Scaling Formula:
    # X_scaled = ((X - X_min) / (X_max - X_min)) * (Max - Min) + Min
    
    df[f'{column}_scaled'] = (
        (df[column] - col_min) / (col_max - col_min)
    ) * (scale_max - scale_min) + scale_min
    
    return df

if __name__ == "__main__":
    # Example usage with your data:
    data = {
        'column': ['abc', 'dfg', 'lmo', 'qrs', 'ggy'],
        'value': [321449, 46727, 293731, 23669, 295160]
    }
    df = pd.DataFrame(data)

    df = weighted_scale(df, 'value', scale=(0, 10))
    print(df)


    # Alternate
    """ from sklearn.preprocessing import MinMaxScaler

    df = pd.read_clipboard()
    scaler = MinMaxScaler(feature_range=(0, 100))
    df['value_scaled'] = scaler.fit_transform(df[['value']]) """
   
