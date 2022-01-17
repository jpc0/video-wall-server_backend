import time
import os
import json
from urllib import response
from flask import Flask, Response, request, redirect, send_from_directory, jsonify
from werkzeug.utils import secure_filename
import zmq


UPLOAD_FOLDER = '/srv/video_wall_server_images/'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
all_files_list = os.listdir(app.config['UPLOAD_FOLDER'])


class image_file_data:
    id: int
    file_path: str

    def __init__(self, id: int, file_path: str) -> None:
        self.id = id
        self.file_path = file_path

    def __iter__(self):
        for key in self.__dict__:
            yield key, getattr(self, key)


all_files: list[image_file_data] = []


def image_in_list(image: str) -> bool:
    global all_files
    for i in all_files:
        if image == i.file_path:
            return True
    return False


def update_all_files():
    global all_files, all_files_list
    all_files_list = os.listdir(app.config['UPLOAD_FOLDER'])
    for i in all_files_list:
        if image_in_list(i):
            continue
        all_files.append(image_file_data(all_files_list.index(i)+1, i))
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
        response = jsonify({
            "version": "0.1.0",
            "message": "info",
            "content": [
                "No file submitted"
            ]
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
    file = request.files['file']
    # If the user does not select a file, the browser submits an
    # empty file without a filename.
    if file.filename == '':
        response = jsonify({
            "version": "0.1.0",
            "message": "info",
            "content": [
                "No file selected"
            ]
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        response = jsonify({
            "version": "0.1.0",
            "message": "info",
            "content": [
                "Success"
            ]
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response

    response = jsonify({
        "version": "0.1.0",
        "message": "info",
        "content": [
            "Invalid file type submitted"
        ]
    })
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response


@app.route("/get_all", methods=["GET"])
def get_all_route():
    update_all_files()
    if all_files:
        response = jsonify({
            "version": "0.1.0",
            "message": "all_files",
            "content": list(map(lambda i: dict(i), all_files))
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
    else:
        response = jsonify({
            "version": "0.1.0",
            "message": "info",
            "content": [
                "No Files uploaded"
            ]
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response


@app.route("/get/<filename>", methods=["GET"])
def get_route(filename):
    response = send_from_directory(
        app.config["UPLOAD_FOLDER"], filename)
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response


@app.route("/display/<id>", methods=["GET"])
def display_route(id):
    context = zmq.Context()
    _requester = context.socket(zmq.REQ)
    _requester.connect("tcp://127.0.0.1:9091")
    data = {
        "version": "0.1.0",
        "command": "display_image",
        "location": f"{UPLOAD_FOLDER}{filename_from_id(int(id))}",
    }
    _requester.send_json(data)
    response = jsonify(_requester.recv_json())
    _requester.close()
    context.term()
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response


@app.route("/display_many", methods=["GET"])
def display_many_route():
    context = zmq.Context()
    _requester = context.socket(zmq.REQ)
    _requester.connect("tcp://127.0.0.1:9091")
    data = {
        "version": "0.1.0",
        "command": "display_image_loop",
        "loop_time": request.args.get('time', type=int),
        "locations": [],
    }

    for id in request.args.get('ids').split(','):
        data["locations"].append(f"{UPLOAD_FOLDER}{filename_from_id(int(id))}")
    _requester.send_json(data)
    response = jsonify(_requester.recv_json())
    _requester.close()
    context.term()
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response


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
    response = jsonify(_requester.recv_jsosn())
    _requester.close()
    context.term()
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response


@app.route("/delete/<id>", methods=["GET"])
def delete_route(id):
    os.remove(os.path.join(
        app.config['UPLOAD_FOLDER'], filename_from_id(int(id))))
    response = jsonify({
        "version": "0.1.0",
        "message": "info",
        "content": [
            f"You deleted {id}"
        ]
    })
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response
