# Nuri Assistant

## Assistant Mode

Nuri Assistant combines file organization and purchase decisions in one review-first desktop workflow.

- File assistant: choose a folder and type a request such as `20260715 ja00 1부터 하위 폴더까지 정리해줘`. The app extracts the date, media code, page number, naming order, and recursive option, then shows a rename preview before any files change.
- Purchase assistant: add the product you are considering plus alternatives. It ranks products from the price, rating, review count, warranty, and your fit score. The result only uses the facts entered in the app; it does not claim live prices, reviews, or market research.

Live shopping recommendations need a separate, approved data source (for example a shopping-search API) and an AI provider. That integration should keep the same flow: collect sources, show the evidence, recommend, and require user approval for any action.

반복되는 문서 파일명 정리 작업을 빠르고 안전하게 처리하기 위한 데스크톱 파일 관리 도구입니다.

파일을 추가하면 날짜, 매체코드, 페이지 번호를 기반으로 변경 예정 파일명을 미리 보여주고, 충돌 여부를 확인한 뒤 일괄 rename을 실행합니다. 변경 이력은 SQLite에 저장되며 마지막 변경은 되돌릴 수 있습니다.

## 핵심 기능

- PDF 및 일반 파일 다중 선택
- 폴더 스캔 및 하위폴더 포함 스캔
- `{DATE}_{MEDIA}_{PAGE}` 기반 파일명 규칙 생성
- 실무용 파일명 규칙 프리셋
- 작업 프로필 저장 및 불러오기
- 날짜, 매체코드, 페이지 번호 자동 추론
- 변경 예정 파일명 미리보기
- 검색어 및 상태별 미리보기 필터
- 목록에서 선택 항목 제거
- 상태별 색상 표시
- 미리보기 결과 CSV 저장
- 대상 파일명 충돌 및 배치 내 중복 감지
- SQLite 기반 rename 히스토리 저장
- 마지막 작업 배치 전체 되돌리기
- 외부 패키지 없이 실행 가능한 Tkinter GUI

## 파일명 규칙

기본 규칙은 다음과 같습니다.

```text
{DATE}_{MEDIA}_{PAGE}
```

예시:

```text
20260628_ja00_001.pdf
```

규칙 입력창에서 다음처럼 바꿀 수 있습니다.

```text
{MEDIA}-{DATE}-{PAGE}
```

결과:

```text
ja00-20260628-001.pdf
```

지원하는 토큰:

- `{DATE}`: `YYYYMMDD`
- `{MEDIA}`: 영문 2자 + 숫자 2자, 예: `ja00`
- `{PAGE}`: 3자리 페이지 번호, 예: `001`

## 실행 방법

Python 3.11 이상을 권장합니다.

```bash
cd nuri-assistant
python src/run_nuri.py
```

## 실무 사용 흐름

1. `파일 추가` 또는 `폴더 불러오기`로 작업 대상을 추가합니다.
2. 필요하면 `하위폴더 포함`을 켜고 폴더를 다시 불러옵니다.
3. 날짜, 매체코드, 시작 페이지를 확인합니다.
4. 프리셋 또는 직접 입력으로 파일명 규칙을 정합니다.
5. 반복 작업이면 `작업 프로필`로 현재 설정을 저장합니다.
6. `미리보기`에서 `ready`, `conflict`, `error` 상태를 검수합니다.
7. 검색어 또는 상태 필터로 특정 파일과 문제 항목만 확인합니다.
8. 제외할 파일은 선택 후 `선택 제거`를 누릅니다.
9. 승인/공유가 필요하면 `CSV 저장`으로 변경 예정 목록을 남깁니다.
10. 문제가 없으면 `변경 실행`을 누릅니다.
11. 실수한 경우 `마지막 배치 취소`로 직전 작업 묶음을 되돌립니다.

## 작업 프로필

자주 쓰는 작업 조건은 프로필로 저장할 수 있습니다. 프로필에는 다음 설정이 포함됩니다.

- 날짜
- 매체코드
- 시작 페이지
- 파일명 규칙
- 하위폴더 포함 여부

프로필 파일은 사용자 홈의 `.nuri-assistant/profiles.json`에 저장됩니다.

## 테스트

```bash
cd nf-file-engine
python -m unittest discover -s tests
```

## 프로젝트 구조

```text
nuri-assistant/
├── README.md
├── src/
│   ├── run_nuri.py
│   └── nuri_assistant/
│       ├── __init__.py
│       ├── core/
│       │   ├── export.py
│       │   ├── models.py
│       │   ├── naming.py
│       │   ├── operations.py
│       │   ├── planner.py
│       │   └── scanner.py
│       ├── metadata/
│       │   ├── patterns.py
│       │   └── inference.py
│       ├── storage/
│       │   ├── history.py
│       │   └── profiles.py
│       └── ui/
│           └── desktop.py
└── tests/
    └── test_nuri_assistant.py
```

## 설계 방향

기존 MVP는 하나의 엔진 파일에 검증, 추론, 미리보기, 실행, 히스토리 저장이 모두 섞여 있었습니다. 현재 구조는 기능 확장을 염두에 두고 역할별로 나눴습니다.

- `core`: 파일명 생성, 검증, 미리보기, rename/undo 실행
- `core.export`: 검수용 CSV 저장
- `core.scanner`: 폴더 내 문서/이미지 파일 스캔
- `metadata`: 파일명에서 날짜, 매체코드, 페이지를 추론하는 규칙
- `storage`: SQLite 히스토리 저장소, 배치 단위 이력, 작업 프로필
- `ui`: Tkinter 데스크톱 화면

이 구조를 기준으로 다음 단계에서는 폴더 감시, OCR 필요 여부 검사, 업로드 상태 모니터링 같은 기능을 독립 모듈로 붙일 수 있습니다.

## 개발 로드맵

### 1단계: File Rename MVP

- 파일 선택
- 규칙 기반 파일명 생성
- 미리보기
- 일괄 rename
- 히스토리 저장
- 마지막 변경 취소

### 2단계: Folder Watcher

- 다운로드 폴더 감시
- 새 PDF 자동 감지
- rename 후보 자동 생성
- 처리 완료 알림

### 3단계: OCR Inspector

- PDF 텍스트 존재 여부 검사
- OCR 필요 파일 분류
- OCR 처리 도구 연동 준비

### 4단계: Upload Monitor

- 업로드 성공, 실패, 재시도 이력 관리
- 작업 현황 대시보드 제공

### 5단계: NewsFlow

Nuri Assistant, Folder Watcher, OCR Inspector, Upload Monitor를 하나의 문서 처리 파이프라인으로 통합합니다.

## 포트폴리오 포인트

이 프로젝트는 단순 파일명 변경 도구에서 시작하지만, 장기적으로는 콘텐츠 제작 업무에서 발생하는 문서 처리 흐름을 자동화하는 파이프라인으로 확장할 수 있습니다. 핵심은 `미리보기 -> 실행 -> 이력 기록 -> 되돌리기` 흐름을 안전하게 제공하는 것입니다.
