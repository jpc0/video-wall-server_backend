import os
import json
from flask import Flask, request, redirect, send_from_directory
from werkzeug.utils import secure_filename


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
        print(f"{i} is here")
        if not (i.file_path in all_files_list):
            all_files.remove(i)


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def filename_from_id(id: int):
    global all_files
    print(all_files)
    for i in all_files:
        print(f"Comparing {i.id} to {id}")
        if i.id == id:
            return i.file_path


@app.route("/")
def default_route():
    return f"Video wall server"


@app.route("/upload", methods=["POST"])
def upload_route():
    if 'file' not in request.files:
        return json.dumps({
            "version": "0.1.0",
            "message": "info",
            "content": [
                "No file submitted"
            ]
        })
    file = request.files['file']
    # If the user does not select a file, the browser submits an
    # empty file without a filename.
    if file.filename == '':
        return json.dumps({
            "version": "0.1.0",
            "message": "info",
            "content": [
                "No file selected"
            ]
        })
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return json.dumps({
            "version": "0.1.0",
            "message": "info",
            "content": [
                "Success"
            ]
        })

    return json.dumps({
        "version": "0.1.0",
        "message": "info",
        "content": [
            "Invalid file type submitted"
        ]
    })


@app.route("/get_all", methods=["GET"])
def get_all_route():
    update_all_files()
    if all_files:
        return json.dumps({
            "version": "0.1.0",
            "message": "all_files",
            "content": list(map(lambda i: dict(i), all_files))
        })
    else:
        return json.dumps({
            "version": "0.1.0",
            "message": "info",
            "content": [
                "No Files uploaded"
            ]
        })


@app.route("/get/<id>", methods=["GET"])
def get_route(id):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename_from_id(int(id)))


@ app.route("/display/<id>", methods=["POST"])
def display_route(id):
    return f"You display {id}"


@ app.route("/delete/<id>", methods=["DELETE"])
def delete_route(id):
    os.remove(os.path.join(
        app.config['UPLOAD_FOLDER'], filename_from_id(int(id))))
    return json.dumps({
        "version": "0.1.0",
        "message": "info",
        "content": [
            f"You deleted {id}"
        ]
    })
