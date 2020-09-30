import logging
from pathlib import Path
from unittest.mock import patch
import requests

from ska_sdp_proccontrol import processing_controller

LOG = logging.getLogger(__name__)

PC_DIR = Path(processing_controller.__file__).parent
TEST_DIR = Path(__file__).parent
SCHEMA = PC_DIR / 'schema' / 'workflows.json'
WORKFLOWS = TEST_DIR / 'data' / 'workflows.json'


def test_with_nonexistent_file():
    wf = processing_controller.Workflows('not_there.json')
    assert wf.version == {}


def test_with_non_json():
    wf = processing_controller.Workflows(PC_DIR / 'workflows.py')
    assert wf.version == {}


def test_with_bad_json():
    wf = processing_controller.Workflows(WORKFLOWS)
    assert wf.version == {}


def test_before_update():
    wf = processing_controller.Workflows(SCHEMA)
    assert wf.version == {}


@patch('requests.get')
def test_workflows_methods(mock_get):

    class Request:
        def __init__(self, ok: bool):
            self.ok = ok
            self.reason = 'none'
            with open(WORKFLOWS, 'r') as f:
                self.text = f.read()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    wf = processing_controller.Workflows(SCHEMA)
    wf.update_file(WORKFLOWS)
    assert wf.version['date-time'].startswith('20')

    # Non-existent has no effect.
    wf.update_file('not-there')
    assert wf.version['date-time'].startswith('20')

    mock_get.return_value = Request(True)
    wf.update_url('who-cares')
    assert wf.version['date-time'].startswith('20')

    mock_get.return_value = Request(False)
    wf.update_url('who-cares')
    assert wf.version['date-time'].startswith('20')

    rt = wf.batch('test_batch', '0.2.1')
    assert rt.startswith('nexus')
    rt = wf.batch('not_there', '0.2.1')
    assert rt is None

    rt = wf.realtime('test_realtime', '0.2.1')
    assert rt.startswith('nexus')
    rt = wf.realtime('not_there', '0.2.1')
    assert rt is None
