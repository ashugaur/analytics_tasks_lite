def visualize_directory_tree_levels(unc, max_depth=None):
    from pathlib import Path
    import subprocess as sp

    class DisplayablePath(object):
        display_filename_prefix_middle = "┣━"
        display_filename_prefix_last = "┗━"
        display_parent_prefix_middle = "    "
        display_parent_prefix_last = "┃   "

        def __init__(self, path, parent_path, is_last):
            self.path = Path(str(path))
            self.parent = parent_path
            self.is_last = is_last
            if self.parent:
                self.depth = self.parent.depth + 1
            else:
                self.depth = 0

        @property
        def displayname(self):
            if self.path.is_dir():
                return self.path.name + "/"
            return self.path.name

        @classmethod
        def make_tree(
            cls, root, parent=None, is_last=False, criteria=None, max_depth=None
        ):
            root = Path(str(root))
            criteria = criteria or cls._default_criteria

            displayable_root = cls(root, parent, is_last)
            yield displayable_root

            # Check if we've reached the maximum depth
            if max_depth is not None and displayable_root.depth >= max_depth:
                return

            children = sorted(
                list(path for path in root.iterdir() if criteria(path)),
                key=lambda s: str(s).lower(),
            )
            count = 1
            for path in children:
                is_last = count == len(children)
                if path.is_dir():
                    yield from cls.make_tree(
                        path,
                        parent=displayable_root,
                        is_last=is_last,
                        criteria=criteria,
                        max_depth=max_depth,
                    )
                else:
                    yield cls(path, displayable_root, is_last)
                count += 1

        @classmethod
        def _default_criteria(cls, path):
            return True

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

    # default run with max_depth parameter
    paths = DisplayablePath.make_tree(Path(unc), max_depth=max_depth)

    # export
    with open(r"directory_tree.txt", "w", encoding="utf-8") as f:
        for path in paths:
            f.write(str(path.displayable()) + "\n")
            print(path.displayable())

    # open
    sp.Popen('explorer "directory_tree.txt"')


if __name__ == "__main__":
    visualize_directory_tree_levels(_ao, max_depth=1)
