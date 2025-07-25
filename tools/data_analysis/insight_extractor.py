"""
인사이트 추출 도구

LLM을 활용하여 데이터프레임의 실제 내용을 분석하고 핵심 인사이트를 추출하는 기능을 제공합니다.
"""

import pandas as pd
import openai
from typing import Dict, Any, List, Tuple
import json
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from config import Config

class InsightExtractor:
    """인사이트 추출 클래스"""
    
    def __init__(self):
        self.client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)
    
    def analyze_data_content(self, df: pd.DataFrame, filename: str = "") -> Dict[str, Any]:
        """LLM을 활용하여 데이터의 실제 내용을 분석하고 핵심 인사이트 추출 (시각화 제외)"""
        try:
            # 데이터 샘플 준비 (처리 가능한 크기로 제한)
            sample_size = min(100, len(df))
            sample_df = df.sample(n=sample_size, random_state=42) if len(df) > 100 else df
            
            # 데이터 정보 수집
            data_info = {
                "filename": filename,
                "total_rows": len(df),
                "total_columns": len(df.columns),
                "columns": df.columns.tolist(),
                "data_types": df.dtypes.astype(str).to_dict(),
                "sample_data": sample_df.head(10).to_dict('records'),
                "numeric_summary": {},
                "categorical_summary": {}
            }
            
            # 수치형 컬럼 요약
            numeric_cols = df.select_dtypes(include=['number']).columns
            for col in numeric_cols:
                data_info["numeric_summary"][col] = {
                    "mean": float(df[col].mean()),
                    "min": float(df[col].min()),
                    "max": float(df[col].max()),
                    "std": float(df[col].std())
                }
            
            # 범주형 컬럼 요약
            categorical_cols = df.select_dtypes(include=['object']).columns
            for col in categorical_cols:
                value_counts = df[col].value_counts().head(5)
                data_info["categorical_summary"][col] = value_counts.to_dict()
            
            # LLM 프롬프트 구성
            prompt = self._create_analysis_prompt(data_info)
            
            # LLM 분석 요청
            response = self.client.chat.completions.create(
                model=Config.DEFAULT_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "당신은 데이터 분석 전문가입니다. 엑셀 데이터의 실제 내용을 분석하여 핵심 인사이트를 제공합니다."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            # 응답 파싱
            analysis_result = response.choices[0].message.content
            
            return {
                "success": True,
                "analysis": analysis_result,
                "data_info": data_info
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"분석 중 오류 발생: {str(e)}"
            }
    
    def _create_analysis_prompt(self, data_info: Dict[str, Any]) -> str:
        """데이터 분석을 위한 LLM 프롬프트 생성"""
        prompt = f"""
다음 엑셀 데이터를 분석하여 핵심 내용과 주요 인사이트를 제공해주세요.

**파일 정보:**
- 파일명: {data_info['filename']}
- 총 행 수: {data_info['total_rows']:,}개
- 총 열 수: {data_info['total_columns']}개

**컬럼 정보:**
{', '.join(data_info['columns'])}

**데이터 샘플 (상위 10개):**
{json.dumps(data_info['sample_data'], ensure_ascii=False, indent=2)}

**수치형 데이터 요약:**
"""
        
        for col, stats in data_info['numeric_summary'].items():
            prompt += f"- {col}: 평균 {stats['mean']:.2f}, 최소 {stats['min']:.2f}, 최대 {stats['max']:.2f}\n"
        
        prompt += "\n**범주형 데이터 요약:**\n"
        for col, values in data_info['categorical_summary'].items():
            prompt += f"- {col}: {', '.join([f'{k}({v}개)' for k, v in list(values.items())[:3]])}\n"
        
        prompt += """
위 데이터를 분석하여 다음 형식으로 답변해주세요:

**📋 데이터 개요**
(이 데이터가 무엇에 대한 데이터인지, 주요 특징은 무엇인지 간략히 설명)

**🔍 주요 인사이트**
(데이터에서 발견된 주요 패턴, 특징, 의미있는 정보들을 나열)

** 핵심 수치**
(가장 중요한 수치나 통계 정보 - 구체적인 숫자와 함께)

**💡 비즈니스 관점**
(이 데이터가 비즈니스적으로 어떤 의미가 있는지, 어떤 의사결정에 도움이 될 수 있는지)

간결하고 명확하게 분석해주세요.
"""
        
        return prompt
    
    def get_available_visualizations(self, df: pd.DataFrame) -> Dict[str, List[str]]:
        """데이터에 따라 사용 가능한 시각화 옵션 반환"""
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
        
        available_viz = {
            "분포 분석": [],
            "관계 분석": [],
            "비교 분석": [],
            "트렌드 분석": [],
            "비율 분석": []
        }
        
        # 분포 분석
        if len(numeric_cols) > 0:
            available_viz["분포 분석"].append("히스토그램")
            available_viz["분포 분석"].append("박스플롯")
        if len(categorical_cols) > 0:
            available_viz["분포 분석"].append("막대 차트")
        
        # 관계 분석
        if len(numeric_cols) >= 2:
            available_viz["관계 분석"].append("산점도")
            available_viz["관계 분석"].append("상관관계 히트맵")
        
        # 비교 분석
        if len(categorical_cols) > 0 and len(numeric_cols) > 0:
            available_viz["비교 분석"].append("범주별 평균 비교")
            available_viz["비교 분석"].append("범주별 분포 비교")
        
        # 트렌드 분석
        if len(numeric_cols) > 0:
            available_viz["트렌드 분석"].append("라인 차트")
        
        # 비율 분석
        if len(categorical_cols) > 0:
            available_viz["비율 분석"].append("파이 차트")
            available_viz["비율 분석"].append("누적 막대 차트")
        
        return available_viz
    
    def generate_selected_visualizations(self, df: pd.DataFrame, selected_viz: List[str]) -> List[Dict[str, Any]]:
        """선택된 시각화 옵션에 따라 차트 생성"""
        visualizations = []
        
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
        
        for viz_type in selected_viz:
            if viz_type == "히스토그램" and len(numeric_cols) > 0:
                for col in numeric_cols[:2]:  # 최대 2개까지만
                    fig = px.histogram(df, x=col, title=f"{col} 분포", nbins=20)
                    fig.update_layout(height=400)
                    visualizations.append({
                        "type": "histogram",
                        "title": f"{col} 분포",
                        "figure": fig
                    })
            
            elif viz_type == "박스플롯" and len(numeric_cols) > 0:
                fig = px.box(df, y=numeric_cols[:3], title="수치형 컬럼 분포 비교")
                fig.update_layout(height=400)
                visualizations.append({
                    "type": "box",
                    "title": "수치형 컬럼 비교",
                    "figure": fig
                })
            
            elif viz_type == "막대 차트" and len(categorical_cols) > 0:
                for col in categorical_cols[:2]:  # 최대 2개까지만
                    value_counts = df[col].value_counts().head(10)
                    fig = px.bar(x=value_counts.index, y=value_counts.values, 
                               title=f"{col} 상위 10개 값 분포")
                    fig.update_layout(height=400)
                    visualizations.append({
                        "type": "bar",
                        "title": f"{col} 분포",
                        "figure": fig
                    })
            
            elif viz_type == "산점도" and len(numeric_cols) >= 2:
                fig = px.scatter(df, x=numeric_cols[0], y=numeric_cols[1], 
                               title=f"{numeric_cols[0]} vs {numeric_cols[1]} 상관관계")
                fig.update_layout(height=400)
                visualizations.append({
                    "type": "scatter",
                    "title": f"{numeric_cols[0]} vs {numeric_cols[1]}",
                    "figure": fig
                })
            
            elif viz_type == "상관관계 히트맵" and len(numeric_cols) >= 2:
                corr_matrix = df[numeric_cols].corr()
                fig = px.imshow(
                    corr_matrix,
                    title="수치형 컬럼 간 상관관계",
                    color_continuous_scale='RdBu',
                    aspect="auto"
                )
                fig.update_layout(height=400)
                visualizations.append({
                    "type": "correlation",
                    "title": "상관관계 히트맵",
                    "figure": fig
                })
            
            elif viz_type == "범주별 평균 비교" and len(categorical_cols) > 0 and len(numeric_cols) > 0:
                cat_col = categorical_cols[0]
                num_col = numeric_cols[0]
                group_means = df.groupby(cat_col)[num_col].mean().sort_values(ascending=False)
                fig = px.bar(
                    x=group_means.index, 
                    y=group_means.values,
                    title=f"{cat_col}별 {num_col} 평균 비교"
                )
                fig.update_layout(height=400)
                visualizations.append({
                    "type": "comparison",
                    "title": f"{cat_col}별 {num_col} 비교",
                    "figure": fig
                })
            
            elif viz_type == "라인 차트" and len(numeric_cols) > 0:
                col = numeric_cols[0]
                fig = px.line(
                    df.reset_index(), 
                    x=df.index, 
                    y=col, 
                    title=f"{col} 트렌드 분석"
                )
                fig.update_layout(height=400)
                visualizations.append({
                    "type": "trend",
                    "title": f"{col} 트렌드",
                    "figure": fig
                })
            
            elif viz_type == "파이 차트" and len(categorical_cols) > 0:
                cat_col = categorical_cols[0]
                value_counts = df[cat_col].value_counts().head(5)
                fig = px.pie(
                    values=value_counts.values, 
                    names=value_counts.index,
                    title=f"{cat_col} 비율 분석"
                )
                fig.update_layout(height=400)
                visualizations.append({
                    "type": "ratio",
                    "title": f"{cat_col} 비율",
                    "figure": fig
                })
        
        return visualizations 