def docstring_fix(*sub):
    def dec(obj):
        obj.__doc__ = obj.__doc__.format(*sub)
        return obj

    return dec


def get_default_params(docstr):
    pass
