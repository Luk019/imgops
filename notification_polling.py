#!/usr/bin/env python

import argparse
import json
import time
import os
import subprocess
from google.cloud import pubsub_v1, storage

def summarize(message):
    data = message.data.decode("utf-8")
    attributes = message.attributes

    event_type = attributes["eventType"]
    bucket_id = attributes["bucketId"]
    object_id = attributes["objectId"]
    generation = attributes["objectGeneration"]
    description = (
        "\tEvent type: {event_type}\n"
        "\tBucket ID: {bucket_id}\n"
        "\tObject ID: {object_id}\n"
        "\tGeneration: {generation}\n"
    ).format(
        event_type=event_type,
        bucket_id=bucket_id,
        object_id=object_id,
        generation=generation,
    )

    if "overwroteGeneration" in attributes:
        description += f"\tOverwrote generation: {attributes['overwroteGeneration']}\n"
    if "overwrittenByGeneration" in attributes:
        description += f"\tOverwritten by generation: {attributes['overwrittenByGeneration']}\n"

    payload_format = attributes["payloadFormat"]
    if payload_format == "JSON_API_V1":
        object_metadata = json.loads(data)
        size = object_metadata["size"]
        content_type = object_metadata["contentType"]
        metageneration = object_metadata["metageneration"]
        description += (
            "\tContent type: {content_type}\n"
            "\tSize: {object_size}\n"
            "\tMetageneration: {metageneration}\n"
        ).format(
            content_type=content_type,
            object_size=size,
            metageneration=metageneration,
        )
    return description

def download_image(bucket_name, source_blob_name, destination_file_name):
    """Downloads a blob from the bucket."""
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(source_blob_name)
    blob.download_to_filename(destination_file_name)

    print(f"Blob {source_blob_name} downloaded to {destination_file_name}.")

def send_to_cloud_run(local_image_path, local_rotated_image_path, rotation_angle):
    """ Send image to Cloud Run for rotation. """
    service_url = "https://image-transform-dwyfq6br7q-lz.a.run.app/rotate"

    # Example using subprocess to call curl for sending image to Cloud Run
    subprocess.run(["curl", "-X", "POST", "-H", "Content-Type: image/png",
                    "--data-binary", f"@{local_image_path}",
                    f"{service_url}/{rotation_angle}",
                    "-o", local_rotated_image_path])

def process_image(message):
    data = message.data.decode("utf-8")
    attributes = message.attributes
    event_type = attributes["eventType"]
    bucket_id = attributes["bucketId"]
    object_id = attributes["objectId"]
    generation = attributes["objectGeneration"]
    
    if event_type == "OBJECT_FINALIZE":
        image_name = object_id.split("/")[-1]
        local_image_path = f"/tmp/{image_name}"
        local_rotated_image_path = f"/home/ul0190828/rotated_{image_name}"
    
        try:
            # Step 1: Read from storage
            download_image(bucket_id, object_id, local_image_path)
            
            # Step 2: Get metadata from Cloud Storage
            storage_client = storage.Client()
            bucket = storage_client.bucket(bucket_id)
            blob = bucket.blob(object_id)
            blob.reload()  # Reload the blob to get the latest metadata

            print(f"Metadata: {blob.metadata}")

            custom_fields = blob.metadata

            if custom_fields and "rotation-angle" in custom_fields:
                rotation_angle = custom_fields["rotation-angle"]
                print(f"Rotation angle: {rotation_angle}")
            else:
                print(f"No rotation angle found for {image_name}. Using default 90.")
                rotation_angle = 90

            if custom_fields and "output-path" in custom_fields:
                output_path = custom_fields["output-path"]
                local_rotated_image_path = os.path.join(output_path, f"rotated_{image_name}")
                print(f"Output path: {output_path}")
            else:
                print(f"No output path found for {image_name}. Using default path.")
                local_rotated_image_path = f"/home/ul0190828/rotated_{image_name}"
                
            # Step 3: Send to Google Run
            send_to_cloud_run(local_image_path, local_rotated_image_path, rotation_angle)
    
            # Step 4: Save image on disk
            print(f"Rotated image saved to {local_rotated_image_path}.")
            
            # Potwierdź odbiór wiadomości Pub/Sub
            message.ack()
            
        except Exception as e:
            print(f"Error processing image {image_name}: {e}")

def poll_notifications(project, subscription_name):
    """Polls a Cloud Pub/Sub subscription for new GCS events for display."""
    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(
        project, subscription_name
    )

    def callback(message):
        print(f"Received message:\n{summarize(message)}")
        process_image(message)
        message.ack()

    subscriber.subscribe(subscription_path, callback=callback)

    # The subscriber is non-blocking, so we must keep the main thread from
    # exiting to allow it to process messages in the background.
    print(f"Listening for messages on {subscription_path}")
    while True:
        time.sleep(60)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "project", help="The ID of the project that owns the subscription"
    )
    parser.add_argument(
        "subscription", help="The ID of the Pub/Sub subscription"
    )
    args = parser.parse_args()
    poll_notifications(args.project, args.subscription)
