from io import BytesIO

import pandas as pd


def convert_to_excel(df):

    output = BytesIO()


    with pd.ExcelWriter(
        output,
        engine="openpyxl"
    ) as writer:

        df.to_excel(
            writer,
            index=False,
            sheet_name="Job Listings"
        )


    return output.getvalue()