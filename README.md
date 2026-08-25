# card-legal-data

폐쇄망에 법률 데이터를 전달하기 위한 데이터 전용 wheel입니다.

## 설치

데이터가 PyPI 파일 상한(100MB)을 넘어 **5개 wheel로 나눠 발행**합니다.
다섯 개가 같은 `card_legal_data/` 트리에 풀리는 네임스페이스 패키지라, 설치 후
레이아웃은 단일 wheel일 때와 같습니다 — 적재 스크립트는 고칠 필요가 없습니다.

```bash
pip install --index-url <PYPI_INDEX_URL> \
  card-legal-data \
  card-legal-data-guidelines \
  card-legal-data-press \
  card-legal-data-press-fss \
  card-legal-data-precedents
```

| 패키지 | 내용 |
|---|---|
| `card-legal-data` | 법령·해석례·비조치의견서·약관 + 개인정보위·KISA 안내서 |
| `card-legal-data-guidelines` | 금감원 업무자료·해설서 |
| `card-legal-data-press` | 보도자료 — 금융위·개인정보위·KISA |
| `card-legal-data-press-fss` | 보도자료 — 금감원 |
| `card-legal-data-precedents` | 상위 tier 판례 |

부분 설치도 동작합니다(적재 스크립트가 없는 폴더는 건너뜁니다).

> ⚠️ **분할선을 바꾼 릴리스는 깨끗한 환경에 설치하십시오.** 파일이 패키지 사이를
> 옮겨간 경우, 설치 순서에 따라 새 패키지가 넣은 파일을 옛 패키지의 업그레이드가
> 지워버릴 수 있습니다. 기존 환경이라면 `pip uninstall` 로 `card-legal-data*` 를 모두
> 지운 뒤 다시 설치하십시오.

wheel에는 Python 소스 코드 없이 `card_legal_data/` 아래의 JSON 및 Markdown
데이터만 포함됩니다. 설치 후 데이터 디렉터리는 다음처럼 찾을 수 있습니다.

```python
from importlib.resources import files

data_root = files("card_legal_data")
```

## 배포

`main` 브랜치의 데이터가 변경되면 GitHub Actions가
`YYYY.MM.DD.RUN_NUMBER` 버전의 wheel을 만들어 PyPI Trusted Publishing으로
배포합니다.
