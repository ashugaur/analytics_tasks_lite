# %% spacing_tables_for_txt_files

## Dependencies
import pandas as pd


def spacing_tables_for_txt_files(*, _df=pd.DataFrame({})):
    global clip_df

    if pd.read_clipboard().shape[0] == 0:
        clip_dfx = _df.copy()
    else:
        clip_dfx = pd.read_clipboard()
        clip_dfx = clip_dfx.astype(str)

    # format all fields to string
    clip_dfx = clip_dfx.astype(str)

    clip_df = pd.DataFrame()
    for cl in clip_dfx.columns:
        # cl_len = clip_dfx[cl].str.len().max()
        if (len(cl) - clip_dfx[cl].str.len().max()) > 0:
            cl_len = len(cl)
        else:
            cl_len = clip_dfx[cl].str.len().max()
        cln = cl + " " * (cl_len - len(cl))
        for i in range(0, len(clip_dfx)):
            clip_df.loc[i, cln] = clip_dfx.loc[i, cl] + " " * (
                cl_len - len(clip_dfx.loc[i, cl])
            )

    clip_df.to_clipboard(index=False)
    print("☑️  Fixed width formatted content copied to clipboard.")
