import os
import logging
from unittest.mock import patch

from ska_sdp_proccontrol import processing_controller

import ska_sdp_config
import workflows_test

LOG = logging.getLogger(__name__)

os.environ['SDP_CONFIG_BACKEND'] = 'memory'
os.environ['SDP_CONFIG_HOST'] = 'localhost'
os.environ['SDP_HELM_NAMESPACE'] = 'helm'


def test_stuff():
    controller = processing_controller.ProcessingController(workflows_test.SCHEMA,
                                                            workflows_test.WORKFLOWS, 1)

    # Annoyingly requests doesn't support local (file) URLs, so redirect. It is possible to
    # create an adapter for this, but that seems like overkill.
    controller._workflows.update_url = controller._workflows.update_file

    wf = {'type': 'batch', 'id':  'test_batch', 'version': '0.2.1'}
    pb = ska_sdp_config.ProcessingBlock(
        id='test',
        sbi_id='test',
        workflow=wf,
        parameters={},
        dependencies=[]
    )

    config = ska_sdp_config.Config()

    for txn in config.txn():
        assert controller._get_pb_status(txn, "test") is None
        txn.create_processing_block(pb)

    controller.main_loop()

    for txn in config.txn():
        deployment_ids = txn.list_deployments()

    LOG.info(deployment_ids)
    assert 'proc-test-workflow' in deployment_ids


@patch('signal.signal')
@patch('sys.exit')
def test_main(mock_exit, mock_signal):
    processing_controller.main(backend='memory')
    processing_controller.terminate(None, None)
