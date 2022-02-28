# Python Version: 3.x
import functools
import modulefinder
import pathlib
import sys
import textwrap
from logging import getLogger
from typing import Any, Dict, List, Sequence

from onlinejudge_verify.languages.models import Language, LanguageEnvironment

logger = getLogger(__name__)


class PythonLanguageEnvironment(LanguageEnvironment):
    def compile(self, path: pathlib.Path, *, basedir: pathlib.Path, tempdir: pathlib.Path) -> None:
        code = textwrap.dedent(f"""\
            #!{sys.executable}
            \"\"\"This is a helper script to run the target Python code.

            We need this script to set PYTHONPATH portably. The env command, quoting something, etc. are not portable or difficult to implement.
            \"\"\"

            import os
            import sys

            # arguments
            path = {repr(str(path.resolve()))}
            basedir = {repr(str(basedir.resolve()))}

            # run {str(path)}
            env = dict(os.environ)
            if "PYTHONPATH" in env:
                env["PYTHONPATH"] = basedir + os.pathsep + env["PYTHONPATH"]
            else:
                env["PYTHONPATH"] = basedir  # set `PYTHONPATH` to import files relative to the root directory
            os.execve(sys.executable, [sys.executable, path], env=env)  # use `os.execve` to avoid making an unnecessary parent process
        """)
        with open(tempdir / 'compiled.py', 'wb') as fh:
            fh.write(code.encode())

    def get_execute_command(self, path: pathlib.Path, *, basedir: pathlib.Path, tempdir: pathlib.Path) -> List[str]:
        return [sys.executable, str(tempdir / 'compiled.py')]


@functools.lru_cache(maxsize=None)
def _python_list_depending_files(path: pathlib.Path, basedir: pathlib.Path) -> List[pathlib.Path]:
    # collect Python files which are depended by the `path` and under `basedir`
    res_deps = []  # type: List[pathlib.Path]
    finder = modulefinder.ModuleFinder(path=[str(basedir)])
    # find files imported by `path`
    finder.run_script(str(path))
    for module in finder.modules.values():
        #exclude modules that don't have source file (like sys).
        if module.__file__ is None:  #type: ignore
            continue
        file = pathlib.Path(module.__file__)  # type: ignore
        try:  # check under `basedir`
            file.relative_to(basedir)
            res_deps.append(file)
        except ValueError:
            pass
    return list(set(res_deps))


class PythonLanguage(Language):
    def list_dependencies(self, path: pathlib.Path, *, basedir: pathlib.Path) -> List[pathlib.Path]:
        return _python_list_depending_files(path.resolve(), basedir)

    def bundle(self, path: pathlib.Path, *, basedir: pathlib.Path, options: Dict[str, Any]) -> bytes:
        """
        :throws NotImplementedError:
        """
        raise NotImplementedError

    def is_verification_file(self, path: pathlib.Path, *, basedir: pathlib.Path) -> bool:
        return '.test.py' in path.name

    def list_environments(self, path: pathlib.Path, *, basedir: pathlib.Path) -> Sequence[PythonLanguageEnvironment]:
        # TODO add another environment (e.g. pypy)
        return [PythonLanguageEnvironment()]
