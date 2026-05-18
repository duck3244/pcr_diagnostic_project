# PCR Diagnostic Project — UML 다이어그램

본 문서는 Mermaid 표기로 작성된 UML 다이어그램 모음이다. GitHub/IntelliJ/VS Code의 Mermaid 프리뷰에서 바로 렌더링된다.

목차
1. 컴포넌트 다이어그램 (시스템 구성)
2. 클래스 다이어그램 — 도메인 계층 (`pcr_diagnostic`)
3. 클래스 다이어그램 — API 계층 (FastAPI + Storage + Schemas)
4. 클래스 다이어그램 — 프론트엔드 (Vue + Pinia + axios)
5. 시퀀스 다이어그램 — 데이터셋 업로드
6. 시퀀스 다이어그램 — QC 분석
7. 시퀀스 다이어그램 — ΔΔCt 정량
8. 시퀀스 다이어그램 — ML 학습
9. 상태 다이어그램 — Dataset 라이프사이클

---

## 1. 컴포넌트 다이어그램

```mermaid
flowchart LR
    subgraph Browser["Browser"]
        UI["Vue 3 SPA<br/>(Vite :5173)"]
    end

    subgraph Server["Server"]
        API["FastAPI<br/>(Uvicorn :8000)"]
        DOMAIN["pcr_diagnostic<br/>(domain library)"]
        FS[("storage/<br/>datasets/<br/>runs/")]
    end

    UI -- "HTTP / JSON<br/>(/api/*)" --> API
    API -- "function calls" --> DOMAIN
    API -- "read/write" --> FS
```

---

## 2. 클래스 다이어그램 — 도메인 계층

`backend/src/pcr_diagnostic/`

```mermaid
classDiagram
    class PCRDataLoader {
        +Path filepath
        +DataFrame data
        +Dict metadata
        +load_data() DataFrame
        +get_metadata() Dict
        +filter_by_gene(genes) DataFrame
        +filter_by_group(groups) DataFrame
        +get_replicates(sample_id, gene) DataFrame
        +calculate_mean_ct(group_by) DataFrame
        +remove_outliers(method, threshold) DataFrame
        +export_processed_data(path, format)
        -_validate_data()
        -_collect_metadata()
    }

    class AmplificationCurveLoader {
        +Path filepath
        +DataFrame data
        +load_curve_data() DataFrame
        +get_sample_curve(sample_id) DataFrame
    }

    class QualityControl {
        +DataFrame data
        +Dict qc_results
        +run_full_qc(ct_threshold, reference_genes) Dict
        +check_ct_range(threshold) Dict
        +check_ntc() Dict
        +check_reproducibility(cv_threshold) Dict
        +detect_outliers(method, alpha) DataFrame
        +estimate_efficiency(exclude_genes, ...) Dict
        +generate_qc_report(output_path) str
        -_grubbs_test(data, alpha) List~int~
    }

    class DeltaDeltaCt {
        +DataFrame data
        +Dict results
        +calculate(target_gene, reference_gene, control_group, treatment_groups, eff_target, eff_ref) Dict
        +export_results(output_path)
        -_calculate_mean_ct() DataFrame
        -_calculate_delta_ct(mean_ct, target, ref) DataFrame
        -_calculate_delta_delta_ct(delta_ct, ctrl, trt, eff_t, eff_r) Dict
    }

    class StandardCurve {
        +DataFrame data
        +Dict curves
        +build_standard_curve(gene) Dict
        +quantify_unknown(gene, ct_values) Dict
        +validate_curve(gene) Dict
    }

    class EfficiencyCorrectedQuantification {
        +DataFrame data
        +calculate_with_efficiency(...)
    }

    class PCRClassifier {
        +str model_type
        +int random_state
        +Any model
        +StandardScaler scaler
        +LabelEncoder label_encoder
        +List feature_names
        +bool is_trained
        +prepare_features(data, target_col) Tuple
        +train(X_train, y_train, ...) Dict
        +predict(X_test) ndarray
        +predict_proba(X_test) ndarray
        +evaluate(X_test, y_test) Dict
        +get_feature_importance(top_n) DataFrame
        -_initialize_model()
    }

    class AnomalyDetector {
        +str method
        +Any model
        +fit_predict(X) ndarray
        +get_anomaly_scores(X) ndarray
    }

    class PCRVisualizer {
        +Tuple figsize
        +int dpi
        +plot_ct_distribution(...)
        +plot_amplification_curve(...)
        +plot_standard_curve(...)
        +plot_fold_change(...)
        +plot_heatmap(...)
        +plot_roc_curve(...)
        +plot_confusion_matrix(...)
        +plot_feature_importance(...)
        +create_diagnostic_dashboard(...)
    }

    PCRDataLoader ..> QualityControl : "produces df for"
    PCRDataLoader ..> DeltaDeltaCt
    PCRDataLoader ..> PCRClassifier
    QualityControl ..> PCRVisualizer
    DeltaDeltaCt ..> PCRVisualizer
    PCRClassifier ..> PCRVisualizer
```

---

## 3. 클래스 다이어그램 — API 계층

`backend/api/`

```mermaid
classDiagram
    class FastAPI_App {
        +include_router(datasets)
        +include_router(qc)
        +include_router(quantification)
        +include_router(ml)
        +health() Dict
    }
    note for FastAPI_App "create_app() in api/main.py\nCORS: http://localhost:5173"

    class DatasetRecord {
        <<dataclass>>
        +str id
        +str filename
        +str uploaded_at
        +int n_rows
        +int n_samples
        +int n_genes
        +List~str~ groups
        +List~str~ genes
        +to_dict() Dict
    }

    class storage {
        <<module>>
        +Path STORAGE_ROOT
        +Path DATASETS_DIR
        +Path RUNS_DIR
        +ensure_dirs()
        +save_dataset(filename, contents) DatasetRecord
        +list_datasets() List~DatasetRecord~
        +get_dataset(id) Optional~DatasetRecord~
        +load_dataset_df(id) DataFrame
        +delete_dataset(id) bool
        +save_run(kind, payload) str
        +get_run(id) Optional~Dict~
    }

    class DatasetSummary { <<Pydantic>> }
    class DatasetPreview { <<Pydantic>> }
    class QCRequest {
        <<Pydantic>>
        +float ct_threshold = 35.0
        +List~str~ reference_genes
        +float cv_threshold = 5.0
        +str outlier_method = "modified_zscore"
    }
    class DDCTRequest {
        <<Pydantic>>
        +str target_gene
        +str reference_gene
        +str control_group
        +Optional~List~str~~ treatment_groups
        +float efficiency_target = 2.0
        +float efficiency_reference = 2.0
    }
    class MLTrainRequest {
        <<Pydantic>>
        +str model_type = "random_forest"
        +str target_col = "group"
        +float test_size = 0.3
        +int random_state = 42
    }

    class datasets_router {
        <<APIRouter>>
        +upload_dataset(file) DatasetSummary
        +list_datasets() List~DatasetSummary~
        +get_dataset(id) DatasetSummary
        +preview_dataset(id, n) DatasetPreview
        +delete_dataset(id)
    }
    note for datasets_router "prefix=/api/datasets\nPOST   ''\nGET    ''\nGET    /:id\nGET    /:id/preview\nDELETE /:id"

    class qc_router {
        <<APIRouter>>
        +run_qc(id, QCRequest) Dict
    }
    note for qc_router "prefix=/api/qc\nPOST /:dataset_id"

    class quantification_router {
        <<APIRouter>>
        +run_ddct(id, DDCTRequest) Dict
    }
    note for quantification_router "prefix=/api/quantification\nPOST /ddct/:dataset_id"

    class ml_router {
        <<APIRouter>>
        +train_model(id, MLTrainRequest) Dict
    }
    note for ml_router "prefix=/api/ml\nPOST /train/:dataset_id"

    FastAPI_App --> datasets_router
    FastAPI_App --> qc_router
    FastAPI_App --> quantification_router
    FastAPI_App --> ml_router

    datasets_router ..> storage
    qc_router ..> storage
    quantification_router ..> storage
    ml_router ..> storage

    storage ..> DatasetRecord : creates

    datasets_router ..> DatasetSummary
    datasets_router ..> DatasetPreview
    qc_router ..> QCRequest
    quantification_router ..> DDCTRequest
    ml_router ..> MLTrainRequest

    qc_router ..> QualityControl : uses
    quantification_router ..> DeltaDeltaCt : uses
    ml_router ..> PCRClassifier : uses
```

---

## 4. 클래스 다이어그램 — 프론트엔드

`frontend/src/`

```mermaid
classDiagram
    class App_vue {
        <<Component>>
        +header
        +nav
        +RouterView
        +ToastContainer
    }
    note for App_vue "nav links: Upload, QC, DDct, ML"

    class router {
        <<VueRouter>>
        +routes
    }
    note for router "/        redirect /upload\n/upload          UploadView\n/qc              QCView\n/quantification  QuantificationView\n/ml              MLView"

    class axios_client {
        <<AxiosInstance>>
        +baseURL
        +timeout
        +interceptors
    }
    note for axios_client "baseURL=/api, timeout=120000ms\nresponse interceptor: detail to Error.message"

    class datasetsApi {
        <<module>>
        +list()
        +get(id)
        +preview(id, n)
        +upload(file, onProgress)
        +remove(id)
    }
    class qcApi {
        <<module>>
        +run(datasetId, body)
    }
    class ddctApi {
        <<module>>
        +run(datasetId, body)
    }
    class mlApi {
        <<module>>
        +train(datasetId, body)
    }

    class useDatasetsStore {
        <<PiniaStore>>
        +items
        +selectedId
        +loading
        +error
        +fetchAll()
        +upload(file, onProgress)
        +remove(id)
        +selected()
    }
    class useToastsStore {
        <<PiniaStore>>
        +items
        +push(msg, opts)
        +success(msg)
        +error(msg)
        +info(msg)
        +dismiss(id)
    }

    class UploadView
    class QCView
    class QuantificationView
    class MLView

    class UploadDropzone
    class DatasetSelector
    class DataTable
    class PlotlyChart
    class Spinner
    class ErrorBanner
    class ToastContainer

    App_vue --> router
    router --> UploadView
    router --> QCView
    router --> QuantificationView
    router --> MLView
    App_vue --> ToastContainer

    UploadView --> useDatasetsStore
    QCView --> useDatasetsStore
    QuantificationView --> useDatasetsStore
    MLView --> useDatasetsStore

    useDatasetsStore ..> datasetsApi
    QCView ..> qcApi
    QuantificationView ..> ddctApi
    MLView ..> mlApi

    datasetsApi ..> axios_client
    qcApi ..> axios_client
    ddctApi ..> axios_client
    mlApi ..> axios_client

    ToastContainer --> useToastsStore
```

---

## 5. 시퀀스 다이어그램 — 데이터셋 업로드

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant V as UploadView
    participant DS as datasetsStore
    participant API as datasetsApi
    participant R as datasets router
    participant S as storage
    participant FS as filesystem

    U->>V: drop CSV file
    V->>DS: upload(file, onProgress)
    DS->>API: POST /api/datasets (multipart)
    API->>R: upload_dataset(file)
    R->>R: validate size ≤10MB, .csv 확장자
    R->>S: save_dataset(filename, contents)
    S->>FS: mkdir datasets/<id>
    S->>FS: write data.csv
    S->>S: pd.read_csv + 필수 컬럼 검증
    alt 필수 컬럼 누락
        S--xR: ValueError
        R--xAPI: HTTP 422
    else 정상
        S->>FS: write meta.json
        S-->>R: DatasetRecord
        R-->>API: 201 DatasetSummary
    end
    API-->>DS: DatasetSummary
    DS->>API: GET /api/datasets (refresh list)
    DS->>DS: selectedId = created.id
    DS-->>V: done
    V-->>U: 미리보기/다음 단계 활성화
```

---

## 6. 시퀀스 다이어그램 — QC 분석

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant V as QCView
    participant API as qcApi
    participant R as qc router
    participant S as storage
    participant QC as QualityControl

    U->>V: submit (ct_threshold, cv_threshold, outlier_method, ref_genes)
    V->>API: run(datasetId, QCRequest)
    API->>R: POST /api/qc/{id}
    R->>S: get_dataset(id)
    alt 없음
        R--xAPI: 404
    end
    R->>S: load_dataset_df(id)
    S-->>R: DataFrame
    R->>QC: new QualityControl(df)
    R->>QC: check_ct_range / check_ntc / check_reproducibility / detect_outliers
    opt concentration 컬럼 존재
        R->>QC: estimate_efficiency(exclude=ref_genes)
    end
    R->>R: _to_jsonable(payload) + boxplot 데이터 구성
    R->>S: save_run("qc", payload)
    S-->>R: run_id
    R-->>API: {run_id, ct_check, ntc_check, reproducibility, outliers, efficiency, boxplot}
    API-->>V: result
    V->>V: PlotlyChart(boxplot) + DataTable(outliers)
```

---

## 7. 시퀀스 다이어그램 — ΔΔCt 정량

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant V as QuantificationView
    participant API as ddctApi
    participant R as quantification router
    participant S as storage
    participant DD as DeltaDeltaCt

    U->>V: select target/reference/control + 실행
    V->>API: run(datasetId, DDCTRequest)
    API->>R: POST /api/quantification/ddct/{id}
    R->>S: get_dataset(id)
    R->>S: load_dataset_df(id)
    S-->>R: DataFrame
    R->>R: validate target_gene/reference_gene/control_group ∈ df
    alt 유효하지 않음
        R--xAPI: 422
    end
    R->>DD: new DeltaDeltaCt(df)
    R->>DD: calculate(target, ref, ctrl, treatments, eff_t, eff_r)
    DD->>DD: mean_ct → ΔCt → ΔΔCt → fold_change → t-test
    DD-->>R: results
    R->>R: _to_jsonable(strip DataFrame fields)
    R->>S: save_run("ddct", payload)
    R-->>API: {run_id, comparisons, ...}
    API-->>V: result
    V->>V: PlotlyChart(fold_change bar) + DataTable(p-values)
```

---

## 8. 시퀀스 다이어그램 — ML 학습

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant V as MLView
    participant API as mlApi
    participant R as ml router
    participant TP as threadpool
    participant S as storage
    participant ML as PCRClassifier
    participant SK as scikit-learn

    U->>V: choose model_type + 실행
    V->>API: train(datasetId, MLTrainRequest)
    API->>R: POST /api/ml/train/{id}
    R->>S: get_dataset(id) / load_dataset_df(id)
    R->>TP: run_in_threadpool(_do_train, df, request)
    TP->>ML: new PCRClassifier(model_type, random_state)
    TP->>ML: prepare_features(df, target_col)
    ML-->>TP: X, y
    TP->>SK: train_test_split(X, y, stratify if min_per_class≥2)
    TP->>ML: train(X_train, y_train)
    ML->>SK: cross_val_score + model.fit
    ML-->>TP: {cv_mean, cv_std}
    TP->>ML: evaluate(X_test, y_test)
    ML-->>TP: {accuracy, f1, roc_auc, confusion_matrix}
    TP->>ML: get_feature_importance(top_n=15)
    TP-->>R: result dict
    R->>R: _to_jsonable + save_run("ml", payload)
    R-->>API: {run_id, metrics, confusion_matrix, feature_importance}
    API-->>V: result
    V->>V: PlotlyChart(confusion / importance) + 지표 카드
```

---

## 9. 상태 다이어그램 — Dataset 라이프사이클

```mermaid
stateDiagram-v2
    [*] --> Uploading: User drops CSV
    Uploading --> Validating: bytes received
    Validating --> Rejected: 필수 컬럼 누락 / 비-CSV / >10MB
    Validating --> Stored: meta.json 작성
    Rejected --> [*]

    Stored --> Selected: store.selectedId = id
    Selected --> QCRun: POST /api/qc/{id}
    Selected --> DDCTRun: POST /api/quantification/ddct/{id}
    Selected --> MLRun: POST /api/ml/train/{id}
    QCRun --> Selected: run 저장 후 결과 반환
    DDCTRun --> Selected
    MLRun --> Selected

    Stored --> Deleted: DELETE /api/datasets/{id}
    Selected --> Deleted
    Deleted --> [*]
```

---

> 참고: 본 다이어그램은 `2026-05-18` 시점의 코드 기준이다. 클래스 시그니처가 갱신되면 함께 업데이트할 것.
