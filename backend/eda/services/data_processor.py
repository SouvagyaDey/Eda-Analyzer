import pandas as pd
import numpy as np
from typing import Dict, Any


class DataProcessor:
    
    def __init__(self, dataframe: pd.DataFrame):
        self.df = dataframe.copy()
        self.original_df = dataframe.copy()
    
    def clean_data(self) -> pd.DataFrame:
        
        # Normalize column names
        self.df.columns = [col.strip().replace(' ', '_').lower() for col in self.df.columns]
        
        # Infer and convert data types
        self.df = self._infer_types()
        
        # Handle missing values
        self.df = self._handle_missing_values()
        
        return self.df
    
    def _infer_types(self) -> pd.DataFrame:

        df = self.df.copy()
        
        for col in df.columns:
            # Try to convert to numeric
            try:
                numeric_col = pd.to_numeric(df[col], errors='coerce')
                # Only convert if at least some values are numeric
                if not numeric_col.isna().all():
                    df[col] = pd.to_numeric(df[col], errors='ignore')
            except:
                pass
            
            # Try to convert to datetime
            if df[col].dtype == 'object':
                try:
                    df[col] = pd.to_datetime(df[col], errors='ignore')
                except:
                    pass
        
        return df
    
    def _handle_missing_values(self) -> pd.DataFrame:
        df = self.df.copy()
        
        for col in df.columns:
            missing_count = df[col].isnull().sum()
            if missing_count > 0:
                if pd.api.types.is_numeric_dtype(df[col]):
                    # Fill numeric columns with median
                    df[col].fillna(df[col].median(), inplace=True)
                else:
                    # Fill categorical columns with mode or 'Unknown'
                    if not df[col].mode().empty:
                        df[col].fillna(df[col].mode()[0], inplace=True)
                    else:
                        df[col].fillna('Unknown', inplace=True)
        
        return df
    
    def get_summary(self) -> Dict[str, Any]:
        
        summary = {
            'shape': {
                'rows': len(self.df),
                'columns': len(self.df.columns)
            },
            'columns': [],
            'missing_values': {},
            'duplicates': int(self.df.duplicated().sum()),
            'numeric_columns': [],
            'categorical_columns': [],
            'datetime_columns': []
        }
        
        for col in self.df.columns:
            col_info = {
                'name': col,
                'dtype': str(self.df[col].dtype),
                'missing': int(self.df[col].isnull().sum()),
                'unique': int(self.df[col].nunique())
            }
            
            if pd.api.types.is_numeric_dtype(self.df[col]):
                col_info['statistics'] = {
                    'mean': float(self.df[col].mean()) if not pd.isna(self.df[col].mean()) else None,
                    'median': float(self.df[col].median()) if not pd.isna(self.df[col].median()) else None,
                    'std': float(self.df[col].std()) if not pd.isna(self.df[col].std()) else None,
                    'min': float(self.df[col].min()) if not pd.isna(self.df[col].min()) else None,
                    'max': float(self.df[col].max()) if not pd.isna(self.df[col].max()) else None,
                }
                summary['numeric_columns'].append(col)
            elif pd.api.types.is_datetime64_any_dtype(self.df[col]):
                col_info['statistics'] = {
                    'min': str(self.df[col].min()) if not pd.isna(self.df[col].min()) else None,
                    'max': str(self.df[col].max()) if not pd.isna(self.df[col].max()) else None,
                }
                summary['datetime_columns'].append(col)
            else:
                # Categorical
                value_counts = self.df[col].value_counts().head(5).to_dict()
                col_info['top_values'] = {str(k): int(v) for k, v in value_counts.items()}
                summary['categorical_columns'].append(col)
            
            summary['columns'].append(col_info)
            
            if col_info['missing'] > 0:
                summary['missing_values'][col] = col_info['missing']
        
        return summary
    
    def detect_outliers(self, column: str) -> pd.Series:
        """Detect outliers using IQR method"""
        if not pd.api.types.is_numeric_dtype(self.df[column]):
            return pd.Series([False] * len(self.df))
        
        Q1 = self.df[column].quantile(0.25)
        Q3 = self.df[column].quantile(0.75)
        IQR = Q3 - Q1
        
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        
        return (self.df[column] < lower_bound) | (self.df[column] > upper_bound)
