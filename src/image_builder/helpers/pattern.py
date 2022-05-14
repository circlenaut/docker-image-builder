import os
import re
from abc import ABC

from pathlib import Path

from ..configs import Constants, Settings

__all__ = ['Pattern', 'PatternMatcher']


def fnmatch(name, pat):
    """Test whether FILENAME matches PATTERN.
    Patterns are Unix shell style:
    *       matches everything
    ?       matches any single character
    [seq]   matches any character in seq
    [!seq]  matches any char not in seq
    An initial period in FILENAME is not special.
    Both FILENAME and PATTERN are first case-normalized
    if the operating system requires it.
    If you don't want this, use fnmatchcase(FILENAME, PATTERN).
    """

    name = name.lower()
    pat = pat.lower()
    return fnmatchcase(name, pat)

def fnmatchcase(name, pat):
    """Test whether FILENAME matches PATTERN, including case.
    This is a version of fnmatch() which doesn't case-normalize
    its arguments.
    """
    constants = Constants()
    try:
        re_pat = constants._cache[pat]
    except KeyError:
        res = translate(pat)
        if len(constants._cache) >= constants._MAXCACHE:
            constants._cache.clear()
        constants._cache[pat] = re_pat = re.compile(res)
    return re_pat.match(name) is not None

def normalize_slashes(p):
    constants = Constants()
    if constants.IS_WINDOWS_PLATFORM:
        return '/'.join(split_path(p))
    return p

def split_path(p):
    constants = Constants()
    return [pt for pt in re.split(constants._SEP, p) if pt and pt != '.']

def translate(pat):
    """Translate a shell PATTERN to a regular expression.
    There is no way to quote meta-characters.
    """
    i, n = 0, len(pat)
    res = '^'
    while i < n:
        c = pat[i]
        i = i + 1
        if c == '*':
            if i < n and pat[i] == '*':
                # is some flavor of "**"
                i = i + 1
                # Treat **/ as ** so eat the "/"
                if i < n and pat[i] == '/':
                    i = i + 1
                if i >= n:
                    # is "**EOF" - to align with .gitignore just accept all
                    res = res + '.*'
                else:
                    # is "**"
                    # Note that this allows for any # of /'s (even 0) because
                    # the .* will eat everything, even /'s
                    res = res + '(.*/)?'
            else:
                # is "*" so map it to anything but "/"
                res = res + '[^/]*'
        elif c == '?':
            # "?" is any char except "/"
            res = res + '[^/]'
        elif c == '[':
            j = i
            if j < n and pat[j] == '!':
                j = j + 1
            if j < n and pat[j] == ']':
                j = j + 1
            while j < n and pat[j] != ']':
                j = j + 1
            if j >= n:
                res = res + '\\['
            else:
                stuff = pat[i:j].replace('\\', '\\\\')
                i = j + 1
                if stuff[0] == '!':
                    stuff = '^' + stuff[1:]
                elif stuff[0] == '^':
                    stuff = '\\' + stuff
                res = '%s[%s]' % (res, stuff)
        else:
            res = res + re.escape(c)

    return res + '$'


class Pattern(ABC):
    def __init__(self, pattern_str):
        self.exclusion = False
        if pattern_str.startswith('!'):
            self.exclusion = True
            pattern_str = pattern_str[1:]

        self.dirs = self.normalize(pattern_str)
        self.cleaned_pattern = '/'.join(self.dirs)

    @classmethod
    def normalize(cls, p):
        # Leading and trailing slashes are not relevant. Yes,
        # "foo.py/" must exclude the "foo.py" regular file. "."
        # components are not relevant either, even if the whole
        # pattern is only ".", as the Docker reference states: "For
        # historical reasons, the pattern . is ignored."
        # ".." component must be cleared with the potential previous
        # component, regardless of whether it exists: "A preprocessing
        # step [...]  eliminates . and .. elements using Go's
        # filepath.".
        i = 0
        split = split_path(p)
        while i < len(split):
            if split[i] == '..':
                del split[i]
                if i > 0:
                    del split[i - 1]
                    i -= 1
            else:
                i += 1
        return split

    def match(self, filepath):
        return fnmatch(normalize_slashes(filepath), self.cleaned_pattern)


class PatternMatcher(ABC):
    def __init__(self, patterns):
        self.patterns = list(filter(
            lambda p: p.dirs, [Pattern(p) for p in patterns]
        ))
        self.patterns.append(Pattern('!.dockerignore'))

    def matches(self, filepath):
        matched = False
        parent_path = Path(filepath).parent
        parent_path_dirs = split_path(parent_path.as_posix())

        for pattern in self.patterns:
            negative = pattern.exclusion
            match = pattern.match(filepath)
            if not match and parent_path != '':
                if len(pattern.dirs) <= len(parent_path_dirs):
                    match = pattern.match(
                        os.path.sep.join(parent_path_dirs[:len(pattern.dirs)])
                    )

            if match:
                matched = not negative

        return matched

    def walk(self, root):
        def rec_walk(current_dir):
            for f in os.listdir(current_dir):
                fpath = os.path.join(
                    os.path.relpath(current_dir, root), f
                )
                if fpath.startswith('.' + os.path.sep):
                    fpath = fpath[2:]
                match = self.matches(fpath)
                if not match:
                    yield fpath

                cur = os.path.join(root, fpath)
                if not os.path.isdir(cur) or os.path.islink(cur):
                    continue

                if match:
                    # If we want to skip this file and it's a directory
                    # then we should first check to see if there's an
                    # excludes pattern (e.g. !dir/file) that starts with this
                    # dir. If so then we can't skip this dir.
                    skip = True

                    for pat in self.patterns:
                        if not pat.exclusion:
                            continue
                        if pat.cleaned_pattern.startswith(
                                normalize_slashes(fpath)):
                            skip = False
                            break
                    if skip:
                        continue
                for sub in rec_walk(cur):
                    yield sub

        return rec_walk(root)
