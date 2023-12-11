from flask import Flask, request ,redirect, render_template , send_from_directory
import logging
import os  
from azure.storage.blob import BlobServiceClient
from flask import Flask, request, redirect
from azure.cognitiveservices.vision.customvision.training import CustomVisionTrainingClient
import requests

app = Flask(__name__)  
connect_str = os.getenv('AZURE_STORAGE_CONNECTION_STRING') # retrieve the connection string from the environment variable
container_name = "photos" # container name in which images will be store in the storage account
blob_service_client = BlobServiceClient.from_connection_string(conn_str=connect_str)

try:
    container_client = blob_service_client.get_container_client(container=container_name) # get container client to interact with the container in which images will be stored
    container_client.get_container_properties() # get properties of the container to force exception to be thrown if container does not exist
except Exception as e:
    container_client = blob_service_client.create_container(container_name)
# Azure Custom Vision configuration
endpoint = "https://westeurope.api.cognitive.microsoft.com/"
training_key = "35f13ca622044df0849a1191b52b0fac"
project_id = "cdcbd1eb-8682-42e0-bff8-408c3f4479d6" 
published_model_name = "3ab5b43b-3606-44ab-84f1-7c57dc47617f"

training_client = CustomVisionTrainingClient(training_key, endpoint)
def classify_image(image_url):
    # Call Custom Vision API to classify the image
    headers = {"Content-Type": "application/json"}
    params = {"iterationId": published_model_name}
    data = {"url": image_url}
    prediction_endpoint = f"{endpoint}/customvision/v3.0/training/projects/{project_id}/classify"
    response = requests.post(prediction_endpoint, headers=headers, params=params, json=data)
    prediction_results = response.json()
    return prediction_results

@app.route('/app/<path:filename>')
def app_dir(filename):
    # Ajustez le chemin en fonction de la structure de votre application
    app_path = os.path.join('/home/site/wwwroot', 'app')
    return send_from_directory(azure12, filename)
     
@app.route("/")
def view_photos():
    logging.info("Endpoint view_photos a été atteint.")
    blob_items = container_client.list_blobs() # list all the blobs in the container

    img_html = "<div style='display: flex; justify-content: space-between; flex-wrap: wrap;'>"

    for blob in blob_items:
        blob_client = container_client.get_blob_client(blob=blob.name) # get blob client to interact with the blob and get blob url
        img_html += "<img src='{}' width='auto' height='200' style='margin: 0.5em 0;'/>".format(blob_client.url) # get the blob url and append it to the html
   
    img_html += "</div>"

    # return the html with the images
    return """
    <head>
    <!-- CSS only -->
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-1BmE4kWBq78iYhFldvKuhfTAU6auU8tT94WrHftjDbrCEXSU1oBoqyl2QvZ6jIW3" crossorigin="anonymous">
    </head>
    <body>
        <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
            <div class="container">
                <a class="navbar-brand" href="/">Photos App</a>
            </div>
        </nav>
        <div class="container">
            <div class="card" style="margin: 1em 0; padding: 1em 0 0 0; align-items: center;">
                <h3>Upload new File</h3>
                <div class="form-group">
                    <form method="post" action="/upload-photos"
                        enctype="multipart/form-data">
                        <div style="display: flex;">
                            <input type="file" accept=".png, .jpeg, .jpg, .gif" name="photos" multiple class="form-control" style="margin-right: 1em;">
                            <input type="submit" class="btn btn-primary">
                        </div>
                    </form>
                </div>
            </div>
       
    """ + img_html + "</div></body>"
 
#flask endpoint to upload a photo
#flask endpoint to upload a photo
@app.route("/upload-photos", methods=["POST"])
def upload_photos():
    filenames = ""

    for file in request.files.getlist("photos"):
        try:
            container_client.upload_blob(file.filename, file) # upload the file to the container using the filename as the blob name
            filenames += file.filename + "<br /> "
        except Exception as e:
            print(e)
            print("Ignoring duplicate filenames") # ignore duplicate filenames
       
    return redirect('/') 
@app.route("/classify-photos", methods=["GET"])
def classify_photos():
    blob_items = container_client.list_blobs()
    results = []

    for blob in blob_items:
        blob_client = container_client.get_blob_client(blob=blob.name)
        image_url = blob_client.url

        prediction_results = classify_image(image_url)
        results.append((blob.name, prediction_results))

        # Inline HTML for classification results
    classification_html = "<h1>Classification Results</h1>"
    for filename, predictions in results:
        classification_html += f"<h2>{filename}</h2><ul>"
        for prediction in predictions["predictions"]:
            classification_html += f"<li>{prediction['tagName']}: {prediction['probability']}</li>"
        classification_html += "</ul>"

    return classification_html
if __name__=="__main__":
    app.run(debug=True, host="0.0.0.0",port=5000 )