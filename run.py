#!flask/bin/python
from app import app 
from app import modules

if __name__ == "__main__":
    MOD = modules.Modules()
    print(MOD)
    app.run(debug=True)
