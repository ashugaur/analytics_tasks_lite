# %% Visualize .zip file

## Dependencies
from pathlib import Path
import zipfile


class DisplayableZipPath:
    display_filename_prefix_middle = "┣━"
    display_filename_prefix_last = "┗━"
    display_parent_prefix_middle = "    "
    display_parent_prefix_last = "┃   "

    def __init__(self, path, parent_path, is_last):
        self.path = path
        self.parent = parent_path
        self.is_last = is_last
        if self.parent:
            self.depth = self.parent.depth + 1
        else:
            self.depth = 0

    @property
    def displayname(self):
        return self.path

    def displayable(self):
        if self.parent is None:
            return self.displayname

        _filename_prefix = (
            self.display_filename_prefix_last
            if self.is_last
            else self.display_filename_prefix_middle
        )

        parts = ["{!s} {!s}".format(_filename_prefix, self.displayname)]

        parent = self.parent
        while parent and parent.parent is not None:
            parts.append(
                self.display_parent_prefix_middle
                if parent.is_last
                else self.display_parent_prefix_last
            )
            parent = parent.parent

        return "".join(reversed(parts))


def get_zip_file_structure(zip_ref, path=""):
    file_names = [
        f.filename
        for f in zip_ref.filelist
        if f.filename.startswith(path) and f.filename != path
    ]
    dir_names = set()
    for file_name in file_names:
        relative_path = Path(file_name).relative_to(path).parts
        if len(relative_path) > 1:
            dir_names.add(Path(path) / relative_path[0])

    dir_names = [d.as_posix() + "/" for d in dir_names if d.as_posix().startswith(path)]
    file_names_in_dir = [
        f
        for f in file_names
        if Path(f).parent.as_posix() + "/" == path or (path == "" and "/" not in f)
    ]

    return dir_names, file_names_in_dir


def visualize_zip_file(zip_path, output_file):
    try:
        with (
            zipfile.ZipFile(zip_path, "r") as zip_ref,
            open(output_file, "w", encoding="utf-8") as f,
        ):
            root = DisplayableZipPath("", None, False)

            def make_tree(parent_path, parent_displayable):
                dir_names, file_names_in_dir = get_zip_file_structure(
                    zip_ref, parent_path
                )

                file_names_in_dir = sorted(file_names_in_dir, key=lambda s: s.lower())
                dir_names = sorted(dir_names, key=lambda s: s.lower())

                count = 1
                for dir_name in dir_names:
                    dir_name_short = Path(dir_name).name
                    dir_displayable = DisplayableZipPath(
                        dir_name_short,
                        parent_displayable,
                        count == len(dir_names) + len(file_names_in_dir),
                    )
                    output = dir_displayable.displayable()
                    print(output)
                    f.write(output + "\n")
                    make_tree(dir_name, dir_displayable)
                    count += 1

                for file_name in file_names_in_dir:
                    file_name_short = Path(file_name).name
                    file_displayable = DisplayableZipPath(
                        file_name_short,
                        parent_displayable,
                        count == len(dir_names) + len(file_names_in_dir),
                    )
                    output = file_displayable.displayable()
                    print(output)
                    f.write(output + "\n")
                    count += 1

            print(f"Contents of {zip_path}:")
            f.write(f"Contents of {zip_path}:\n")
            make_tree("", root)
        print(f"Output saved to {output_file}")

    except zipfile.BadZipFile:
        print(f"Invalid zip file: {zip_path}")
    except FileNotFoundError:
        print(f"File not found: {zip_path}")


if __name__ == "__main__":
    zip_path = r"C:\Users\Ashut\Downloads\2016-citibike-tripdata.zip"  # replace with your zip file path
    output_file = "zip_contents.txt"
    visualize_zip_file(zip_path, output_file)
