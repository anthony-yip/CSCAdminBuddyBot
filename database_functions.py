import pandas as pd
import json
from datetime import date, datetime
# NOTICE: keep date columns as STRING throughout.
def dict_to_excel(dict, file_path):
    # for exporting
    pd.read_json(json.dumps(dict), dtype=False, orient='index').to_excel(file_path)
    return file_path


def excel_to_dict(file_path):
    # just for testing purposes
    df = pd.read_excel(file_path, index_col=0, dtype={"Rank": object, "Name": object, "Start Date": object,
                                                     "End Date": object, "URTI?": bool})
    return json.loads(df.to_json(orient='index'))


def dict_to_df(dict):
    return pd.read_json(json.dumps(dict), dtype=False, orient='index')


def df_to_dict(df):
    return json.loads(df.to_json(orient='index'))


def datify(string):
    return datetime.strptime(str(string), "%d%m%y").date()


def archive_and_split(dict):
    # archives all mcs that have ended
    df = dict_to_df(dict)
    mask = df['End Date'].apply(datify, convert_dtype=False) < date.today()
    archive = df[mask]
    main = df[~mask]
    return df_to_dict(main), df_to_dict(archive)


def who_is_not_around_today(dict):
    df = dict_to_df(dict)
    mask = (df['Start Date'].apply(datify, convert_dtype=False) <= date.today()) & (df['End Date'].apply(datify,
                                                                        convert_dtype=False) >= date.today())
    return df[mask]


test_dict = excel_to_dict("test.xlsx")
main, archive = archive_and_split(test_dict)
print(who_is_not_around_today(test_dict))