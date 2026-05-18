"""
머신러닝 기반 PCR 진단 모듈
분류 모델, 이상 탐지, 특징 중요도 분석 등을 수행합니다.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, VotingClassifier
from sklearn.svm import SVC
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report, roc_auc_score, roc_curve
)
from sklearn.ensemble import IsolationForest
from sklearn.covariance import EllipticEnvelope
import warnings

try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    warnings.warn("XGBoost가 설치되지 않았습니다. XGBoost 모델을 사용할 수 없습니다.")


class PCRClassifier:
    """
    PCR 데이터 기반 분류 모델
    """
    
    def __init__(self, model_type: str = 'random_forest', random_state: int = 42):
        """
        Args:
            model_type: 모델 유형 ('random_forest', 'svm', 'xgboost', 'gradient_boosting', 'ensemble')
            random_state: 난수 시드
        """
        self.model_type = model_type
        self.random_state = random_state
        self.model = None
        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()
        self.feature_names = None
        self.is_trained = False
        
        # 모델 초기화
        self._initialize_model()
    
    def _initialize_model(self):
        """모델 초기화"""
        if self.model_type == 'random_forest':
            self.model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                min_samples_split=5,
                random_state=self.random_state,
                n_jobs=-1
            )
        
        elif self.model_type == 'svm':
            self.model = SVC(
                kernel='rbf',
                C=1.0,
                gamma='scale',
                probability=True,
                random_state=self.random_state
            )
        
        elif self.model_type == 'gradient_boosting':
            self.model = GradientBoostingClassifier(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=5,
                random_state=self.random_state
            )
        
        elif self.model_type == 'xgboost':
            if not XGBOOST_AVAILABLE:
                raise ValueError("XGBoost가 설치되지 않았습니다.")
            self.model = xgb.XGBClassifier(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=5,
                random_state=self.random_state,
                eval_metric='logloss'
            )
        
        elif self.model_type == 'ensemble':
            # 여러 모델의 앙상블
            rf = RandomForestClassifier(n_estimators=50, random_state=self.random_state)
            gb = GradientBoostingClassifier(n_estimators=50, random_state=self.random_state)
            svm = SVC(probability=True, random_state=self.random_state)
            
            self.model = VotingClassifier(
                estimators=[('rf', rf), ('gb', gb), ('svm', svm)],
                voting='soft'
            )
        
        else:
            raise ValueError(f"지원하지 않는 모델 유형: {self.model_type}")
    
    def prepare_features(self, data: pd.DataFrame, target_col: str = 'diagnosis') -> Tuple[np.ndarray, np.ndarray]:
        """
        PCR 데이터로부터 특징 추출
        
        Args:
            data: PCR 데이터프레임
            target_col: 타겟 컬럼명
            
        Returns:
            (X, y) 튜플
        """
        # 샘플별로 특징 집계
        features_list = []
        labels = []
        
        for sample_id in data['sample_id'].unique():
            sample_data = data[data['sample_id'] == sample_id]
            
            # NTC 샘플은 제외
            if 'NTC' in str(sample_id):
                continue
            
            features = {}
            
            # 각 유전자별 Ct 값
            for gene in sample_data['gene'].unique():
                gene_ct = sample_data[sample_data['gene'] == gene]['ct_value'].dropna()
                if len(gene_ct) > 0:
                    features[f'{gene}_ct_mean'] = gene_ct.mean()
                    features[f'{gene}_ct_std'] = gene_ct.std() if len(gene_ct) > 1 else 0
                    features[f'{gene}_ct_min'] = gene_ct.min()
                    features[f'{gene}_ct_max'] = gene_ct.max()
            
            # 추가 특징: 유전자 간 차이
            genes = sample_data['gene'].unique()
            if len(genes) >= 2:
                for i, gene1 in enumerate(genes):
                    for gene2 in genes[i+1:]:
                        ct1 = sample_data[sample_data['gene'] == gene1]['ct_value'].mean()
                        ct2 = sample_data[sample_data['gene'] == gene2]['ct_value'].mean()
                        features[f'delta_{gene1}_{gene2}'] = ct1 - ct2
            
            features_list.append(features)
            
            # 레이블 (그룹 또는 진단 결과)
            if target_col in sample_data.columns:
                label = sample_data[target_col].iloc[0]
            elif 'group' in sample_data.columns:
                label = sample_data['group'].iloc[0]
            else:
                label = 'unknown'
            
            labels.append(label)
        
        # DataFrame으로 변환
        X = pd.DataFrame(features_list).fillna(0)
        y = np.array(labels)
        
        self.feature_names = X.columns.tolist()
        
        return X.values, y
    
    def train(
        self, 
        X_train: np.ndarray, 
        y_train: np.ndarray,
        tune_hyperparameters: bool = False
    ) -> Dict:
        """
        모델 학습
        
        Args:
            X_train: 학습 특징
            y_train: 학습 레이블
            tune_hyperparameters: 하이퍼파라미터 튜닝 여부
            
        Returns:
            학습 결과 딕셔너리
        """
        print(f"=== {self.model_type} 모델 학습 시작 ===")
        print(f"학습 샘플 수: {len(X_train)}")
        print(f"특징 수: {X_train.shape[1]}")
        
        # 데이터 스케일링
        X_train_scaled = self.scaler.fit_transform(X_train)
        
        # 레이블 인코딩
        y_train_encoded = self.label_encoder.fit_transform(y_train)
        
        # 하이퍼파라미터 튜닝
        if tune_hyperparameters and self.model_type == 'random_forest':
            print("\n하이퍼파라미터 튜닝 중...")
            param_grid = {
                'n_estimators': [50, 100, 200],
                'max_depth': [5, 10, 15],
                'min_samples_split': [2, 5, 10]
            }
            
            grid_search = GridSearchCV(
                self.model,
                param_grid,
                cv=5,
                scoring='accuracy',
                n_jobs=-1
            )
            grid_search.fit(X_train_scaled, y_train_encoded)
            
            self.model = grid_search.best_estimator_
            print(f"최적 파라미터: {grid_search.best_params_}")
        else:
            # 모델 학습
            self.model.fit(X_train_scaled, y_train_encoded)
        
        # 교차 검증 (샘플 수에 따라 cv 조정)
        # 각 클래스별 최소 샘플 수 계산
        unique_classes, class_counts = np.unique(y_train_encoded, return_counts=True)
        min_samples_per_class = min(class_counts)
        
        # cv를 샘플 수에 맞게 조정 (최소 2, 최대 5)
        n_cv = min(5, max(2, min_samples_per_class))
        
        print(f"교차 검증 폴드 수: {n_cv} (클래스당 최소 샘플 수: {min_samples_per_class})")
        
        cv_scores = cross_val_score(
            self.model, 
            X_train_scaled, 
            y_train_encoded, 
            cv=n_cv, 
            scoring='accuracy'
        )
        
        self.is_trained = True
        
        print(f"\n교차 검증 정확도: {cv_scores.mean():.3f} (+/- {cv_scores.std():.3f})")
        
        return {
            'cv_scores': cv_scores,
            'cv_mean': cv_scores.mean(),
            'cv_std': cv_scores.std()
        }
    
    def predict(self, X_test: np.ndarray) -> np.ndarray:
        """
        예측 수행
        
        Args:
            X_test: 테스트 특징
            
        Returns:
            예측 레이블
        """
        if not self.is_trained:
            raise ValueError("모델이 학습되지 않았습니다. 먼저 train()을 실행하세요.")
        
        X_test_scaled = self.scaler.transform(X_test)
        y_pred_encoded = self.model.predict(X_test_scaled)
        y_pred = self.label_encoder.inverse_transform(y_pred_encoded)
        
        return y_pred
    
    def predict_proba(self, X_test: np.ndarray) -> np.ndarray:
        """예측 확률 반환"""
        if not self.is_trained:
            raise ValueError("모델이 학습되지 않았습니다.")
        
        X_test_scaled = self.scaler.transform(X_test)
        return self.model.predict_proba(X_test_scaled)
    
    def evaluate(self, X_test: np.ndarray, y_test: np.ndarray) -> Dict:
        """
        모델 평가
        
        Args:
            X_test: 테스트 특징
            y_test: 테스트 레이블
            
        Returns:
            평가 메트릭 딕셔너리
        """
        y_pred = self.predict(X_test)
        
        # 메트릭 계산
        metrics = {
            'accuracy': accuracy_score(y_test, y_pred),
            'precision': precision_score(y_test, y_pred, average='weighted', zero_division=0),
            'recall': recall_score(y_test, y_pred, average='weighted', zero_division=0),
            'f1_score': f1_score(y_test, y_pred, average='weighted', zero_division=0),
            'confusion_matrix': confusion_matrix(y_test, y_pred),
            'classification_report': classification_report(y_test, y_pred)
        }
        
        # ROC AUC (이진 분류인 경우)
        if len(np.unique(y_test)) == 2:
            y_proba = self.predict_proba(X_test)[:, 1]
            metrics['roc_auc'] = roc_auc_score(y_test, y_proba)
            metrics['roc_curve'] = roc_curve(y_test, y_proba)
        
        print("\n=== 모델 평가 결과 ===")
        print(f"정확도: {metrics['accuracy']:.3f}")
        print(f"정밀도: {metrics['precision']:.3f}")
        print(f"재현율: {metrics['recall']:.3f}")
        print(f"F1-점수: {metrics['f1_score']:.3f}")
        if 'roc_auc' in metrics:
            print(f"ROC AUC: {metrics['roc_auc']:.3f}")
        
        print("\n혼동 행렬:")
        print(metrics['confusion_matrix'])
        
        print("\n분류 리포트:")
        print(metrics['classification_report'])
        
        return metrics
    
    def get_feature_importance(self, top_n: int = 10) -> pd.DataFrame:
        """
        특징 중요도 반환
        
        Args:
            top_n: 상위 N개 특징
            
        Returns:
            특징 중요도 데이터프레임
        """
        if not self.is_trained:
            raise ValueError("모델이 학습되지 않았습니다.")
        
        # 모델별로 특징 중요도 추출
        if hasattr(self.model, 'feature_importances_'):
            importances = self.model.feature_importances_
        elif self.model_type == 'svm':
            # SVM은 특징 중요도가 없으므로 절대값 계산
            importances = np.abs(self.model.coef_[0]) if hasattr(self.model, 'coef_') else None
        else:
            importances = None
        
        if importances is None:
            warnings.warn(f"{self.model_type} 모델은 특징 중요도를 제공하지 않습니다.")
            return pd.DataFrame()
        
        # 데이터프레임 생성
        feature_importance = pd.DataFrame({
            'feature': self.feature_names,
            'importance': importances
        }).sort_values('importance', ascending=False)
        
        print(f"\n=== 상위 {top_n}개 중요 특징 ===")
        print(feature_importance.head(top_n))
        
        return feature_importance.head(top_n)


class AnomalyDetector:
    """
    이상치/이상 샘플 탐지 클래스
    """
    
    def __init__(self, method: str = 'isolation_forest'):
        """
        Args:
            method: 이상 탐지 방법 ('isolation_forest', 'elliptic_envelope')
        """
        self.method = method
        self.model = None
        self.scaler = StandardScaler()
        
        if method == 'isolation_forest':
            self.model = IsolationForest(
                contamination=0.1,
                random_state=42,
                n_jobs=-1
            )
        elif method == 'elliptic_envelope':
            self.model = EllipticEnvelope(
                contamination=0.1,
                random_state=42
            )
        else:
            raise ValueError(f"지원하지 않는 방법: {method}")
    
    def fit_predict(self, X: np.ndarray) -> np.ndarray:
        """
        이상치 탐지
        
        Args:
            X: 특징 배열
            
        Returns:
            예측 결과 (1: 정상, -1: 이상)
        """
        X_scaled = self.scaler.fit_transform(X)
        predictions = self.model.fit_predict(X_scaled)
        
        n_anomalies = (predictions == -1).sum()
        print(f"\n=== 이상 탐지 결과 ({self.method}) ===")
        print(f"총 샘플: {len(predictions)}")
        print(f"이상 샘플: {n_anomalies} ({n_anomalies/len(predictions)*100:.1f}%)")
        
        return predictions
    
    def get_anomaly_scores(self, X: np.ndarray) -> np.ndarray:
        """이상 점수 반환 (낮을수록 이상)"""
        X_scaled = self.scaler.transform(X)
        if hasattr(self.model, 'score_samples'):
            return self.model.score_samples(X_scaled)
        else:
            return None


if __name__ == "__main__":
    from pcr_diagnostic.data_loader import PCRDataLoader

    loader = PCRDataLoader('data/sample_pcr_data.csv')
    data = loader.load_data()
    
    # 분류 모델 테스트
    print("=== Random Forest 분류 테스트 ===")
    classifier = PCRClassifier(model_type='random_forest')
    
    # 특징 추출
    X, y = classifier.prepare_features(data, target_col='group')
    
    # 학습/테스트 분할
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42, stratify=y
    )
    
    # 학습
    classifier.train(X_train, y_train)
    
    # 평가
    metrics = classifier.evaluate(X_test, y_test)
    
    # 특징 중요도
    importance = classifier.get_feature_importance(top_n=5)
