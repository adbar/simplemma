"""Parts related to tokenization."""

import re


TOKREGEX = re.compile(r'(?:[0-9.,]+[\w_-]+|[\$§]? ?[0-9.,]+€?(?=[^\w.,_-])|[@#]?\w[\w*_-]*|[,;:\.?!¿¡‽⸮…()\[\]–{}—/‒_“„”’′″‘’“”\'"«»=+−×÷•·]+)')
