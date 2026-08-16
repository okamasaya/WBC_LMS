import pandas as pd

file_name = "JLPT_N2_LK_Vo"

input = file_name + ".csv"
output = file_name + ".json"
print(input, output)


# encodingを 'shift_jis' または 'utf-8' に変更します
try:
    df = pd.read_csv(input, encoding='shift_jis')
except UnicodeDecodeError:
    # shift_jisでもエラーが出る場合は、utf-8に変換する
    df = pd.read_csv(input, encoding='utf-8')

# 2. JSONファイルに変換して保存する
df.to_json(output, orient='records', force_ascii=False, indent=4)
