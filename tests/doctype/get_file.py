import os


def get_file_from_path(name: str,path: str|None,) -> dict[str, str|int|None]:
    """ Test the existence of a file given its file name or the folder it expected to be found. 
    The file name can be derived from a doctype name. In addition to the above, given
    a file, path, we must also check that the file exists in that path as well.
    """
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__),"../../"))
    public = "public" if path is None else path
    full_path = os.path.join(project_root, public, name)
    file_size =  os.path.getsize(full_path)
    file_contents = None
    with open(full_path, 'r') as f:
        file_contents= f.read()
    return {"contents": file_contents, "size": file_size}