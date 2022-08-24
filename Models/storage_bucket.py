from firebase_admin import storage


def upload_blob_from_memory(file_name, blob_name,):
    """Uploads a file to the bucket, potentially for uploading image evidence"""
    bucket = storage.bucket()
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(file_name)
    print("Success! ", blob.public_url)
