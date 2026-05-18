"""
TensorFlow 딥러닝 예제 (CPU 모드)
RTX 5060 Laptop GPU는 Compute Capability 12.0으로 인한 CUDA 오류 방지를 위해
CPU 모드로 실행합니다.
"""

import os

# TensorFlow 경고 억제 및 GPU 비활성화 (RTX 5060 sm_120 호환성 이슈)
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers, Model

from pcr_diagnostic import PCRDataLoader

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("🎮 TensorFlow 딥러닝 PCR 진단 예제")
print("=" * 60)
print()

# 1. 실행 환경 확인
print("1️⃣  실행 환경 확인...")
print(f"   TensorFlow 버전: {tf.__version__}")
print(f"   실행 모드: CPU (RTX 5060 호환성 이슈로 CPU 모드 사용)")
print(f"   ✅ CPU는 PCR 데이터 분석에 충분히 빠릅니다")
print()

print("💡 참고:")
print("   - RTX 5060 Laptop GPU는 Compute Capability 12.0")
print("   - TensorFlow 현재 버전은 sm_120 완전 지원 대기 중")
print("   - CUDA 오류 방지를 위해 CPU 모드로 실행")
print("   - 샘플 수가 적을 때는 CPU가 더 효율적입니다")
print()

# 2. 데이터 로드
print("2️⃣  데이터 로드 중...")
data_path = os.path.join(project_root, 'data', 'sample_pcr_data.csv')
loader = PCRDataLoader(data_path)
data = loader.load_data()

metadata = loader.get_metadata()
print(f"   샘플 수: {metadata['total_samples']}")
print(f"   유전자: {', '.join(metadata['genes'])}")
print()

# 3. 특징 추출
print("3️⃣  특징 추출 중...")

def extract_features(data, target_col='group'):
    """PCR 데이터에서 특징 추출"""
    features = []
    labels = []
    sample_ids = []
    
    for sample_id in data['sample_id'].unique():
        if pd.isna(sample_id):
            continue
            
        sample_data = data[data['sample_id'] == sample_id]
        
        # 그룹 정보
        group = sample_data[target_col].iloc[0]
        if pd.isna(group):
            continue
        
        feature_dict = {}
        
        # 유전자별 통계
        for gene in data['gene'].unique():
            if pd.isna(gene):
                continue
                
            gene_data = sample_data[sample_data['gene'] == gene]['ct_value'].dropna()
            
            if len(gene_data) > 0:
                feature_dict[f'{gene}_mean'] = gene_data.mean()
                feature_dict[f'{gene}_std'] = gene_data.std() if len(gene_data) > 1 else 0
                feature_dict[f'{gene}_min'] = gene_data.min()
                feature_dict[f'{gene}_max'] = gene_data.max()
            else:
                feature_dict[f'{gene}_mean'] = 0
                feature_dict[f'{gene}_std'] = 0
                feature_dict[f'{gene}_min'] = 0
                feature_dict[f'{gene}_max'] = 0
        
        features.append(feature_dict)
        labels.append(group)
        sample_ids.append(sample_id)
    
    X = pd.DataFrame(features).fillna(0)
    y = np.array(labels)
    
    return X.values, y, sample_ids

X, y, sample_ids = extract_features(data, target_col='group')

print(f"   특징 수: {X.shape[1]}")
print(f"   샘플 수: {X.shape[0]}")

unique_classes = np.unique(y)
print(f"   클래스: {unique_classes}")
print()

# 4. 데이터 전처리
print("4️⃣  데이터 전처리...")

# 레이블 인코딩
label_encoder = LabelEncoder()
y_encoded = label_encoder.fit_transform(y)
n_classes = len(label_encoder.classes_)

# 원-핫 인코딩
y_categorical = keras.utils.to_categorical(y_encoded, n_classes)

# 특징 정규화
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# 데이터 분할
X_train, X_test, y_train, y_test = train_test_split(
    X_scaled, y_categorical, test_size=0.3, random_state=42
)

X_train, X_val, y_train, y_val = train_test_split(
    X_train, y_train, test_size=0.2, random_state=42
)

print(f"   학습 세트: {len(X_train)} 샘플")
print(f"   검증 세트: {len(X_val)} 샘플")
print(f"   테스트 세트: {len(X_test)} 샘플")
print()

# 5. 모델 정의
print("5️⃣  TensorFlow 딥러닝 모델 구성...")

def create_pcr_model(input_dim, n_classes):
    """PCR 진단용 딥러닝 모델"""
    inputs = keras.Input(shape=(input_dim,))
    
    # Dense layers with BatchNormalization and Dropout
    x = layers.Dense(128, activation='relu')(inputs)
    x = layers.BatchNormalization()(x)
    x = layers.Dropout(0.3)(x)
    
    x = layers.Dense(64, activation='relu')(x)
    x = layers.BatchNormalization()(x)
    x = layers.Dropout(0.2)(x)
    
    x = layers.Dense(32, activation='relu')(x)
    x = layers.BatchNormalization()(x)
    x = layers.Dropout(0.1)(x)
    
    outputs = layers.Dense(n_classes, activation='softmax')(x)
    
    model = Model(inputs=inputs, outputs=outputs)
    return model

model = create_pcr_model(X_scaled.shape[1], n_classes)

# 모델 컴파일
model.compile(
    optimizer=keras.optimizers.Adam(learning_rate=0.001),
    loss='categorical_crossentropy',
    metrics=['accuracy']
)

print()
print(model.summary())
print()

# 6. 학습
print("6️⃣  모델 학습 중 (CPU 모드)...")
print()

# 콜백 설정
callbacks = [
    keras.callbacks.EarlyStopping(
        monitor='val_loss',
        patience=10,
        restore_best_weights=True,
        verbose=1
    ),
    keras.callbacks.ReduceLROnPlateau(
        monitor='val_loss',
        factor=0.5,
        patience=5,
        verbose=1
    )
]

# 학습
history = model.fit(
    X_train, y_train,
    validation_data=(X_val, y_val),
    epochs=100,
    batch_size=8,
    callbacks=callbacks,
    verbose=1
)

print()

# 7. 평가
print("7️⃣  모델 평가...")

# 테스트 세트 평가
test_loss, test_accuracy = model.evaluate(X_test, y_test, verbose=0)
print(f"   테스트 정확도: {test_accuracy:.4f} ({test_accuracy*100:.1f}%)")
print(f"   테스트 손실: {test_loss:.4f}")

# 예측
y_pred_prob = model.predict(X_test, verbose=0)
y_pred = np.argmax(y_pred_prob, axis=1)
y_true = np.argmax(y_test, axis=1)

# 혼동 행렬
from sklearn.metrics import confusion_matrix, classification_report

cm = confusion_matrix(y_true, y_pred)
print("\n혼동 행렬:")
print(cm)

print("\n분류 리포트:")
print(classification_report(
    y_true, y_pred, 
    target_names=label_encoder.classes_,
    zero_division=0
))

print()
print("=" * 60)
print("✅ TensorFlow 딥러닝 분석 완료!")
print("=" * 60)
print()

# 8. 결과 요약
print("📊 최종 결과 요약:")
print(f"   - 테스트 정확도: {test_accuracy*100:.1f}%")
print(f"   - 학습 에폭: {len(history.history['loss'])}")
print(f"   - 실행 모드: CPU")
print(f"   - 학습 샘플: {len(X_train)}개")
print(f"   - 테스트 샘플: {len(X_test)}개")
print()

print("💡 성능 팁:")
print("   ✅ CPU 모드는 PCR 분석에 충분히 빠릅니다")
print("   ✅ 샘플 수가 100개 미만일 때 CPU가 효율적")
print("   ✅ 배치 크기 조정으로 성능 최적화 가능")
print()

print("🔧 GPU 사용이 필요하다면:")
print("   - PyTorch Nightly 버전 사용")
print("   - 또는 클라우드 GPU (Google Colab, AWS, Azure)")
print("   - RTX 5060 완전 지원은 TensorFlow 차기 버전 예상")
