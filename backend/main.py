from fastapi import FastAPI
from fastapi import UploadFile
from fastapi import File
from fastapi import Request
from fastapi import Form
from fastapi import Query

from starlette.middleware.sessions import SessionMiddleware

from fastapi.staticfiles import StaticFiles

from fastapi.responses import RedirectResponse
from fastapi.responses import FileResponse

from fastapi.templating import Jinja2Templates

from database import get_connection

from password_utils import (
    hash_password,
    verify_password
)

import uuid
import shutil
import tempfile
import os
import boto3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

S3_BUCKET = "manoj-file-sharing-platform"

CLOUDFRONT_URL = "https://dmy3tuz6xjjcd.cloudfront.net"

s3 = boto3.client(
    "s3",
    region_name="ap-south-1"
)

app = FastAPI()

app.add_middleware(
    SessionMiddleware,
    secret_key="manoj_secret_key_123"
)

app.mount(
    "/static",
    StaticFiles(directory="../frontend"),
    name="static"
)

templates = Jinja2Templates(
    directory="../frontend/templates"
)


@app.get("/")
def home(
    request: Request,
    success: str = "",
    error: str = "",
    deleted: int = 0,
    search: str = ""
):

    conn = get_connection()
    cursor = conn.cursor()

    user_id = request.session.get(
        "user_id"
    )

    if user_id:

        cursor.execute(
            """
            SELECT
                id,
                filename,
                file_size,
                upload_date,
                is_public
            FROM files
            WHERE
                (
                    is_public = TRUE
                    OR user_id = %s
                )
                AND is_deleted = FALSE
                AND filename LIKE %s
            ORDER BY upload_date DESC
            """,
            (
                user_id,
                f"%{search}%"
            )
        )

    else:

        cursor.execute(
            """
            SELECT
                id,
                filename,
                file_size,
                upload_date,
                is_public
            FROM files
            WHERE
                is_public = TRUE
                AND is_deleted = FALSE
                AND filename LIKE %s
            ORDER BY upload_date DESC
            """,
            (
                f"%{search}%",
            )
        )
    
    user_name = request.session.get(
        "user_name"
    )

    files = cursor.fetchall()

    cursor.execute("""
        SELECT
            COALESCE(SUM(file_size),0)
        FROM files
    """)

    total_storage = cursor.fetchone()[0]

    cursor.close()
    conn.close()

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "files": files,
            "success": success,
            "error": error,
            "deleted": deleted,
            "total_storage": round(
                total_storage / (1024 * 1024),
                2
            ),
            "user_name": user_name,
            "search": search
        }
    )


@app.post("/upload")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    visibility: str = Form("public")
):

    conn = get_connection()
    cursor = conn.cursor()

    user_id = request.session.get(
        "user_id"
    )

    is_public = (
        visibility == "public"
    )

    if not user_id and not is_public:

        cursor.close()
        conn.close()

        return RedirectResponse(
            url="/?error=Please login for private uploads",
            status_code=303
    )

    cursor.execute(
        """
        SELECT id
        FROM files
        WHERE filename = %s
        """,
        (file.filename,)
    )

    existing_file = cursor.fetchone()

    if existing_file:

        cursor.close()
        conn.close()

        return RedirectResponse(
            url=f"/?error={file.filename}",
            status_code=303
        )

    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)

    s3_key = f"{uuid.uuid4()}_{file.filename}"

    s3.upload_fileobj(
        file.file,
        S3_BUCKET,
        s3_key,
        ExtraArgs={
            "ContentType": file.content_type
        }
    )

    cursor.execute(
        """
        INSERT INTO files
        (
            filename,
            file_path,
            file_size,
            user_id,
            is_public
        )
        VALUES
        (
            %s,
            %s,
            %s,
            %s,
            %s
        )
        """,
        (
            file.filename,
            s3_key,
            file_size,
            user_id,
            is_public
        )
    )

    conn.commit()

    cursor.close()
    conn.close()

    return RedirectResponse(
        url=f"/?success={file.filename}",
        status_code=303
    )

@app.get("/download/{file_id}")
def download_file(file_id: int):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT filename, file_path
        FROM files
        WHERE id = %s
        """,
        (file_id,)
    )

    file = cursor.fetchone()

    cursor.close()
    conn.close()

    if not file:
        return {
            "error": "File not found"
        }

    cloudfront_url = f"{CLOUDFRONT_URL}/{file[1]}"

    return RedirectResponse(
        url=cloudfront_url,
        status_code=302
    )

@app.get("/delete/{file_id}")
def delete_file(
    file_id: int,
    from_page: str = "home"
):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE files
        SET is_deleted = TRUE
        WHERE id = %s
        """,
        (file_id,)
    )

    conn.commit()

    cursor.close()
    conn.close()

    if from_page == "my-files":
        url = "/my-files?deleted=1"

    elif from_page == "shared-files":
        url = "/shared-files?deleted=1"

    else:
        url = "/?deleted=1"

    return RedirectResponse(
        url=url,
        status_code=303
    )

@app.get("/register")
def register_page(
    request: Request
):

    return templates.TemplateResponse(
        request=request,
        name="register.html"
    )


@app.post("/register")
def register_user(

    name: str = Form(...),

    email: str = Form(...),

    password: str = Form(...)

):

    conn = get_connection()
    cursor = conn.cursor()

    hashed_password = hash_password(password)

    cursor.execute(
        """
        SELECT id
        FROM users
        WHERE email = %s
        """,
        (email,)
    )

    existing_user = cursor.fetchone()

    if existing_user:

        cursor.close()
        conn.close()

        return {
            "message": "Email already registered"
        }

    cursor.execute(
        """
        INSERT INTO users
        (
            name,
            email,
            password_hash
        )
        VALUES
        (
            %s,
            %s,
            %s
        )
        """,
        (
            name,
            email,
            hashed_password
        )
    )

    conn.commit()

    cursor.close()
    conn.close()

    return RedirectResponse(
        url="/login",
        status_code=303
    )

@app.get("/login")
def login_page(
    request: Request
):

    return templates.TemplateResponse(
        request=request,
        name="login.html"
    )

@app.post("/login")
def login_user(
    request: Request,
    email: str = Form(...),
    password: str = Form(...)
):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            id,
            name,
            password_hash
        FROM users
        WHERE email = %s
        """,
        (email,)
    )

    user = cursor.fetchone()

    cursor.close()
    conn.close()

    if not user:
        return {"message": "Invalid Email"}

    if not verify_password(
        password,
        user[2]
    ):
        return {"message": "Invalid Password"}

    request.session["user_id"] = user[0]
    request.session["user_name"] = user[1]

    return RedirectResponse(
        url="/",
        status_code=303
    )

@app.get("/logout")
def logout(
    request: Request
):

    request.session.clear()

    return RedirectResponse(
        url="/",
        status_code=303
    )

@app.post("/share-file")
def share_file(

    file_id: int = Form(...),

    email: str = Form(...)

):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id
        FROM users
        WHERE email = %s
        """,
        (email,)
    )

    user = cursor.fetchone()

    if not user:

        cursor.close()
        conn.close()

        return {
            "message": "User not found"
        }

    cursor.execute(
        """
        INSERT INTO file_shares
        (
            file_id,
            shared_with_user_id
        )
        VALUES
        (
            %s,
            %s
        )
        """,
        (
            file_id,
            user[0]
        )
    )

    conn.commit()

    cursor.close()
    conn.close()

    return {
        "message": "File shared successfully"
    }

@app.get("/my-files")
def my_files(
    request: Request
):

    user_id = request.session.get(
        "user_id"
    )

    if not user_id:

        return RedirectResponse(
            "/login",
            status_code=303
        )

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            id,
            filename,
            file_size,
            upload_date,
            is_public
        FROM files
        WHERE 
            user_id = %s
            AND is_deleted = FALSE
        ORDER BY upload_date DESC
        """,
        (user_id,)
    )

    files = cursor.fetchall()

    cursor.close()
    conn.close()

    return templates.TemplateResponse(
        request=request,
        name="my_files.html",
        context={
            "files": files,
            "user_name":
            request.session.get(
                "user_name"
            ),
            "deleted": request.query_params.get("deleted")
        }
    )

@app.get("/shared-files")
def shared_files(
    request: Request
):

    user_id = request.session.get(
        "user_id"
    )

    if not user_id:

        return RedirectResponse(
            "/login",
            status_code=303
        )

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            f.id,
            f.filename,
            f.file_size,
            f.upload_date,
            f.is_public

        FROM files f

        JOIN file_shares fs
        ON f.id = fs.file_id

        WHERE
            fs.shared_with_user_id = %s
            AND f.is_deleted = FALSE
        """,
        (user_id,)
    )

    files = cursor.fetchall()

    cursor.close()
    conn.close()

    return templates.TemplateResponse(
        request=request,
        name="shared_files.html",
        context={
            "files": files,
            "user_name":
            request.session.get(
                "user_name"
            )
        }
    )

@app.get("/recycle-bin")
def recycle_bin(
    request: Request,
    restored: int = 0,
    permanent: int = 0
):

    conn = get_connection()
    cursor = conn.cursor()

    user_id = request.session.get("user_id")

    cursor.execute(
        """
        SELECT
            id,
            filename,
            file_size,
            upload_date,
            is_public
        FROM files
        WHERE
            is_deleted = TRUE
        ORDER BY upload_date DESC
        """
    )

    files = cursor.fetchall()

    cursor.close()
    conn.close()

    return templates.TemplateResponse(
        request=request,
        name="recycle_bin.html",
        context={
            "files": files,
            "user_name": request.session.get("user_name"),
            "restored": restored,
            "permanent": permanent,
            "deleted": request.query_params.get("deleted")
        }
    )

@app.post("/share-files")
def share_files(

    request: Request,

    file_ids: str = Form(...),

    email: str = Form(...)

):

    user_id = request.session.get(
        "user_id"
    )

    if not user_id:

        return RedirectResponse(
            "/login",
            status_code=303
        )

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id
        FROM users
        WHERE email = %s
        """,
        (email,)
    )

    target_user = cursor.fetchone()

    if not target_user:

        cursor.close()
        conn.close()

        return RedirectResponse(
            "/?error=User Not Found",
            status_code=303
        )

    target_user_id = target_user[0]

    ids = file_ids.split(",")

    for file_id in ids:

        cursor.execute(
            """
            INSERT INTO file_shares
            (
                file_id,
                shared_with_user_id
            )
            VALUES
            (
                %s,
                %s
            )
            """,
            (
                file_id,
                target_user_id
            )
        )

    conn.commit()

    cursor.close()
    conn.close()

    return RedirectResponse(
        "/?success=Files Shared",
        status_code=303
    )

@app.get("/generate-share-link/{file_id}")
def generate_share_link(
    file_id: int
):

    token = str(
        uuid.uuid4()
    )

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE files
        SET share_token=%s
        WHERE id=%s
        """,
        (
            token,
            file_id
        )
    )

    conn.commit()

    cursor.close()
    conn.close()

    return {
        "share_link":
        f"/shared/{token}"
    }

@app.get("/shared/{token}")
def shared_file(
    token: str
):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            filename,
            file_path
        FROM files
        WHERE share_token=%s
        """,
        (token,)
    )

    file = cursor.fetchone()

    cursor.close()
    conn.close()

    if not file:

        return {
            "message":
            "Invalid Share Link"
        }

    temp_file = tempfile.NamedTemporaryFile(delete=False)

    s3.download_file(
        S3_BUCKET,
        file[1],
        temp_file.name
    )

    return FileResponse(
        path=temp_file.name,
        filename=file[0]
    )

@app.get("/preview/{file_id}")
def preview_file(
    request: Request,
    file_id: int,
    from_page: str = Query("home", alias="from")
):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            filename,
            file_path,
            file_size,
            upload_date,
            is_public
        FROM files
        WHERE
            id=%s
            AND is_deleted = FALSE
    """,(file_id,))

    row = cursor.fetchone()

    cursor.close()
    conn.close()

    if not row:
        return {"message":"File not found"}

    file = {
        "id":row[0],
        "filename":row[1],
        "file_path":row[2],
        "file_size":row[3],
        "upload_date":row[4],
        "is_public":row[5]
    }

    return templates.TemplateResponse(
        name="preview.html",
        request=request,
        context={
            "file": file,
            "user_name": request.session.get("user_name"),
            "from_page": from_page
        }
    )

@app.get("/restore/{file_id}")
def restore_file(file_id: int):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE files
        SET is_deleted = FALSE
        WHERE id=%s
        """,
        (file_id,)
    )

    conn.commit()

    cursor.close()
    conn.close()

    return RedirectResponse(
        url="/recycle-bin?restored=1",
        status_code=303
    )

@app.get("/delete-permanently/{file_id}")
def delete_permanently(file_id: int):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT file_path
        FROM files
        WHERE id=%s
        """,
        (file_id,)
    )

    file = cursor.fetchone()

    if file:

        if os.path.exists(file[0]):
            os.remove(file[0])

        cursor.execute(
            """
            DELETE FROM files
            WHERE id=%s
            """,
            (file_id,)
        )

        conn.commit()

    cursor.close()
    conn.close()

    return RedirectResponse(
        url="/recycle-bin?permanent=1",
        status_code=303
    )