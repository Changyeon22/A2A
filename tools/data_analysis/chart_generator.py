"""
차트 생성 도구

데이터프레임을 받아 자동으로 차트를 생성하는 기능을 제공합니다.
"""

import plotly.express as px
from typing import List, Dict, Any
import pandas as pd

class ChartGenerator:
    """차트 생성 클래스"""
    
    def auto_generate_charts(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """데이터 특성에 따라 자동으로 적절한 차트 생성"""
        charts = []
        
        # 수치형 컬럼 분석
        numeric_cols = df.select_dtypes(include=['number']).columns
        if len(numeric_cols) >= 2:
            # 산점도 생성
            fig = px.scatter(df, x=numeric_cols[0], y=numeric_cols[1], 
                           title=f"{numeric_cols[0]} vs {numeric_cols[1]}")
            charts.append({
                "type": "scatter",
                "title": f"{numeric_cols[0]} vs {numeric_cols[1]}",
                "figure": fig
            })
            
        # 카테고리형 컬럼 분석
        categorical_cols = df.select_dtypes(include=['object']).columns
        for col in categorical_cols[:3]:  # 최대 3개까지만
            value_counts = df[col].value_counts()
            fig = px.bar(x=value_counts.index, y=value_counts.values, 
                        title=f"{col} 분포")
            charts.append({
                "type": "bar",
                "title": f"{col} 분포",
                "figure": fig
            })
            
        return charts 