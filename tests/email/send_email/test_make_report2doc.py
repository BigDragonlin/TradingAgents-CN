import pytest
from app_email.send_email.make_report2doc import MakeReport2Doc

@pytest.fixture
def make_report2doc():
    return MakeReport2Doc("1363992060@qq.com", "600111")

def test_make_report2doc(make_report2doc):
    make_report2doc.make_report2doc()