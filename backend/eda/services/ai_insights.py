import google.generativeai as genai
import pandas as pd
from typing import Dict, List, Any
from pathlib import Path

class AiInsightsGenerator:
    """
    Lightweight, clean, short-prompt EDA insights generator using Gemini 2.0 Flash with Vision.
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        if api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel("gemini-2.0-flash")
        else:
            self.model = None

    # MAIN METHOD
    def generate_insights(self, df: pd.DataFrame, summary: Dict[str, Any], chart_paths: List[Dict[str, str]] = None) -> str:
        if not self.model:
            print("Gemini API not configured → using fallback insights.")
            return self._fallback_insights(df, summary)

        try:
            text_summary = self._compact_summary(summary)
            images = self._load_images(chart_paths)

            prompt = self._short_prompt(text_summary, chart_paths)

            parts = [prompt] + images
            response = self.model.generate_content(parts)
            return response.text

        except Exception as e:
            print("AI Error → fallback:", e)
            return self._fallback_insights(df, summary)

    def _short_prompt(self, data_summary: str, chart_paths: List[Dict[str, str]]):
        # Group charts by type for better organization
        distributions = [c for c in chart_paths if c['type'] == 'distribution']
        correlations = [c for c in chart_paths if c['type'] == 'correlation_heatmap']
        categoricals = [c for c in chart_paths if c['type'] == 'bar_chart']
        others = [c for c in chart_paths if c['type'] not in ['distribution', 'correlation_heatmap', 'bar_chart']]
        
        chart_list = []
        if distributions:
            chart_list.append("\n**Distribution Plots:**")
            chart_list.extend([f"- Distribution of {c.get('column','')}" for c in distributions])
        if correlations:
            chart_list.append("\n**Correlation Analysis:**")
            chart_list.extend([f"- {c['type']}" for c in correlations])
        if categoricals:
            chart_list.append("\n**Categorical Analysis:**")
            chart_list.extend([f"- Bar chart: {c.get('column','')}" for c in categoricals])
        if others:
            chart_list.append("\n**Other Charts:**")
            chart_list.extend([f"- {c['type']} : {c.get('column','')}" for c in others])
        
        chart_list_str = "\n".join(chart_list) if chart_list else "No charts provided."

        return f"""
You are a senior data analyst. Analyze the dataset summary and the charts provided.
Your output must be structured, concise, and highly actionable.

## 1) High-Level Overview
- Summarize rows, columns, missing values, duplicates, numeric vs categorical counts.
- Mention 3–5 strong early insights from the data.

## 2) Chart-Based Interpretations
Analyze the distribution plots and other charts provided. For EACH distribution chart, describe:
- Shape (normal, skewed left/right, bimodal, uniform)
- Outliers or unusual patterns
- Data range and concentration
- Missing values or data quality issues
- Business/practical implications of the distribution

For correlation heatmap and other charts:
- Strong positive/negative correlations
- Unexpected patterns or anomalies
- Multicollinearity concerns

### Charts Provided:
{chart_list_str}

## 3) Feature-vs-Feature Plot Order (VERY IMPORTANT)
List the exact order in which the next plots should be generated:
1. Strongest correlated numerical pairs (explain why)
2. Numerical × categorical pairs revealing separation (explain why)
3. Pairs showing signs of nonlinear patterns
4. Pairs that may expose cluster-like structures

For each pair, give 1–2 lines explaining why the user should plot it.

## 4) Key Findings
Provide 5–7 concise insights across:
- Distributions
- Outliers
- Correlations
- Categorical patterns
- Relationships visible in charts

## 5) Recommended Next Steps
Give clear steps for:
- Data cleaning
- Additional plots to generate
- Feature engineering
- Modeling direction (classification / regression / clustering)

Keep the analysis sharp, helpful, and easy to understand.

### Dataset Summary
{data_summary}
"""
    # COMPACT DATA SUMMARY

    def _compact_summary(self, summary: Dict[str, Any]) -> str:
        rows = summary['shape']['rows']
        cols = summary['shape']['columns']
        dup = summary['duplicates']
        num = len(summary['numeric_columns'])
        cat = len(summary['categorical_columns'])

        out = [
            f"• Rows: {rows}",
            f"• Columns: {cols}",
            f"• Duplicate rows: {dup}",
            f"• Numeric columns: {num}",
            f"• Categorical columns: {cat}"
        ]

        if summary.get('missing_values'):
            miss_count = sum(summary['missing_values'].values())
            out.append(f"• Missing cells: {miss_count}")
        else:
            out.append("• Missing cells: 0")

        return "\n".join(out)

    # LOAD IMAGES
    def _load_images(self, chart_paths: List[Dict[str, str]]):
        """
        Load EDA chart images from eda_outputs/ folder (not media/).
        Handles absolute paths reliably so Gemini receives the image.
        """
        if not chart_paths:
            return []

        imgs = []

        # Locate project root
        project_root = Path(__file__).resolve().parent.parent  # adjust if needed
        eda_root = project_root / "eda_outputs"

        for chart in chart_paths:
            try:
                # Paths stored like: "eda_outputs/session/file.png"
                relative_path = chart["path"]

                # Make absolute path
                abs_path = project_root / relative_path

                if not abs_path.exists():
                    continue

                data = abs_path.read_bytes()

                imgs.append({
                    "mime_type": "image/png",
                    "data": data
                })
            except Exception as e:
                continue

        return imgs

    # FALLBACK ANALYSIS (SHORT)
    def _fallback_insights(self, df: pd.DataFrame, summary: Dict[str, Any]):
        return f"""
# Fallback Insights (AI Disabled)
Dataset shape: {summary['shape']}
Numeric columns: {summary['numeric_columns']}
Categorical columns: {summary['categorical_columns']}
Missing values: {summary['missing_values']}
Duplicates: {summary['duplicates']}

AI is disabled. Enable GEMINI_API_KEY for full insights.
"""