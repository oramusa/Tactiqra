import csv
from review_export import spreadsheet_safe

def test_spreadsheet_formula_escape():
    for value in ('=HYPERLINK("evil")','+cmd','-cmd','@SUM(1,2)','  =1+1'):
        assert spreadsheet_safe(value).startswith("'")
    assert spreadsheet_safe('ordinary-event-id') == 'ordinary-event-id'
