import os
from random import randint
from dataclasses import dataclass
from flask import Flask, Response, request, redirect, send_from_directory, jsonify
from werkzeug.utils import secure_filename
import zmq


UPLOAD_FOLDER = '/srv/video_wall_server_images/'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
all_files_list = os.listdir(app.config['UPLOAD_FOLDER'])


@dataclass
class ImageFileData:
    id: int
    file_path: str

    def __iter__(self):
        for key in self.__dict__:
            yield key, getattr(self, key)


all_files: list[ImageFileData] = []


def image_in_list(image: str) -> bool:
    global all_files
    for i in all_files:
        if image == i.file_path:
            return True
    return False


def update_all_files():
    global all_files
    global all_files_list
    all_files_list = os.listdir(app.config['UPLOAD_FOLDER'])
    for i in all_files_list:
        if image_in_list(i):
            continue
        all_files.append(ImageFileData(randint(1, 1000000), i))
    for i in all_files:
        if not i:
            continue
        if not (i.file_path in all_files_list):
            all_files.remove(i)


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def filename_from_id(id: int):
    global all_files
    for i in all_files:
        if i.id == id:
            return i.file_path


@app.route("/")
def default_route():
    return f"Video wall server"


@app.route("/upload", methods=["POST"])
def upload_route():
    if 'file' not in request.files:
        res = jsonify({
            "version": "0.1.0",
            "message": "info",
            "content": [
                "No file submitted"
            ]
        })
        res.headers.add('Access-Control-Allow-Origin', '*')
        return res
    file = request.files['file']
    # If the user does not select a file, the browser submits an
    # empty file without a filename.
    if file.filename == '':
        res = jsonify({
            "version": "0.1.0",
            "message": "info",
            "content": [
                "No file selected"
            ]
        })
        res.headers.add('Access-Control-Allow-Origin', '*')
        return res
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        res = jsonify({
            "version": "0.1.0",
            "message": "info",
            "content": [
                "Success"
            ]
        })
        res.headers.add('Access-Control-Allow-Origin', '*')
        return res

    res = jsonify({
        "version": "0.1.0",
        "message": "info",
        "content": [
            "Invalid file type submitted"
        ]
    })
    res.headers.add('Access-Control-Allow-Origin', '*')
    return res


@app.route("/get_all", methods=["GET"])
def get_all_route():
    update_all_files()
    if all_files:
        res = jsonify({
            "version": "0.1.0",
            "message": "all_files",
            "content": list(map(lambda i: dict(i), all_files))
        })
        res.headers.add('Access-Control-Allow-Origin', '*')
        return res
    else:
        res = jsonify({
            "version": "0.1.0",
            "message": "info",
            "content": [
                "No Files uploaded"
            ]
        })
        res.headers.add('Access-Control-Allow-Origin', '*')
        return res


@app.route("/get/<filename>", methods=["GET"])
def get_route(filename):
    res = send_from_directory(
        app.config["UPLOAD_FOLDER"], filename)
    res.headers.add('Access-Control-Allow-Origin', '*')
    return res


@app.route("/display/<id_>", methods=["GET"])
def display_route(id_):
    if not filename_from_id(int(id_)):
        res = jsonify({
            "version": "0.1.0",
            "message": "info",
            "content": [
                "No file selected"
            ]
        })
        res.headers.add('Access-Control-Allow-Origin', '*')
        return res
    context = zmq.Context()
    _requester = context.socket(zmq.REQ)
    _requester.connect("tcp://127.0.0.1:9091")
    data = {
        "version": "0.1.0",
        "command": "display_image",
        "location": f"http://backend.woordenlewe.com/get/{filename_from_id(int(id_))}",
    }
    _requester.send_json(data)
    res = jsonify(_requester.recv_json())
    _requester.close()
    context.term()
    res.headers.add('Access-Control-Allow-Origin', '*')
    return res


@app.route("/display_many", methods=["GET"])
def display_many_route():
    data = {
        "version": "0.1.0",
        "command": "display_image_loop",
        "loop_time": request.args.get('time', type=int),
        "locations": [],
    }

    for i in request.args.get('ids').split(','):
        if not filename_from_id(int(i)):
            continue
        data["locations"].append(f"http://backend.woordenlewe.com/get/{filename_from_id(int(i))}")

    if not data["locations"]:
        res = jsonify({
            "version": "0.1.0",
            "message": "info",
            "content": [
                "No files selected"
            ]
        })
        res.headers.add('Access-Control-Allow-Origin', '*')
        return res

    context = zmq.Context()
    _requester = context.socket(zmq.REQ)
    _requester.connect("tcp://127.0.0.1:9091")

    _requester.send_json(data)
    res = jsonify(_requester.recv_json())
    _requester.close()
    context.term()
    res.headers.add('Access-Control-Allow-Origin', '*')
    return res


@app.route("/adjust_color", methods=["GET"])
def adjust_color_route():
    context = zmq.Context()
    _requester = context.socket(zmq.REQ)
    _requester.connect("tcp://127.0.0.1:9091")

    print(request.args.get('attribute'))
    print(request.args.get('channel'))
    print(request.args.get('value'))

    data = {
        "version": "0.1.0",
        "command": "adjust_color",
        "attribute": request.args.get('attribute'),
        "channel": request.args.get('channel'),
        "value": request.args.get("value", type=float),
    }
    _requester.send_json(data)
    res = jsonify(_requester.recv_jsosn())
    _requester.close()
    context.term()
    res.headers.add('Access-Control-Allow-Origin', '*')
    return res


@app.route("/delete/<id_>", methods=["GET"])
def delete_route(id_):
    os.remove(os.path.join(
        app.config['UPLOAD_FOLDER'], filename_from_id(int(id_))))
    res = jsonify({
        "version": "0.1.0",
        "message": "info",
        "content": [
            f"You deleted {id_}"
        ]
    })
    res.headers.add('Access-Control-Allow-Origin', '*')
    return res
