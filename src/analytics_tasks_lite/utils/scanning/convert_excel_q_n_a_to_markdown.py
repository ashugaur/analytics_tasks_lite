import pandas as pd
import os


def convert_excel_q_n_a_to_markdown(_source, _destination):
    os.chdir(_destination)

    q = pd.read_excel(_source, sheet_name="q_n_a")
    q = q[~q["discipline"].isin(["sas"])].reset_index(drop=True)
    q["topic"] = q["topic"].str.capitalize()

    d_list = q["discipline"].unique().tolist()
    for _d in d_list:
        _qd = q[q["discipline"] == _d].reset_index(drop=True)
        file_out = str(_d).replace(" ", "_") + ".md"
        # _d_heading = _d.lower().capitalize()
        _d_heading = _d.lower()

        with open(file_out, "w", encoding="utf-8") as f:
            # f.write('---\n# title: ' + _d_heading + '\nhide:' + '\n\t# - navigation' + '\n\t# - toc' + '\n\t# - footer' + '\n---\n\n')
            f.write("# " + _d_heading + "\n\n")

            t_list = _qd["topic"].drop_duplicates().sort_values().tolist()
            for _t in t_list:
                _qt = _qd[_qd["topic"] == _t].reset_index(drop=True)
                # _t_heading = _t.lower().capitalize()
                _t_heading = _t.lower()
                f.write(
                    '<br>\n\n<hr style="height:1px;border-width:100%;color:gray;background-color:#045a8d">\n\n## '
                    + _t_heading
                    + "\n\n"
                )

                on_list = _qt["on"].drop_duplicates().sort_values().tolist()
                on_list_len = len(on_list)
                on_list_r = 0
                for _h in on_list:
                    on_list_r += 1
                    on_list_diff = on_list_len - on_list_r
                    _qh = _qt[_qt["on"] == _h].reset_index(drop=True)
                    # _h_heading = _h.lower().capitalize()
                    _h_heading = _h.lower()
                    if on_list_r == 1:
                        f.write("\n\n\n\n### " + _h_heading + "\n\n")
                    else:
                        f.write("\n\n<hr>\n\n### " + _h_heading + "\n\n")

                    q_list = _qh["question"].drop_duplicates().sort_values().tolist()
                    q_len = len(q_list)
                    q_r = 0
                    for _q in q_list:
                        q_r += 1
                        _qq = _qh[_qh["question"] == _q].reset_index(drop=True)
                        _q = str(_q).replace("\n", "<br>")
                        q_diff = q_len - q_r
                        # print('q_diff: ', q_diff, _q)
                        if q_diff == 0:
                            _qn = (
                                "\t: "
                                + str(_qq["notes"][0]).replace("\n", "<br>")
                                + "\n\n"
                            )
                            f.write("??? " + "null" + ' "' + _q + '"\n\n')
                            f.write(_qn + "\n\n\n\n")
                        else:
                            _qn = (
                                "\t: "
                                + str(_qq["notes"][0]).replace("\n", "<br>")
                                + "\n\n<hr>"
                            )
                            f.write("??? " + "null" + ' "' + _q + '"\n\n')
                            f.write(_qn + "\n\n\n\n")
