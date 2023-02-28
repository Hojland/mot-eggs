import gradio as gr
import dataclasses
import detect_mot
from loguru import logger
import cv2


@dataclasses.dataclass
class BytetrackArgs:
    track_thresh: int = 0.65
    track_buffer: int = 30 * 0.1  # 30 framerate * 0.1 second
    mot20: bool = False
    match_thresh: float = 0.950
    fps: int = 30
    tsize: int = 416
    test_size: tuple = (416, 416)


def mot_video(video):
    logger.info(video)
    video = detect_mot.run("ml/best.pt", source=video, data="ml/egg.yaml", device="cpu", bytetrackargs=BytetrackArgs())
    return video


title = "GoAutonomous Eggs Detection"
description = "Finding eastereggs prior to easter using yolov5 and byte"

demo = gr.Interface(
    mot_video,
    gr.Video(type="file", interactive=True),
    gr.Video(),
    examples=[["ml/goautonomous_eggs_short.mp4"], ["ml/goautonomous_eggs_small.mp4"]],
    cache_examples=True,
    title=title,
    description=description,
    theme="default",
    allow_flagging="never",
)

if __name__ == "__main__":
    demo.launch(
        share=False,
        server_port=8000,
        server_name="0.0.0.0",
        enable_queue=True,
    )
