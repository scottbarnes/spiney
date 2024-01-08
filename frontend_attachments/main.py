from fastapi import Depends, FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from models import Attachment, get_db_session

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    return FileResponse("static/index.html")


@app.get("/attachments/")
async def read_attachments(skip: int = 0, limit: int = 10, db: Session = Depends(get_db_session)):
    return db.query(Attachment).order_by(Attachment.created.desc()).offset(skip).limit(limit).all()
