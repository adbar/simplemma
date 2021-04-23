"""Parts related to tokenization."""

import re

TOKREGEX = re.compile(r'(?:(?:[0-9][0-9.,:%-]*|St\.)[\w_€-]+|https?://[^ ]+|[@#§$]?\w[\w*_-]*|[,;:\.?!¿¡‽⸮…()\[\]–{}—/‒_“„”’′″‘’“”\'"«»=+−×÷•·]+)')
