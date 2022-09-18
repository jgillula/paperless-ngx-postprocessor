#!/usr/bin/env python3

import os

if __name__ == "__main__":
    for key in os.environ.keys():
        print(f"{key}={os.environ[key]}")

