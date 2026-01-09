"""
PCR 정량 분석 모듈
ΔΔCt 방법, Standard Curve 방법 등을 구현합니다.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from scipy import stats
import warnings


class DeltaDeltaCt:
    """
    ΔΔCt 방법을 사용한 상대 정량 분석
    """
    
    def __init__(self, data: pd.DataFrame):
        """
        Args:
            data: PCR 데이터프레임
        """
        self.data = data.copy()
        self.results = None
    
    def calculate(
        self,
        target_gene: str,
        reference_gene: str,
        control_group: str,
        treatment_groups: Optional[List[str]] = None,
        efficiency_target: float = 2.0,
        efficiency_reference: float = 2.0
    ) -> Dict:
        """
        ΔΔCt 계산 수행
        
        Args:
            target_gene: 목표 유전자
            reference_gene: 참조 유전자 (housekeeping gene)
            control_group: 대조군 그룹명
            treatment_groups: 실험군 그룹명 리스트 (None이면 control 제외 모두)
            efficiency_target: 목표 유전자 증폭 효율 (기본값 2.0 = 100%)
            efficiency_reference: 참조 유전자 증폭 효율 (기본값 2.0 = 100%)
            
        Returns:
            분석 결과 딕셔너리
        """
        print(f"=== ΔΔCt 분석 시작 ===")
        print(f"목표 유전자: {target_gene}")
        print(f"참조 유전자: {reference_gene}")
        print(f"대조군: {control_group}\n")
        
        # 그룹 확인
        if treatment_groups is None:
            all_groups = self.data['group'].unique()
            treatment_groups = [g for g in all_groups if g != control_group]
        
        # 평균 Ct 계산
        mean_ct = self._calculate_mean_ct()
        
        # ΔCt 계산 (Target - Reference)
        delta_ct = self._calculate_delta_ct(mean_ct, target_gene, reference_gene)
        
        # ΔΔCt 계산 (Treatment - Control)
        results = {}
        
        for treatment_group in treatment_groups:
            result = self._calculate_delta_delta_ct(
                delta_ct, 
                control_group, 
                treatment_group,
                efficiency_target,
                efficiency_reference
            )
            
            # None 체크 추가
            if result is None:
                print(f"\n{treatment_group} vs {control_group}:")
                print(f"  ⚠️  데이터 부족으로 분석 불가")
                continue
            
            results[treatment_group] = result
            
            print(f"\n{treatment_group} vs {control_group}:")
            print(f"  ΔΔCt: {result['delta_delta_ct']:.3f}")
            print(f"  Fold Change: {result['fold_change']:.3f}")
            print(f"  P-value: {result['p_value']:.4f}")
            print(f"  상태: {'유의함' if result['significant'] else '유의하지 않음'} (α=0.05)")
        
        self.results = {
            'target_gene': target_gene,
            'reference_gene': reference_gene,
            'control_group': control_group,
            'comparisons': results,
            'mean_ct': mean_ct,
            'delta_ct': delta_ct
        }
        
        return self.results
    
    def _calculate_mean_ct(self) -> pd.DataFrame:
        """샘플-유전자-그룹별 평균 Ct 계산"""
        mean_ct = self.data.groupby(['sample_id', 'gene', 'group']).agg({
            'ct_value': ['mean', 'std', 'count']
        }).reset_index()
        
        mean_ct.columns = ['sample_id', 'gene', 'group', 'ct_mean', 'ct_std', 'n']
        return mean_ct
    
    def _calculate_delta_ct(
        self, 
        mean_ct: pd.DataFrame, 
        target_gene: str, 
        reference_gene: str
    ) -> pd.DataFrame:
        """ΔCt 계산 (Target - Reference)"""
        
        # Target과 Reference 데이터 분리
        target_data = mean_ct[mean_ct['gene'] == target_gene].copy()
        reference_data = mean_ct[mean_ct['gene'] == reference_gene].copy()
        
        # 병합
        merged = pd.merge(
            target_data,
            reference_data,
            on=['sample_id', 'group'],
            suffixes=('_target', '_ref')
        )
        
        # ΔCt = Ct(target) - Ct(reference)
        merged['delta_ct'] = merged['ct_mean_target'] - merged['ct_mean_ref']
        
        # 오차 전파
        merged['delta_ct_std'] = np.sqrt(
            merged['ct_std_target']**2 + merged['ct_std_ref']**2
        )
        
        return merged[['sample_id', 'group', 'delta_ct', 'delta_ct_std']]
    
    def _calculate_delta_delta_ct(
        self,
        delta_ct: pd.DataFrame,
        control_group: str,
        treatment_group: str,
        efficiency_target: float = 2.0,
        efficiency_reference: float = 2.0
    ) -> Dict:
        """ΔΔCt 계산 및 통계 검정"""
        
        # 각 그룹의 ΔCt 값
        control_delta_ct = delta_ct[delta_ct['group'] == control_group]['delta_ct'].values
        treatment_delta_ct = delta_ct[delta_ct['group'] == treatment_group]['delta_ct'].values
        
        if len(control_delta_ct) == 0 or len(treatment_delta_ct) == 0:
            warnings.warn(f"그룹 데이터가 충분하지 않습니다: {control_group} or {treatment_group}")
            return None
        
        # ΔΔCt = ΔCt(treatment) - mean(ΔCt(control))
        mean_control_delta_ct = np.mean(control_delta_ct)
        delta_delta_ct_values = treatment_delta_ct - mean_control_delta_ct
        mean_delta_delta_ct = np.mean(delta_delta_ct_values)
        
        # Fold Change 계산
        # 효율을 고려한 계산: FC = E_target^(-ΔΔCt) / E_reference^(-ΔΔCt)
        # 효율이 같다면: FC = E^(-ΔΔCt)
        if efficiency_target == efficiency_reference:
            fold_change = efficiency_target ** (-mean_delta_delta_ct)
        else:
            # 효율이 다른 경우의 보정
            fold_change = (efficiency_target / efficiency_reference) ** (-mean_delta_delta_ct)
        
        # t-test 수행
        t_stat, p_value = stats.ttest_ind(treatment_delta_ct, control_delta_ct)
        
        # 95% 신뢰구간 계산
        se = np.std(delta_delta_ct_values, ddof=1) / np.sqrt(len(delta_delta_ct_values))
        ci_95 = stats.t.interval(
            0.95, 
            len(delta_delta_ct_values) - 1, 
            loc=mean_delta_delta_ct, 
            scale=se
        )
        
        return {
            'delta_delta_ct': float(mean_delta_delta_ct),
            'fold_change': float(fold_change),
            'log2_fold_change': float(np.log2(fold_change)),
            'p_value': float(p_value),
            't_statistic': float(t_stat),
            'ci_95_lower': float(ci_95[0]),
            'ci_95_upper': float(ci_95[1]),
            'significant': p_value < 0.05,
            'n_control': len(control_delta_ct),
            'n_treatment': len(treatment_delta_ct)
        }
    
    def export_results(self, output_path: str):
        """결과를 CSV 파일로 저장"""
        if self.results is None:
            raise ValueError("먼저 calculate()를 실행하세요.")
        
        # 결과를 DataFrame으로 변환
        rows = []
        for group, result in self.results['comparisons'].items():
            if result is not None:
                row = {
                    'comparison': f"{group} vs {self.results['control_group']}",
                    'target_gene': self.results['target_gene'],
                    'reference_gene': self.results['reference_gene'],
                    **result
                }
                rows.append(row)
        
        df = pd.DataFrame(rows)
        df.to_csv(output_path, index=False)
        print(f"\n결과가 저장되었습니다: {output_path}")


class StandardCurve:
    """
    Standard Curve 방법을 사용한 절대 정량 분석
    """
    
    def __init__(self, data: pd.DataFrame):
        """
        Args:
            data: 농도 정보가 포함된 PCR 데이터프레임
        """
        self.data = data.copy()
        self.standard_curves = {}
    
    def build_standard_curve(self, gene: str) -> Dict:
        """
        특정 유전자의 표준 곡선 생성
        
        Args:
            gene: 유전자 이름
            
        Returns:
            표준 곡선 정보 딕셔너리
        """
        # 해당 유전자 데이터 필터링
        gene_data = self.data[self.data['gene'] == gene].copy()
        
        # 농도와 Ct 값이 있는 데이터만 사용
        gene_data = gene_data.dropna(subset=['concentration', 'ct_value'])
        gene_data = gene_data[gene_data['concentration'] > 0]
        
        if len(gene_data) < 3:
            raise ValueError(f"{gene}의 표준 곡선 데이터가 부족합니다 (최소 3개 필요).")
        
        # 농도별 평균 Ct 계산
        mean_data = gene_data.groupby('concentration').agg({
            'ct_value': ['mean', 'std', 'count']
        }).reset_index()
        
        mean_data.columns = ['concentration', 'ct_mean', 'ct_std', 'n']
        
        # 로그 농도
        log_conc = np.log10(mean_data['concentration'].values)
        ct_values = mean_data['ct_mean'].values
        
        # 선형 회귀
        slope, intercept, r_value, p_value, std_err = stats.linregress(log_conc, ct_values)
        
        # 증폭 효율 계산
        efficiency = (10 ** (-1 / slope) - 1) * 100
        
        # 표준 곡선 정보 저장
        curve_info = {
            'gene': gene,
            'slope': float(slope),
            'intercept': float(intercept),
            'r_squared': float(r_value ** 2),
            'efficiency': float(efficiency),
            'p_value': float(p_value),
            'std_err': float(std_err),
            'data_points': len(mean_data),
            'concentration_range': (
                float(mean_data['concentration'].min()),
                float(mean_data['concentration'].max())
            ),
            'equation': f"Ct = {slope:.3f} × log10(Conc) + {intercept:.3f}"
        }
        
        self.standard_curves[gene] = curve_info
        
        print(f"\n=== {gene} 표준 곡선 ===")
        print(f"방정식: {curve_info['equation']}")
        print(f"R² = {curve_info['r_squared']:.4f}")
        print(f"증폭 효율 = {curve_info['efficiency']:.1f}%")
        print(f"농도 범위: {curve_info['concentration_range'][0]:.2e} - {curve_info['concentration_range'][1]:.2e}")
        
        return curve_info
    
    def quantify_unknown(self, gene: str, ct_values: List[float]) -> Dict:
        """
        표준 곡선을 사용하여 미지 샘플의 농도 계산
        
        Args:
            gene: 유전자 이름
            ct_values: 미지 샘플의 Ct 값 리스트
            
        Returns:
            정량 결과 딕셔너리
        """
        if gene not in self.standard_curves:
            raise ValueError(f"{gene}의 표준 곡선이 없습니다. 먼저 build_standard_curve()를 실행하세요.")
        
        curve = self.standard_curves[gene]
        slope = curve['slope']
        intercept = curve['intercept']
        
        # Ct 값으로부터 농도 계산
        # Ct = slope × log10(Conc) + intercept
        # log10(Conc) = (Ct - intercept) / slope
        # Conc = 10^((Ct - intercept) / slope)
        
        concentrations = []
        for ct in ct_values:
            log_conc = (ct - intercept) / slope
            conc = 10 ** log_conc
            concentrations.append(conc)
        
        mean_conc = np.mean(concentrations)
        std_conc = np.std(concentrations, ddof=1) if len(concentrations) > 1 else 0
        
        return {
            'gene': gene,
            'ct_values': ct_values,
            'concentrations': concentrations,
            'mean_concentration': float(mean_conc),
            'std_concentration': float(std_conc),
            'cv_percent': float((std_conc / mean_conc * 100) if mean_conc > 0 else 0),
            'n_replicates': len(ct_values)
        }
    
    def validate_curve(self, gene: str) -> Dict:
        """
        표준 곡선 검증
        
        Args:
            gene: 유전자 이름
            
        Returns:
            검증 결과 딕셔너리
        """
        if gene not in self.standard_curves:
            raise ValueError(f"{gene}의 표준 곡선이 없습니다.")
        
        curve = self.standard_curves[gene]
        
        # 검증 기준
        validation = {
            'gene': gene,
            'r_squared': curve['r_squared'],
            'r_squared_pass': curve['r_squared'] >= 0.98,  # R² ≥ 0.98
            'efficiency': curve['efficiency'],
            'efficiency_pass': 90 <= curve['efficiency'] <= 110,  # 90-110%
            'slope': curve['slope'],
            'slope_pass': -3.6 <= curve['slope'] <= -3.1,  # 이상적 범위
            'overall_pass': False
        }
        
        # 전체 통과 여부
        validation['overall_pass'] = (
            validation['r_squared_pass'] and 
            validation['efficiency_pass'] and 
            validation['slope_pass']
        )
        
        print(f"\n=== {gene} 표준 곡선 검증 ===")
        print(f"R² ≥ 0.98: {'통과' if validation['r_squared_pass'] else '실패'} (R² = {curve['r_squared']:.4f})")
        print(f"효율 90-110%: {'통과' if validation['efficiency_pass'] else '실패'} (효율 = {curve['efficiency']:.1f}%)")
        print(f"Slope -3.6 ~ -3.1: {'통과' if validation['slope_pass'] else '실패'} (slope = {curve['slope']:.3f})")
        print(f"\n전체 결과: {'통과' if validation['overall_pass'] else '실패'}")
        
        return validation


class EfficiencyCorrectedQuantification:
    """
    증폭 효율을 보정한 정량 분석
    """
    
    def __init__(self, data: pd.DataFrame):
        self.data = data.copy()
    
    def calculate_with_efficiency(
        self,
        target_gene: str,
        reference_gene: str,
        control_group: str,
        treatment_group: str,
        efficiency_target: float,
        efficiency_reference: float
    ) -> Dict:
        """
        효율을 고려한 상대 정량
        
        Pfaffl 방법 사용:
        Ratio = (E_target)^(ΔCt_target) / (E_reference)^(ΔCt_reference)
        """
        # 평균 Ct 계산
        mean_ct = self.data.groupby(['gene', 'group'])['ct_value'].mean()
        
        # ΔCt 계산 (control - treatment)
        delta_ct_target = (
            mean_ct.loc[(target_gene, control_group)] - 
            mean_ct.loc[(target_gene, treatment_group)]
        )
        
        delta_ct_ref = (
            mean_ct.loc[(reference_gene, control_group)] - 
            mean_ct.loc[(reference_gene, treatment_group)]
        )
        
        # Pfaffl의 효율 보정 공식
        ratio = (efficiency_target ** delta_ct_target) / (efficiency_reference ** delta_ct_ref)
        
        return {
            'target_gene': target_gene,
            'reference_gene': reference_gene,
            'efficiency_target': efficiency_target,
            'efficiency_reference': efficiency_reference,
            'delta_ct_target': float(delta_ct_target),
            'delta_ct_reference': float(delta_ct_ref),
            'fold_change': float(ratio),
            'log2_fold_change': float(np.log2(ratio))
        }


if __name__ == "__main__":
    # 테스트 코드
    from data_loader import PCRDataLoader
    
    loader = PCRDataLoader('../data/sample_pcr_data.csv')
    data = loader.load_data()
    
    print("=== ΔΔCt 분석 테스트 ===")
    ddct = DeltaDeltaCt(data)
    results = ddct.calculate(
        target_gene='gene_A',
        reference_gene='GAPDH',
        control_group='control'
    )
