
import logging
from subprocess import check_output, CalledProcessError

from . import utils


logger = logging.getLogger(__name__)


def log(msg, level=logging.WARN):
    logger.log(level, msg)


class GitInfo:
    """
    Utility class to retrieve git-based info from a repository
    """
    def __init__(self, fname):
        self.dirname = utils.get_dir(fname)

    def run(self, cmd):
        try:
            output = check_output(cmd, cwd=self.dirname)
            return output.strip().decode('utf-8')
        except OSError:
            log("Git doesn't seem to be installed in your system")
        except CalledProcessError:
            log("Not a git repository")

    def get_commit(self):
        """
        Returns current commit on file or None if an error is thrown by git
        (OSError) or if file is not under git VCS (CalledProcessError)
        """
        return self.run(["git", "describe", "--always"])

    def get_branch(self):
        """
        Returns current active branch on file or None if an error is thrown
        by git (OSError) or if file is not under git VCS (CalledProcessError)
        """
        return self.run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
