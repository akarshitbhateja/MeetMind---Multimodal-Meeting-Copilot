import os
import shutil
import whisper
import google.generativeai as genai
import motor.motor_asyncio
import traceback
import uuid
import httpx
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from datetime import datetime
from pydantic import BaseModel
from typing import List
from bson import ObjectId

# --- INITIAL SETUP & CONNECTIONS ---
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
MONGO_CONNECTION_STRING = os.getenv("MONGO_CONNECTION_STRING")
PABBLY_WEBHOOK_URL = os.getenv("PABBLY_WEBHOOK_URL")
TEMP_DIR = "/tmp" # Vercel uses a /tmp directory for temporary files

if not all([GOOGLE_API_KEY, MONGO_CONNECTION_STRING, PABBLY_WEBHOOK_URL]):
    raise ValueError("One or more environment variables are missing.")

# --- DATABASE & AI MODEL SETUP ---
client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_CONNECTION_STRING)
db = client.meetmind_db
post_meeting_collection = db.get_collection("post_meetings")
pre_meeting_collection = db.get_collection("pre_meetings")

whisper_model = whisper.load_model("tiny") # Using 'tiny' for speed on Vercel's free tier
genai.configure(api_key=GOOGLE_API_KEY)
gemini_model = genai.GenerativeModel('gemini-2.5-pro')

app = FastAPI()
# Add CORS middleware to allow all origins for simplicity in deployment
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DATA MODELS ---
class ReminderRequest(BaseModel): title: str; startTime: str; endTime: str; message: str; attendees: List[str]
class LinkUpdateRequest(BaseModel): meetingId: str; hangoutLink: str

# --- API ENDPOINTS ---
@app.get("/api")
def read_root(): return {"status": "MeetMind Backend is operational."}

@app.post("/api/schedule-reminder")
async def schedule_reminder(request: ReminderRequest):
    new_meeting = {"title": request.title, "startTime": request.startTime, "hangoutLink": None, "created_at": datetime.utcnow()}
    result = await pre_meeting_collection.insert_one(new_meeting)
    meeting_id = str(result.inserted_id)
    try:
        payload = {"meeting_id": meeting_id, "meeting_title": request.title, "start_.time": request.startTime, "end_time": request.endTime, "meeting_message": request.message, "attendee_emails": ", ".join(request.attendees)}
        async with httpx.AsyncClient() as client: webhook_response = await client.post(PABBLY_WEBHOOK_URL, json=payload, timeout=30.0)
        webhook_response.raise_for_status()
        return {"message": "Reminder request sent! Polling for meeting link...", "meetingId": meeting_id}
    except Exception as e:
        await pre_meeting_collection.delete_one({"_id": result.inserted_id})
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@app.post("/api/update-meeting-link")
async def update_meeting_link(request: LinkUpdateRequest):
    result = await pre_meeting_collection.update_one({"_id": ObjectId(request.meetingId)}, {"$set": {"hangoutLink": request.hangoutLink}})
    if result.modified_count == 1: return {"status": "success"}
    raise HTTPException(status_code=404, detail="Meeting ID not found.")

@app.get("/api/get-meeting-link/{meeting_id}")
async def get_meeting_link(meeting_id: str):
    meeting = await pre_meeting_collection.find_one({"_id": ObjectId(meeting_id)})
    if meeting: return {"hangoutLink": meeting.get("hangoutLink")}
    raise HTTPException(status_code=404, detail="Meeting not found.")

@app.post("/api/transcribe-and-summarize")
async def transcribe_and_summarize(file: UploadFile = File(...)):
    temp_file_path = os.path.join(TEMP_DIR, f"{uuid.uuid4()}_{file.filename}")
    try:
        with open(temp_file_path, "wb") as buffer: shutil.copyfileobj(file.file, buffer)
        transcript_text = whisper_model.transcribe(temp_file_path, fp16=False)["text"]
        if not transcript_text.strip(): raise ValueError("Audio could not be transcribed or is empty.")
        prompt = f"Summarize this transcript and list all action items:\n---\n{transcript_text}"
        response = gemini_model.generate_content(prompt)
        summary_text = response.text
        meeting_data = {"filename": file.filename, "upload_timestamp": datetime.utcnow(), "transcript": transcript_text, "summary": summary_text}
        await post_meeting_collection.insert_one(meeting_data)
        return {"transcript": transcript_text, "summary": summary_text}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An internal server error occurred: {str(e)}")
    finally:
        if os.path.exists(temp_file_path): os.remove(temp_file_path)

@app.get("/api/meetings")
async def get_all_meetings():
    meetings = []
    helper = lambda m: {"id": str(m["_id"]), "filename": m["filename"], "upload_timestamp": m["upload_timestamp"], "transcript": m["transcript"], "summary": m["summary"]}
    async for meeting in post_meeting_collection.find().sort("upload_timestamp", -1).limit(20):
        meetings.append(helper(meeting))
    return meetings