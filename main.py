import face_recognition
import cv2
from flask import Flask, Response
import os
import time
import threading

app = Flask(__name__)

# Load images from the folder and encode face embeddings
known_faces = []
known_names = []
attendance_record = {}  # Record attendance for each recognized face
folder_path = 'Images'
for image_name in os.listdir(folder_path):
    image_path = os.path.join(folder_path, image_name)
    img = face_recognition.load_image_file(image_path)
    encoding = face_recognition.face_encodings(img)[0]
    known_faces.append(encoding)
    known_names.append(os.path.splitext(image_name)[0])  # Extract file name without extension
    attendance_record[known_names[-1]] = False  # Initialize attendance record to False

# Function to generate video frames with face recognition
def gen_frames():
    cap = cv2.VideoCapture(0)  # Use camera index 1 for the external camera
    fps = cap.get(cv2.CAP_PROP_FPS)
    process_frame_rate = 1  # Process every 5th frame
    frame_count = 0
    start_time = time.time()

    while True:
        success, frame = cap.read()
        if not success:
            break
        else:
            frame_count += 1
            if frame_count % process_frame_rate == 0:
                # Resize frame for faster processing
                small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
                rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

                # Detect faces and face encodings
                face_locations = face_recognition.face_locations(rgb_small_frame)
                face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

                # Match faces and draw rectangles
                for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                    matches = face_recognition.compare_faces(known_faces, face_encoding)
                    name = "Unknown"
                    if True in matches:
                        first_match_index = matches.index(True)
                        name = known_names[first_match_index]

                    # Check attendance record and adjust rectangle color
                    if not attendance_record[name]:
                        rectangle_color = (0, 255, 0)  # Green for first-time recognition
                        attendance_record[name] = True
                        print(f"{name} is present!")
                    else:
                        rectangle_color = (147, 20, 255)  # Pink for subsequent recognitions
                        print(f"---------{name} is already present!")

                    # Scale back up face locations since the frame we detected in was scaled to 1/2 size
                    top *= 2
                    right *= 2
                    bottom *= 2
                    left *= 2

                    cv2.rectangle(frame, (left, top), (right, bottom), rectangle_color, 2)
                    cv2.putText(frame, name, (left + 6, bottom - 6), cv2.FONT_HERSHEY_DUPLEX, 0.5, rectangle_color, 1)

            elapsed_time = time.time() - start_time
            fps = frame_count / elapsed_time
            cv2.putText(frame, f"FPS: {fps:.2f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)

            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image\jpeg\r\n\r\n' + frame + b'\r\n')

# Route for streaming video with face recognition
@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

# Main function
if __name__ == '__main__':
    app.run(debug=True)