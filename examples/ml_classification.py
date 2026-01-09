"""
머신러닝 분류 예제
PCR 데이터를 사용하여 진단 분류 모델을 학습하고 평가합니다.
"""

import sys
import os

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, 'src'))

# TensorFlow 경고 억제
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

import numpy as np
from data_loader import PCRDataLoader
from ml_diagnostics import PCRClassifier, AnomalyDetector
from visualization import PCRVisualizer
from sklearn.model_selection import train_test_split

def main():
    print("=" * 60)
    print("PCR 진단 분석 - 머신러닝 분류 예제")
    print("=" * 60)
    print()
    
    # 1. 데이터 로드
    print("1. 데이터 로드 중...")
    data_path = os.path.join(project_root, 'data', 'sample_pcr_data.csv')
    loader = PCRDataLoader(data_path)
    data = loader.load_data()
    print()
    
    # 2. 여러 분류 모델 비교
    model_types = ['random_forest', 'gradient_boosting', 'svm']
    
    print(f"테스트할 모델: {', '.join(model_types)}\n")
    
    results_comparison = {}
    output_dir = os.path.join(project_root, 'output')
    os.makedirs(output_dir, exist_ok=True)
    
    for model_type in model_types:
        print(f"\n{'='*60}")
        print(f"모델: {model_type.upper()}")
        print('='*60)
        
        # 3. 분류기 초기화 및 특징 추출
        classifier = PCRClassifier(model_type=model_type)
        
        print("\n특징 추출 중...")
        X, y = classifier.prepare_features(data, target_col='group')
        
        print(f"특징 수: {X.shape[1]}")
        print(f"샘플 수: {X.shape[0]}")
        unique_classes = np.unique(y)
        print(f"클래스: {unique_classes}")
        
        # 클래스별 샘플 수 확인
        class_counts = {cls: np.sum(y == cls) for cls in unique_classes}
        print(f"클래스별 샘플 수: {class_counts}")
        
        # 샘플이 너무 적은 클래스 확인
        min_samples = min(class_counts.values())
        if min_samples < 2:
            print(f"\n⚠️  경고: 일부 클래스의 샘플이 너무 적습니다 (최소 {min_samples}개)")
            print("   stratify 옵션 없이 진행합니다.")
            stratify_option = None
        else:
            stratify_option = y
        
        # 4. 학습/테스트 분할
        try:
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, 
                test_size=0.3, 
                random_state=42, 
                stratify=stratify_option
            )
        except ValueError as e:
            print(f"\n⚠️  Stratified split 실패: {e}")
            print("   일반 split으로 진행합니다.")
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, 
                test_size=0.3, 
                random_state=42
            )
        
        print(f"\n학습 세트: {len(X_train)} 샘플")
        print(f"테스트 세트: {len(X_test)} 샘플")
        
        # 5. 모델 학습
        print("\n모델 학습 중...")
        train_results = classifier.train(X_train, y_train)
        
        # 6. 모델 평가
        print("\n모델 평가 중...")
        metrics = classifier.evaluate(X_test, y_test)
        
        # 결과 저장
        results_comparison[model_type] = {
            'accuracy': metrics['accuracy'],
            'f1_score': metrics['f1_score'],
            'cv_mean': train_results['cv_mean']
        }
        
        # 7. 특징 중요도 (Random Forest, Gradient Boosting)
        if model_type in ['random_forest', 'gradient_boosting']:
            print("\n특징 중요도 분석...")
            importance = classifier.get_feature_importance(top_n=10)
            
            # 시각화
            visualizer = PCRVisualizer()
            visualizer.plot_feature_importance(
                importance,
                save_path=os.path.join(output_dir, f'feature_importance_{model_type}.png')
            )
        
        # 8. ROC 곡선 (이진 분류인 경우)
        if len(unique_classes) == 2 and 'roc_curve' in metrics:
            fpr, tpr, _ = metrics['roc_curve']
            visualizer = PCRVisualizer()
            visualizer.plot_roc_curve(
                fpr, tpr, metrics['roc_auc'],
                save_path=os.path.join(output_dir, f'roc_curve_{model_type}.png')
            )
        
        # 9. 혼동 행렬
        visualizer = PCRVisualizer()
        visualizer.plot_confusion_matrix(
            metrics['confusion_matrix'],
            labels=unique_classes.tolist(),
            save_path=os.path.join(output_dir, f'confusion_matrix_{model_type}.png')
        )
    
    # 10. 모델 비교 결과
    print("\n" + "=" * 60)
    print("모델 성능 비교")
    print("=" * 60)
    print(f"{'Model':<20} {'Accuracy':<12} {'F1-Score':<12} {'CV Mean':<12}")
    print("-" * 60)
    
    for model, results in results_comparison.items():
        print(f"{model:<20} {results['accuracy']:<12.3f} {results['f1_score']:<12.3f} {results['cv_mean']:<12.3f}")
    
    # 최고 성능 모델
    best_model = max(results_comparison.items(), key=lambda x: x[1]['accuracy'])
    print(f"\n🏆 최고 성능 모델: {best_model[0]} (정확도: {best_model[1]['accuracy']:.3f})")
    
    # 11. 이상 탐지 (보너스)
    print("\n" + "=" * 60)
    print("이상 탐지 분석")
    print("=" * 60)
    
    anomaly_detector = AnomalyDetector(method='isolation_forest')
    
    # 첫 번째 모델의 X 사용
    classifier_temp = PCRClassifier()
    X, y = classifier_temp.prepare_features(data, target_col='group')
    
    predictions = anomaly_detector.fit_predict(X)
    
    anomaly_indices = np.where(predictions == -1)[0]
    print(f"\n이상 샘플 개수: {len(anomaly_indices)}")
    if len(anomaly_indices) > 0:
        print(f"이상 샘플 인덱스: {anomaly_indices.tolist()}")
    
    print("\n" + "=" * 60)
    print("✅ 모든 테스트 완료!")
    print("=" * 60)


if __name__ == "__main__":
    main()
