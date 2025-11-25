import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import os
from datetime import datetime

class ChartGenerator:
    def __init__(self, df, session_id, output_dir, theme='light'):
        self.df = df
        self.session_id = session_id
        self.output_dir = output_dir
        self.theme = theme
        self.charts = []
        
        self.session_dir = os.path.join(output_dir, str(session_id))
        os.makedirs(self.session_dir, exist_ok=True)
        
        self.colors = {
            'primary': '#3b82f6',
            'secondary': '#8b5cf6',
            'success': '#10b981',
            'warning': '#f59e0b',
            'danger': '#ef4444'
        }
    
    def _get_layout(self, title):
        return go.Layout(
            title=title,
            showlegend=True,
            plot_bgcolor='#f9fafb',
            paper_bgcolor='white'
        )
    
    def _save_chart(self, fig, chart_type, column_name=None):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{chart_type}_{column_name}_{timestamp}.png" if column_name else f"{chart_type}_{timestamp}.png"
        filepath = os.path.join(self.session_dir, filename)
        
        try:
            fig.write_image(filepath, width=1200, height=700)
            relative_path = os.path.join('eda_outputs', str(self.session_id), filename)
            self.charts.append({
                'type': chart_type,
                'path': relative_path,
                'column': column_name or ''
            })
            
            return filepath
        except Exception as e:
            print(f"Error saving chart {chart_type}: {str(e)}")
            try:
                html_filename = f"{chart_type}_{column_name}_{timestamp}.html" if column_name else f"{chart_type}_{timestamp}.html"
                html_filepath = os.path.join(self.session_dir, html_filename)
                fig.write_html(html_filepath)
                
                relative_path = os.path.join('eda_outputs', str(self.session_id), html_filename)
                self.charts.append({
                    'type': chart_type,
                    'path': relative_path,
                    'column': column_name or ''
                })
                print(f"Saved as HTML instead: {html_filename}")
                return html_filepath
            except Exception as e2:
                print(f"Failed to save chart completely: {str(e2)}")
                return None
    
    def _generate_histogram(self, column):
        fig = px.histogram(
            self.df,
            x=column,
            title=f'Histogram: {column}',
            color_discrete_sequence=[self.colors['primary']]
        )
        fig.update_layout(self._get_layout(f'Histogram: {column}'))
        self._save_chart(fig, 'histogram', column)
    
    def _generate_boxplot(self, column):
        fig = px.box(
            self.df,
            y=column,
            title=f'Boxplot: {column}',
            color_discrete_sequence=[self.colors['secondary']]
        )
        fig.update_layout(self._get_layout(f'Boxplot: {column}'))
        self._save_chart(fig, 'boxplot', column)
    
    def _generate_distribution_plot(self, column):
        fig = px.histogram(
            self.df,
            x=column,
            title=f'Distribution: {column}',
            color_discrete_sequence=[self.colors['primary']]
        )
        fig.update_layout(self._get_layout(f'Distribution: {column}'))
        self._save_chart(fig, 'distribution', column)
    
    def _generate_bar_chart(self, column, y_column=None):
        if y_column:
            fig = px.bar(
                self.df,
                x=column,
                y=y_column,
                title=f'Bar Chart: {y_column} by {column}',
                color_discrete_sequence=[self.colors['success']]
            )
            fig.update_layout(self._get_layout(f'Bar Chart: {y_column} by {column}'))
            self._save_chart(fig, 'bar_chart', f'{column}_vs_{y_column}')
        else:
            value_counts = self.df[column].value_counts().head(20)
            fig = px.bar(
                x=value_counts.index,
                y=value_counts.values,
                title=f'Bar Chart: {column}',
                color_discrete_sequence=[self.colors['success']]
            )
            fig.update_layout(self._get_layout(f'Bar Chart: {column}'))
            self._save_chart(fig, 'bar_chart', column)
    
    def _generate_scatter_plot(self, x_col, y_col):
        fig = px.scatter(
            self.df,
            x=x_col,
            y=y_col,
            title=f'Scatter: {y_col} vs {x_col}',
            color_discrete_sequence=[self.colors['primary']]
        )
        fig.update_layout(self._get_layout(f'Scatter: {y_col} vs {x_col}'))
        self._save_chart(fig, 'scatter', f'{x_col}_vs_{y_col}')
    
    def _generate_line_plot(self, x_col, y_col):
        fig = px.line(
            self.df,
            x=x_col,
            y=y_col,
            title=f'Line: {y_col} vs {x_col}',
            color_discrete_sequence=[self.colors['secondary']]
        )
        fig.update_layout(self._get_layout(f'Line: {y_col} vs {x_col}'))
        self._save_chart(fig, 'line', f'{x_col}_vs_{y_col}')
    
    def _generate_correlation_heatmap(self, numeric_cols=None):
        if numeric_cols is None:
            numeric_cols = self.df.select_dtypes(include=[np.number]).columns.tolist()
        
        if len(numeric_cols) < 2:
            return
        
        corr_matrix = self.df[numeric_cols].corr()
        
        fig = px.imshow(
            corr_matrix,
            title='Correlation Heatmap',
            color_continuous_scale='RdBu_r',
            text_auto='.2f'
        )
        fig.update_layout(self._get_layout('Correlation Heatmap'))
        self._save_chart(fig, 'correlation_heatmap')
    
    def _generate_pairplot(self, numeric_cols=None):
        if numeric_cols is None:
            numeric_cols = self.df.select_dtypes(include=[np.number]).columns.tolist()
        
        if len(numeric_cols) < 2:
            return
        
        numeric_cols = numeric_cols[:5]
        
        fig = px.scatter_matrix(
            self.df,
            dimensions=numeric_cols,
            title='Pairplot',
            color_discrete_sequence=[self.colors['primary']]
        )
        fig.update_layout(self._get_layout('Pairplot'))
        cols_str = '_'.join(numeric_cols[:3])
        self._save_chart(fig, 'pairplot', cols_str)
    
    def _generate_missing_values_chart(self):
        missing = self.df.isnull().sum()
        missing = missing[missing > 0].sort_values(ascending=False)
        
        if len(missing) == 0:
            fig = go.Figure()
            fig.add_annotation(
                text="No Missing Values Found",
                xref="paper", yref="paper",
                x=0.5, y=0.5,
                showarrow=False,
                font=dict(size=20, color=self.colors['success'])
            )
            fig.update_layout(self._get_layout('Missing Values - All Clean'))
            self._save_chart(fig, 'missing_values', 'none')
            return
        
        fig = px.bar(
            x=missing.values,
            y=missing.index,
            orientation='h',
            title='Missing Values',
            labels={'x': 'Count', 'y': 'Column'},
            color_discrete_sequence=[self.colors['danger']]
        )
        fig.update_layout(self._get_layout('Missing Values'))
        self._save_chart(fig, 'missing_values')
    
    def generate_all_charts(self):
        numeric_cols = self.df.select_dtypes(include=[np.number]).columns.tolist()
        categorical_cols = self.df.select_dtypes(include=['object', 'category']).columns.tolist()
        
        for col in numeric_cols:
            self._generate_histogram(col)
            self._generate_boxplot(col)
            self._generate_distribution_plot(col)
        
        for col in categorical_cols:
            self._generate_bar_chart(col)
        
        if len(numeric_cols) >= 2:
            self._generate_correlation_heatmap(numeric_cols)
            self._generate_pairplot(numeric_cols)
        
        self._generate_missing_values_chart()
        
        return self.charts
    
    # def generate_essential_charts_for_ai(self, chart_types):
    #     numeric_cols = self.df.select_dtypes(include=[np.number]).columns.tolist()
        
    #     for chart_type in chart_types:
    #         if chart_type == 'missing_values':
    #             self._generate_missing_values_chart()
    #         elif chart_type == 'correlation_heatmap' and len(numeric_cols) >= 2:
    #             self._generate_correlation_heatmap(numeric_cols)
    #         elif chart_type == 'distribution' and len(numeric_cols) > 0:
    #             self._generate_distribution_plot(numeric_cols[0])
    #         elif chart_type == 'pairplot' and len(numeric_cols) >= 2:
    #             self._generate_pairplot(numeric_cols)
        
    #     return self.charts
    
    def generate_intelligent_charts_for_ai(self, summary):

        total_rows = summary["shape"]["rows"]
        columns_info = summary["columns"]

        numeric_cols = summary.get("numeric_columns", [])
        categorical_cols = summary.get("categorical_columns", [])
        datetime_cols = summary.get("datetime_columns", [])


        self._generate_missing_values_chart()

        if len(numeric_cols) >= 2:
            self._generate_correlation_heatmap(numeric_cols)

        for col_info in columns_info:
            col = col_info["name"]
            
            if col not in numeric_cols:
                continue

            if col_info["missing"] > 0.4 * total_rows:
                continue

            if col_info["unique"] < 5:
                continue
            
            self._generate_distribution_plot(col)

        for col_info in columns_info:
            col = col_info["name"]

            if col not in categorical_cols:
                continue

            if col_info["unique"] > 30:
                continue
            
            if col_info["unique"] < 2:
                continue

            self._generate_bar_chart(col)

        for col in datetime_cols:
            if len(numeric_cols) > 0:
                self._generate_line_plot(col, numeric_cols[0])

        return self.charts

    
    def generate_on_demand_charts(self, x_axis=None, y_axis=None, chart_types=None):
        if not chart_types or chart_types == ['all']:
            chart_types = self._get_all_possible_chart_types(x_axis, y_axis)
        
        numeric_cols = self.df.select_dtypes(include=[np.number]).columns.tolist()
        col = x_axis or y_axis
        
        chart_handlers = {
            'scatter': lambda: self._generate_scatter_plot(x_axis, y_axis) if x_axis and y_axis else None,
            'line': lambda: self._generate_line_plot(x_axis, y_axis) if x_axis and y_axis else None,
            'histogram': lambda: self._generate_histogram(col) if col and pd.api.types.is_numeric_dtype(self.df[col]) else None,
            'boxplot': lambda: self._generate_boxplot(col) if col and pd.api.types.is_numeric_dtype(self.df[col]) else None,
            'distribution': lambda: self._generate_distribution_plot(col) if col and pd.api.types.is_numeric_dtype(self.df[col]) else None,
            'bar_chart': lambda: self._generate_bar_chart(x_axis, y_axis) if x_axis and y_axis else self._generate_bar_chart(col) if col else None,
            'correlation_heatmap': lambda: self._generate_correlation_heatmap(numeric_cols) if len(numeric_cols) >= 2 else None,
            'pairplot': lambda: self._generate_pairplot(numeric_cols) if len(numeric_cols) >= 2 else None,
            'missing_values': lambda: self._generate_missing_values_chart()
        }
        
        for chart_type in chart_types:
            handler = chart_handlers.get(chart_type)
            if handler:
                handler()
        
        return self.charts
    
    def _get_all_possible_chart_types(self, x_axis, y_axis):
        chart_types = []
        numeric_cols = self.df.select_dtypes(include=[np.number]).columns.tolist()
        
        if not x_axis and not y_axis:
            if len(numeric_cols) >= 2:
                chart_types = ['correlation_heatmap', 'pairplot']
            chart_types.append('missing_values')
            return chart_types
        
        if x_axis and y_axis:
            x_numeric = pd.api.types.is_numeric_dtype(self.df[x_axis])
            y_numeric = pd.api.types.is_numeric_dtype(self.df[y_axis])
            
            if x_numeric and y_numeric:
                chart_types = ['scatter', 'line', 'bar_chart']
            elif x_numeric or y_numeric:
                chart_types = ['bar_chart']
            else:
                chart_types = ['bar_chart']
                
        elif x_axis or y_axis:
            col = x_axis or y_axis
            if pd.api.types.is_numeric_dtype(self.df[col]):
                chart_types = ['histogram', 'boxplot', 'distribution']
            else:
                chart_types = ['bar_chart']
        
        chart_types.append('missing_values')
        
        return chart_types
    
    def get_available_chart_types(self, x_axis=None, y_axis=None):
        chart_types = self._get_all_possible_chart_types(x_axis, y_axis)
        
        descriptions = {
            'scatter': 'Scatter Plot - Shows relationship between two numeric variables',
            'line': 'Line Plot - Shows trend between two numeric variables',
            'bar_chart': 'Bar Chart - Shows distribution of categorical data or comparison',
            'histogram': 'Histogram - Shows frequency distribution of numeric data',
            'boxplot': 'Box Plot - Shows quartiles and outliers of numeric data',
            'distribution': 'Distribution Plot - Shows probability distribution of numeric data',
            'correlation_heatmap': 'Correlation Heatmap - Shows correlations between all numeric variables',
            'pairplot': 'Pair Plot - Shows pairwise relationships between numeric variables',
            'missing_values': 'Missing Values - Shows missing data across all columns'
        }
        
        return {
            'chart_types': chart_types,
            'descriptions': {ct: descriptions[ct] for ct in chart_types if ct in descriptions}
        }
