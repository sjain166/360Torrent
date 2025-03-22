class Peer:
    """
    Represents a peer in the network.
    """
    def __init__(self, ip: str, port: int):
        self.ip = ip
        self.port = port
        self.peer_file_registry = []  # Dictionary of files hosted by the peer

    def __repr__(self):
        return f"PeerObject(ip={self.ip}, port={self.port})"


class Chunk:
    """
    Represents a chunk of a file.
    """
    def __init__(self, chunk_name: str, chunk_size: int):
        self.chunk_name = chunk_name
        self.chunk_size = chunk_size
        self.peers = []  # List of PeerObjects hosting this chunk
    
    def add_peer(self, peer: Peer):
        if all(existing_peer.ip != peer.ip for existing_peer in self.peers):
            self.peers.append(peer)
    
    def __repr__(self):
        return f"ChunkObject(chunk_name={self.chunk_name}, chunk_size={self.chunk_size}, peers={self.peers})"


class File:
    """
    Represents a complete file in the system.
    """
    def __init__(self, file_name: str, file_size: int):
        self.file_name = file_name
        self.file_size = file_size
        self.chunks = []  # List of ChunkObjects
    
    def add_chunk(self, chunk: Chunk):
        if chunk not in self.chunks:
            self.chunks.append(chunk)
    
    def __repr__(self):
        return f"FileObject(file_name={self.file_name}, file_size={self.file_size}, chunks={self.chunks})"
