import json
import os
import threading
import base64

from comms.mqtt import MQTTClient, Topic, MQTTMessageHandler
from comms.crc32 import compare_crc32

class meta_data_message(MQTTMessageHandler):
    """
    represents the meta data message for a file transfer, which includes:
        - filename: the name of the file being transferred
        - size: the total size of the file in bytes
        - chunks: the total number of chunks the file is divided into

    The meta data message is expected to be sent as a JSON string in the MQTTClient payload,
    with an optional CRC32 checksum for integrity verification.
    """
    def __init__(self, file_receiver_instance: "file_receiver", is_crc32:bool = False):
            super().__init__()
            self.add_variable("filename", "")
            self.add_variable("size", 0.0)
            self.add_variable("chunks", 0)
            self.add_variable("encoding", "base64")
            self.crc32 = is_crc32
            self._is_valid = True
            self._file_receiver = file_receiver_instance

    def update_values(self, filename: str, size: float, chunks: int):
            """Helper method to update all sensor values at once"""
            self.set_variable("filename", filename)
            self.set_variable("size", size)
            self.set_variable("chunks", chunks)

    @property
    def is_valid(self):
        return self._is_valid

    def decode(self, message):
        """Override decode to ensure correct encodeing and add data to data manager"""     
        payload = message.payload.decode()
        if self.crc32:
            if len(payload) < 8:
                raise ValueError(f"Meta data message payload is too short: {message.payload.decode()}")

            expected_crc = payload[-8:]
            data_without_crc = payload[:-8]
            if not compare_crc32(data_without_crc, expected_crc):
                print(f"Warning: CRC32 checksum does not match for meta data message. Payload may be corrupted. Payload: {payload}")
                self._is_valid = False
            else:
                print(f"CRC32 checksum matches for meta data message.")
        try:
            if self.crc32 and self.is_valid:
                self.args = json.loads(payload[:-8])  # SAFE - only parses JSON
            else:
                self.args = json.loads(payload)  # SAFE - only parses JSON
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON payload: {e}, payload: {payload[:-8]}")
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

class data_chunk_message(MQTTMessageHandler):
    """
    represents a data chunk message for a file transfer, which includes:
        - chunk_index: the index of the chunk in the file (starting from 0)
        - data: the base64 encoded string representing the bytes of the chunk
    The data chunk message is expected to be sent as a base64 encoded string in the MQTTClient payload,
    with an optional CRC32 checksum for integrity verification.
    """

    def __init__(self, file_receiver_instance: "file_receiver", is_crc32:bool = False):
            super().__init__()
            self.add_variable("chunk_index", 0)
            self.add_variable("data", "")
            self._file_receiver = file_receiver_instance
            self._is_valid = True
            self.crc32 = is_crc32

    @property
    def data_bytes(self) -> bytes:
        """Decode the base64 encoded data string to bytes"""
        return base64.b64decode(self.args["data"])
    
    @property
    def chunk_index(self):
        return self.args["chunk_index"] 

    @property
    def is_valid(self):
        return self._is_valid

    def decode(self, message):
        """Override decode -> data is sent as base64 representing file bytes not json"""
        received = message.payload.decode()
        if self.crc32:
            expected_crc = received[-8:]
            data_without_crc = received[:-8]
            if not compare_crc32(base64.b64decode(data_without_crc), expected_crc):
                print(f"Warning: CRC32 checksum does not match for data chunk message. Payload may be corrupted. Payload: {received}")
                self._is_valid = False
            else:
                print(f"CRC32 checksum matches for data chunk message.")
                self.set_variable("data", data_without_crc)  # Store the base64 string without CRC
        else:
            self.set_variable("data", received)  # Store the base64 string as is
        
        index = message.topic.split("/")[-1]  # assuming Topic format is "MAIN_topic_NAME/chunk/{index}"
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
    def start(self, MQTTClient_client: MQTTClient, topic_name: str, crc32: bool = False):
        self._lock = threading.Lock()

        self.data_chunks: dict[int, bytes] = {} # each chunck received will be stored here
        self.file = None

        self.meta_msg = meta_data_message(self, crc32)
        self.crc32 = crc32
        self.chunk_msg: list[data_chunk_message] = []

        self.meta_Topic = Topic(f"{topic_name}/meta", MQTTClient_client)
        self.topic = topic_name
        self.client = MQTTClient_client
        self.chunk_Topic: list[Topic] = []

        self.meta_Topic.subscribe(self.meta_msg)

        self.is_file_received = False

    def _sub_to_chunk_Topics(self):
        """Subscribe to the chunk Topics based on the number of chunks specified in the meta data"""    
        for i in range(self.meta_data.chunks): # type: ignore
            self.chunk_Topic.append(Topic(f"{self.topic}/chunk/{i}", self.client))
            self.chunk_msg.append(data_chunk_message(self, self.crc32))
            self.chunk_Topic[-1].subscribe(self.chunk_msg[-1])

    def add_meta_data(self, meta_data: meta_data_message):
        if not meta_data.is_valid:
            print(f"Received invalid meta data message. Meta data will be ignored. Meta data: {self.meta_data}") 
            print("we will wait for next meta data message...") 
            return
        else:
            self.meta_data = meta_data
            print(f"Received meta data: {self.meta_data}") 
            self._sub_to_chunk_Topics()

    def add_data_chunk(self, chunk: data_chunk_message):
        if not chunk.is_valid:
            print(f"Received invalid data chunk message. Chunk will be ignored. Chunk index: {chunk.chunk_index}") 
            print("we will wait for the chunk to be resent...") 
            return
        with self._lock:
            self.data_chunks[chunk.chunk_index] = chunk.data_bytes
            print(f"Received chunk {chunk.chunk_index}: {len(chunk.data_bytes)} bytes") 
            if self.meta_data and len(self.data_chunks) == self.meta_data.chunks:
                self._assemble_file()
   
    def _assemble_file(self):
        """Assemble the file from the received data chunks and save it to disk"""
        # If somehow add_data_chunk is triggered twice for the last chunk (e.g. MQTTClient QoS retry), _assemble_file runs again while is_file_received is still False
        if self.is_file_received:
            return
    
        if not self.meta_data:
            raise ValueError("Meta data must be set before assembling file")
        
        ordered_chunks = [self.data_chunks[i] for i in range(self.meta_data.chunks)]
        file_data = b"".join(ordered_chunks)

        # DEBUG: Print where file will be saved
        abs_path = os.path.abspath(self.meta_data.filename)
    
        # Save the assembled file to disk
        with open(self.meta_data.filename, "wb") as f:
            f.write(file_data)
        
        # DEBUG: Verify file was created
        if os.path.exists(abs_path):
            print(f"File successfully created at {abs_path}, size: {os.path.getsize(abs_path)} bytes")
        else:
            print(f"ERROR - File was not created at {abs_path}")
            
        self.file = self.meta_data.filename
        print(f"File '{self.meta_data.filename}' assembled and saved successfully.")
        self.on_complete()

    def on_complete(self):
        print(f"Received file: {self.meta_data.filename}") # type: ignore
        self.meta_Topic.unsubscribe(self.meta_msg)
        for i in range(self.meta_data.chunks): # type: ignore
            self.chunk_Topic[i].unsubscribe(self.chunk_msg[i])
        self.is_file_received = True

    @property
    def is_complete(self):
        return self.is_file_received

    @property
    def filename(self):
        return self.file if self.file else None