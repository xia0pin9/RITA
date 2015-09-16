from app import app
from flask import Flask, jsonify, request
from registry import Registry
import json

R = Registry()

@app.route('/api/v1.0/modules/list', methods=['GET'])
def get_modules_list():
    mlist = []
    for m in R.GetModules():
        mlist.append({
            "name": m.name,
            "description": m.description,
            "id": m.id,
            "options": m.options
            })
    return jsonify({'modules': mlist})

@app.route('/api/v1.0/module/<int:module_id>/set', methods=['POST'])
def set_option(module_id):
    if not request.json:
        return jsonify({'success': False, 'reason': "I was expecting json."})
    
    dat = request.json 
    for k in dat:
        if R.GetModules()[module_id].SetOption(k, dat[k]):
            print("Successfully set option ", k)
        else:
            print("Failed to set option ", k)

    return jsonify({'success': True})


## TODO: How do we deal with imports?
#@app.route('/api/v1.0/import/list', methods=['GET'])
#def get_import_list():
#    dirs = [name for name in os.listdir(Settings.import_dir)
#            if os.path.isdir(os.path.join(Settings.import_dir, name))]
#    return jsonify({'import': dirs})

