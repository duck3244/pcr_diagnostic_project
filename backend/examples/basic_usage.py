"""
기본 사용 예제
PCR 데이터를 로드하고 기본 분석을 수행합니다.
"""

import os

# TensorFlow 경고 억제
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from pcr_diagnostic import (
    PCRDataLoader,
    QualityControl,
    DeltaDeltaCt,
    PCRVisualizer,
)

def main():
    print("=" * 60)
    print("PCR 진단 분석 - 기본 사용 예제")
    print("=" * 60)
    print()
    
    # 1. 데이터 로드
    print("1. 데이터 로드 중...")
    data_path = os.path.join(project_root, 'data', 'sample_pcr_data.csv')
    loader = PCRDataLoader(data_path)
    data = loader.load_data()
    
    metadata = loader.get_metadata()
    print(f"   - 총 샘플 수: {metadata['total_samples']}")
    print(f"   - 유전자: {', '.join(metadata['genes'])}")
    # 그룹에서 NaN 제거
    groups = [str(g) for g in metadata['groups'] if g == g]  # NaN 필터링
    print(f"   - 그룹: {', '.join(groups)}")
    print()
    
    # 2. 품질 관리
    print("2. 품질 관리 검사 중...")
    qc = QualityControl(data)
    qc_results = qc.run_full_qc(reference_genes=['GAPDH'])
    print()
    
    # 3. ΔΔCt 정량 분석
    print("3. ΔΔCt 정량 분석 수행 중...")
    ddct = DeltaDeltaCt(data)
    
    # gene_A 분석
    results_gene_a = ddct.calculate(
        target_gene='gene_A',
        reference_gene='GAPDH',
        control_group='control'
    )
    
    # 결과 저장
    output_dir = os.path.join(project_root, 'output')
    os.makedirs(output_dir, exist_ok=True)
    ddct.export_results(os.path.join(output_dir, 'gene_a_results.csv'))
    print()
    
    # 4. 시각화
    print("4. 시각화 생성 중...")
    visualizer = PCRVisualizer()
    
    # Ct 분포 그래프
    print("   - Ct 분포 그래프 생성...")
    visualizer.plot_ct_distribution(
        data, 
        group_by='gene',
        save_path=os.path.join(output_dir, 'ct_distribution.png')
    )
    
    # 히트맵
    print("   - 히트맵 생성...")
    visualizer.plot_heatmap(
        data,
        save_path=os.path.join(output_dir, 'ct_heatmap.png')
    )
    
    # Fold Change 그래프
    print("   - Fold Change 그래프 생성...")
    visualizer.plot_fold_change(
        results_gene_a,
        save_path=os.path.join(output_dir, 'fold_change.png')
    )
    
    # 종합 대시보드
    print("   - 종합 대시보드 생성...")
    visualizer.create_diagnostic_dashboard(
        data,
        qc_results,
        save_path=os.path.join(output_dir, 'dashboard.png')
    )
    
    print()
    print("=" * 60)
    print("✅ 분석 완료!")
    print("=" * 60)
    print("결과 파일:")
    print(f"  - {os.path.join(output_dir, 'gene_a_results.csv')}")
    print(f"  - {os.path.join(output_dir, 'ct_distribution.png')}")
    print(f"  - {os.path.join(output_dir, 'ct_heatmap.png')}")
    print(f"  - {os.path.join(output_dir, 'fold_change.png')}")
    print(f"  - {os.path.join(output_dir, 'dashboard.png')}")
    print("=" * 60)


if __name__ == "__main__":
    main()
