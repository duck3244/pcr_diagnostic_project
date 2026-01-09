"""
PCR 품질 관리 (Quality Control) 모듈
Ct 값 검증, 재현성 평가, 이상치 탐지 등을 수행합니다.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from scipy import stats
import warnings


class QualityControl:
    """
    PCR 데이터의 품질 관리 클래스
    """
    
    def __init__(self, data: pd.DataFrame):
        """
        Args:
            data: PCR 데이터프레임
        """
        self.data = data.copy()
        self.qc_results = {}
    
    def run_full_qc(self, ct_threshold: float = 35.0) -> Dict:
        """
        전체 품질 관리 검사 실행
        
        Args:
            ct_threshold: Ct 값 임계값 (이보다 크면 경고)
            
        Returns:
            QC 결과 딕셔너리
        """
        print("=== PCR 품질 관리 시작 ===\n")
        
        # 1. Ct 값 범위 검사
        ct_check = self.check_ct_range(ct_threshold)
        print(f"1. Ct 범위 검사: {'통과' if ct_check['pass'] else '실패'}")
        print(f"   - 총 측정: {ct_check['total_measurements']}")
        print(f"   - 임계값 초과: {ct_check['above_threshold']}\n")
        
        # 2. NTC (No Template Control) 검사
        ntc_check = self.check_ntc()
        print(f"2. NTC 검사: {'통과' if ntc_check['pass'] else '실패'}")
        print(f"   - NTC 샘플 수: {ntc_check['ntc_count']}")
        print(f"   - 증폭 감지: {ntc_check['amplified_count']}\n")
        
        # 3. 재현성 검사
        reproducibility = self.check_reproducibility()
        print(f"3. 재현성 검사:")
        print(f"   - 평균 CV%: {reproducibility['mean_cv']:.2f}%")
        print(f"   - CV% > 5% 샘플: {reproducibility['high_cv_count']}\n")
        
        # 4. 이상치 검출
        outliers = self.detect_outliers()
        print(f"4. 이상치 검출:")
        print(f"   - 이상치 수: {len(outliers)}\n")
        
        # 5. 증폭 효율 추정 (표준 곡선이 있는 경우)
        if 'concentration' in self.data.columns:
            efficiency = self.estimate_efficiency()
            print(f"5. 증폭 효율:")
            for gene, eff in efficiency.items():
                if eff is not None:
                    print(f"   - {gene}: {eff['efficiency']:.1f}% (R²={eff['r_squared']:.3f})")
        
        # 결과 저장
        self.qc_results = {
            'ct_range_check': ct_check,
            'ntc_check': ntc_check,
            'reproducibility': reproducibility,
            'outliers': outliers,
            'efficiency': efficiency if 'concentration' in self.data.columns else None
        }
        
        print("\n=== 품질 관리 완료 ===")
        return self.qc_results
    
    def check_ct_range(self, threshold: float = 35.0) -> Dict:
        """
        Ct 값 범위 검사
        
        Args:
            threshold: Ct 값 임계값
            
        Returns:
            검사 결과 딕셔너리
        """
        ct_values = self.data['ct_value'].dropna()
        above_threshold = (ct_values > threshold).sum()
        
        return {
            'pass': above_threshold == 0,
            'total_measurements': len(ct_values),
            'above_threshold': int(above_threshold),
            'threshold': threshold,
            'ct_min': float(ct_values.min()),
            'ct_max': float(ct_values.max()),
            'ct_mean': float(ct_values.mean())
        }
    
    def check_ntc(self) -> Dict:
        """
        No Template Control (NTC) 검사
        
        Returns:
            NTC 검사 결과
        """
        # NTC 샘플 찾기
        ntc_data = self.data[self.data['sample_id'].str.contains('NTC', case=False, na=False)]
        
        if len(ntc_data) == 0:
            return {
                'pass': None,
                'ntc_count': 0,
                'amplified_count': 0,
                'message': 'NTC 샘플이 없습니다.'
            }
        
        # Ct 값이 있는 (증폭된) NTC 수
        amplified_ntc = ntc_data['ct_value'].notna().sum()
        
        return {
            'pass': amplified_ntc == 0,
            'ntc_count': len(ntc_data),
            'amplified_count': int(amplified_ntc),
            'amplified_samples': ntc_data[ntc_data['ct_value'].notna()]['sample_id'].unique().tolist()
        }
    
    def check_reproducibility(self, cv_threshold: float = 5.0) -> Dict:
        """
        기술적 반복의 재현성 검사 (Coefficient of Variation)
        
        Args:
            cv_threshold: CV% 임계값
            
        Returns:
            재현성 검사 결과
        """
        # 샘플-유전자별로 그룹화하여 CV 계산
        cv_results = []
        
        for (sample, gene), group in self.data.groupby(['sample_id', 'gene']):
            ct_values = group['ct_value'].dropna()
            
            if len(ct_values) >= 2:  # 최소 2개 이상의 반복이 있어야 함
                mean_ct = ct_values.mean()
                std_ct = ct_values.std()
                cv = (std_ct / mean_ct * 100) if mean_ct > 0 else 0
                
                cv_results.append({
                    'sample_id': sample,
                    'gene': gene,
                    'mean_ct': mean_ct,
                    'std_ct': std_ct,
                    'cv_percent': cv,
                    'n_replicates': len(ct_values)
                })
        
        cv_df = pd.DataFrame(cv_results)
        
        if len(cv_df) == 0:
            return {
                'mean_cv': 0,
                'median_cv': 0,
                'high_cv_count': 0,
                'details': cv_df
            }
        
        high_cv = cv_df[cv_df['cv_percent'] > cv_threshold]
        
        return {
            'mean_cv': float(cv_df['cv_percent'].mean()),
            'median_cv': float(cv_df['cv_percent'].median()),
            'max_cv': float(cv_df['cv_percent'].max()),
            'high_cv_count': len(high_cv),
            'cv_threshold': cv_threshold,
            'details': cv_df,
            'high_cv_samples': high_cv[['sample_id', 'gene', 'cv_percent']].to_dict('records')
        }
    
    def detect_outliers(self, method: str = 'grubbs', alpha: float = 0.05) -> pd.DataFrame:
        """
        이상치 검출
        
        Args:
            method: 검출 방법 ('grubbs', 'zscore', 'modified_zscore')
            alpha: 유의수준 (Grubbs test용)
            
        Returns:
            이상치 데이터프레임
        """
        outliers = []
        
        for (sample, gene), group in self.data.groupby(['sample_id', 'gene']):
            ct_values = group['ct_value'].dropna().values
            
            if len(ct_values) < 3:
                continue
            
            if method == 'grubbs':
                # Grubbs test
                outlier_indices = self._grubbs_test(ct_values, alpha)
                
            elif method == 'zscore':
                # Z-score method
                mean = np.mean(ct_values)
                std = np.std(ct_values)
                z_scores = np.abs((ct_values - mean) / std) if std > 0 else np.zeros_like(ct_values)
                outlier_indices = np.where(z_scores > 3)[0]
                
            elif method == 'modified_zscore':
                # Modified Z-score (using median)
                median = np.median(ct_values)
                mad = np.median(np.abs(ct_values - median))
                modified_z_scores = 0.6745 * (ct_values - median) / mad if mad > 0 else np.zeros_like(ct_values)
                outlier_indices = np.where(np.abs(modified_z_scores) > 3.5)[0]
            
            # 이상치 정보 저장
            for idx in outlier_indices:
                original_idx = group.index[group['ct_value'].notna()][idx]
                outliers.append({
                    'index': original_idx,
                    'sample_id': sample,
                    'gene': gene,
                    'ct_value': ct_values[idx],
                    'method': method
                })
        
        return pd.DataFrame(outliers)
    
    def _grubbs_test(self, data: np.ndarray, alpha: float = 0.05) -> List[int]:
        """
        Grubbs test로 이상치 검출 (양측 검정)
        
        Args:
            data: 데이터 배열
            alpha: 유의수준
            
        Returns:
            이상치 인덱스 리스트
        """
        outlier_indices = []
        data_copy = data.copy()
        
        while len(data_copy) > 2:
            mean = np.mean(data_copy)
            std = np.std(data_copy, ddof=1)
            
            if std == 0:
                break
            
            # G 통계량 계산
            abs_diff = np.abs(data_copy - mean)
            max_idx = np.argmax(abs_diff)
            G = abs_diff[max_idx] / std
            
            # 임계값 계산
            n = len(data_copy)
            t_dist = stats.t.ppf(1 - alpha / (2 * n), n - 2)
            G_critical = ((n - 1) / np.sqrt(n)) * np.sqrt(t_dist**2 / (n - 2 + t_dist**2))
            
            # 이상치 판정
            if G > G_critical:
                # 원본 인덱스 찾기
                original_idx = np.where(data == data_copy[max_idx])[0][0]
                outlier_indices.append(original_idx)
                data_copy = np.delete(data_copy, max_idx)
            else:
                break
        
        return outlier_indices
    
    def estimate_efficiency(self) -> Dict:
        """
        표준 곡선으로부터 증폭 효율 추정
        
        Returns:
            유전자별 증폭 효율 딕셔너리
        """
        if 'concentration' not in self.data.columns:
            warnings.warn("농도 정보가 없어 효율을 계산할 수 없습니다.")
            return {}
        
        efficiency_results = {}
        
        for gene in self.data['gene'].unique():
            gene_data = self.data[self.data['gene'] == gene].copy()
            
            # 농도와 Ct 값이 모두 있는 데이터만 사용
            gene_data = gene_data.dropna(subset=['concentration', 'ct_value'])
            gene_data = gene_data[gene_data['concentration'] > 0]
            
            if len(gene_data) < 3:
                efficiency_results[gene] = None
                continue
            
            # 평균 Ct 계산 (농도별)
            mean_data = gene_data.groupby('concentration')['ct_value'].mean().reset_index()
            
            if len(mean_data) < 2:
                efficiency_results[gene] = None
                continue
            
            # 로그 농도
            log_concentration = np.log10(mean_data['concentration'].values)
            ct_values = mean_data['ct_value'].values
            
            # 선형 회귀
            slope, intercept, r_value, p_value, std_err = stats.linregress(log_concentration, ct_values)
            
            # 효율 계산: E = 10^(-1/slope) - 1
            efficiency = (10 ** (-1 / slope) - 1) * 100 if slope != 0 else 0
            
            efficiency_results[gene] = {
                'efficiency': float(efficiency),
                'slope': float(slope),
                'intercept': float(intercept),
                'r_squared': float(r_value ** 2),
                'p_value': float(p_value)
            }
        
        return efficiency_results
    
    def generate_qc_report(self, output_path: str = None) -> str:
        """
        QC 리포트 생성
        
        Args:
            output_path: 리포트 저장 경로
            
        Returns:
            리포트 텍스트
        """
        if not self.qc_results:
            self.run_full_qc()
        
        report = []
        report.append("=" * 60)
        report.append("PCR 품질 관리 리포트")
        report.append("=" * 60)
        report.append("")
        
        # Ct 범위 검사
        ct_check = self.qc_results['ct_range_check']
        report.append("1. Ct 값 범위 검사")
        report.append(f"   상태: {'통과' if ct_check['pass'] else '실패'}")
        report.append(f"   총 측정: {ct_check['total_measurements']}")
        report.append(f"   임계값({ct_check['threshold']}) 초과: {ct_check['above_threshold']}")
        report.append(f"   Ct 범위: {ct_check['ct_min']:.2f} - {ct_check['ct_max']:.2f}")
        report.append("")
        
        # NTC 검사
        ntc_check = self.qc_results['ntc_check']
        report.append("2. NTC (No Template Control) 검사")
        report.append(f"   상태: {'통과' if ntc_check['pass'] else '실패' if ntc_check['pass'] is not None else '해당없음'}")
        report.append(f"   NTC 샘플 수: {ntc_check['ntc_count']}")
        report.append(f"   증폭 감지: {ntc_check['amplified_count']}")
        report.append("")
        
        # 재현성
        repro = self.qc_results['reproducibility']
        report.append("3. 재현성 검사")
        report.append(f"   평균 CV%: {repro['mean_cv']:.2f}%")
        report.append(f"   중앙값 CV%: {repro['median_cv']:.2f}%")
        report.append(f"   CV% > {repro['cv_threshold']}% 샘플: {repro['high_cv_count']}")
        report.append("")
        
        # 이상치
        outliers = self.qc_results['outliers']
        report.append("4. 이상치 검출")
        report.append(f"   이상치 수: {len(outliers)}")
        report.append("")
        
        # 증폭 효율
        if self.qc_results['efficiency']:
            report.append("5. 증폭 효율")
            for gene, eff in self.qc_results['efficiency'].items():
                if eff:
                    report.append(f"   {gene}:")
                    report.append(f"      효율: {eff['efficiency']:.1f}%")
                    report.append(f"      R²: {eff['r_squared']:.3f}")
                    report.append(f"      Slope: {eff['slope']:.3f}")
            report.append("")
        
        report.append("=" * 60)
        
        report_text = "\n".join(report)
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report_text)
            print(f"리포트가 저장되었습니다: {output_path}")
        
        return report_text


if __name__ == "__main__":
    # 테스트 코드
    from data_loader import PCRDataLoader
    
    loader = PCRDataLoader('../data/sample_pcr_data.csv')
    data = loader.load_data()
    
    qc = QualityControl(data)
    results = qc.run_full_qc()
    
    print("\n" + qc.generate_qc_report())
