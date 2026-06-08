# card-legal-data

폐쇄망에 법률 데이터를 전달하기 위한 데이터 전용 wheel입니다.

## 설치

```bash
pip install --index-url <PYPI_INDEX_URL> card-legal-data
```

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
