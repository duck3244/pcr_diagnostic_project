"""
PCR 데이터 로더 모듈
다양한 형식의 PCR 데이터를 로드하고 전처리합니다.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional, Union, List, Dict
import warnings


class PCRDataLoader:
    """
    PCR 데이터를 로드하고 검증하는 클래스
    """
    
    def __init__(self, filepath: Union[str, Path]):
        """
        Args:
            filepath: 데이터 파일 경로 (CSV, Excel 지원)
        """
        self.filepath = Path(filepath)
        self.data = None
        self.metadata = {}
        
    def load_data(self, **kwargs) -> pd.DataFrame:
        """
        데이터 파일을 로드합니다.
        
        Returns:
            로드된 데이터프레임
        """
        if not self.filepath.exists():
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {self.filepath}")
        
        # 파일 형식에 따라 로드
        if self.filepath.suffix == '.csv':
            self.data = pd.read_csv(self.filepath, **kwargs)
        elif self.filepath.suffix in ['.xlsx', '.xls']:
            self.data = pd.read_excel(self.filepath, **kwargs)
        else:
            raise ValueError(f"지원하지 않는 파일 형식: {self.filepath.suffix}")
        
        # 기본 검증
        self._validate_data()
        
        # 메타데이터 수집
        self._collect_metadata()
        
        return self.data
    
    def _validate_data(self):
        """데이터 기본 검증"""
        required_columns = ['sample_id', 'gene', 'ct_value']
        missing_columns = [col for col in required_columns if col not in self.data.columns]
        
        if missing_columns:
            raise ValueError(f"필수 컬럼이 없습니다: {missing_columns}")
        
        # Ct 값이 숫자인지 확인 (NaN 제외)
        ct_values = self.data['ct_value'].dropna()
        if not pd.api.types.is_numeric_dtype(ct_values):
            warnings.warn("ct_value 컬럼에 숫자가 아닌 값이 있습니다.")
    
    def _collect_metadata(self):
        """메타데이터 수집"""
        self.metadata = {
            'total_samples': self.data['sample_id'].nunique(),
            'total_genes': self.data['gene'].nunique(),
            'total_measurements': len(self.data),
            'genes': self.data['gene'].unique().tolist(),
            'groups': self.data['group'].unique().tolist() if 'group' in self.data.columns else [],
            'ct_range': (self.data['ct_value'].min(), self.data['ct_value'].max()),
            'missing_values': self.data['ct_value'].isna().sum()
        }
    
    def get_metadata(self) -> Dict:
        """메타데이터 반환"""
        return self.metadata
    
    def filter_by_gene(self, genes: Union[str, List[str]]) -> pd.DataFrame:
        """
        특정 유전자만 필터링
        
        Args:
            genes: 유전자 이름 (문자열 또는 리스트)
            
        Returns:
            필터링된 데이터프레임
        """
        if isinstance(genes, str):
            genes = [genes]
        
        return self.data[self.data['gene'].isin(genes)].copy()
    
    def filter_by_group(self, groups: Union[str, List[str]]) -> pd.DataFrame:
        """
        특정 그룹만 필터링
        
        Args:
            groups: 그룹 이름 (문자열 또는 리스트)
            
        Returns:
            필터링된 데이터프레임
        """
        if 'group' not in self.data.columns:
            raise ValueError("데이터에 'group' 컬럼이 없습니다.")
        
        if isinstance(groups, str):
            groups = [groups]
        
        return self.data[self.data['group'].isin(groups)].copy()
    
    def get_replicates(self, sample_id: str, gene: str) -> pd.DataFrame:
        """
        특정 샘플과 유전자의 반복 측정값 반환
        
        Args:
            sample_id: 샘플 ID
            gene: 유전자 이름
            
        Returns:
            반복 측정값 데이터프레임
        """
        return self.data[
            (self.data['sample_id'] == sample_id) & 
            (self.data['gene'] == gene)
        ].copy()
    
    def calculate_mean_ct(self, group_by: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Ct 값의 평균 계산

        Args:
            group_by: 그룹화 기준 컬럼 리스트 (기본값: ['sample_id', 'gene'])

        Returns:
            평균 Ct 값이 포함된 데이터프레임
        """
        if group_by is None:
            group_by = ['sample_id', 'gene']

        result = self.data.groupby(group_by).agg({
            'ct_value': ['mean', 'std', 'count']
        }).reset_index()
        
        # 컬럼 이름 정리
        result.columns = group_by + ['ct_mean', 'ct_std', 'n_replicates']
        
        return result
    
    def remove_outliers(self, method: str = 'zscore', threshold: float = 3.0) -> pd.DataFrame:
        """
        이상치 제거
        
        Args:
            method: 이상치 탐지 방법 ('zscore', 'iqr')
            threshold: 이상치 판정 임계값
            
        Returns:
            이상치가 제거된 데이터프레임
        """
        data_clean = self.data.copy()
        
        if method == 'zscore':
            # Z-score 기반 이상치 제거
            for (sample, gene), group in self.data.groupby(['sample_id', 'gene']):
                if len(group) > 2:  # 최소 3개 이상의 반복이 있을 때만
                    mean = group['ct_value'].mean()
                    std = group['ct_value'].std()
                    
                    if std > 0:
                        z_scores = np.abs((group['ct_value'] - mean) / std)
                        outlier_mask = z_scores > threshold
                        
                        # 이상치를 NaN으로 표시
                        data_clean.loc[group.index[outlier_mask], 'ct_value'] = np.nan
        
        elif method == 'iqr':
            # IQR 기반 이상치 제거
            for (sample, gene), group in self.data.groupby(['sample_id', 'gene']):
                if len(group) > 3:
                    Q1 = group['ct_value'].quantile(0.25)
                    Q3 = group['ct_value'].quantile(0.75)
                    IQR = Q3 - Q1
                    
                    lower_bound = Q1 - threshold * IQR
                    upper_bound = Q3 + threshold * IQR
                    
                    outlier_mask = (group['ct_value'] < lower_bound) | (group['ct_value'] > upper_bound)
                    data_clean.loc[group.index[outlier_mask], 'ct_value'] = np.nan
        
        # NaN이 아닌 행만 반환
        return data_clean.dropna(subset=['ct_value'])
    
    def export_processed_data(self, output_path: Union[str, Path], format: str = 'csv'):
        """
        처리된 데이터 내보내기
        
        Args:
            output_path: 출력 파일 경로
            format: 파일 형식 ('csv', 'excel')
        """
        output_path = Path(output_path)
        
        if format == 'csv':
            self.data.to_csv(output_path, index=False)
        elif format == 'excel':
            self.data.to_excel(output_path, index=False)
        else:
            raise ValueError(f"지원하지 않는 형식: {format}")
        
        print(f"데이터가 저장되었습니다: {output_path}")


class AmplificationCurveLoader:
    """
    증폭 곡선 데이터를 로드하는 클래스
    """
    
    def __init__(self, filepath: Union[str, Path]):
        """
        Args:
            filepath: 증폭 곡선 데이터 파일 경로
        """
        self.filepath = Path(filepath)
        self.data = None
    
    def load_curve_data(self) -> pd.DataFrame:
        """
        증폭 곡선 데이터 로드
        
        예상 형식:
        cycle, sample_1, sample_2, sample_3, ...
        1, 0.1, 0.12, 0.11, ...
        2, 0.15, 0.18, 0.16, ...
        
        Returns:
            Long format의 증폭 곡선 데이터
        """
        # Wide format 로드
        data_wide = pd.read_csv(self.filepath)
        
        # Long format으로 변환
        data_long = data_wide.melt(
            id_vars=['cycle'],
            var_name='sample_id',
            value_name='fluorescence'
        )
        
        self.data = data_long
        return self.data
    
    def get_sample_curve(self, sample_id: str) -> pd.DataFrame:
        """특정 샘플의 증폭 곡선 반환"""
        return self.data[self.data['sample_id'] == sample_id].copy()


if __name__ == "__main__":
    # 테스트 코드
    loader = PCRDataLoader('data/sample_pcr_data.csv')
    data = loader.load_data()
    
    print("=== 데이터 로드 완료 ===")
    print(f"샘플 수: {loader.metadata['total_samples']}")
    print(f"유전자: {loader.metadata['genes']}")
    print(f"그룹: {loader.metadata['groups']}")
    
    print("\n=== 평균 Ct 계산 ===")
    mean_ct = loader.calculate_mean_ct()
    print(mean_ct.head())
    
    print("\n=== gene_A 필터링 ===")
    gene_a = loader.filter_by_gene('gene_A')
    print(gene_a.head())
