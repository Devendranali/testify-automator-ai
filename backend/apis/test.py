import pandas as pd

df = pd.read_excel("test.xlsx")
print(repr(df.columns.tolist()))
