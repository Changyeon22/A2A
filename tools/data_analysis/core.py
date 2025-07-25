"""
데이터 분석 도구 - 핵심 기능

엑셀/CSV 파일 업로드 및 데이터프레임 처리 기능을 제공합니다.
"""

import pandas as pd
from typing import Dict, Any, List
import streamlit as st
import openpyxl
import pdfplumber

class DataAnalysisTool:
    """데이터 분석 도구 클래스 (엑셀/CSV/PDF 통합 지원)"""
    
    def __init__(self):
        self.supported_formats = ['.csv', '.xlsx', '.xls', '.pdf']

    def process_uploaded_file(self, uploaded_file) -> Dict[str, Any]:
        """업로드된 파일을 판다스 데이터프레임 또는 텍스트로 변환하고 기본 정보를 반환"""
        try:
            if uploaded_file.name.endswith('.csv'):
                # CSV 파일은 단일 표로 처리
                df = pd.read_csv(uploaded_file)
                st.write(f"CSV 파일 로드 완료: {df.shape}")
                return {
                    "success": True,
                    "data": df,
                    "shape": df.shape,
                    "columns": df.columns.tolist(),
                    "dtypes": df.dtypes.astype(str).to_dict(),
                    "missing_values": df.isnull().sum().to_dict(),
                    "tables": [{"name": "메인 데이터", "data": df}]
                }
                
            elif uploaded_file.name.endswith(('.xlsx', '.xls')):
                # 엑셀 파일의 경우 여러 표 처리
                tables = self._load_excel_tables(uploaded_file)
                
                if not tables:
                    return {"error": "파일에서 유효한 데이터를 찾을 수 없습니다."}
                
                # 첫 번째 표를 메인 데이터로 사용
                main_df = tables[0]["data"]
                
                return {
                    "success": True,
                    "data": main_df,
                    "shape": main_df.shape,
                    "columns": main_df.columns.tolist(),
                    "dtypes": main_df.dtypes.astype(str).to_dict(),
                    "missing_values": main_df.isnull().sum().to_dict(),
                    "tables": tables
                }
            elif uploaded_file.name.endswith('.pdf'):
                # PDF 파일 분석 (pdfplumber 사용)
                with pdfplumber.open(uploaded_file) as pdf:
                    all_text = ""
                    all_tables = []
                    for i, page in enumerate(pdf.pages):
                        text = page.extract_text() or ""
                        all_text += text + "\n"
                        tables = page.extract_tables()
                        for t in tables:
                            try:
                                df = pd.DataFrame(t[1:], columns=t[0])
                                if not df.empty and df.shape[1] > 1:
                                    all_tables.append({"name": f"PDF 표 {i+1}", "data": df})
                            except Exception as e:
                                continue
                if all_tables:
                    main_df = all_tables[0]["data"]
                    return {
                        "success": True,
                        "data": main_df,
                        "shape": main_df.shape,
                        "columns": main_df.columns.tolist(),
                        "dtypes": main_df.dtypes.astype(str).to_dict(),
                        "missing_values": main_df.isnull().sum().to_dict(),
                        "tables": all_tables,
                        "text": all_text.strip()
                    }
                else:
                    # 표가 없으면 텍스트 요약만 반환
                    return {
                        "success": True,
                        "data": None,
                        "text": all_text.strip(),
                        "tables": [],
                        "message": "PDF에서 표를 찾지 못했습니다. 전체 텍스트를 반환합니다."
                    }
            else:
                return {"error": "지원하지 않는 파일 형식입니다."}
                
        except Exception as e:
            return {"error": f"파일 처리 중 오류: {str(e)}"}
    
    def _load_excel_tables(self, uploaded_file) -> List[Dict[str, Any]]:
        """엑셀 파일에서 모든 표를 로드"""
        tables = []
        
        try:
            # 엑셀 파일의 모든 시트 확인
            excel_file = openpyxl.load_workbook(uploaded_file, read_only=True, data_only=True)
            sheet_names = excel_file.sheetnames
            st.write(f"발견된 시트: {sheet_names}")
            
            for sheet_name in sheet_names:
                try:
                    # 각 시트에서 표들을 찾기
                    sheet_tables = self._extract_tables_from_sheet(uploaded_file, sheet_name)
                    tables.extend(sheet_tables)
                    
                except Exception as e:
                    st.write(f"시트 '{sheet_name}' 처리 중 오류: {str(e)}")
                    continue
            
            excel_file.close()
            
        except Exception as e:
            st.write(f"엑셀 파일 로드 중 오류: {str(e)}")
            # 오류 발생 시 기본 방식으로 로드
            try:
                df = pd.read_excel(uploaded_file, header=0)
                df = self._clean_columns_safe(df)
                if not df.empty:
                    tables.append({"name": "메인 데이터", "data": df})
            except:
                pass
        
        return tables
    
    def _extract_tables_from_sheet(self, uploaded_file, sheet_name: str) -> List[Dict[str, Any]]:
        """시트에서 개별 표들을 추출"""
        tables = []
        
        try:
            # 시트 전체를 데이터프레임으로 로드
            df = pd.read_excel(uploaded_file, sheet_name=sheet_name, header=None)
            st.write(f"시트 '{sheet_name}' 로드: {df.shape}")
            
            # 빈 행을 기준으로 표를 분리
            table_boundaries = self._find_table_boundaries(df)
            
            for i, (start_row, end_row) in enumerate(table_boundaries):
                try:
                    # 표 데이터 추출
                    table_df = df.iloc[start_row:end_row+1].copy()
                    
                    # 표 정리
                    table_df = self._clean_table(table_df)
                    
                    if not table_df.empty and table_df.shape[0] > 1 and table_df.shape[1] > 1:
                        table_name = f"{sheet_name} - 표 {i+1}"
                        tables.append({
                            "name": table_name,
                            "data": table_df,
                            "sheet": sheet_name,
                            "position": f"행 {start_row+1}-{end_row+1}"
                        })
                        
                except Exception as e:
                    st.write(f"표 {i+1} 처리 중 오류: {str(e)}")
                    continue
            
            # 표를 찾지 못한 경우 전체 시트를 하나의 표로 처리
            if not tables and not df.empty:
                df_cleaned = self._clean_columns_safe(df)
                if not df_cleaned.empty:
                    tables.append({
                        "name": f"{sheet_name} - 전체",
                        "data": df_cleaned,
                        "sheet": sheet_name,
                        "position": "전체"
                    })
            
        except Exception as e:
            st.write(f"시트 '{sheet_name}' 표 추출 중 오류: {str(e)}")
        
        return tables
    
    def _find_table_boundaries(self, df: pd.DataFrame) -> List[tuple]:
        """데이터프레임에서 표의 경계를 찾기"""
        boundaries = []
        
        try:
            # 빈 행 찾기 (모든 컬럼이 NaN인 행)
            empty_rows = df.isna().all(axis=1)
            
            # 연속된 빈 행을 기준으로 표 분리
            start_row = 0
            for i in range(len(df)):
                if empty_rows.iloc[i]:  # 빈 행인 경우
                    if i > start_row:  # 이전에 데이터가 있었다면 표로 추가
                        boundaries.append((start_row, i-1))
                    start_row = i + 1
            
            # 마지막 표 처리
            if start_row < len(df):
                boundaries.append((start_row, len(df)-1))
            
            # 너무 작은 표는 제외 (최소 2행 2열)
            boundaries = [(start, end) for start, end in boundaries 
                         if end - start >= 1 and df.iloc[start:end+1].shape[1] >= 2]
            
        except Exception as e:
            st.write(f"표 경계 찾기 중 오류: {str(e)}")
        
        return boundaries
    
    def _clean_table(self, df: pd.DataFrame) -> pd.DataFrame:
        """개별 표 정리"""
        try:
            # 첫 번째 행을 헤더로 사용
            if len(df) > 0:
                df.columns = df.iloc[0]
                df = df.iloc[1:].reset_index(drop=True)
            
            # 빈 컬럼과 행 제거
            df = df.dropna(axis=1, how='all')
            df = df.dropna(axis=0, how='all')
            
            # 컬럼명 정리
            valid_columns = []
            for i, col in enumerate(df.columns):
                if pd.isna(col) or str(col).strip() == '':
                    valid_columns.append(f'Column_{i+1}')
                else:
                    valid_columns.append(str(col))
            
            df.columns = valid_columns
            
            return df
            
        except Exception as e:
            st.write(f"표 정리 중 오류: {str(e)}")
            return df
    
    def _clean_columns_safe(self, df: pd.DataFrame) -> pd.DataFrame:
        """안전한 컬럼 정리"""
        try:
            # 빈 컬럼만 제거
            df = df.dropna(axis=1, how='all')
            
            # 빈 행만 제거
            df = df.dropna(axis=0, how='all')
            
            # 컬럼명이 비어있거나 None인 경우에만 처리
            valid_columns = []
            for i, col in enumerate(df.columns):
                if pd.isna(col) or str(col).strip() == '':
                    valid_columns.append(f'Column_{i+1}')
                else:
                    valid_columns.append(str(col))
            
            df.columns = valid_columns
            
            return df
            
        except Exception as e:
            st.write(f"컬럼 정리 중 오류: {str(e)}")
            return df 