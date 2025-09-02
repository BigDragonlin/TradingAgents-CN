from app_email.analysis.pipeline import AnalysisPipeline
import pytest

@pytest.fixture
def user_analysisPipeline():
    selection = {
        "ticker": "600276",
        "market": {
            "name": "A股",
            "name_en": "China A-Share",
            "default": "600036",
            "examples": [
                "000001 (平安银行)",
                "600036 (招商银行)",
                "000858 (五粮液)"
            ],
            "format": "6位数字代码 (如: 600036, 000001)",
            "pattern": "^\\d{6}$",
            "data_source": "china_stock"
        },
        "analysis_date": "2025-09-01",
        "analysts": [
            "market"
        ],
        "research_depth": 1,
        "llm_provider": "deepseek v3",
        "backend_url": "https://api.deepseek.com",
        "shallow_thinker": "deepseek-chat",
        "deep_thinker": "deepseek-reasoner"
    }
    return AnalysisPipeline(selection)

def test_configure(user_analysisPipeline):
    user_analysisPipeline.configure()
    print(user_analysisPipeline.config["llm_provider"])


