import os, sys
from io import BytesIO
from gzip import GzipFile

import logging

log = logging.getLogger(__name__)

def compress_str(value, compression_type="gzip"):
    return compress(value.encode('utf-8'), compression_type)

def compress(value, compression_type="gzip"):
    if compression_type == "gzip":
        return compress_gzip(value)
    else:
        raise NotImplementedError(
            "compression type %s not implemented" % (compression_type,))

def compress_gzip(value):
    if not isinstance(value, bytes):
        raise Exception("only values of type bytes can be compressed")
    gz_body = BytesIO()
    gz = GzipFile(None, 'wb', 9, gz_body)
    gz.write(value)
    gz.close()
    return gz_body.getvalue()

def uncompress_gzip(value):
    b = BytesIO(value)
    gzf = GzipFile(None, 'rb', fileobj=b)
    return gzf.read()

def uncompress_str(value, compression_type="gzip"):
    if compression_type == "gzip":
        return uncompress_gzip(value).decode("utf-8")
    else:
        raise NotImplementedError(
            "uncompress type %s not implemented" % (compression_type,))
