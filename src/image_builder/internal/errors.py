class BuildError(Exception):
    '''raise this when there's an Exception during the build process'''


class LoadError(Exception):
    '''raise this when there's an Exception loading config files'''


class OperationError(Exception):
    '''raise this when there's an Exception running operations'''