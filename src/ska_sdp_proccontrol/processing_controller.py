"""
Main processing controller class which contains the event loop.
"""
import logging
import os
import re
import signal
import sys

import ska_sdp_config
from ska.logging import configure_logging

LOG_LEVEL = os.getenv("SDP_LOG_LEVEL", "DEBUG")

LOG = logging.getLogger(__name__)

# Regular expression to match processing block ID as substring
_RE_PB = "pb(-[0-9a-zA-Z]*){3}"

# Compiled regular expression to match processing deployments associated with
# a processing block
_RE_DEPLOY_PROC_ANY = re.compile("^proc-(?P<pb_id>{}).*$".format(_RE_PB))


class ProcessingController:
    """
    Processing controller.
    """

    # pylint: disable=invalid-name, too-few-public-methods

    def __init__(self):
        pass

    @staticmethod
    def _get_pb_status(txn, pb_id: str) -> str:
        """
        Get status of processing block.

        :param txn: config DB transaction
        :param pb_id: processing block ID
        :returns: processing block status

        """
        state = txn.get_processing_block_state(pb_id)
        if state is None:
            status = None
        else:
            status = state.get("status")
        return status

    def _start_new_pb_workflows(self, watcher, pb_ids):
        """
        Start the workflows for new processing blocks.

        :param watcher: config DB watcher object (Config.watcher())
        :param pb_ids: list of processing block ids
        """
        for pb_id in pb_ids:
            for txn in watcher.txn():
                if txn.get_processing_block(pb_id) is None:
                    continue

                state = txn.get_processing_block_state(pb_id)
                if state is None:
                    self._start_workflow(txn, pb_id)

    @staticmethod
    def _start_workflow(txn, pb_id):
        """
        Start the workflow for a processing block.

        :param txn: config DB transaction
        :param pb_id: processing block ID

        """
        LOG.info("Making deployment for processing block %s", pb_id)

        # Read the processing block
        pb = txn.get_processing_block(pb_id)

        # Get workflow type, id and version
        wf_type = pb.workflow["type"]
        wf_id = pb.workflow["id"]
        wf_version = pb.workflow["version"]
        wf_description = "{} workflow {}, version {}".format(wf_type, wf_id, wf_version)

        # Get the container image for the workflow
        workflow = txn.get_workflow(wf_type, wf_id, wf_version)
        if workflow is None:
            wf_image = None
        else:
            wf_image = workflow.get("image")

        if wf_image is not None:
            # Make the deployment
            LOG.info("Deploying %s", wf_description)
            deploy_id = "proc-{}-workflow".format(pb_id)
            values = {}
            values["env"] = {}
            for v in ["SDP_CONFIG_HOST", "SDP_HELM_NAMESPACE"]:
                values["env"][v] = os.environ[v]
            values["wf_image"] = wf_image
            values["pb_id"] = pb_id
            chart = {"chart": "workflow", "values": values}
            deploy = ska_sdp_config.Deployment(deploy_id, "helm", chart)
            txn.create_deployment(deploy)
            # Set status to STARTING, and resources_available to False
            state = {"status": "STARTING", "resources_available": False}
        else:
            # Invalid workflow, so set status to FAILED
            state = {"status": "FAILED", "reason": "No image for " + wf_description}

        # Create the processing block state.
        txn.create_processing_block_state(pb_id, state)

    def _release_pbs_with_finished_dependencies(self, watcher, pb_ids):
        """
        Release processing blocks whose dependencies are all finished.

        :param watcher: config DB watcher object (Config.watcher())
        :param pb_ids: list of processing block ids
        """
        for pb_id in pb_ids:
            for txn in watcher.txn():
                if txn.get_processing_block(pb_id) is None:
                    continue

                state = txn.get_processing_block_state(pb_id)
                if state is None:
                    status = None
                    ra = None
                else:
                    status = state.get("status")
                    ra = state.get("resources_available")
                if status == "WAITING" and not ra:
                    # Check status of dependencies.
                    pb = txn.get_processing_block(pb_id)
                    dep_finished = all(
                        self._get_pb_status(txn, dep["pb_id"]) == "FINISHED"
                        for dep in pb.dependencies
                    )
                    if dep_finished:
                        LOG.info("Releasing processing block %s", pb_id)
                        state["resources_available"] = True
                        txn.update_processing_block_state(pb_id, state)

    @staticmethod
    def _delete_deployments_without_pb(watcher, pb_ids, deploy_ids):
        """
        Delete processing deployments not associated with a processing block.

        :param watcher: config DB watcher object (Config.watcher())
        :param pb_ids: list of processing block ids
        :param deploy_ids: list of deployment ids
        """
        for deploy_id in deploy_ids:
            for txn in watcher.txn():
                if txn.get_deployment(deploy_id) is None:
                    continue

                match = _RE_DEPLOY_PROC_ANY.match(deploy_id)
                if match is not None:
                    pb_id = match.group("pb_id")
                    if (pb_id not in pb_ids) or (
                        pb_id in pb_ids and txn.get_processing_block(pb_id) is None
                    ):
                        LOG.info("Deleting deployment %s", deploy_id)
                        deploy = txn.get_deployment(deploy_id)
                        txn.delete_deployment(deploy)

    def main_loop(self, backend=None):
        """
        Main event loop, executing three processes on a transaction,
        performing actions depending on the transaction state.

        :param backend: config DB backend to use

        """
        # Connect to config DB
        LOG.info("Connecting to config DB")
        config = ska_sdp_config.Config(backend=backend)

        LOG.info("Starting main loop")
        for watcher in config.watcher():

            # List processing blocks and deployments
            for txn in watcher.txn():
                pb_ids = txn.list_processing_blocks()
                deploy_ids = txn.list_deployments()
                LOG.info("processing block ids %s", pb_ids)

            # Perform actions.
            self._start_new_pb_workflows(watcher, pb_ids)
            self._release_pbs_with_finished_dependencies(watcher, pb_ids)
            self._delete_deployments_without_pb(watcher, pb_ids, deploy_ids)


def terminate(_signame, _frame):
    """Terminate the program."""
    LOG.info("Asked to terminate")
    # Note that this will likely send SIGKILL to child processes -
    # not exactly how this is supposed to work. But all of this is
    # temporary anyway.
    sys.exit(0)


def main(backend=None):
    """
    Start the processing controller.

    :param backend: config DB backend

    """
    configure_logging(level=LOG_LEVEL)

    # Register SIGTERM handler
    signal.signal(signal.SIGTERM, terminate)

    # Initialise processing controller
    proccontrol = ProcessingController()

    # Enter main loop
    proccontrol.main_loop(backend=backend)


# Replaced __main__.py with this construct to simplify testing.
if __name__ == "__main__":
    main()
