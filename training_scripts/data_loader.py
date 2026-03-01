import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
import joblib


class DataLoader:
    def __init__(self, scaler_path=None):
        self.scaler = None
        self.feature_columns = None
        if scaler_path:
            self.scaler = joblib.load(scaler_path)
    
    def load_and_preprocess(self, path, label_column='Label'):
        df = pd.read_csv(path)
        df.columns = df.columns.str.strip()
        
        labels = df[label_column] if label_column in df.columns else None
        df = df.drop(columns=[label_column], errors='ignore')
        
        if self.feature_columns is None:
            self.feature_columns = df.columns.tolist()
        else:
            df = df[self.feature_columns]
        
        df = df.replace([np.inf, -np.inf], np.nan)
        df = df.fillna(df.median(numeric_only=True))
        
        return df.values.astype('float32'), labels
    
    def fit_scaler(self, X):
        self.scaler = MinMaxScaler()
        return self.scaler.fit_transform(X)
    
    def transform(self, X):
        return self.scaler.transform(X)
    
    def save_scaler(self, path):
        joblib.dump(self.scaler, path)
