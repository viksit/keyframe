
from __future__ import absolute_import
import sys, os
from os.path import expanduser, join
from flask import Flask, request, Response
from flask import Flask, current_app, jsonify, make_response
from flask_cors import CORS, cross_origin

app = Flask(__name__)
CORS(app, supports_credentials=True)

VERSION = "3.0.0"

@app.route("/version", methods=["GET"])
def version():
    return VERSION

@app.route("/ping", methods=["GET"])
def ping():
    return 'ok'

@app.route("/ng", methods=["GET"])
def ng():
    n = request.args.get("n", None)
    if not n:
        raise Exception("Need parameter n")
    n = int(n)
    x = "%s" % (n - 25,)
    return jsonify([x[0], x[1]])

@app.route("/ts", methods=["GET"])
def ts():
    nt = request.args.get("nt", None)
    if not nt:
        raise Exception("Need parameter n")
    nt = int(nt)
    cpt = request.args.get("cpt", 5)
    cpt = float(cpt)
    pct = request.args.get("pct", None)
    pct = pct.rstrip("%")
    pct = float(pct)
    return jsonify({"saving":nt*cpt*pct/100})


if __name__ == "__main__":
    port = None
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    app.run(debug=True, port=port)
