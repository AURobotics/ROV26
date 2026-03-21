import json
import threading
from time import sleep
from typing import Any
import base64

from comms.mqtt import mqtt, topic, mqtt_message

MAIN_TOPIC_NAME = "float/data"

class meta_data_message(mqtt_message):
    def __init__(self, file_receiver_instance: file_receiver):
            super().__init__()
            self.add_variable("filename", "")
            self.add_variable("size", 0.0)
            self.add_variable("chunks", 0)
            self.add_variable("encoding", "base64")
            self._file_receiver = file_receiver_instance

    def update_values(self, filename: str, size: float, chunks: int):
            """Helper method to update all sensor values at once"""
            self.set_variable("filename", filename)
            self.set_variable("size", size)
            self.set_variable("chunks", chunks)

    def decode(self, message):
        """Override decode to ensure correct encodeing and add data to data manager"""
        super().decode(message)  # Decode the message as usual
        if self.args.get("encoding") != "base64":
            raise ValueError(f"Unsupported encoding: {self.args.get('encoding')}")
        
        self._file_receiver.add_meta_data(self)  # Add the decoded meta data to the data manager
        
    @property
    def filename(self):
        return self.args["filename"]
    @property
    def size(self):
        return self.args["size"]
    @property
    def chunks(self):
        return self.args["chunks"]

    def __str__(self):
        return f"meta_data(filename={self.args['filename']}, size={self.args['size']}, chunks={self.args['chunks']}, encoding={self.args['encoding']})"

class data_chunk_message(mqtt_message):
    def __init__(self, file_receiver_instance: file_receiver):
            super().__init__()
            self.add_variable("chunk_index", 0)
            self.add_variable("data", "")
            self._file_receiver = file_receiver_instance

    @property
    def data_bytes(self) -> bytes:
        """Decode the base64 encoded data string to bytes"""
        return base64.b64decode(self.args["data"])
    
    @property
    def chunk_index(self):
        return self.args["chunk_index"] 

    def decode(self, message):
        """Override decode -> data is sent as base64 representing file bytes not json"""
        self.set_variable("data", message.payload.decode())  # Store the base64 string as is
        
        index = message.topic.split("/")[-1]  # assuming topic format is "MAIN_TOPIC_NAME/chunk/{index}"
        self.set_variable("chunk_index", int(index))  # Store the chunk index as an integer
        
        self._file_receiver.add_data_chunk(self)  # Add the decoded data chunk to the data manager

    def __str__(self):
        return f"data_chunk(chunk_index={self.args['chunk_index']}, data_length={len(self.args['data'])} characters)"

class file_receiver:
    """
    receives meta data and data chunks for a file,
    assembles the file once all chunks are received,
    and saves it to disk.
    
    it is designed for: 
    - messages sent in base64 encoding to handle binary data
    - expects a meta data message that describes the file and how many chunks to expect.
    """
    def __init__(self, mqtt_client: mqtt, topic_name: str, ):
        self._lock = threading.Lock()

        self.meta_data: meta_data_message | None = None
        self.data_chunks: dict[int, bytes] = {}
        self.file = None

        self.meta_msg = meta_data_message(self)
        self.chunk_msg = data_chunk_message(self)

        self.meta_topic = topic(f"{topic_name}/meta", mqtt_client)
        self.chunk_topic = topic(f"{topic_name}/chunk/#", mqtt_client)

        self.meta_topic.subscribe(self.meta_msg)
        self.chunk_topic.subscribe(self.chunk_msg)

        self.is_file_received = False

    def add_meta_data(self, meta_data: meta_data_message):
        self.meta_data = meta_data
        # just in case we receive the meta data after some chunks, check if we can assemble the file now
        if self.data_chunks and len(self.data_chunks) == self.meta_data.chunks:
            self._assemble_file()

    def add_data_chunk(self, chunk: data_chunk_message):
        with self._lock:
            self.data_chunks[chunk.chunk_index] = chunk.data_bytes
            if self.meta_data and len(self.data_chunks) == self.meta_data.chunks:
                self._assemble_file()
   
    def _assemble_file(self):
        """Assemble the file from the received data chunks and save it to disk"""
        if not self.meta_data:
            raise ValueError("Meta data must be set before assembling file")
        
        ordered_chunks = [self.data_chunks[i] for i in range(self.meta_data.chunks)]
        file_data = b"".join(ordered_chunks)

        # Save the assembled file to disk
        with open(self.meta_data.filename, "wb") as f:
            f.write(file_data)
        self.file = self.meta_data.filename
        print(f"File '{self.meta_data.filename}' assembled and saved successfully.")
        self.on_complete()

    def on_complete(self):
        print(f"Received file: {file_receiver_instance.filename}")
        self.meta_topic.unsubscribe(self.meta_msg)
        self.chunk_topic.unsubscribe(self.chunk_msg)
        self.is_file_received = True

    @property
    def is_complete(self):
        return self.is_file_received

    @property
    def filename(self):
        return self.file if self.file else None

# class file_sender:
#     def __init__(self, filename: str, mqtt_client: mqtt, topic_name: str):
#         self.CHUNK_SIZE = 512  # 512 bytes per chunk to work with mqtt limits

#         self.filename = filename
#         self.mqtt_client = mqtt_client
#         self.meta_topic = topic(f"{topic_name}/meta", mqtt_client)
#         self.chunk_topic = topic(f"{topic_name}/chunk", mqtt_client)

if __name__ == "__main__":
    mqtt_client = mqtt("localhost", 1883)
    
    file_receiver_instance = file_receiver(mqtt_client, f"{MAIN_TOPIC_NAME}")

    while not file_receiver_instance.is_complete:
        print("Waiting for file...")
        sleep(2)
    print(f"Received file: {file_receiver_instance.filename}")
