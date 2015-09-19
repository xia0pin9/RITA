from app import app
from flask import Flask, jsonify, request, make_response
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
            "options": m.GetOptions()
            })
    return make_response(json.dumps(mlist))

@app.route('/api/v1.0/importers/list', methods=['GET'])
def get_importers_list():
    ilist = []
    for i in R.GetImporters():
        ilist.append({
            "name": i.name,
            "description": i.description,
            "id": i.id,
            "options": i.GetOptions()
            })
    return jsonify({"importers": ilist})

@app.route('/api/v1.0/module/<int:module_id>/set', methods=['POST'])
def set_module_option(module_id):
    if not request.json:
        print("where's my json yo?")
        return jsonify({'success': False, 'reason': "I was expecting json."})
    
    dat = request.json 
    for k in dat:
        if R.GetModules()[module_id].SetOption(k, dat[k]):
            print("Successfully set option ", k)
        else:
            print("Failed to set option ", k)

    return jsonify({'success': True})

@app.route('/api/v1.0/importer/<int:importer_id>/set', methods=['POST'])
def set_importer_option(importer_id):
    if not request.json:
        return jsonify({'success': False, 'reason': "I was expecting json."})

    for k in request.json:
        if not R.GetImporters()[importer_id].SetOption(k, request.json[k]):
            return jsonify({'success': False})
    return jsonify({'success': True})

@app.route('/api/v1.0/importer/<int:importer_id>/run', methods=['GET'])
def run_importer(importer_id):
    R.GetImporters()[importer_id].Read()
    return

@app.route('/api/v1.0/customer/set', methods=['POST'])
def set_customer():
    if not request.json["customer"]:
        return jsonify({'success': False, 
            'reason': 'I expected json to contain customer'})

    R.SetGlobal("customer", request.json["customer"])
    return jsonify({'success': True})

@app.route('/api/v1.0/esserver/set', methods=['POST'])
def set_server():
    if not request.json["server"]:
        return jsonify({'success': False, 
            'reason': 'I expected json to contain server'})
    R.SetGlobal("server", request.json["server"])
    return jsonify({'success': True})

## TODO: How do we deal with imports?
#@app.route('/api/v1.0/import/list', methods=['GET'])
#def get_import_list():
#    dirs = [name for name in os.listdir(Settings.import_dir)
#            if os.path.isdir(os.path.join(Settings.import_dir, name))]
#    return jsonify({'import': dirs})

