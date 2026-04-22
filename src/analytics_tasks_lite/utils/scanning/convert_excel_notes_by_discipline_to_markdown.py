import pathlib
import pandas as pd
import shutil
import os


def convert_excel_notes_by_discipline_to_markdown(_source, _destination):
    _filler = "uncat"
    # os.chdir(_destination.replace('\\', '/'))

    # remove folder
    os.chdir("\\".join(str(_destination).split("\\")[:-1]))
    shutil.rmtree(str(_destination).split("\\")[-1])

    # create folder
    pathlib.Path(str(_destination).split("\\")[-1]).mkdir(parents=True, exist_ok=True)
    os.chdir(_destination)

    _notes = pd.read_excel(_source, sheet_name="notes")
    _notes = _notes.fillna(".")

    _fields = ["category", "discipline", "on", "by", "source", "rank"]
    for i in range(0, len(_notes)):
        for _field in _fields:
            if _notes.loc[i, _field] == ".":
                _notes.loc[i, _field] = _filler

    _notes["discipline"] = _notes["discipline"].str.capitalize()
    _notes["on"] = _notes["on"].str.lower()

    for _dir in _notes["discipline"].unique().tolist():
        __dir = _dir.lower()
        pathlib.Path(__dir).mkdir(parents=True, exist_ok=True)
        _notesd = (
            _notes[_notes["discipline"] == _dir]
            .sort_values(["on"])
            .reset_index(drop=True)
        )

        for _c in _notesd["category"].unique().tolist():
            __c = _c.lower()
            _notesc = (
                _notesd[_notesd["category"] == _c]
                .sort_values(["on"])
                .reset_index(drop=True)
            )

            _reference_file_out = str(__c).replace(" ", "_")
            _d_heading = _c.lower().capitalize()
            if _reference_file_out.lower().strip() == _filler.lower().strip():
                file_out = __dir + "/index.md"
                # _d_heading = __dir.lower().capitalize()
                _d_heading = __dir.lower()
            else:
                file_out = __dir + "/" + _reference_file_out + ".md"

            with open(file_out, "w", encoding="utf-8") as f:
                # f.write('---\n# title: ' + _d_heading + '\nhide:' + '\n\t# - navigation' + '\n\t# - toc' + '\n\t# - footer' + '\n---\n\n')
                f.write("# " + _d_heading + "\n\n")

                for _on in _notesc["on"].drop_duplicates().sort_values().tolist():
                    _noteson = (
                        _notesc[_notesc["on"] == _on]
                        .sort_values(["on"])
                        .reset_index(drop=True)
                    )
                    # _t_heading = _on.lower().capitalize()
                    _t_heading = _on.lower()
                    f.write("<hr>\n\n### " + _t_heading + "\n\n")
                    # f.write('!!! ' + 'text' + ' ""\n\n')

                    for _n in _noteson["note"].drop_duplicates().sort_values().tolist():
                        _notesn = (
                            _noteson[_noteson["note"] == _n]
                            .sort_values(["on"])
                            .reset_index(drop=True)
                        )
                        _n = str(_n).replace("\n", "<br>")

                        _reference_by = str(_notesn["by"][0]).replace("\n", "<br>")
                        if _reference_by.lower().strip() == _filler.lower().strip():
                            _n_by = ""
                        else:
                            _n_by = "`" + _reference_by + "`"

                        _reference_source = str(_notesn["source"][0]).replace(
                            "\n", "<br>"
                        )
                        if _reference_source.lower().strip() == _filler.lower().strip():
                            _n_source = ""
                        else:
                            _n_source = "\t`" + _reference_source + "`"
                        # _n_rank = '\t&nbsp; `Rank: ' + str(_notesn['rank'][0]).replace('\n', '<br>')+'`'
                        # _nn = '\t' + str(_notesn['note'][0]).replace('\n', '<br>')
                        f.write(_n + "<br>\n")
                        # f.write('\t'+ _n_by + _n_source + _n_rank+ '\n\n')
                        f.write(_n_by + _n_source + "\n\n")
                        # f.write('\t??? null' + ' ""\n\n')
                        # f.write(_nn + '\n\n\n')
