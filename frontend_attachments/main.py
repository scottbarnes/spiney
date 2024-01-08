import os
from typing import Final

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from models import Attachment, get_db_session

USER: Final = os.environ.get("ART_USERNAME", "")
PASSWORD: Final = os.environ.get("ART_PASSWORD", "")

app = FastAPI()
security = HTTPBasic()

app.mount("/static", StaticFiles(directory="static"), name="static")


def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = USER
    correct_password = PASSWORD

    if credentials.username == correct_username and credentials.password == correct_password:
        return credentials.username
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )


@app.get("/")
async def root(username: str = Depends(verify_credentials)):
    return FileResponse("static/index.html")


@app.get("/attachments/", dependencies=[Depends(verify_credentials)])
async def read_attachments(skip: int = 0, limit: int = 10, db: Session = Depends(get_db_session)):
    return db.query(Attachment).order_by(Attachment.created.desc()).offset(skip).limit(limit).all()
