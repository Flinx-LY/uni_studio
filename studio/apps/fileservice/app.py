#!flask/bin/python

# Author: Ngo Duy Khanh
# Email: ngokhanhit@gmail.com
# Git repository: https://github.com/ngoduykhanh/flask-file-uploader
# This work based on jQuery-File-Upload which can be found at https://github.com/blueimp/jQuery-File-Upload/

import os
import PIL, re
from PIL import Image
import simplejson
import traceback

from flask import Flask, Blueprint, request, current_app, render_template, redirect, url_for, send_from_directory, g
from flask_bootstrap import Bootstrap
from werkzeug.utils import secure_filename

from .libs.upload_file import uploadfile

app = Blueprint("fileservice", __name__, template_folder='templates', static_folder='static')

ALLOWED_EXTENSIONS = set(['txt', 'gif', 'png', 'jpg', 'jpeg', 'bmp', 'rar', 'zip', '7zip', 'doc', 'docx'])
IGNORED_FILES = set(['.gitignore'])


def allowed_file(filename):
    return True
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def gen_file_name(filename):
    """
    If file was exist already, rename it and return a new name
    """

    i = 1
    while os.path.exists(os.path.join(current_app.config['FILESERVICE_UPLOAD_FOLDER'], filename)):
        name, extension = os.path.splitext(filename)
        filename = '%s_%s%s' % (name, str(i), extension)
        i += 1

    return filename


def get_dir_name(uid):
    dir_name = os.path.join(current_app.config['FILESERVICE_UPLOAD_FOLDER'], uid)
    if not os.path.isdir(dir_name):
        os.makedirs(dir_name)
        thumbnail_dir = os.path.join(current_app.config['FILESERVICE_THUMBNAIL_FOLDER'], uid)
        os.makedirs(thumbnail_dir)
        print('created dir', dir_name)
    else:
        print('dir exists.')
    return dir_name


def create_thumbnail(image):
    try:
        base_width = 80
        img = Image.open(os.path.join(current_app.config['FILESERVICE_UPLOAD_FOLDER'], str(g.user.id), image))
        w_percent = (base_width / float(img.size[0]))
        h_size = int((float(img.size[1]) * float(w_percent)))
        img = img.resize((base_width, h_size), PIL.Image.ANTIALIAS)
        img.save(os.path.join(current_app.config['FILESERVICE_THUMBNAIL_FOLDER'], str(g.user.id), image))

        return True

    except:
        print(traceback.format_exc())
        return False


@app.route("/upload", methods=['GET', 'POST'])
def upload():
    def filename_filter(s):
        return re.sub('[\/:*?"<>|]', '-', s)

    if request.method == 'POST':
        files = request.files['file']

        if files:

            #filename = secure_filename(files.filename)
            filename = filename_filter(files.filename)
            filename = gen_file_name(filename)
            mime_type = files.content_type

            if not allowed_file(files.filename):
                result = uploadfile(name=filename, type=mime_type, size=0, not_allowed_msg="File type not allowed")

            else:
                # save file to disk
                uploaded_file_path = os.path.join(current_app.config['FILESERVICE_UPLOAD_FOLDER'], str(g.user.id),
                                                  filename)
                files.save(uploaded_file_path)
                os.chmod(uploaded_file_path, 0o666)

                # create thumbnail after saving
                if mime_type.startswith('image'):
                    create_thumbnail(filename)

                # get file size after saving
                size = os.path.getsize(uploaded_file_path)

                # return json for js call back
                result = uploadfile(name=filename, type=mime_type, size=size)

            return simplejson.dumps({"files": [result.get_file()]})

    if request.method == 'GET':
        # get all file in ./data directory
        files = [f for f in os.listdir(os.path.join(current_app.config['FILESERVICE_UPLOAD_FOLDER'],str(g.user.id)))\
                 if os.path.isfile(os.path.join(current_app.config['FILESERVICE_UPLOAD_FOLDER'],str(g.user.id),f)) \
                     and f not in IGNORED_FILES ]

        file_display = []

        for f in files:
            size = os.path.getsize(os.path.join(current_app.config['FILESERVICE_UPLOAD_FOLDER'], str(g.user.id), f))
            file_saved = uploadfile(name=f, size=size)
            file_display.append(file_saved.get_file())

        return simplejson.dumps({"files": file_display})

    return redirect(url_for('index'))


@app.route("/delete/<string:filename>", methods=['DELETE'])
def delete(filename):
    file_path = os.path.join(current_app.config['FILESERVICE_UPLOAD_FOLDER'], str(g.user.id), filename)
    file_thumb_path = os.path.join(current_app.config['FILESERVICE_THUMBNAIL_FOLDER'], str(g.user.id), filename)

    if os.path.exists(file_path):
        try:
            os.remove(file_path)

            if os.path.exists(file_thumb_path):
                os.remove(file_thumb_path)

            return simplejson.dumps({filename: 'True'})
        except:
            return simplejson.dumps({filename: 'False'})


# serve static files
@app.route("/thumbnail/<string:filename>", methods=['GET'])
def get_thumbnail(filename):
    return send_from_directory(os.path.join(current_app.config['FILESERVICE_THUMBNAIL_FOLDER'], str(g.user.id)),
                               filename=filename)


@app.route("/data/<string:filename>", methods=['GET'])
def get_file(filename):
    return send_from_directory(os.path.join(current_app.config['FILESERVICE_UPLOAD_FOLDER'], str(g.user.id)),
                               filename=filename)


@app.route('/', methods=['GET', 'POST'])
def index():
    get_dir_name(str(g.user.id))
    return render_template('fileservice_index.html')
