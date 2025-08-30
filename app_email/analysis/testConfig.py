from cli.models import AnalystType

# CONFIG = {
#     'ticker': '000001',
#     'market': {
#         'name': 'A股',
#         'name_en': 'China A-Share',
#         'default': '600036',
#         'examples': ['000001 (平安银行)', '600036 (招商银行)', '000858 (五粮液)'],
#         'format': '6位数字代码 (如: 600036, 000001)',
#         'pattern': r'^\d{6}$',
#         'data_source': 'china_stock'
#     },
#     'analysis_date': '2025-08-29',
#     'analysts': [
#         AnalystType.MARKET,
#         AnalystType.SOCIAL,
#         AnalystType.NEWS,
#         AnalystType.FUNDAMENTALS,
#     ],
#     'research_depth': 1,
#     'llm_provider': '阿里百炼 (dashscope)',
#     'backend_url': 'https://dashscope.aliyuncs.com/api/v1',
#     'shallow_thinker': 'qwen-turbo',
#     'deep_thinker': 'qwen-turbo',
# }

CONFIG ={
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
    "analysis_date": "2025-08-29",
    "analysts": [
        AnalystType.MARKET,
        AnalystType.SOCIAL,
        AnalystType.NEWS,
        AnalystType.FUNDAMENTALS,
    ],
    "research_depth": 1,
    "llm_provider": "deepseek v3",
    "backend_url": "https://api.deepseek.com",
    "shallow_thinker": "deepseek-chat",
    "deep_thinker": "deepseek-reasoner"
}
