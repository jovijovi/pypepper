import json


class Version:
    def __init__(self):
        self._unknown = 'unknown'
        self._version_info_filename = 'git.json'
        self._version_info = ''

    def get_version_info(self):
        try:
            if not self._version_info:
                with open(self._version_info_filename, 'r') as fd:
                    data = fd.read()
                self._version_info = json.loads(data)

            return self._version_info
        except (Exception,):
            return {
                "version": self._unknown,
                "gitCommit": self._unknown,
                "buildTime": self._unknown,
                "pythonVersion": self._unknown,
            }


version = Version()
