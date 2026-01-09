# PCR 진단 분석 프로젝트

PCR 데이터 분석을 위한 Python 패키지입니다(테스트용).

## 주요 기능

### 1. 기본 PCR 분석
- **데이터 로드**: CSV 형식의 PCR 데이터 읽기
- **품질 관리 (QC)**: Ct 범위, NTC, 재현성, 이상치 검출
- **ΔΔCt 정량 분석**: 유전자 발현량 계산
- **시각화**: 다양한 그래프 및 대시보드 생성

### 2. 머신러닝 분류
- Random Forest
- Gradient Boosting
- Support Vector Machine (SVM)
- 특징 중요도 분석
- 혼동 행렬 및 ROC 곡선

### 3. 딥러닝 분류 (TensorFlow)
- Multi-Layer Perceptron (MLP)
- Batch Normalization
- Dropout Regularization
- Early Stopping

## 설치

### 1. 환경 설정

```bash
# Conda 환경 생성
conda create -n pcr_analysis python=3.10 -y
conda activate pcr_analysis

# 필수 패키지 설치
pip install -r requirements.txt

# 프로젝트 설치
pip install -e .
```

### 2. 필수 패키지

```
numpy>=1.24.0
pandas>=2.0.0
scipy>=1.10.0
scikit-learn>=1.3.0
matplotlib>=3.7.0
seaborn>=0.12.0
tensorflow>=2.15.0
```

## 사용 방법

### 기본 PCR 분석

```bash
python examples/basic_usage.py
```

**출력 파일:**
- `output/gene_a_results.csv` - ΔΔCt 분석 결과
- `output/ct_distribution.png` - Ct 분포 그래프
- `output/ct_heatmap.png` - 히트맵
- `output/fold_change.png` - Fold Change 그래프
- `output/dashboard.png` - 종합 대시보드

### 머신러닝 분류

```bash
python examples/ml_classification.py
```

**주요 결과:**
- Random Forest, Gradient Boosting, SVM 모델 비교
- 특징 중요도 분석
- 혼동 행렬
- 성능 지표 (정확도, F1-score)

### TensorFlow 딥러닝

```bash
python examples/tensorflow_gpu_example.py
```

**특징:**
- CPU 모드로 안정적 실행
- Batch Normalization
- Dropout (과적합 방지)
- Early Stopping

## 프로젝트 구조

```
pcr_diagnostic_project/
├── data/
│   └── sample_pcr_data.csv          # 샘플 데이터 (22개 샘플)
├── examples/
│   ├── basic_usage.py               # 기본 분석 예제
│   ├── ml_classification.py         # 머신러닝 분류
│   └── tensorflow_gpu_example.py    # 딥러닝 (CPU)
├── src/
│   ├── data_loader.py               # 데이터 로드
│   ├── quality_control.py           # 품질 관리
│   ├── quantification.py            # ΔΔCt 계산
│   ├── ml_diagnostics.py            # 머신러닝
│   └── visualization.py             # 시각화
├── output/                          # 결과 저장 폴더
├── requirements.txt                 # 패키지 의존성
└── README.md                        # 프로젝트 문서
```

## 데이터 형식

입력 데이터는 CSV 형식이어야 하며 다음 컬럼을 포함해야 합니다:

```csv
sample_id,gene,ct_value,group,replicate,concentration,plate_id
S001,gene_A,18.5,control,1,100,plate1
S001,GAPDH,16.2,control,1,100,plate1
...
```

### 필수 컬럼
- `sample_id`: 샘플 ID
- `gene`: 유전자 이름
- `ct_value`: Ct 값
- `group`: 실험 그룹 (control, treatment, positive, negative 등)

### 선택 컬럼
- `replicate`: 반복 실험 번호
- `concentration`: 농도
- `plate_id`: 플레이트 ID

## 예제 결과

### 기본 분석
```
✅ 분석 완료!
   - 총 샘플 수: 22
   - 유전자: gene_A, GAPDH, gene_B, COVID_N
   - 그룹: control, treatment, positive, negative
```

### 머신러닝 성능
| 모델 | 정확도 | F1-Score |
|------|--------|----------|
| Random Forest | 71.4% | 0.714 |
| Gradient Boosting | **100%** | **1.000** |
| SVM | 85.7% | 0.848 |

### 딥러닝 성능
- 테스트 정확도: 약 85-90%
- 학습 시간: ~30초 (CPU)

## 문제 해결

### ImportError 발생 시
```bash
pip install -e .
```

### 데이터 로드 오류
- CSV 파일 경로 확인
- 필수 컬럼 존재 여부 확인
- 인코딩 문제 시: UTF-8로 저장

### 메모리 부족
- 배치 크기 감소
- 샘플 수 줄이기

## 성능 최적화

### CPU 최적화
```python
# 멀티코어 사용
import os
os.environ['OMP_NUM_THREADS'] = '4'
```

### 배치 크기 조정
```python
# TensorFlow 학습 시
history = model.fit(..., batch_size=8)  # 기본값
```

## 라이선스

MIT License

## 참고 자료

- [Real-time PCR 원리](https://en.wikipedia.org/wiki/Real-time_polymerase_chain_reaction)
- [ΔΔCt 방법](https://en.wikipedia.org/wiki/Real-time_polymerase_chain_reaction#Relative_quantification)
- [TensorFlow 문서](https://www.tensorflow.org/)
- [scikit-learn 문서](https://scikit-learn.org/)

