#!/usr/bin/env python3

import os
from datetime import datetime,timedelta,timezone
from threading import Thread
from queue import Queue
from pathlib import Path
from time import time
from pathlib import Path

import gi
import numpy as np
from aion.microservice import main_decorator, Options
from aion.kanban import Kanban
from aion.logger import lprint, initialize_logger

gi.require_version('Gst', '1.0')  # noqa
from gi.repository import Gst  # isort:skip

SERVICE_NAME = "real-time-video-streaming"

JST = timezone(timedelta(hours=+9), 'JST')
initialize_logger(SERVICE_NAME)

# video paramator
video_id = 0
width = 1920
height = 1080
fps = 5
output_npy_flag = False


def get_now_datetime_string():
    return datetime.now(JST).strftime("%Y%m%d%H%M%S%f")[:-3]


# threading output method
def output_jpg_file(q, data_path):
    while True:
        data, date_str = q.get()
        if data is None:
            break
        if output_npy_flag:
            file_path = data_path / (date_str + ".npy")
            array = np.ndarray(
                (height, width, 4),
                buffer=data,
                dtype=np.uint8)
            rgb, _ = np.split(array, [3], axis=2)
            np.savez_compressed(str(file_path), rgb)
        else:
            file_path = data_path / (date_str + ".jpg")
            with file_path.open("wb") as f:
                f.write(data)

@main_decorator(SERVICE_NAME)
def main(opt: Options):
    conn = opt.get_conn()
    num = opt.get_number()
    kanban: Kanban = conn.set_kanban(SERVICE_NAME, num)

    data_path = kanban.get_data_path()
    data_path = Path(data_path + "/output")
    os.makedirs(data_path, exist_ok=True)
    # initialize gstreamer pipeline
    Gst.init(None)
    # for debug
    # Gst.debug_set_active(True)
    # Gst.debug_set_default_threshold(3)

    if output_npy_flag:
        pipe = Gst.parse_launch("""
                v4l2src device=/dev/video{id} io-mode=2 !
                image/jpeg, width={width}, height={height}, framerate={fps}/1 !
                nvjpegdec ! video/x-raw ! nvvideoconvert !
                video/x-raw(memory:NVMM) ! nvvideoconvert !
                video/x-raw, format=BGRx !
                appsink sync=false max-buffers=2 drop=true
                name=sink emit-signals=true"""
                                .format(id=video_id, width=width,
                                        height=height, fps=fps))
    else:
        pipe = Gst.parse_launch("""
                v4l2src device=/dev/video{id} !
                image/jpeg ,width={width},height={height},framerate={fps}/1 !
                appsink sync=false max-buffers=2 drop=true
                name=sink emit-signals=true"""
                                .format(id=video_id, width=width,
                                        height=height, fps=fps))

    sink = pipe.get_by_name('sink')
    pipe.set_state(Gst.State.PLAYING)

    if not sink:
        lprint("cant connect to camera id: ", video_id)
        exit(-1)

    # initialize thread
    q = Queue()
    t = Thread(
        target=output_jpg_file,
        args=(q,data_path,))
    t.start()

    try:
        count = 0
        t1 = time()
        while True:
            count = count + 1
            sample = sink.emit('pull-sample')
            buf = sample.get_buffer()

            data = buf.extract_dup(0, buf.get_size())
            q.put((data, get_now_datetime_string()))
            if count >= fps:
                lprint("success: output picture fps: ", (fps/(time()-t1)))
                count = 0
                t1 = time()
    finally:
        q.put(None)
        t.join()


if __name__ == "__main__":
    main()
