# PCR Diagnostic Project

PCR(Polymerase Chain Reaction) 데이터 분석을 위한 풀스택 웹 애플리케이션입니다.
도메인 라이브러리(`pcr_diagnostic`), FastAPI 백엔드, Vue 3 SPA 프론트엔드로 구성된 단일 사용자 MVP입니다.

---

## 주요 기능

- **데이터셋 관리** — CSV 업로드(≤10MB), 필수 컬럼 검증, 미리보기, 목록·삭제
- **품질 관리 (QC)** — Ct 범위, NTC, 재현성(CV%), 이상치(Grubbs / Z-score / Modified Z-score), 증폭 효율 추정
- **ΔΔCt 정량** — 평균 Ct → ΔCt → ΔΔCt → Fold Change, t-test 유의성
- **머신러닝 분류** — Random Forest / SVM / Gradient Boosting / XGBoost, 교차검증·혼동행렬·특징 중요도
- **시각화** — Plotly.js 기반 인터랙티브 차트 (boxplot, fold-change, confusion matrix, feature importance)

---

## 아키텍처 한눈에 보기

```
┌─────────────────────┐      HTTP/JSON       ┌─────────────────────┐
│  Frontend (Vue 3)   │  ───────────────▶   │  Backend (FastAPI)  │
│  Vite dev :5173     │  ◀───────────────   │  Uvicorn :8000      │
└─────────────────────┘                      └──────────┬──────────┘
                                                        │
                                                        ▼
                                            ┌─────────────────────┐
                                            │  pcr_diagnostic     │
                                            │  (numpy/pandas/     │
                                            │   scikit-learn/     │
                                            │   scipy)            │
                                            └──────────┬──────────┘
                                                       ▼
                                              backend/storage/
                                              (datasets/, runs/)
```

자세한 설명은 [`docs/architecture.md`](docs/architecture.md), 다이어그램은 [`docs/uml.md`](docs/uml.md)를 참고하세요.

---

## 디렉토리 구조

```
pcr_diagnostic_project/
├── backend/
│   ├── api/                          # FastAPI (main, schemas, storage, routers/)
│   ├── src/pcr_diagnostic/           # 도메인 라이브러리
│   ├── examples/                     # CLI 사용 예시
│   ├── tests/                        # pytest
│   ├── storage/                      # 런타임 산출물 (datasets/, runs/)
│   ├── data/sample_pcr_data.csv
│   ├── environment.yml / requirements.txt / setup.py
│
├── frontend/
│   ├── src/
│   │   ├── main.js · App.vue
│   │   ├── router/                   # vue-router (Upload / QC / ΔΔCt / ML)
│   │   ├── api/client.js             # axios + 4개 API 모듈
│   │   ├── stores/                   # Pinia (datasets, toasts)
│   │   ├── views/                    # 라우트별 화면
│   │   └── components/               # 공용 컴포넌트
│   ├── vite.config.js · tailwind.config.js · package.json
│
├── docs/
│   ├── architecture.md               # 계층·플로우·확장 고려사항
│   └── uml.md                        # Mermaid UML (component/class/sequence/state)
│
└── README.md
```

---

## 빠른 시작

### 1) 백엔드

```bash
cd backend

# Conda 환경 (권장)
conda env create -f environment.yml
conda activate pcr_analysis

# 또는 pip
pip install -r requirements.txt
pip install -e .

# 개발 서버 (FastAPI + Uvicorn)
uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

확인:

- Swagger UI: <http://127.0.0.1:8000/docs>
- Health: <http://127.0.0.1:8000/api/health>

### 2) 프론트엔드

```bash
cd frontend
npm install
npm run dev    # http://localhost:5173
```

Vite dev 서버는 `/api` 요청을 `http://127.0.0.1:8000`으로 프록시합니다.

---

## API 개요

- `POST /api/datasets` — CSV 업로드 (multipart, ≤10MB)
- `GET /api/datasets` — 데이터셋 목록
- `GET /api/datasets/{id}` — 데이터셋 메타
- `GET /api/datasets/{id}/preview?n=20` — 상위 N행 미리보기
- `DELETE /api/datasets/{id}` — 삭제
- `POST /api/qc/{dataset_id}` — QC 실행 (`QCRequest`)
- `POST /api/quantification/ddct/{dataset_id}` — ΔΔCt 실행 (`DDCTRequest`)
- `POST /api/ml/train/{dataset_id}` — ML 학습/평가 (`MLTrainRequest`)
- `GET /api/health` — 헬스 체크

요청/응답 스키마는 `backend/api/schemas.py` 또는 Swagger UI에서 확인할 수 있습니다.

---

## 데이터 형식

입력 CSV는 다음 컬럼을 포함해야 합니다.

```csv
sample_id,gene,ct_value,group,replicate,concentration,plate_id
S001,gene_A,18.5,control,1,100,plate1
S001,GAPDH,16.2,control,1,100,plate1
...
```

**필수 컬럼**: `sample_id`, `gene`, `ct_value`
**선택 컬럼**: `group`, `replicate`, `concentration`, `plate_id`

샘플 데이터: [`backend/data/sample_pcr_data.csv`](backend/data/sample_pcr_data.csv)

---

## 사용 흐름 (웹 UI)

1. **Upload** — CSV를 드롭존에 업로드 → 미리보기 확인 → 데이터셋 선택
2. **QC** — Ct 임계값·CV 임계값·이상치 방법 설정 → 분석 → 박스플롯과 이상치 테이블 확인
3. **ΔΔCt** — target/reference 유전자 + control 그룹 선택 → 그룹별 Fold Change·p-value 확인
4. **ML** — 모델 선택(random_forest / svm / gradient_boosting) → 학습 → 혼동행렬·특징 중요도 확인

CLI 사용 예시는 [`backend/examples`](backend/examples)에 있습니다.

```bash
cd backend
python examples/basic_usage.py
python examples/ml_classification.py
python examples/tensorflow_gpu_example.py
```

---

## 도메인 라이브러리 사용 예

```python
import pandas as pd
from pcr_diagnostic import QualityControl, DeltaDeltaCt, PCRClassifier

df = pd.read_csv("backend/data/sample_pcr_data.csv")

# QC
qc = QualityControl(df)
print(qc.check_ct_range(threshold=35.0))
print(qc.check_reproducibility(cv_threshold=5.0))

# ΔΔCt
ddct = DeltaDeltaCt(df).calculate(
    target_gene="gene_A",
    reference_gene="GAPDH",
    control_group="control",
)

# ML
clf = PCRClassifier(model_type="random_forest")
X, y = clf.prepare_features(df, target_col="group")
# ... train_test_split → clf.train(...) → clf.evaluate(...)
```

---

## 기술 스택

**Backend**
- Python 3.10+ / FastAPI / Uvicorn / Pydantic
- pandas · numpy · scipy · scikit-learn (선택: xgboost, lightgbm, tensorflow)
- matplotlib · seaborn (예제 스크립트 시각화)

**Frontend**
- Vue 3 (Composition API) · Vue Router · Pinia
- axios · Plotly.js
- Vite · Tailwind CSS · PostCSS

**저장소**
- 로컬 파일시스템 (`backend/storage/datasets/<id>/`, `backend/storage/runs/<id>/`)
- DB 없음 (단일 사용자 MVP)

---

## 테스트

```bash
cd backend
pytest                              # 전체
pytest tests/test_quality_control.py
```

---

## 문서

- [Architecture](docs/architecture.md) — 계층 책임, 데이터 플로우, 횡단 관심사
- [UML](docs/uml.md) — 컴포넌트 / 클래스 / 시퀀스 / 상태 다이어그램 (Mermaid)

---

## 제한 사항 / 알려진 이슈

- **단일 사용자**: 인증·인가 없음. 동시 쓰기 보호 없음.
- **저장소 보존**: `backend/storage/`는 로컬 디스크에 영속화되지만 백업/마이그레이션은 수동.
- **장시간 ML**: 현재 `run_in_threadpool` 동기 처리. 분/시간 단위 학습은 작업 큐 도입 필요.
- **`PCRVisualizer`(matplotlib)**: 예제 전용. 웹 UI는 Plotly로 클라이언트 렌더링.

확장 고려사항은 [`docs/architecture.md` §8](docs/architecture.md)을 참고하세요.

---

## 라이선스

MIT License — [`LICENSE`](LICENSE)

---

## 참고 자료

- [Real-time PCR (Wikipedia)](https://en.wikipedia.org/wiki/Real-time_polymerase_chain_reaction)
- [ΔΔCt method](https://en.wikipedia.org/wiki/Real-time_polymerase_chain_reaction#Relative_quantification)
- [FastAPI](https://fastapi.tiangolo.com/) · [Vue 3](https://vuejs.org/) · [Pinia](https://pinia.vuejs.org/) · [Plotly.js](https://plotly.com/javascript/)
- [scikit-learn](https://scikit-learn.org/)
