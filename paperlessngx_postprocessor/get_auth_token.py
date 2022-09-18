#!/usr/bin/env python3

import os
import sys
from django.db import connection

def get_auth_token(paperless_src_dir="/usr/src/paperless/src"):
    # We set this environment variable so django knows what settings to use
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "paperless.settings")
    # And we have to make sure the paperless.settings module is on the path, so we add the path to the paperless source code here
    sys.path.insert(0, paperless_src_dir)

    try:
        cursor = connection.cursor()
        cursor.execute("SELECT key FROM authtoken_token")
        result = cursor.fetchone()
        cursor.close()
        if len(result) > 0:
            return result[0]
        else:
            raise RuntimeError(f"Unable to find an auth token in paperless-ngx's database using paperless_src_dir={paperless_src_dir}")
    except ModuleNotFoundError as e:
        # If we get a ModuleNotFoundError exception, it probably means
        # that when django tried to create the cursor, it couldn't
        # find the paperless.settings module, which means
        # paperless_src_dir probably wasn't correct
        raise RuntimeError(f"Couldn't find paperless-ngx's source code in {paperless_src_dir}")

if __name__ == "__main__":
    print(get_auth_token())
