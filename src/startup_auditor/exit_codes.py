"""Exit codes for the Startup-Auditor CLI.

Following Unix conventions:
- 0: Success
- 1: Analysis failed (partial results may exist)
- 2: Config error (missing API key, invalid configuration)
"""

EXIT_SUCCESS = 0
EXIT_FAILURE = 1
EXIT_CONFIG_ERROR = 2
