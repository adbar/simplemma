import os
import tempfile

from training import dictionary_pickler

TEST_DIR = os.path.abspath(os.path.dirname(__file__))


def test_logic() -> None:
    """Test if certain code parts correspond to the intended logic."""
    # dict generation
    testfile = os.path.join(TEST_DIR, "data/zz.txt")
    # simple generation, silent mode
    mydict = dictionary_pickler._read_dict(testfile, "zz", silent=True)
    assert len(mydict) == 3
    mydict = dictionary_pickler._load_dict(
        "zz", listpath=os.path.join(TEST_DIR, "data"), silent=True
    )
    assert len(mydict) == 3
    # log warning
    mydict = dictionary_pickler._read_dict(testfile, "zz", silent=False)
    assert len(mydict) == 3
    # different length
    mydict = dictionary_pickler._read_dict(testfile, "en", silent=True)
    assert len(mydict) == 5
    # different order
    mydict = dictionary_pickler._read_dict(testfile, "es", silent=True)
    assert len(mydict) == 5
    assert mydict[b"closeones"] == b"closeone"
    item = sorted(mydict.keys(), reverse=True)[0]
    assert item == b"valid-word"

    # file I/O
    assert dictionary_pickler._determine_path("lists", "de").endswith("de.txt")

    # dict pickling
    listpath = os.path.join(TEST_DIR, "data")
    os_handle, temp_outputfile = tempfile.mkstemp(suffix=".pkl", text=True)
    dictionary_pickler._pickle_dict("zz", listpath, temp_outputfile)
    dictionary_pickler._pickle_dict("zz", listpath, in_place=True)
