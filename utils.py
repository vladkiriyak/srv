def is_in(obj, array: list):
    for o in array:
        if obj is o:
            return True

    return False