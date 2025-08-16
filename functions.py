import requests
import cv2

def get_result(lp_crop):
    _, img_encoded = cv2.imencode('.jpg', lp_crop)
    url = "https://e820815ef5f5.ngrok-free.app/ocr"
    files = {'image': img_encoded}
    response = requests.post(url, files = files)
    try:
        data = response.json()  # parse JSON
        return data.get('OCR result')  # safely get the value
    except Exception as e:
        print("Error parsing JSON:", e)
        print("Response text:", response.text)
        return None
