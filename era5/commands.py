class Command(object):
    @staticmethod
    def arguments(parser):
        raise NotImplementedError("you must override this function.")
