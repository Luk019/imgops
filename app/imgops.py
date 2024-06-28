import os
from   flask import Flask, request
import flask

from PIL import Image
import io

app = Flask(__name__)

config = {
    'filedir': os.path.join(os.curdir, 'files')
}

# Statyczna informacja o aplikacji 
@app.route('/')
def root():
    return "Sample REST API image application!"



# Zmiana zawartości pliku
@app.route('/rotate/<angle>', methods = ['POST'])
def img_rotate(angle):
    buf = request.get_data(as_text=False)
    format = request.mimetype.split("/")[1]
    img = Image.open(io.BytesIO(buf))
    #img = Image.frombytes(mode="L", size=(1500, 500), data=buf, )
    

    memfile = io.BytesIO()
    img.rotate(angle=int(angle), expand=True).save(memfile, format="png")
    memfile.seek(0, io.SEEK_SET)
    return flask.send_file(memfile, mimetype="image/png")
    
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', '8080')), debug=True)
        