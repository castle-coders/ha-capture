#!/usr/bin/env python

import time
import asyncws
import asyncio
import json
import requests
import shutil
import os

# host protocol (https or http)
http_proto = os.getenv("HTTP_PROTO") or "https"
# host name or ip for home assistant
host = os.getenv("HOST")
# access token (aka long lived token)
token = os.getenv("TOKEN")
# entity id for motion detected (or any entity that changes state when an image should be captured)
sensor = os.getenv("SENSOR")
# entity id for camera
camera_entity = os.getenv("CAMERA")
# path to write images
output_path = os.getenv("OUTPUT_PATH")
# file suffix, should match format of entity_picture
image_suffix = os.getenv("IMG_SUFFIX") or ".jpg"

headers = {"Content-Type": "application/json", "Authorization" : "Bearer {}".format(token)}

def ha_url(path):
    return '{}://{}{}'.format(http_proto, host, path)
    
async def initSocket():
    websocket = await asyncws.connect('ws://{}/api/websocket'.format(host))

    await websocket.send(json.dumps({'type': 'auth','access_token': token}))
    await websocket.send(json.dumps({'id': 1, 'type': 'subscribe_events', 'event_type': 'state_changed'}))
    
    print("Start socket...")

    while True:
        message = await websocket.recv()
        if message is None:
            break
        
        try:   
            data = json.loads(message)['event']['data']
            entity_id = data['entity_id']
            
            if entity_id == sensor:
                print("{} new state {}".format(entity_id, data['new_state']['state']))
                cam_response = requests.get(ha_url('/api/states/{}'.format(camera_entity)), headers=headers)
                if cam_response.ok:
                    picture_path = cam_response.json()["attributes"]["entity_picture"]
                    picture_response = requests.get(ha_url(picture_path), stream=True)
                    if picture_response.ok:
                        with open('{}{}{}'.format(output_path, int(time.time()), image_suffix), 'wb') as fp:
                            picture_response.raw.decode_content = True
                            shutil.copyfileobj(picture_response.raw, fp)
                    else:
                        print(picture_response)
                else:
                    print(cam_response)
                    
        except Exception:
            pass

async def main(): 
    listen = asyncio.create_task(initSocket()) 
    await listen

if __name__ == "__main__":    
    asyncio.run(main())