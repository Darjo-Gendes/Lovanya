"""Detection + segmentation stage.

Per ARCHITECTURE-DECISIONS.md this will be GroundingDINO + SAM2. That wiring
is deferred; the current implementation passes the whole image through so the
pipeline shape (segment -> perceive -> judge) is already real. Replacing this
stub with real detection must not require changes anywhere else.
"""


def segment(image_path: str) -> str:
    """Return the path of the image region to analyze.

    Stub: returns the input unchanged (whole image). The real implementation
    will detect/crop the garment region and return a path to the crop.
    """
    return image_path
