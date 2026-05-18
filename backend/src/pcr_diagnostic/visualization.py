"""
PCR 데이터 시각화 모듈
증폭 곡선, 융해 곡선, 통계 그래프 등을 생성합니다.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Optional, List, Dict, Tuple
from pathlib import Path

# 한글 폰트 설정
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['axes.unicode_minus'] = False

# 스타일 설정
sns.set_style("whitegrid")
sns.set_palette("husl")


class PCRVisualizer:
    """
    PCR 데이터 시각화 클래스
    """
    
    def __init__(self, figsize: Tuple[int, int] = (10, 6), dpi: int = 100):
        """
        Args:
            figsize: 기본 그래프 크기
            dpi: 해상도
        """
        self.figsize = figsize
        self.dpi = dpi
    
    def plot_ct_distribution(
        self, 
        data: pd.DataFrame, 
        group_by: str = 'gene',
        save_path: Optional[str] = None
    ):
        """
        Ct 값 분포 시각화
        
        Args:
            data: PCR 데이터프레임
            group_by: 그룹화 기준 ('gene', 'group', etc.)
            save_path: 저장 경로
        """
        fig, ax = plt.subplots(figsize=self.figsize, dpi=self.dpi)
        
        # Ct 값이 있는 데이터만 사용
        data_valid = data.dropna(subset=['ct_value'])
        
        if group_by in data_valid.columns:
            sns.boxplot(data=data_valid, x=group_by, y='ct_value', ax=ax)
            ax.set_xlabel(group_by.capitalize())
        else:
            sns.histplot(data=data_valid, x='ct_value', bins=30, ax=ax)
        
        ax.set_ylabel('Ct Value')
        ax.set_title('Ct Value Distribution')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, bbox_inches='tight')
            print(f"그래프가 저장되었습니다: {save_path}")
        
        plt.show()
    
    def plot_amplification_curve(
        self,
        cycle_data: pd.DataFrame,
        sample_ids: Optional[List[str]] = None,
        save_path: Optional[str] = None
    ):
        """
        증폭 곡선 그리기
        
        Args:
            cycle_data: 사이클별 형광 데이터 (컬럼: cycle, sample_id, fluorescence)
            sample_ids: 표시할 샘플 ID 리스트 (None이면 전체)
            save_path: 저장 경로
        """
        fig, ax = plt.subplots(figsize=self.figsize, dpi=self.dpi)
        
        if sample_ids is None:
            sample_ids = cycle_data['sample_id'].unique()
        
        for sample_id in sample_ids:
            sample_data = cycle_data[cycle_data['sample_id'] == sample_id]
            ax.plot(
                sample_data['cycle'], 
                sample_data['fluorescence'],
                label=sample_id,
                marker='o',
                markersize=3,
                alpha=0.7
            )
        
        ax.set_xlabel('Cycle Number')
        ax.set_ylabel('Fluorescence')
        ax.set_title('PCR Amplification Curves')
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, bbox_inches='tight')
            print(f"증폭 곡선이 저장되었습니다: {save_path}")
        
        plt.show()
    
    def plot_standard_curve(
        self,
        concentrations: np.ndarray,
        ct_values: np.ndarray,
        slope: float,
        intercept: float,
        r_squared: float,
        efficiency: float,
        save_path: Optional[str] = None
    ):
        """
        표준 곡선 그리기
        
        Args:
            concentrations: 농도 배열
            ct_values: Ct 값 배열
            slope: 기울기
            intercept: 절편
            r_squared: R² 값
            efficiency: 증폭 효율
            save_path: 저장 경로
        """
        fig, ax = plt.subplots(figsize=self.figsize, dpi=self.dpi)
        
        # 로그 스케일로 변환
        log_conc = np.log10(concentrations)
        
        # 데이터 포인트
        ax.scatter(log_conc, ct_values, s=100, alpha=0.6, label='Data points')
        
        # 회귀선
        x_line = np.linspace(log_conc.min(), log_conc.max(), 100)
        y_line = slope * x_line + intercept
        ax.plot(x_line, y_line, 'r--', linewidth=2, label='Regression line')
        
        # 정보 표시
        info_text = f'y = {slope:.3f}x + {intercept:.3f}\n'
        info_text += f'R² = {r_squared:.4f}\n'
        info_text += f'Efficiency = {efficiency:.1f}%'
        
        ax.text(
            0.05, 0.95, info_text,
            transform=ax.transAxes,
            verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        )
        
        ax.set_xlabel('Log10(Concentration)')
        ax.set_ylabel('Ct Value')
        ax.set_title('PCR Standard Curve')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, bbox_inches='tight')
            print(f"표준 곡선이 저장되었습니다: {save_path}")
        
        plt.show()
    
    def plot_fold_change(
        self,
        results: Dict,
        save_path: Optional[str] = None
    ):
        """
        Fold Change 바 차트
        
        Args:
            results: ΔΔCt 분석 결과 딕셔너리
            save_path: 저장 경로
        """
        fig, ax = plt.subplots(figsize=self.figsize, dpi=self.dpi)
        
        comparisons = list(results['comparisons'].keys())
        fold_changes = [results['comparisons'][comp]['fold_change'] 
                       for comp in comparisons]
        p_values = [results['comparisons'][comp]['p_value'] 
                   for comp in comparisons]
        
        # 색상 (유의미한 결과는 다른 색)
        colors = ['red' if p < 0.05 else 'gray' for p in p_values]
        
        bars = ax.bar(comparisons, fold_changes, color=colors, alpha=0.7)
        
        # 기준선 (Fold Change = 1)
        ax.axhline(y=1, color='black', linestyle='--', linewidth=1, alpha=0.5)
        
        # p-value 표시
        for i, (bar, p_val) in enumerate(zip(bars, p_values)):
            height = bar.get_height()
            significance = '***' if p_val < 0.001 else '**' if p_val < 0.01 else '*' if p_val < 0.05 else 'ns'
            ax.text(
                bar.get_x() + bar.get_width() / 2., height,
                significance,
                ha='center', va='bottom'
            )
        
        ax.set_ylabel('Fold Change')
        ax.set_title(f'Gene Expression: {results["target_gene"]} (vs {results["control_group"]})')
        ax.set_yscale('log')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, bbox_inches='tight')
            print(f"Fold Change 그래프가 저장되었습니다: {save_path}")
        
        plt.show()
    
    def plot_heatmap(
        self,
        data: pd.DataFrame,
        pivot_index: str = 'sample_id',
        pivot_columns: str = 'gene',
        pivot_values: str = 'ct_value',
        save_path: Optional[str] = None
    ):
        """
        Ct 값 히트맵
        
        Args:
            data: PCR 데이터프레임
            pivot_index: 행 인덱스
            pivot_columns: 열 인덱스
            pivot_values: 값
            save_path: 저장 경로
        """
        # 평균 Ct 계산
        mean_ct = data.groupby([pivot_index, pivot_columns])[pivot_values].mean().reset_index()
        
        # 피벗 테이블 생성
        pivot_table = mean_ct.pivot(
            index=pivot_index,
            columns=pivot_columns,
            values=pivot_values
        )
        
        fig, ax = plt.subplots(figsize=(12, 8), dpi=self.dpi)
        
        sns.heatmap(
            pivot_table,
            annot=True,
            fmt='.2f',
            cmap='RdYlGn_r',
            cbar_kws={'label': 'Ct Value'},
            ax=ax
        )
        
        ax.set_title('Ct Value Heatmap')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, bbox_inches='tight')
            print(f"히트맵이 저장되었습니다: {save_path}")
        
        plt.show()
    
    def plot_roc_curve(
        self,
        fpr: np.ndarray,
        tpr: np.ndarray,
        roc_auc: float,
        save_path: Optional[str] = None
    ):
        """
        ROC 곡선 그리기
        
        Args:
            fpr: False Positive Rate
            tpr: True Positive Rate
            roc_auc: AUC 값
            save_path: 저장 경로
        """
        fig, ax = plt.subplots(figsize=self.figsize, dpi=self.dpi)
        
        ax.plot(fpr, tpr, color='darkorange', lw=2, 
               label=f'ROC curve (AUC = {roc_auc:.2f})')
        ax.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--', 
               label='Random classifier')
        
        ax.set_xlim([0.0, 1.0])
        ax.set_ylim([0.0, 1.05])
        ax.set_xlabel('False Positive Rate')
        ax.set_ylabel('True Positive Rate')
        ax.set_title('Receiver Operating Characteristic (ROC) Curve')
        ax.legend(loc="lower right")
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, bbox_inches='tight')
            print(f"ROC 곡선이 저장되었습니다: {save_path}")
        
        plt.show()
    
    def plot_confusion_matrix(
        self,
        cm: np.ndarray,
        labels: List[str],
        save_path: Optional[str] = None
    ):
        """
        혼동 행렬 시각화
        
        Args:
            cm: 혼동 행렬
            labels: 클래스 레이블
            save_path: 저장 경로
        """
        fig, ax = plt.subplots(figsize=(8, 6), dpi=self.dpi)
        
        sns.heatmap(
            cm,
            annot=True,
            fmt='d',
            cmap='Blues',
            xticklabels=labels,
            yticklabels=labels,
            ax=ax
        )
        
        ax.set_ylabel('True Label')
        ax.set_xlabel('Predicted Label')
        ax.set_title('Confusion Matrix')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, bbox_inches='tight')
            print(f"혼동 행렬이 저장되었습니다: {save_path}")
        
        plt.show()
    
    def plot_feature_importance(
        self,
        feature_importance: pd.DataFrame,
        top_n: int = 10,
        save_path: Optional[str] = None
    ):
        """
        특징 중요도 바 차트
        
        Args:
            feature_importance: 특징 중요도 데이터프레임
            top_n: 상위 N개 특징
            save_path: 저장 경로
        """
        fig, ax = plt.subplots(figsize=self.figsize, dpi=self.dpi)
        
        top_features = feature_importance.head(top_n)
        
        ax.barh(range(len(top_features)), top_features['importance'])
        ax.set_yticks(range(len(top_features)))
        ax.set_yticklabels(top_features['feature'])
        ax.set_xlabel('Importance')
        ax.set_title(f'Top {top_n} Feature Importances')
        ax.invert_yaxis()
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, bbox_inches='tight')
            print(f"특징 중요도 그래프가 저장되었습니다: {save_path}")
        
        plt.show()
    
    def create_diagnostic_dashboard(
        self,
        data: pd.DataFrame,
        qc_results: Dict,
        save_path: Optional[str] = None
    ):
        """
        종합 진단 대시보드 생성
        
        Args:
            data: PCR 데이터프레임
            qc_results: QC 결과
            save_path: 저장 경로
        """
        fig = plt.figure(figsize=(16, 12), dpi=self.dpi)
        gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)
        
        # 1. Ct 분포
        ax1 = fig.add_subplot(gs[0, :2])
        data_valid = data.dropna(subset=['ct_value'])
        sns.boxplot(data=data_valid, x='gene', y='ct_value', ax=ax1)
        ax1.set_title('Ct Value Distribution by Gene')
        ax1.tick_params(axis='x', rotation=45)
        
        # 2. 재현성 (CV%)
        ax2 = fig.add_subplot(gs[0, 2])
        cv_data = qc_results['reproducibility']['details']
        ax2.hist(cv_data['cv_percent'], bins=20, edgecolor='black')
        ax2.axvline(x=5, color='r', linestyle='--', label='Threshold (5%)')
        ax2.set_xlabel('CV%')
        ax2.set_ylabel('Count')
        ax2.set_title('Reproducibility (CV%)')
        ax2.legend()
        
        # 3. 그룹별 비교
        if 'group' in data.columns:
            ax3 = fig.add_subplot(gs[1, :])
            sns.violinplot(data=data_valid, x='gene', y='ct_value', hue='group', ax=ax3)
            ax3.set_title('Ct Values by Gene and Group')
            ax3.tick_params(axis='x', rotation=45)
        
        # 4. QC 요약
        ax4 = fig.add_subplot(gs[2, :])
        ax4.axis('off')
        
        qc_text = "=== Quality Control Summary ===\n\n"
        qc_text += f"Total Samples: {data['sample_id'].nunique()}\n"
        qc_text += f"Total Genes: {data['gene'].nunique()}\n"
        qc_text += f"Ct Range Check: {'PASS' if qc_results['ct_range_check']['pass'] else 'FAIL'}\n"
        qc_text += f"NTC Check: {'PASS' if qc_results['ntc_check']['pass'] else 'FAIL'}\n"
        qc_text += f"Mean CV%: {qc_results['reproducibility']['mean_cv']:.2f}%\n"
        qc_text += f"Outliers Detected: {len(qc_results['outliers'])}\n"
        
        ax4.text(0.1, 0.5, qc_text, fontsize=12, verticalalignment='center',
                family='monospace', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        if save_path:
            plt.savefig(save_path, bbox_inches='tight')
            print(f"대시보드가 저장되었습니다: {save_path}")
        
        plt.show()


if __name__ == "__main__":
    from pcr_diagnostic.data_loader import PCRDataLoader
    from pcr_diagnostic.quality_control import QualityControl

    loader = PCRDataLoader('data/sample_pcr_data.csv')
    data = loader.load_data()

    qc = QualityControl(data)
    qc.run_full_qc()

    visualizer = PCRVisualizer()
    visualizer.plot_ct_distribution(data, group_by='gene')
    visualizer.plot_heatmap(data)
