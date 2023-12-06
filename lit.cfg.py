import lit.formats

root_dir = os.path.dirname(__file__)

config.name = "Domain Types"
config.test_format = lit.formats.ShTest()
config.suffixes = [".doty", ".mlir"]
config.test_exec_root = os.path.join(root_dir, "build")
config.substitutions += [
    ("doty", os.path.join(root_dir, "doty")),
]
python_path = root_dir
if env := os.environ.get("PYTHONPATH"):
    python_path += ":" + env
config.environment["PYTHONPATH"] = python_path
