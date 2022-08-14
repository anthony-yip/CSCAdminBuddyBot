import pandas as pd
import json
from datetime import date, datetime
# NOTICE: keep date columns as STRING throughout.

standard_dtypes = {"Rank": object, "Name": object, "Start Date": object,
                                                     "End Date": object, "Type": object}
order = ["Rank", "Name", "Start Date", "End Date", "Type"]


def dict_to_excel(dict, file_path):
    # for exporting
    pd.read_json(json.dumps(dict), dtype=standard_dtypes, orient='index')[order].to_excel(file_path)
    return file_path


def excel_to_dict(file_path):
    # just for testing purposes
    df = pd.read_excel(file_path, index_col=0, dtype=standard_dtypes)
    return json.loads(df.to_json(orient='index'))


def dict_to_df(dict):
    return pd.read_json(json.dumps(dict), dtype=standard_dtypes, orient='index')[order]


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


def create_parade_state(mc_dict, off_dict):
    # take the two dicts form the database, returns a multiline text.
    mc_df = who_is_not_around_today(mc_dict)
    mc_df["Type"] = mc_df["Type"].replace(to_replace=["URTI", "Non-URTI"], value=["MC (URTI)", "MC (Non-URTI)"])
    off_df = who_is_not_around_today(off_dict)
    df = pd.concat([mc_df, off_df], ignore_index=True).astype("string")
    df["Text"] = df["Rank"] + " " + df["Name"] + ": " + df["Start Date"] + " - " + df["End Date"]
    ret = ""
    for category in ["MC (URTI)", "MC (Non-URTI)", "Off", "Leave"]:
        _iter = df[df["Type"]==category]["Text"]
        ret += f"{category} ({len(_iter)})\n"
        ret += "\n".join(_iter)
        ret += "\n"
    return ret

# what if empty?
test_dict = excel_to_dict("test.xlsx")
test_dict1 = excel_to_dict("test1.xlsx")
df1 = who_is_not_around_today(test_dict)
df2 = who_is_not_around_today(test_dict1)

print(create_parade_state(test_dict, test_dict1))