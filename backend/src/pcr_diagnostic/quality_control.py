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
    
    def run_full_qc(
        self,
        ct_threshold: float = 35.0,
        reference_genes: Optional[List[str]] = None,
    ) -> Dict:
        """
        전체 품질 관리 검사 실행

        Args:
            ct_threshold: Ct 값 임계값 (이보다 크면 경고)
            reference_genes: 표준 곡선 효율 계산에서 제외할 housekeeping 유전자

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
        efficiency = None
        if 'concentration' in self.data.columns:
            efficiency = self.estimate_efficiency(exclude_genes=reference_genes)
            print(f"5. 증폭 효율:")
            for gene, eff in efficiency.items():
                if eff is not None:
                    print(f"   - {gene}: {eff['efficiency']:.1f}% (R²={eff['r_squared']:.3f})")
                else:
                    print(f"   - {gene}: 표준 곡선 데이터 아님 (스킵)")
        
        # 결과 저장
        self.qc_results = {
            'ct_range_check': ct_check,
            'ntc_check': ntc_check,
            'reproducibility': reproducibility,
            'outliers': outliers,
            'efficiency': efficiency,
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
            non_na = group.dropna(subset=['ct_value'])
            ct_values = non_na['ct_value'].to_numpy()
            original_indices = non_na.index.to_numpy()

            if len(ct_values) < 3:
                continue

            if method == 'grubbs':
                outlier_positions = self._grubbs_test(ct_values, alpha)

            elif method == 'zscore':
                mean = np.mean(ct_values)
                std = np.std(ct_values)
                z_scores = np.abs((ct_values - mean) / std) if std > 0 else np.zeros_like(ct_values)
                outlier_positions = np.where(z_scores > 3)[0].tolist()

            elif method == 'modified_zscore':
                median = np.median(ct_values)
                mad = np.median(np.abs(ct_values - median))
                if mad > 0:
                    modified_z_scores = 0.6745 * (ct_values - median) / mad
                    outlier_positions = np.where(np.abs(modified_z_scores) > 3.5)[0].tolist()
                else:
                    outlier_positions = []
            else:
                raise ValueError(f"지원하지 않는 method: {method}")

            for pos in outlier_positions:
                outliers.append({
                    'index': int(original_indices[pos]),
                    'sample_id': sample,
                    'gene': gene,
                    'ct_value': float(ct_values[pos]),
                    'method': method
                })

        return pd.DataFrame(outliers)
    
    def _grubbs_test(self, data: np.ndarray, alpha: float = 0.05) -> List[int]:
        """
        Grubbs test로 이상치 검출 (양측 검정, iterative)

        Args:
            data: 데이터 배열
            alpha: 유의수준

        Returns:
            data 기준 위치 인덱스 리스트
        """
        outlier_positions = []
        active = np.arange(len(data))  # 원본 위치 인덱스 추적

        while len(active) > 2:
            sub = data[active]
            mean = np.mean(sub)
            std = np.std(sub, ddof=1)

            if std == 0:
                break

            abs_diff = np.abs(sub - mean)
            local_max = int(np.argmax(abs_diff))
            G = abs_diff[local_max] / std

            n = len(sub)
            t_dist = stats.t.ppf(1 - alpha / (2 * n), n - 2)
            G_critical = ((n - 1) / np.sqrt(n)) * np.sqrt(t_dist**2 / (n - 2 + t_dist**2))

            if G > G_critical:
                outlier_positions.append(int(active[local_max]))
                active = np.delete(active, local_max)
            else:
                break

        return outlier_positions
    
    def estimate_efficiency(
        self,
        exclude_genes: Optional[List[str]] = None,
        min_concentration_levels: int = 3,
        min_r_squared: float = 0.9,
    ) -> Dict:
        """
        표준 곡선으로부터 증폭 효율 추정

        Args:
            exclude_genes: 효율 계산에서 제외할 유전자 (housekeeping 등)
            min_concentration_levels: 표준 곡선으로 인정할 최소 농도 수준 개수
            min_r_squared: 적합도 최소 R² (이보다 낮으면 표준 곡선 아님으로 판정)

        Returns:
            유전자별 증폭 효율 딕셔너리. 표준 곡선 데이터가 아니면 값은 None.
        """
        if 'concentration' not in self.data.columns:
            warnings.warn("농도 정보가 없어 효율을 계산할 수 없습니다.")
            return {}

        exclude = set(exclude_genes or [])
        efficiency_results: Dict = {}

        for gene in self.data['gene'].unique():
            if gene in exclude:
                efficiency_results[gene] = None
                continue

            gene_data = self.data[self.data['gene'] == gene].dropna(
                subset=['concentration', 'ct_value']
            )
            gene_data = gene_data[gene_data['concentration'] > 0]

            # 농도 수준이 충분한지 확인 (시리얼 희석 표준 곡선 여부)
            if gene_data['concentration'].nunique() < min_concentration_levels:
                efficiency_results[gene] = None
                continue

            mean_data = gene_data.groupby('concentration')['ct_value'].mean().reset_index()
            log_concentration = np.log10(mean_data['concentration'].values)
            ct_values = mean_data['ct_value'].values

            slope, intercept, r_value, p_value, std_err = stats.linregress(
                log_concentration, ct_values
            )
            r_squared = float(r_value ** 2)

            # 표준 곡선이라면 slope는 음수여야 함 (농도↑ → Ct↓).
            # 양수/0이거나 적합도가 낮으면 표준 곡선이 아님.
            if slope >= 0 or r_squared < min_r_squared:
                efficiency_results[gene] = None
                continue

            efficiency = (10 ** (-1 / slope) - 1) * 100

            efficiency_results[gene] = {
                'efficiency': float(efficiency),
                'slope': float(slope),
                'intercept': float(intercept),
                'r_squared': r_squared,
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
    from pcr_diagnostic.data_loader import PCRDataLoader

    loader = PCRDataLoader('data/sample_pcr_data.csv')
    data = loader.load_data()

    qc = QualityControl(data)
    qc.run_full_qc()
    print("\n" + qc.generate_qc_report())
