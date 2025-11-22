"""Application entrypoint mounting a Gradio UI on FastAPI for Cloud Run."""

import uuid

import gradio as gr
from fastapi import FastAPI
import uvicorn

from chain import answer_question, process_document

app = FastAPI()


def get_session_id() -> str:
    return str(uuid.uuid4())


def _analyze(file_obj, arxiv_id):
    file_path = file_obj.name if file_obj else None
    return process_document(file_path, arxiv_id)


def _init_session():
    return get_session_id()


with gr.Blocks() as demo:
    gr.Markdown("# Scientific Paper Analyzer")
    session_id = gr.State()

    with gr.Row():
        with gr.Column(scale=1):
            file_in = gr.File(label="Upload PDF")
            arxiv_in = gr.Textbox(label="ArXiv ID")
            btn = gr.Button("Analyze")
            status = gr.Textbox(label="Status")
            summary = gr.Textbox(label="Summary")
        with gr.Column(scale=2):
            gr.ChatInterface(fn=answer_question, additional_inputs=[session_id])

    btn.click(_analyze, [file_in, arxiv_in], [status, summary])
    demo.load(_init_session, None, session_id)

app = gr.mount_gradio_app(app, demo, path="/")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
