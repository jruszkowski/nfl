import xlwings as xw
import run_nf

def main():
    wb = xw.Book.caller()
    sheet = wb.sheets[0]


@xw.func
def hello(name):
    return f"Hello {name}!"


if __name__ == "__main__":
    xw.Book("xl_ui.xlsm").set_mock_caller()
    main()
