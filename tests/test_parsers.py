import csv
import io
from pathlib import Path

import pytest

from app.imports.parsers import read_table


def test_read_table_scans_excel_header_after_preamble(tmp_path):
    pytest.importorskip("openpyxl")
    import openpyxl

    path = tmp_path / "商品.xlsx"
    book = openpyxl.Workbook()
    sheet = book.active
    sheet.append(["说明", "导出时间"])
    sheet.append(["仅供参考", "2026-01-01"])
    sheet.append([])
    sheet.append(["日期", "商品ID", "商品名称", "支付金额"])
    sheet.append(["2026-01-02", "p1", "咖啡", "12.5"])
    book.save(path)

    result = read_table(path)
    assert result.headers == ["日期", "商品ID", "商品名称", "支付金额"]
    assert result.rows[0]["商品ID"] == "p1"


def test_read_table_decodes_gb18030_csv(tmp_path):
    path = tmp_path / "推广.csv"
    path.write_bytes("日期,主体ID,主体类型,主体名称,花费,总成交金额\n2026-01-02,p1,商品,咖啡,1.5,12\n".encode("gb18030"))

    result = read_table(path)
    assert result.rows[0]["主体名称"] == "咖啡"
    assert result.encoding == "gb18030"
