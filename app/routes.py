from flask import Flask, jsonify
from app import app

from registry import Registry

R = Registry()

@app.route('/api/v1.0/modules/list', methods=['GET'])
def get_modules_list():
    mlist = []
    for m in R.GetModules():
        mlist.append({
            "name": m.name,
            "description": m.description,
            "options": m.options
            })
    return jsonify({'modules': mlist})

@app.route('/api/v1.0/import/list', methods=['GET'])
def get_import_list():
    dirs = [name for name in os.listdir(Settings.import_dir)
            if os.path.isdir(os.path.join(Settings.import_dir, name))]
    return jsonify({'import': dirs})

