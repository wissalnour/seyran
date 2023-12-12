from flask import Flask, request, redirect, render_template, send_from_directory
import logging
import os
from azure.storage.blob import BlobServiceClient
from flask import Flask, request, redirect
from azure.cognitiveservices.vision.customvision.training import CustomVisionTrainingClient
import requests

app = Flask(__name__)
connect_str = os.getenv('AZURE_STORAGE_CONNECTION_STRING')  # retrieve the connection string from the environment variable
container_name = "photos"  # container name in which images will be stored in the storage account
blob_service_client = BlobServiceClient.from_connection_string(conn_str=connect_str)

try:
    container_client = blob_service_client.get_container_client(
        container=container_name)  # get container client to interact with the container in which images will be stored
    container_client.get_container_properties()  # get properties of the container to force exception to be thrown if container does not exist
except Exception as e:
    container_client = blob_service_client.create_container(container_name)

# Azure Custom Vision configuration
endpoint = "https://westeurope.api.cognitive.microsoft.com/"
training_key = "35f13ca622044df0849a1191b52b0fac"
project_id = "cdcbd1eb-8682-42e0-bff8-408c3f4479d6"
published_model_name = "3ab5b43b-3606-44ab-84f1-7c57dc47617f"
prediction_endpoint = "https://westeurope.api.cognitive.microsoft.com/customvision/v3.0/Prediction/cdcbd1eb-8682-42e0-bff8-408c3f4479d6/classify/iterations/Iteration3/url"

Prediction_Key ="4d935f41d3cc40539215268e3f2b9c04"
training_client = CustomVisionTrainingClient(training_key, endpoint)


def classify_image(image_url):
    # Call Custom Vision API to classify the image
    headers = {
        "Content-Type": "application/json",
        "Prediction-Key": "4d935f41d3cc40539215268e3f2b9c04"
    }
    params = {"iterationId": published_model_name}
    data = {"url": image_url}
    try:
        response = requests.post(prediction_endpoint, headers=headers, params=params, json=data)
        response.raise_for_status()  # Raise HTTPError for bad responses
        prediction_results = response.json()

          # Print the entire response for debugging
        print(f"Full response for {image_url}: {prediction_results}")
        # Vérifiez si le champ 'predictions' est présent dans la réponse
        if 'predictions' in prediction_results:
            return prediction_results
        else:
            print("Error: 'predictions' field is missing in the response.")
            return None
    except Exception as e:
        print("Error in classify_image:", e)
        return None


@app.route("/")
def view_photos():
    logging.info("Endpoint view_photos a été atteint.")
    blob_items = container_client.list_blobs()  # list all the blobs in the container

    img_html = "<div style='display: flex; justify-content: space-between; flex-wrap: wrap;'>"

    for blob in blob_items:
        blob_client = container_client.get_blob_client(blob=blob.name)  # get blob client to interact with the blob and get blob url
        img_html += "<img src='{}' width='auto' height='200' style='margin: 0.5em 0;'/>".format(
            blob_client.url)  # get the blob url and append it to the html

    img_html += "</div>"

    # Add a link to the classification page
    img_html += "<p><a href='/classify-photos'>View Classification</a></p>"

    # return the html with the images
    return """
    <html>
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
                        <form method="post" action="/upload-photos" enctype="multipart/form-data">
                            <div style="display: flex;">
                                <input type="file" accept=".png, .jpeg, .jpg, .gif" name="photos" multiple class="form-control" style="margin-right: 1em;">
                                <input type="submit" class="btn btn-primary">
                            </div>
                        </form>
                    </div>
                </div>
            """ + img_html + "</div></body></html>"


# flask endpoint to upload a photo
@app.route("/upload-photos", methods=["POST"])
def upload_photos():
    filenames = ""

    for file in request.files.getlist("photos"):
        try:
            container_client.upload_blob(file.filename, file)  # upload the file to the container using the filename as the blob name
            filenames += file.filename + "<br /> "
        except Exception as e:
            print(e)
            print("Ignoring duplicate filenames")  # ignore duplicate filenames

    return redirect('/')


# Ajoutez cette route pour "/classify-photos"
@app.route("/classify-photos", methods=["GET"])
def classify_photos():
    try:
        blob_items = container_client.list_blobs()
        results = []

        for blob in blob_items:
            blob_client = container_client.get_blob_client(blob=blob.name)
            image_url = blob_client.url
            print(f"Processing {blob.name} - {image_url}")
            prediction_results = classify_image(image_url)

            if prediction_results is not None:
                print(f"Prediction results for {blob.name}: {prediction_results}")
                if 'predictions' in prediction_results:
                    results.append((blob.name, prediction_results))
                else:
                    print(f"Error: 'predictions' field is missing in the response for {blob.name}")
            else:
                print(f"Error: No prediction results for {blob.name}")

        # Inline HTML for classification results
        classification_html = "<html><head></head><body><h1>Classification Results</h1>"

        for filename, predictions in results:
            classification_html += f"<h2>{filename}</h2><ul>"
            for prediction in predictions["predictions"]:
                classification_html += f"<li>{prediction['tagName']}: {prediction['probability']}</li>"
            classification_html += "</ul>"

        classification_html += "</body></html>"

        # Return the classification results as the response
        return classification_html

    except Exception as e:
        # Log the exception for debugging purposes
        print("Error in classify_photos:", e)
        # Return an error message with details to the client
        return f"An error occurred while processing the classification request. Details: {str(e)}"


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
