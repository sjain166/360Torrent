from tabulate import tabulate
from scripts.class_object import Peer, Chunk, File, FileMetadata


# Rich Print
import builtins
from rich import print as rich_print
builtins.print = rich_print


def print_tracker_file_registry(TRACKER_FILE_REGISTRY):
    """
    Prints the TRACKER_FILE_REGISTRY in a tabular format without repeating file names.
    """
    table_data = []
    for file_obj in TRACKER_FILE_REGISTRY:
        file_displayed = False
        for chunk_obj in file_obj.chunks:
            peer_list = ", ".join(
                [f"{peer.ip}:{peer.port}" for peer in chunk_obj.peers]
            )
            table_data.append(
                [
                    (
                        file_obj.file_name if not file_displayed else ""
                    ),  # Print file name only once
                    (
                        file_obj.file_size if not file_displayed else ""
                    ),  # Print file size only once
                    chunk_obj.chunk_name,
                    chunk_obj.chunk_size,
                    peer_list,
                ]
            )
            file_displayed = True
    headers = [
        "File Name",
        "File Size (Bytes)",
        "Chunk Name",
        "Chunk Size (Bytes)",
        "Peers Hosting Chunk",
    ]
    print(tabulate(table_data, headers=headers, tablefmt="grid"))


def print_registry_summary(summary):
    """
    Display the tracker file registry summary in a table.
    """
    if not summary:
        print("[WARN] No files available on the tracker.")
        return
    table_data = [
        [file["file_name"], file["file_size"], file["seeders"]] for file in summary
    ]
    headers = ["File Name", "File Size (Bytes)", "Number of Seeders"]
    print(tabulate(table_data, headers=headers, tablefmt="grid"))


# def print_peer_file_registry(PEER_FILE_REGISTRY):
#     """
#     Prints the PEER_FILE_REGISTRY in a tabular format without repeating file names.
#     """
#     table_data = []

#     for file_obj in PEER_FILE_REGISTRY:
#         file_displayed = False
#         for chunk_obj in file_obj.chunks:
#             peer_list = ", ".join(
#                 [f"{peer.ip}:{peer.port}" for peer in chunk_obj.peers]
#             )
#             table_data.append(
#                 [
#                     (
#                         file_obj.file_name if not file_displayed else ""
#                     ),  # Print file name only once
#                     (
#                         file_obj.file_size if not file_displayed else ""
#                     ),  # Print file size only once
#                     chunk_obj.chunk_name,
#                     chunk_obj.chunk_size,
#                     peer_list,
#                 ]
#             )
#             file_displayed = True
#     headers = [
#         "File Name",
#         "File Size (Bytes)",
#         "Chunk Name",
#         "Chunk Size (Bytes)",
#         "Peers Hosting Chunk",
#     ]
#     print(tabulate(table_data, headers=headers, tablefmt="grid"))


def print_file_metadata(metadata: FileMetadata):
    if not metadata:
        print("[WARN] No metadata found.")
        return
    table_data = []
    file_displayed = False
    for chunk in metadata.chunks:
        table_data.append(
            [
                metadata.file_name if not file_displayed else "",
                metadata.file_size if not file_displayed else "",
                chunk.chunk_name,
                chunk.chunk_size,
                "Downloaded" if chunk.download_status else "Pending",
            ]
        )
        file_displayed = True
    headers = [
        "File Name",
        "File Size (Bytes)",
        "Chunk Name",
        "Chunk Size (Bytes)",
        "Download Status",
    ]
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
