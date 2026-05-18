# PCR Diagnostic Project — 아키텍처

본 문서는 `pcr_diagnostic_project`의 전체 아키텍처를 설명한다. 프로젝트는 PCR 데이터 분석을 위한 도메인 라이브러리(`pcr_diagnostic`)와, 이를 노출하는 FastAPI 백엔드, 그리고 Vue 3 기반 SPA 프론트엔드로 구성된다.

---

## 1. 시스템 개요

```
┌─────────────────────┐      HTTP/JSON       ┌─────────────────────┐
│                     │  ───────────────▶   │                     │
│  Frontend (Vue 3)   │                      │  Backend (FastAPI)  │
│  Vite dev server    │  ◀───────────────   │  Uvicorn            │
│  :5173              │                      │  :8000              │
└─────────────────────┘                      └──────────┬──────────┘
                                                        │ 호출
                                                        ▼
                                            ┌─────────────────────┐
                                            │  pcr_diagnostic     │
                                            │  도메인 라이브러리  │
                                            │  (numpy/pandas/     │
                                            │   scikit-learn/     │
                                            │   scipy)            │
                                            └──────────┬──────────┘
                                                       │ 읽기/쓰기
                                                       ▼
                                            ┌─────────────────────┐
                                            │  storage/ (로컬 FS) │
                                            │  - datasets/        │
                                            │  - runs/            │
                                            └─────────────────────┘
```

- **단일 사용자 MVP**: DB 없이 백엔드 로컬 파일시스템(`backend/storage/`)에 데이터셋과 실행 결과를 저장한다.
- **계층 분리**: 도메인 로직(`pcr_diagnostic`)은 HTTP/저장소에 무지하며, 라우터가 얇은 어댑터로 동작한다.
- **개발 환경**: Vite dev server(5173)가 `/api` 경로를 Uvicorn(8000)으로 프록시한다.

---

## 2. 디렉토리 구조

```
pcr_diagnostic_project/
├── backend/
│   ├── api/                          # FastAPI 어플리케이션 계층
│   │   ├── main.py                   # create_app(), CORS, 라우터 등록
│   │   ├── schemas.py                # Pydantic 요청/응답 모델
│   │   ├── storage.py                # 파일시스템 기반 데이터셋·런 저장소
│   │   └── routers/
│   │       ├── datasets.py           # 업로드/목록/미리보기/삭제
│   │       ├── qc.py                 # 품질 관리 분석
│   │       ├── quantification.py     # ΔΔCt 정량
│   │       └── ml.py                 # ML 학습/평가
│   ├── src/pcr_diagnostic/           # 도메인 라이브러리
│   │   ├── data_loader.py            # PCRDataLoader, AmplificationCurveLoader
│   │   ├── quality_control.py        # QualityControl
│   │   ├── quantification.py         # DeltaDeltaCt, StandardCurve, EfficiencyCorrected…
│   │   ├── ml_diagnostics.py         # PCRClassifier, AnomalyDetector
│   │   └── visualization.py          # PCRVisualizer (matplotlib/seaborn)
│   ├── examples/                     # CLI 사용 예시 스크립트
│   ├── tests/                        # pytest 테스트
│   ├── storage/                      # 런타임 산출물 (datasets/, runs/)
│   ├── data/sample_pcr_data.csv
│   ├── environment.yml / requirements.txt / setup.py
│
├── frontend/
│   ├── src/
│   │   ├── main.js                   # Vue/Pinia/Router 부트스트랩
│   │   ├── App.vue                   # 헤더 + RouterView + ToastContainer
│   │   ├── router/index.js           # Upload / QC / ΔΔCt / ML 4개 라우트
│   │   ├── api/client.js             # axios 인스턴스 + 4개 API 모듈
│   │   ├── stores/                   # Pinia (datasets, toasts)
│   │   ├── views/                    # 라우트별 화면
│   │   │   ├── UploadView.vue
│   │   │   ├── QCView.vue
│   │   │   ├── QuantificationView.vue
│   │   │   └── MLView.vue
│   │   ├── components/               # 공용 컴포넌트
│   │   │   ├── DatasetSelector.vue
│   │   │   ├── DataTable.vue
│   │   │   ├── UploadDropzone.vue
│   │   │   ├── PlotlyChart.vue
│   │   │   ├── Spinner.vue
│   │   │   ├── ErrorBanner.vue
│   │   │   └── ToastContainer.vue
│   │   └── assets/main.css           # Tailwind entry
│   ├── vite.config.js                # @ alias, /api 프록시
│   ├── tailwind.config.js / postcss.config.js
│   └── package.json
│
└── docs/                             # 본 문서들
```

---

## 3. 계층 책임

### 3.1 도메인 계층 — `backend/src/pcr_diagnostic/`

순수 Python 라이브러리. HTTP·파일시스템에 의존하지 않으며 `pandas.DataFrame`을 입력/출력으로 사용한다.

| 모듈 | 핵심 클래스 | 역할 |
|---|---|---|
| `data_loader.py` | `PCRDataLoader`, `AmplificationCurveLoader` | CSV/Excel 로드, 필수 컬럼 검증, 메타데이터 수집, 필터링, 이상치 제거 |
| `quality_control.py` | `QualityControl` | Ct 범위, NTC, 재현성(CV%), 이상치(Grubbs/Z/Modified Z), 증폭 효율 추정 |
| `quantification.py` | `DeltaDeltaCt`, `StandardCurve`, `EfficiencyCorrectedQuantification` | ΔCt / ΔΔCt, Fold Change, t-test 유의성, 표준 곡선 기반 정량 |
| `ml_diagnostics.py` | `PCRClassifier`, `AnomalyDetector` | RandomForest/SVM/GradientBoosting/XGBoost, IsolationForest 기반 이상 탐지 |
| `visualization.py` | `PCRVisualizer` | matplotlib/seaborn 그래프 (현재 API에서는 미사용; 예제 스크립트 전용) |

설계 원칙:
- 입력 검증은 모듈 내부에서 처리하고, 잘못된 입력은 `ValueError`로 명시한다.
- 결과는 직렬화 가능한 dict/`pd.DataFrame`을 반환한다 — 라우터에서 JSON 변환을 책임진다.

### 3.2 API 계층 — `backend/api/`

FastAPI 어플리케이션. 도메인 라이브러리와 저장소를 얇게 감싼다.

- **`main.py`** — `create_app()` 팩토리. CORS(개발 시 `localhost:5173`만 허용), 4개 라우터 등록, `/api/health` 제공.
- **`schemas.py`** — `DatasetSummary`, `DatasetPreview`, `QCRequest`, `DDCTRequest`, `MLTrainRequest`, `RunResponse` Pydantic 모델.
- **`storage.py`** — `STORAGE_ROOT = backend/storage/` 기준 파일 저장소.
  - `datasets/<id>/data.csv`, `datasets/<id>/meta.json`
  - `runs/<id>/result.json`
  - ID는 `uuid4().hex[:12]`
  - `save_dataset`은 업로드된 bytes를 저장하고, `pd.read_csv`로 즉시 검증·메타 산출
- **`routers/`** — 각 라우터는 다음 순서를 반복한다:
  1. `storage.get_dataset(dataset_id)`로 존재 확인 (없으면 404)
  2. `storage.load_dataset_df`로 DataFrame 로드
  3. 도메인 클래스 호출 (CPU-bound한 ML은 `run_in_threadpool`로 처리)
  4. `_to_jsonable`로 numpy/pandas 스칼라를 표준 Python 타입으로 변환
  5. `storage.save_run`으로 결과 영속화 후 `{run_id, ...payload}` 반환

| 라우터 | prefix | 주요 엔드포인트 |
|---|---|---|
| datasets | `/api/datasets` | `POST ""` 업로드 / `GET ""` 목록 / `GET /{id}` / `GET /{id}/preview?n=` / `DELETE /{id}` |
| qc | `/api/qc` | `POST /{dataset_id}` |
| quantification | `/api/quantification` | `POST /ddct/{dataset_id}` |
| ml | `/api/ml` | `POST /train/{dataset_id}` |
| (root) | `/api/health` | `GET` |

업로드 제한: 10MB, CSV 만 허용. ML 학습은 `min_per_class < 2`인 경우 stratify 비활성, `test_size`는 `[0.1, 0.5]`로 클램프.

### 3.3 저장소 계층 — `backend/storage/` (런타임)

```
storage/
├── datasets/
│   └── <dataset_id>/
│       ├── data.csv      # 원본 업로드 CSV
│       └── meta.json     # DatasetRecord (id, filename, uploaded_at, n_rows/samples/genes, groups, genes)
└── runs/
    └── <run_id>/
        └── result.json   # {kind: "qc"|"ddct"|"ml", created_at, ...payload}
```

DB가 없으므로 동시 쓰기 보호는 없다. 단일 사용자 MVP 가정.

### 3.4 프론트엔드 계층 — `frontend/src/`

Vue 3 (Composition API) + Vue Router + Pinia + Tailwind + Plotly.js.

- **`main.js`** — `createApp(App).use(createPinia()).use(router).mount('#app')`
- **`router/index.js`** — 4개 라우트(`/upload`, `/qc`, `/quantification`, `/ml`). 모든 view는 lazy import.
- **`api/client.js`** — axios 인스턴스(`baseURL: /api`, `timeout: 120s`). 인터셉터가 FastAPI의 `{detail: ...}`을 `Error.message`로 정규화. `datasetsApi` / `qcApi` / `ddctApi` / `mlApi` 4 모듈 export.
- **Pinia stores**
  - `datasets` — 데이터셋 목록·선택 상태·업로드/삭제·`selected()` getter. 모든 view가 공유.
  - `toasts` — 글로벌 알림 큐(success/error/info, 자동 만료).
- **Views** — 각 view는 `useDatasetsStore`에서 `selectedId`를 읽어 분석 폼을 노출하고, 대응되는 `*Api`를 호출한 뒤 결과를 `PlotlyChart`/`DataTable`로 렌더한다.

---

## 4. 주요 데이터 플로우

### 4.1 데이터셋 업로드

```
User → UploadDropzone → datasetsStore.upload(file)
                       → datasetsApi.upload (POST /api/datasets, multipart)
                       → routers/datasets.upload_dataset
                       → storage.save_dataset (CSV 저장 + 메타 검증)
                       → DatasetSummary 응답
                       → datasetsStore.fetchAll() + selectedId 갱신
```

검증 실패(필수 컬럼 누락) 시 422; 크기 초과 시 413; CSV가 아니면 415.

### 4.2 QC 분석

```
QCView → qcApi.run(datasetId, QCRequest)
       → POST /api/qc/{dataset_id}
       → storage.load_dataset_df
       → QualityControl(df).check_* / detect_outliers / estimate_efficiency
       → _to_jsonable + save_run("qc", payload)
       → {run_id, ct_check, ntc_check, reproducibility, outliers, efficiency, boxplot}
```

응답에 `boxplot`(유전자별 Ct 배열)이 포함되어 프론트에서 Plotly로 즉시 시각화 가능.

### 4.3 ΔΔCt 정량

```
QuantificationView → ddctApi.run(datasetId, DDCTRequest)
                   → POST /api/quantification/ddct/{dataset_id}
                   → target_gene/reference_gene/control_group 존재 검증 (422)
                   → DeltaDeltaCt(df).calculate(...)
                     · mean_ct → delta_ct (target − reference)
                     · delta_delta_ct (treatment − control)
                     · fold_change = efficiency_target^(−ΔΔCt) 등
                     · scipy.stats.ttest_ind 로 유의성 평가
                   → comparisons만 응답으로 보내고 내부 DataFrame은 제거
```

### 4.4 ML 학습

```
MLView → mlApi.train(datasetId, MLTrainRequest)
       → POST /api/ml/train/{dataset_id}
       → run_in_threadpool(_do_train, df, request)
           · PCRClassifier(model_type, random_state)
           · prepare_features(df, target_col)
           · train_test_split (stratify는 클래스당 ≥2일 때만)
           · train() → cv_mean/cv_std
           · evaluate() → accuracy/precision/recall/f1/roc_auc/confusion_matrix
           · get_feature_importance(top_n=15)
       → save_run("ml", payload)
       → {run_id, metrics, confusion_matrix, feature_importance, ...}
```

scikit-learn 호출이 GIL을 점유할 수 있으므로 `run_in_threadpool`로 이벤트 루프를 보호한다.

---

## 5. 횡단 관심사

- **에러 처리**:
  - 백엔드: `HTTPException(status, detail)` 사용. `ValueError`는 422로, 일반 예외는 500으로 매핑.
  - 프론트: axios 인터셉터가 `detail`을 `Error.message`로 변환, store들이 잡아 `toasts.error(...)`로 통지.
- **직렬화**: `routers/qc._to_jsonable`이 numpy/pandas → 표준 Python 변환을 담당. `NaN`은 `None`으로.
- **CORS**: 개발 전용으로 `localhost:5173`만 허용. 프록시를 사용하므로 운영에서는 동일 호스트라면 제거 가능.
- **인증·인가**: 없음. 단일 사용자 가정.
- **테스트**: pytest. `backend/tests/` 아래에 `data_loader`, `quality_control`, `quantification` 단위 테스트. 라우터/프론트 테스트는 아직 없음.

---

## 6. 의존성 요약

**Backend (`backend/requirements.txt` 핵심)**
- `fastapi`, `uvicorn`, `python-multipart`, `pydantic`
- `numpy`, `pandas`, `scipy`, `scikit-learn`, `matplotlib`, `seaborn`
- (선택) `xgboost`, `tensorflow`

**Frontend (`frontend/package.json`)**
- `vue@^3.5`, `vue-router@^4.4`, `pinia@^2.2`
- `axios@^1.7`, `plotly.js-dist-min@^2.35`
- 개발: `vite@^5`, `@vitejs/plugin-vue`, `tailwindcss`, `postcss`, `autoprefixer`

---

## 7. 실행 방법 (개발)

```bash
# 백엔드
cd backend
pip install -r requirements.txt
pip install -e .
uvicorn api.main:app --reload --host 127.0.0.1 --port 8000

# 프론트엔드
cd frontend
npm install
npm run dev    # http://localhost:5173, /api → 127.0.0.1:8000 프록시
```

---

## 8. 확장 시 고려사항

- **다중 사용자**: 현재 `storage/`는 ID 충돌은 없으나 권한 분리가 없다. 사용자/세션 도입 시 데이터셋·런 소유자 컬럼 + 인증 미들웨어 추가가 필요.
- **DB 전환**: `storage.py`만 교체하면 라우터 변경 없이 SQLite/Postgres로 이전 가능 (인터페이스가 함수 기반).
- **장기 실행 ML**: 현재 동기/스레드풀. 분/시간 단위 작업이라면 작업 큐(Redis + RQ/Celery)와 polling 엔드포인트가 필요.
- **시각화 일원화**: `PCRVisualizer`(matplotlib)는 예제 전용. 웹 UI는 Plotly로 클라이언트 렌더링하므로, 향후 두 경로의 데이터 모양을 통일하는 게 좋다.
