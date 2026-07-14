import gradio as gr
import subprocess

# Start bot in a background process
subprocess.Popen(["python", "main.py"])

# Create a dummy Gradio interface to satisfy the Space
with gr.Blocks() as demo:
    gr.Markdown("# ZEHN mini Bot is running in the background!")
    gr.Markdown("Bu oyna faqat serverni faol ushlab turish uchun ochilgan. Bot bemalol Telegramda ishlayveradi.")

demo.launch()
