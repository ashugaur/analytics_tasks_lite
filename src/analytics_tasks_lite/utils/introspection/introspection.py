def object_attributes(obj, keyword=None):
    """
    Prints the attributes of an object, filtered by a keyword if provided.

    Args:
        obj (object): The object to inspect.
        keyword (str, optional): A keyword to filter attributes. Defaults to None.
    """
    attributes = [attr for attr in dir(obj) if not attr.startswith("_")]

    if keyword:
        attributes = [
            attr for attr in attributes if keyword.casefold() in attr.casefold()
        ]

    for attr in attributes:
        print(attr)


if __name__ == "__main__":
    x = 1
    object_attributes(x)
    object_attributes(x, keyword="im")
