import time
import requests
import base64
from flask import Flask, jsonify, request, render_template
import os
from pymongo import MongoClient
from bson.objectid import ObjectId
app = Flask(__name__)

client = MongoClient('mongodb://localhost:27017/')  # Update with your MongoDB URI
db = client['photo_rating_db']  # Replace with your database name
collection = db['ratings'] 

@app.route('/')
def home():
    image_data = fetch_image()
    return render_template('index.html', image_data=image_data['images'], image_id=image_data['ids'])

def fetch_image():
    image_url = "https://thispersondoesnotexist.com"  # Resim URL'si
    images = []
    ids = []
    for i in range(4):
        response = requests.get(image_url)
        base64_image = base64.b64encode(response.content).decode('utf-8')
        
        # Save image to tmp folder with unique name
        os.makedirs('tmp', exist_ok=True)
        timestamp = str(int(time.time() * 1000))  # Millisecond timestamp
        unique_filename = f'image_{timestamp}.png'
        tmp_path = os.path.join('tmp', unique_filename)
        
        with open(tmp_path, 'wb') as f:
            f.write(response.content)
            
        # Save image info to photos collection
        photos = db['photos']
        photo_id = photos.insert_one({
            "filename": unique_filename,
            "path": tmp_path,
            "timestamp": timestamp
        }).inserted_id
        ids.append(str(photo_id))
        images.append(f"data:image/jpeg;base64,{base64_image}")
    return {
        "images": images,
        "ids": ids
    }
@app.route('/fetch-image', methods=['GET'])
def get_image():
    try:
        image_data = fetch_image()
        return jsonify(image_data)
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500

@app.route('/submit-rating', methods=['POST'])
def submit_rating():
    data = request.json
    for key, value in data.items():
        rating = value.get("rating")
        if rating is not None:
            collection.insert_one({
                "photo_id": key,
                "rating": rating
            })
            # Get image info from photos collection
            photos = db['photos']
            photo = photos.find_one({"_id": ObjectId(key)})
            
            if photo:
                # Create dataset folder if it doesn't exist
                os.makedirs('dataset', exist_ok=True)
                
                # Move file from tmp to dataset
                src_path = photo['path']
                dst_path = os.path.join('dataset', photo['filename'])
                
                if os.path.exists(src_path):
                    os.rename(src_path, dst_path)
                    
                    # Update path in database
                    photos.update_one(
                        {"_id": ObjectId(key)},
                        {"$set": {"path": dst_path}}
                    )

    return jsonify({"message": "Rating received successfully"}), 200

if __name__ == '__main__':
    app.run(debug=True)
