import cv2
import pytesseract
import csv
import os
from google.cloud import vision
from google.cloud import vision_v1

# Set Tesseract path conditionally based on the operating system
if os.name == 'nt':  # If running on Windows
    pytesseract.pytesseract.tesseract_cmd = r'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'
elif platform.system() == 'Linux':  # If running on Linux (e.g., inside Docker)
    pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'
else:
    raise OSError('Unsupported OS: Please configure Tesseract path manually')

def detectText(content):
    """
    Use Google Cloud Vision API to detect text in an image.
    """
    dir_list = os.listdir("./jsonfile")
    if not dir_list:
        raise FileNotFoundError("No credentials file found in './jsonfile' directory.")
    
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = f"./jsonfile/{dir_list[0]}"
    client = vision.ImageAnnotatorClient()
    image = vision.Image(content=content)
    response = client.document_text_detection(image=image)
    texts = response.text_annotations

    # Combine all detected text into a single string
    data = "".join([text.description for text in texts])
    return data

def coTox(img, L_id, name, X, Y, W, H, file_name, page_n, option, dformat):
    """
    Extract text from an image using coordinates.
    """
    if not os.path.exists(img):
        raise FileNotFoundError(f"Image file not found: {img}")

    image = cv2.imread(img, 0)
    thresh = 255 - cv2.threshold(image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    
    # Define region of interest (ROI) based on coordinates
    x = X
    y = Y
    w = W - x
    h = H - y
    ROI = thresh[y:y+h, x:x+w]

    # Extract text based on selected option
    if option == "1":
        data = pytesseract.image_to_string(ROI, lang='eng', config='--psm 6')
    elif option == "2":
        success, image_encoded = cv2.imencode('.png', ROI)
        if not success:
            raise Exception("Failed to encode image")
        content = image_encoded.tobytes()
        data = detectText(content)
    else:
        raise ValueError("Invalid option. Choose '1' for Tesseract or '2' for Google Vision.")
    
    extracted_data = {
        "folder_name": file_name.split("/")[0],
        "filename": file_name,
        "Page_n": page_n,
        "id": L_id,
        "field_name": name,
        "label_data": data,
        "Format": dformat
    }
    return extracted_data

def Main(img_name, file_name, page_n, option):
    """
    Extract text from a PDF file by processing coordinates from a CSV file.
    """
    All_Data = {}
    try:
        with open('out.csv', 'r') as csv_file:
            csv_reader = csv.reader(csv_file)
            header = next(csv_reader)  # Skip header
            for line in csv_reader:
                if img_name == line[0]:
                    try:
                        All_Data[line[1]] = coTox(
                            f"./images/{img_name}",
                            line[1],
                            line[2],
                            int(line[3]),
                            int(line[5]),
                            int(line[4]),
                            int(line[6]),
                            file_name,
                            page_n,
                            option,
                            line[7]
                        )
                    except Exception as e:
                        print(f"Error processing line {line}: {e}")
    except FileNotFoundError as e:
        print(f"CSV file not found: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
    
    return All_Data

def MainImg(img_name, file_name, page_n, option):
    """
    Extract text from image files by processing coordinates from a CSV file.
    """
    All_Data = {}
    try:
        with open('out.csv', 'r') as csv_file:
            csv_reader = csv.reader(csv_file)
            header = next(csv_reader)  # Skip header
            for line in csv_reader:
                try:
                    All_Data[line[1]] = coTox(
                        img_name,
                        line[1],
                        line[2],
                        int(line[3]),
                        int(line[5]),
                        int(line[4]),
                        int(line[6]),
                        file_name,
                        page_n,
                        option,
                        line[7]
                    )
                except Exception as e:
                    print(f"Error processing line {line}: {e}")
    except FileNotFoundError as e:
        print(f"CSV file not found: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
    
    print("Dtaexztract.py -> MainImg", All_Data)
    return All_Data