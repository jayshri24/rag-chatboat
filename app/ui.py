
import uuid
import json
import httpx
import asyncio
import logging
from nicegui import app, ui
from dotenv import load_dotenv
from typing import Any
from app.config import get_settings
from app.main import app as fastapi_app
from nicegui.events import UploadEventArguments

logger = logging.getLogger(__name__)

load_dotenv()
settings = get_settings()

current_session_id: str = str(uuid.uuid4())
chat_messages: list[dict[str, Any]] = []
current_status: str = ""

status_container: Any | None = None
chat_container: Any | None = None
message_input: Any | None = None
send_button: Any | None = None
current_message_container: Any | None = None

def update_status(status: str, elapsed: float | None = None, token_count: int | None = None) -> None:
    """Update status display with optional timing and token count."""
    global current_status, status_container
    current_status = status
    if not status_container:
        return
    status_container.clear()
    if status:
        with status_container:
            ui.spinner("dots", size="sm").classes("mr-2")
            # Build status text with timing and token count
            status_text = status
            if elapsed is not None:
                status_text += f" ({elapsed:.1f}s)"
            if token_count is not None:
                status_text += f" [{token_count} tokens]"
            ui.label(status_text).classes("text-body2 text-primary")


def add_chat_message(role: str, content: str, is_streaming: bool = False) -> None:
    global chat_container, current_message_container
    if not chat_container:
        return
    with chat_container:
        with ui.card().classes("w-full mb-2"):
            if role == "user":
                ui.label("You").classes("text-caption text-primary font-medium")
                ui.label(content).classes("text-body1")
            else:
                ui.label("Assistant").classes("text-caption text-secondary font-medium")
                if is_streaming:
                    current_message_container = ui.label("").classes("text-body1")
                else:
                    ui.label(content).classes("text-body1")


def update_streaming_message(content: str) -> None:
    global current_message_container
    if current_message_container:
        current_message_container.text = (current_message_container.text or "") + content


def clear_streaming_message() -> None:
    global current_message_container
    current_message_container = None


async def handle_pdf_upload(e: UploadEventArguments) -> None:
    try:
        update_status("Uploading PDF...")
        file_content = await e.file.read()
        
        # Show file size information
        file_size_mb = len(file_content) / (1024 * 1024)
        if file_size_mb > 0.1:
            update_status(f"Uploading PDF... ({file_size_mb:.2f} MB)")
        else:
            file_size_kb = len(file_content) / 1024
            update_status(f"Uploading PDF... ({file_size_kb:.1f} KB)")
        
        async with httpx.AsyncClient() as client:
            files = {"file": (e.file.name, file_content, "application/pdf")}
            data = {"session_id": current_session_id}
            response = await client.post("http://localhost:8000/upload/pdf", files=files, data=data)
        if response.status_code == 200:
            result = response.json()
            if result["success"]:
                update_status("PDF uploaded successfully!")
                add_chat_message(
                    "system",
                    f"Succesfully Uploaded: {result['metadata']['filename']}"
                )
            else:
                update_status("")
                add_chat_message("system", f"Upload failed: {result['message']}")
        else:
            update_status("")
            add_chat_message("system", f"Upload failed: HTTP {response.status_code}")
    except Exception as e:
        logger.error(f"Error uploading PDF: {e}")
        update_status("")
        add_chat_message("system", f"Upload error: {str(e)}")
    finally:
        await asyncio.sleep(2)
        update_status("")


async def send_message(message: str) -> None:
    global message_input, send_button
    if not message.strip():
        return

    if message_input:
        message_input.value = ""
    if send_button:
        send_button.props("loading=true")

    try:
        add_chat_message("user", message)
        add_chat_message("assistant", "", is_streaming=True)

        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
            url = "http://localhost:8000/chat/stream"
            logger.info(f"🔗 Sending message to: {url}")

            async with client.stream("POST", url, json={"message": message, "session_id": current_session_id}) as response:
                logger.info(f"Received response status: {response.status_code}")

                if response.status_code != 200:
                    text = await response.aread()
                    raise Exception(f"HTTP {response.status_code}: {text.decode()}")

                async for line in response.aiter_lines():
                    if not line.strip():
                        continue

                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError:
                        logger.warning(f"Skipping malformed line: {line}")
                        continue

                    t = chunk.get("type")
                    if t == "status":
                        update_status(
                            chunk.get("step", ""),
                            elapsed=chunk.get("elapsed_seconds"),
                            token_count=chunk.get("token_count")
                        )
                    elif t == "token":
                        update_streaming_message(chunk.get("content", ""))
                        # Update status with token count during streaming
                        if chunk.get("token_count"):
                            update_status(
                                "Generating response",
                                elapsed=chunk.get("elapsed_seconds"),
                                token_count=chunk.get("token_count")
                            )
                    elif t == "done":
                        # Show final stats before clearing
                        final_elapsed = chunk.get("elapsed_seconds")
                        final_tokens = chunk.get("token_count")
                        if final_elapsed is not None or final_tokens is not None:
                            stats_text = "Complete"
                            if final_elapsed is not None:
                                stats_text += f" ({final_elapsed:.1f}s"
                            if final_tokens is not None:
                                stats_text += f", {final_tokens} tokens" if final_elapsed else f" ({final_tokens} tokens"
                            if final_elapsed is not None:
                                stats_text += ")"
                            update_status(stats_text)
                            await asyncio.sleep(0.5)  # Brief display of completion stats
                        update_status("")
                        clear_streaming_message()
                        break
                    elif t == "error":
                        update_status("")
                        clear_streaming_message()
                        add_chat_message("system", f"Error: {chunk.get('content', 'Unknown')}")
                        break

    except Exception as e:
        logger.error("Error sending message", exc_info=True)
        update_status("")
        clear_streaming_message()
        add_chat_message("system", f"Error: {str(e)}")

    finally:
        if send_button:
            send_button.props("loading=false")

def new_session() -> None:
    global current_session_id, chat_container
    current_session_id = str(uuid.uuid4())
    if chat_container:
        chat_container.clear()
    ui.notify("New session started", type="info")


def create_app() -> None:
    app.add_static_files("/static", "static")
    app.mount("/api", fastapi_app)

@ui.page("/")
def main_page():
    ui.page_title("Document QA Chatbot")

    with ui.column().classes("w-full max-w-3xl mx-auto p-4 gap-4"):

        # HEADER
        ui.label("Document QA Chatbot").classes("text-3xl font-bold text-primary")
        ui.label("Upload a PDF and ask questions easily!").classes("text-md text-gray-600")

        # PDF UPLOAD CARD
        with ui.card().classes("w-full p-4 shadow-lg"):
            ui.label("Upload PDF Document").classes("text-lg font-semibold mb-2")

            upload = ui.upload(
                on_upload=handle_pdf_upload,
                auto_upload=True,
                max_file_size=10 * 1024 * 1024,
            ).classes("w-full border rounded-lg p-4 bg-gray-50")
            upload.props("accept=.pdf")

            ui.label("Drag & drop a PDF or click browse").classes(
                "text-xs text-gray-500 mt-1"
            )

        # SESSION INFO
        with ui.row().classes("items-center w-full"):
            ui.badge(f"Session: {current_session_id[:8]}").classes(
                "text-sm bg-indigo-100 text-indigo-600 px-3 py-1 rounded-lg"
            )
            ui.button("New Session", on_click=new_session).classes(
                "ml-auto bg-indigo-600 text-white rounded-lg"
            )

        # STATUS + CHAT AREA
        global status_container, chat_container
        status_container = ui.row().classes("w-full text-gray-600 text-sm")
        chat_container = ui.column().classes(
            "w-full max-h-[500px] overflow-y-auto bg-white p-4 rounded-xl shadow-inner gap-3"
        )

        # INPUT BAR
        global message_input, send_button
        with ui.row().classes(
            "w-full items-center sticky bottom-0 bg-white p-2 shadow-md gap-2"
        ):
            message_input = ui.input(placeholder="Ask a question...").classes("flex-1")
            send_button = ui.button(
                "Send",
                on_click=lambda: asyncio.create_task(send_message(message_input.value)),
            ).classes("bg-blue-600 text-white px-4")

if __name__ in {"__main__", "__mp_main__"}:
    create_app()
    print("STORAGE_SECRET =", settings.storage_secret)
    ui.run(
        host=settings.frontend_host,
        port=settings.frontend_port,
        title=settings.app_name,
        favicon="🤖",
        storage_secret=settings.storage_secret,
    )


