class ReprAble:
    def __repr__(self):
        class_name = type(self).__name__
        public_args = [
            arg for arg in self.__dir__() if not arg.startswith("_")
        ]
        first_arg = public_args[0]
        repr_str = (
            f"{class_name}<{first_arg} {self.__getattribute__(first_arg)}"
        )
        for arg in public_args[1:]:
            repr_str += f":{arg} {self.__getattribute__(arg)}"
        repr_str += ">"

        return repr_str